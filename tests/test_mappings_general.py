import unittest

from tests import _bootstrap  # noqa: F401
from tmdbhelper.lib.items.database.mappings.general import GeneralMapperMethods


class GeneralMapperMethodsTest(unittest.TestCase):
    def test_get_runtime_converts_minutes_to_seconds(self):
        self.assertEqual(GeneralMapperMethods.get_runtime(90), 5400)

    def test_get_runtime_handles_list_input(self):
        self.assertEqual(GeneralMapperMethods.get_runtime([45]), 2700)

    def test_get_runtime_returns_zero_on_invalid_input(self):
        self.assertEqual(GeneralMapperMethods.get_runtime(None), 0)

    def test_get_configured_item_maps_simple_keys(self):
        result = GeneralMapperMethods.get_configured_item({'a': 1, 'b': 2}, x='a', y='b')
        self.assertEqual(result, {'x': 1, 'y': 2})

    def test_get_configured_item_supports_callables(self):
        result = GeneralMapperMethods.get_configured_item({'a': 5}, doubled=lambda i: i['a'] * 2)
        self.assertEqual(result, {'doubled': 10})

    def test_get_configured_item_drops_blanks_when_requested(self):
        result = GeneralMapperMethods.get_configured_item({'a': None}, x='a', blanks=False)
        self.assertEqual(result, {})

    def test_split_array_maps_list_of_dicts(self):
        result = GeneralMapperMethods.split_array([{'a': 1}, {'a': 2}], name='a')
        self.assertEqual(result, [{'name': 1}, {'name': 2}])

    def test_split_array_returns_empty_for_falsy_input(self):
        self.assertEqual(GeneralMapperMethods.split_array(None), [])

    def test_split_array_filters_missing_haskeys(self):
        result = GeneralMapperMethods.split_array([{'a': 1}, {'b': 2}], haskeys=('a',), name='a')
        self.assertEqual(result, [{'name': 1}])

    def test_get_custom_time_formats_duration(self):
        result = GeneralMapperMethods.get_custom_time(3725)  # 1h 2m 5s
        self.assertEqual(result['duration.H'], 1)
        self.assertEqual(result['duration.M'], 2)
        self.assertEqual(result['duration.HHMM'], '01:02')

    def test_get_custom_time_returns_empty_dict_for_falsy_duration(self):
        self.assertEqual(GeneralMapperMethods.get_custom_time(0), {})

    def test_get_custom_property_wraps_key_value(self):
        result = GeneralMapperMethods.get_custom_property('budget', '$1,000')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].base, 'custom')
        self.assertEqual(result[0].data, {'key': 'budget', 'value': '$1,000'})

    def test_get_unique_ids_maps_id_fields(self):
        result = GeneralMapperMethods.get_unique_ids({'id': 550, 'imdb_id': 'tt0137523'})
        self.assertIn({'key': 'tmdb', 'value': '550'}, result)
        self.assertIn({'key': 'imdb', 'value': 'tt0137523'}, result)

    def test_get_unique_ids_returns_none_for_empty_input(self):
        self.assertIsNone(GeneralMapperMethods.get_unique_ids(None))

    def test_get_video_filters_to_youtube(self):
        items = {'results': [
            {'site': 'YouTube', 'name': 'Trailer', 'iso_3166_1': 'US', 'iso_639_1': 'en',
             'published_at': '2024-01-01', 'key': 'abc123', 'type': 'Trailer'},
            {'site': 'Vimeo', 'name': 'Other', 'iso_3166_1': 'US', 'iso_639_1': 'en',
             'published_at': '2024-01-01', 'key': 'xyz', 'type': 'Clip'},
        ]}
        result = GeneralMapperMethods.get_video(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['key'], 'abc123')
        self.assertEqual(result[0]['path'], 'plugin://plugin.video.youtube/play/?video_id=abc123')

    def test_get_media_item_data_builds_movie_entry(self):
        class FakeGeneral(GeneralMapperMethods):
            tmdb_id = 550
            language = 'en'

            def get_genre_items(self, genre_ids):
                # Stand-in for GenreMapperMethods.get_genre_items (added in Task 5) -
                # this test only verifies GeneralMapperMethods' own logic.
                return [{'name': 'Action', 'tmdb_id': g} for g in genre_ids]

        fake = FakeGeneral()
        result = fake.get_media_item_data({
            'id': 550, 'title': 'Fight Club', 'release_date': '1999-10-15',
            'overview': 'plot', 'vote_average': 8.4, 'vote_count': 100,
            'popularity': 50.0, 'genre_ids': [28], 'poster_path': None, 'backdrop_path': None,
        }, 'movie')
        movie_entry = next(i for i in result if i.base == 'movie')
        self.assertEqual(movie_entry.data['title'], 'Fight Club')
        self.assertEqual(movie_entry.data['year'], 1999)
        self.assertEqual(movie_entry.unique_id, 'movie.550')
        genre_entry = next(i for i in result if i.base == 'genre')
        self.assertEqual(genre_entry.data['name'], 'Action')


if __name__ == '__main__':
    unittest.main()
