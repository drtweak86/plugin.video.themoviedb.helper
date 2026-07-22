import unittest

from tests import _bootstrap  # noqa: F401
from tmdbhelper.lib.items.database.mappings.translations import TranslationMapperMethods


class TranslationMapperMethodsTest(unittest.TestCase):
    def test_get_providers_maps_flatrate_availability(self):
        items = {'results': {'US': {'flatrate': [
            {'provider_id': 8, 'provider_name': 'Netflix', 'logo_path': '/n.jpg', 'display_priority': 1},
        ]}}}
        result = TranslationMapperMethods.get_providers(items)
        self.assertEqual(result, [{'iso_country': 'US', 'availability': 'flatrate', 'tmdb_id': 8}])

    def test_get_providers_service_mode_maps_provider_details(self):
        items = {'results': {'US': {'flatrate': [
            {'provider_id': 8, 'provider_name': 'Netflix', 'logo_path': '/n.jpg', 'display_priority': 1},
        ]}}}
        result = TranslationMapperMethods.get_providers(items, service=True)
        self.assertEqual(result, [{'display_priority': 1, 'name': 'Netflix', 'logo': '/n.jpg', 'tmdb_id': 8}])

    def test_get_providers_returns_none_for_falsy_input(self):
        self.assertIsNone(TranslationMapperMethods.get_providers(None))

    def test_get_translations_maps_title_and_plot(self):
        items = {'translations': [{
            'iso_3166_1': 'US', 'iso_639_1': 'en',
            'data': {'title': 'Fight Club', 'overview': 'A plot', 'tagline': 'Tag'},
        }]}
        result = TranslationMapperMethods.get_translations(items)
        self.assertEqual(result, [{
            'iso_country': 'US', 'iso_language': 'en', 'title': 'Fight Club', 'plot': 'A plot', 'tagline': 'Tag',
        }])

    def test_get_certifications_maps_release_dates(self):
        items = {'results': [{'iso_3166_1': 'US', 'release_dates': [
            {'certification': 'R', 'iso_639_1': 'en', 'release_date': '1999-10-15', 'type': 3},
        ]}]}
        result = TranslationMapperMethods.get_certifications(items)
        self.assertEqual(result, [{
            'name': 'R', 'iso_country': 'US', 'iso_language': 'en',
            'release_date': '1999-10-15', 'release_type': 'Theatrical',
        }])

    def test_get_certifications_returns_none_for_falsy_input(self):
        self.assertIsNone(TranslationMapperMethods.get_certifications(None))


if __name__ == '__main__':
    unittest.main()
