from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import AdminReservationNotification, BoardGame, CustomerProfile, CustomerQuote, StockReservation
from .notifications import create_reservation_notification, email_alerts_ready, send_reservation_alert


@override_settings(
    WHATSAPP_SHOP_NUMBER='+353891234567', RESERVATION_NOTIFICATION_EMAIL='owner@example.com',
    DEFAULT_FROM_EMAIL='shop@example.com', EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}},
)
class ReservationNotificationTests(TestCase):
    def setUp(self):
        self.customer = get_user_model().objects.create_user(username='buyer@example.com', email='buyer@example.com')
        CustomerProfile.objects.create(user=self.customer, full_name='Example Buyer', phone='+353891234568')
        self.admin = get_user_model().objects.create_user(username='owner')
        self.admin.groups.add(Group.objects.get(name='admin'))
        self.other_admin = get_user_model().objects.create_user(username='partner')
        self.other_admin.groups.add(Group.objects.get(name='admin'))
        self.game = BoardGame.objects.create(name='Test game', sale_price=20, stock_quantity=3)
        self.client.force_login(self.customer)
        session = self.client.session
        session['cart'] = {str(self.game.pk): 2}
        session.save()

    def reserve(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('checkout'))
        self.assertRedirects(response, reverse('checkout_success'))
        return AdminReservationNotification.objects.get()

    def test_notification_and_email_created_without_whatsapp_or_success_page_visit(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('checkout'))
        self.assertEqual(response.status_code, 302)
        notification = AdminReservationNotification.objects.get()
        self.assertEqual(notification.quote.reservations.count(), 1)
        self.assertEqual(notification.email_status, 'sent')
        self.assertEqual(mail.outbox[0].to, ['owner@example.com'])
        self.assertEqual(mail.outbox[1].to, ['buyer@example.com'])
        self.assertIn('SHOP NOTIFICATION', mail.outbox[0].alternatives[0].content)
        for text in (str(notification.quote_id), 'Example Buyer', '2 × Test game', 'Total: €40.00',
                     'independent of whether they send the WhatsApp message'):
            self.assertIn(text, mail.outbox[0].body)
        self.assertEqual(self.client.session['cart'], {})
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('checkout'))
        self.assertEqual(AdminReservationNotification.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 2)

    def test_rollback_discards_notification_and_email_callback(self):
        def fail_after_alert(quote):
            create_reservation_notification(quote)
            raise RuntimeError('Simulated rollback')
        with patch('catalog.cart_views.create_reservation_notification', side_effect=fail_after_alert):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(reverse('checkout'))
        self.assertRedirects(response, reverse('view_cart'))
        self.assertFalse(AdminReservationNotification.objects.exists())
        self.assertFalse(CustomerQuote.objects.exists())
        self.assertFalse(StockReservation.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_unavailable_stock_does_not_notify(self):
        BoardGame.objects.filter(pk=self.game.pk).update(stock_quantity=0)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('checkout'))
        self.assertFalse(AdminReservationNotification.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_email_failure_preserves_reservation_and_retry_does_not_duplicate(self):
        with patch('catalog.notifications.send_mail', side_effect=OSError('SMTP unavailable')):
            notification = self.reserve()
        self.assertEqual(notification.email_status, 'failed')
        self.assertEqual(self.game.available_quantity, 1)
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.post(reverse('notification_retry_email', args=[notification.pk])), reverse('notification_list'))
        notification.refresh_from_db()
        self.assertEqual(notification.email_status, 'sent')
        self.assertIsNotNone(notification.email_sent_at)
        self.assertFalse(send_reservation_alert(notification.pk))
        call_command('send_reservation_alerts', verbosity=0)
        self.assertEqual(len(mail.outbox), 2)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_console_is_setup_required_and_never_claims_email_delivered(self):
        with patch('catalog.notifications.send_mail') as send:
            notification = self.reserve()
        send.assert_not_called()
        self.assertEqual(notification.email_status, 'not_configured')
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('notification_list')), 'Email delivery needs setup')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
                       EMAIL_HOST='smtp.gmail.com', EMAIL_HOST_USER='owner@example.com', EMAIL_HOST_PASSWORD='')
    def test_missing_smtp_password_does_not_attempt_a_connection(self):
        self.assertFalse(email_alerts_ready())
        with patch('catalog.notifications.send_mail') as send:
            notification = self.reserve()
        send.assert_not_called()
        self.assertEqual(notification.email_status, 'not_configured')

    def test_read_receipts_are_per_admin_and_opening_does_not_change_reservation(self):
        notification = self.reserve()
        self.client.force_login(self.admin)
        response = self.client.get(reverse('notification_status'), {'after': 0})
        self.assertEqual(response.json(), {'unread_count': 1, 'new_count': 1, 'latest_id': notification.pk})
        self.assertContains(self.client.get(reverse('notification_list')), 'Unread')
        response = self.client.post(reverse('notification_open', args=[notification.pk]))
        expected = reverse('reservation_management') + '?' + urlencode({'quote': notification.quote_id, 'status': ''})
        self.assertRedirects(response, expected)
        self.assertEqual(self.client.get(reverse('notification_status')).json()['unread_count'], 0)
        self.assertEqual(notification.quote.reservations.get().status, 'active')
        self.client.force_login(self.other_admin)
        self.assertEqual(self.client.get(reverse('notification_status')).json()['unread_count'], 1)
        # Alert survives expiry so unreviewed reservations remain visible to the shop.
        StockReservation.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertContains(self.client.get(reverse('notification_list')), 'Expired')

    def test_new_alert_poll_cursor_and_private_access(self):
        notification = self.reserve()
        for route, args in [('notification_status', []), ('notification_list', []),
                            ('notification_open', [notification.pk]), ('notification_retry_email', [notification.pk]),
                            ('notification_dismiss', [notification.pk])]:
            self.assertEqual(self.client.get(reverse(route, args=args)).status_code, 403)
        self.client.force_login(self.admin)
        status_url = reverse('notification_status')
        self.assertEqual(self.client.get(status_url, {'after': notification.pk}).json()['new_count'], 0)
        for value in ('bad', '-1', '9' * 50):
            self.assertEqual(self.client.get(status_url, {'after': value}).status_code, 400)
        response = self.client.get(status_url)
        self.assertNotContains(response, 'Example Buyer')
        self.assertIn('private', response.headers['Cache-Control'])
        self.assertEqual(self.client.get(reverse('notification_open', args=[notification.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse('notification_retry_email', args=[notification.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse('notification_dismiss', args=[notification.pk])).status_code, 405)

    def test_dismiss_hides_alert_only_for_current_admin_and_preserves_reservation(self):
        notification = self.reserve()
        self.client.force_login(self.admin)
        url = reverse('notification_dismiss', args=[notification.pk])
        self.assertContains(self.client.get(reverse('notification_list')), 'Dismiss notification')
        for _ in range(2):
            self.assertRedirects(self.client.post(url), reverse('notification_list'))
        self.assertEqual(list(self.client.get(reverse('notification_list')).context['notifications']), [])
        self.assertEqual(self.client.get(reverse('notification_status')).json(), {
            'unread_count': 0, 'new_count': 0, 'latest_id': notification.pk,
        })
        self.assertEqual(self.client.get(reverse('catalog')).context['reservation_unread_count'], 0)
        self.assertEqual(AdminReservationNotification.objects.count(), 1)
        self.assertEqual(notification.quote.reservations.get().status, 'active')
        self.assertEqual(self.game.available_quantity, 1)
        self.assertEqual(len(mail.outbox), 2)
        self.client.force_login(self.other_admin)
        self.assertContains(self.client.get(reverse('notification_list')), str(notification.quote_id))
        self.assertEqual(self.client.get(reverse('notification_status')).json()['unread_count'], 1)

    def test_dismiss_requires_admin_and_csrf_and_handles_missing_alert(self):
        notification = self.reserve()
        url = reverse('notification_dismiss', args=[notification.pk])
        self.assertEqual(self.client.post(url).status_code, 403)
        from django.test import Client
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin)
        self.assertEqual(csrf_client.post(url).status_code, 403)
        self.assertFalse(notification.dismissed_by.exists())
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(reverse('notification_dismiss', args=[notification.pk + 1])).status_code, 404)

    def test_quote_filter_and_admin_badge(self):
        notification = self.reserve()
        self.client.force_login(self.admin)
        response = self.client.get(reverse('catalog'))
        self.assertContains(response, 'reservation-notification-count')
        self.assertContains(response, 'reservation-notifications.js')
        url = reverse('reservation_management')
        self.assertEqual(len(self.client.get(url, {'quote': notification.quote_id}).context['reservations']), 1)
        self.assertEqual(len(self.client.get(url, {'quote': 'invalid'}).context['reservations']), 0)
        self.client.force_login(self.customer)
        self.assertNotContains(self.client.get(reverse('catalog')), 'reservation-notifications.js')
