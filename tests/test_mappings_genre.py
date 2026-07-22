import unittest

from tests import _bootstrap  # noqa: F401
from tmdbhelper.lib.items.database.mappings.genre import GenreMapperMethods


class GenreMapperMethodsTest(unittest.TestCase):
    def test_get_genre_items_maps_known_ids(self):
        class FakeGenre(GenreMapperMethods):
            genres_map = {28: 'Action', 12: 'Adventure'}

        result = FakeGenre().get_genre_items([28, 12])
        self.assertEqual(result, [{'name': 'Action', 'tmdb_id': 28}, {'name': 'Adventure', 'tmdb_id': 12}])

    def test_get_genre_items_skips_unknown_ids(self):
        class FakeGenre(GenreMapperMethods):
            genres_map = {28: 'Action'}

        result = FakeGenre().get_genre_items([28, 999])
        self.assertEqual(result, [{'name': 'Action', 'tmdb_id': 28}])

    def test_get_genre_items_returns_empty_list_for_no_ids(self):
        class FakeGenre(GenreMapperMethods):
            genres_map = {}

        self.assertEqual(FakeGenre().get_genre_items([]), [])

    def test_get_genres_maps_list_of_genre_dicts(self):
        class FakeGenre(GenreMapperMethods):
            genres_map = {28: 'Action'}

        result = FakeGenre().get_genres([{'id': 28}])
        self.assertEqual(result, [{'name': 'Action', 'tmdb_id': 28}])


if __name__ == '__main__':
    unittest.main()
