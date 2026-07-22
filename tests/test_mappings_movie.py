import unittest

from tests import _bootstrap  # noqa: F401
from tmdbhelper.lib.items.database.mappings.movie import MovieMapperMethods
from tmdbhelper.lib.items.database.mappings.general import GeneralMapperMethods


class FakeMovie(MovieMapperMethods, GeneralMapperMethods):
    tmdb_id = 550
    language = 'en'

    def get_genre_items(self, genre_ids):
        return []


def make_part(tmdb_id, title):
    return {
        'id': tmdb_id, 'title': title, 'release_date': '2001-01-01', 'overview': 'p',
        'vote_average': 7, 'vote_count': 5, 'popularity': 10, 'genre_ids': [],
        'poster_path': None, 'backdrop_path': None,
    }


class MovieMapperMethodsTest(unittest.TestCase):
    def test_get_belongs_to_collection_builds_collection_and_belongs_entries(self):
        fake = FakeMovie()
        result = fake.get_belongs_to_collection({'id': 10, 'name': 'Test Collection', 'poster_path': None, 'backdrop_path': None})
        collection_entry = next(i for i in result if i.base == 'collection')
        self.assertEqual(collection_entry.data['title'], 'Test Collection')
        belongs_entry = next(i for i in result if i.base == 'belongs')
        self.assertEqual(belongs_entry.unique_id, 'movie.550')
        self.assertEqual(belongs_entry.data['parent_id'], 'collection.10')

    def test_get_collection_maps_each_part_and_links_to_collection(self):
        fake = FakeMovie()
        result = fake.get_collection({'id': 10, 'parts': [make_part(551, 'Part 2')]})
        movie_entry = next(i for i in result if i.base == 'movie')
        self.assertEqual(movie_entry.data['title'], 'Part 2')
        belongs_entry = next(i for i in result if i.base == 'belongs')
        self.assertEqual(belongs_entry.unique_id, 'movie.551')
        self.assertEqual(belongs_entry.data['parent_id'], 'collection.10')

    def test_get_collection_returns_empty_list_for_falsy_input(self):
        fake = FakeMovie()
        self.assertEqual(fake.get_collection(None), [])

    def test_get_parts_uses_self_tmdb_id_as_collection_id(self):
        fake = FakeMovie()
        result = fake.get_parts([make_part(552, 'Part 3')])
        belongs_entry = next(i for i in result if i.base == 'belongs')
        self.assertEqual(belongs_entry.data['parent_id'], 'collection.550')  # fake.tmdb_id, not the part's id


if __name__ == '__main__':
    unittest.main()
