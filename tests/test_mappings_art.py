import unittest

from tests import _bootstrap  # noqa: F401
from tmdbhelper.lib.items.database.mappings.art import ArtMapperMethods


class ArtMapperMethodsTest(unittest.TestCase):
    def test_add_art_type_builds_expected_dict(self):
        result = ArtMapperMethods.add_art_type('movie.550', '/poster.jpg', 'posters', 'poster')
        self.assertEqual(result['parent_id'], 'movie.550')
        self.assertEqual(result['icon'], '/poster.jpg')
        self.assertEqual(result['type'], 'posters')
        self.assertEqual(result['extension'], 'jpg')

    def test_get_aspect_ratio_classifies_landscape(self):
        from tmdbhelper.lib.addon.consts import IMAGEPATH_ASPECTRATIO
        self.assertEqual(ArtMapperMethods.get_aspect_ratio(1.78), IMAGEPATH_ASPECTRATIO.index('landscape'))

    def test_get_aspect_ratio_classifies_poster(self):
        from tmdbhelper.lib.addon.consts import IMAGEPATH_ASPECTRATIO
        self.assertEqual(ArtMapperMethods.get_aspect_ratio(0.67), IMAGEPATH_ASPECTRATIO.index('poster'))

    def test_get_art_builds_extended_map_entries(self):
        items = {'posters': [{
            'file_path': '/p1.jpg', 'aspect_ratio': 0.67, 'width': 1000, 'height': 1500,
            'iso_639_1': 'en', 'iso_3166_1': 'US', 'vote_average': 5.5, 'vote_count': 10,
        }]}
        result = ArtMapperMethods.get_art(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].base, 'art')
        self.assertEqual(result[0].data['type'], 'posters')
        self.assertEqual(result[0].data['rating'], 550)

    def test_get_art_returns_empty_list_for_falsy_input(self):
        self.assertEqual(ArtMapperMethods.get_art(None), [])

    def test_set_default_art_extends_data_for_each_present_path(self):
        data = []
        ArtMapperMethods.set_default_art(
            data, {'poster_path': '/p.jpg', 'backdrop_path': None, 'profile_path': None}, parent_id='movie.550')
        self.assertEqual(len(data), 2)  # default_art + art entries for the one present path
        self.assertEqual(data[0].data['type'], 'posters')

    def test_get_default_art_builds_default_art_and_art_entries(self):
        result = ArtMapperMethods.get_default_art('/p.jpg', 'posters', parent_id='movie.550')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].base, 'default_art')
        self.assertEqual(result[1].base, 'art')
        self.assertEqual(result[1].data['extension'], 'jpg')

    def test_get_fanart_tv_maps_movie_poster(self):
        items = {'movieposter': [{'url': 'http://example.com/p.jpg', 'lang': 'en', 'likes': '5'}]}
        result = ArtMapperMethods().get_fanart_tv(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].data['type'], 'poster')

    def test_get_fanart_tv_returns_none_for_falsy_input(self):
        self.assertIsNone(ArtMapperMethods().get_fanart_tv(None))


if __name__ == '__main__':
    unittest.main()
