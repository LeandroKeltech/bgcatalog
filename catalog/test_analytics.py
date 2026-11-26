"""Check tracking inclusion and exclusion without a database or remote calls."""
from django.contrib.auth.models import AnonymousUser, User
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings


@override_settings(
    DEBUG=False,
    CLARITY_PROJECT_ID='testproject123',
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class ClarityTests(SimpleTestCase):
    def render_page(self, user=None, **context):
        request = RequestFactory().get('/')
        request.user = user if user is not None else AnonymousUser()
        request.session = {}
        return render_to_string('catalog/base.html', context, request=request)

    def test_public_page_loads_async_tracking_with_denied_cookie_storage(self):
        html = self.render_page()
        self.assertIn('https://www.clarity.ms/tag/', html)
        self.assertIn('"testproject123"', html)
        self.assertIn('t.async=1', html)
        self.assertIn("ad_Storage: 'denied', analytics_Storage: 'denied'", html)
        self.assertLess(html.index('https://www.clarity.ms/tag/'), html.index('</head>'))

    @override_settings(CLARITY_PROJECT_ID='')
    def test_unconfigured_site_does_not_load_tracking(self):
        self.assertNotIn('clarity.ms', self.render_page())

    @override_settings(DEBUG=True)
    def test_local_development_does_not_load_tracking(self):
        self.assertNotIn('clarity.ms', self.render_page())

    def test_staff_does_not_load_tracking(self):
        # An inactive, unsaved account needs no database group lookup.
        staff = User(is_staff=True, is_active=False)
        self.assertNotIn('clarity.ms', self.render_page(user=staff))

    def test_admin_group_does_not_load_tracking(self):
        self.assertNotIn('clarity.ms', self.render_page(can_access_admin=True))

    @override_settings(CLARITY_PROJECT_ID='</script><script>alert("x")</script>')
    def test_project_id_cannot_inject_markup(self):
        html = self.render_page()
        self.assertNotIn('</script><script>alert', html)
        self.assertIn(r'\u003C/script\u003E', html)
