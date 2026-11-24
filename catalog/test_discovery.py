from django.test import TestCase, override_settings
from django.urls import reverse

from .models import BoardGame


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class DiscoveryFiltersTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.quick = BoardGame.objects.create(name='Quick pair', min_players=2, max_players=4,
                                              min_playtime=15, max_playtime=30, sale_price=15)
        cls.long = BoardGame.objects.create(name='Long pair', min_players=2, max_players=2,
                                             min_playtime=60, max_playtime=120, sale_price=40)
        cls.party = BoardGame.objects.create(name='Party', min_players=3, max_players=6,
                                              min_playtime=15, max_playtime=30, sale_price=15)
        cls.unknown = BoardGame.objects.create(name='Unknown')

    def test_player_range_includes_boundaries_and_excludes_unknown_metadata(self):
        response = self.client.get(reverse('catalog'), {'players': '2'})
        self.assertEqual(set(response.context['games']), {self.quick, self.long})
        response = self.client.get(reverse('catalog'), {'players': '4'})
        self.assertEqual(set(response.context['games']), {self.quick, self.party})

    def test_combined_filters_and_removal_links_preserve_other_selections(self):
        response = self.client.get(reverse('catalog'), {'players': '2', 'duration': '30', 'max_price': '20'})
        self.assertEqual(list(response.context['games']), [self.quick])
        self.assertContains(response, 'duration=30&amp;max_price=20')
        self.assertContains(response, 'players=2&amp;max_price=20')
        self.assertContains(response, 'value="30" selected')

    def test_invalid_or_extreme_gameplay_parameters_are_ignored(self):
        for value in ('abc', '-1', '999999999999999999999999', '0'):
            response = self.client.get(reverse('catalog'), {'players': value, 'duration': value})
            self.assertEqual(response.context['page_obj'].paginator.count, 4)
            self.assertEqual(response.context['players'], '')
            self.assertEqual(response.context['duration'], '')

    def test_empty_results_offer_a_reset(self):
        response = self.client.get(reverse('catalog'), {'search': 'no matching game'})
        self.assertContains(response, 'No games found this time')
        self.assertContains(response, 'Explore all games')
