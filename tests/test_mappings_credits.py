import unittest

from tests import _bootstrap  # noqa: F401
from tmdbhelper.lib.items.database.mappings.credits import CreditsMapperMethods
from tmdbhelper.lib.items.database.mappings.general import GeneralMapperMethods


class FakeCredits(CreditsMapperMethods, GeneralMapperMethods):
    tmdb_id = 550
    language = 'en'

    def get_genre_items(self, genre_ids):
        return []


class CreditsMapperMethodsTest(unittest.TestCase):
    def test_get_credits_maps_cast_and_crew(self):
        fake = FakeCredits()
        credits_data = {
            'cast': [{'id': 1, 'name': 'Actor', 'gender': 2, 'order': 0, 'character': 'Hero', 'credit_id': 'c1'}],
            'crew': [],
        }
        result = fake.get_credits(credits_data)
        cast_entry = next(i for i in result if i.base == 'castmember')
        self.assertEqual(cast_entry.data['role'], 'Hero')
        self.assertEqual(cast_entry.unique_id, 'c1')
        person_entry = next(i for i in result if i.base == 'person')
        self.assertEqual(person_entry.data['name'], 'Actor')

    def test_get_person_movie_credits_data_builds_movie_and_castmember_entries(self):
        fake = FakeCredits()
        person_credits = {
            'cast': [{
                'id': 550, 'title': 'Fight Club', 'release_date': '1999-10-15', 'overview': 'plot',
                'vote_average': 8.4, 'vote_count': 100, 'popularity': 50.0, 'genre_ids': [],
                'poster_path': None, 'backdrop_path': None, 'character': 'Narrator', 'order': 0,
                'credit_id': 'c1',
            }],
            'crew': [],
        }
        result = fake.get_person_movie_credits_data(person_credits)
        movie_entry = next(i for i in result if i.base == 'movie')
        self.assertEqual(movie_entry.data['title'], 'Fight Club')
        cast_entry = next(i for i in result if i.base == 'castmember')
        self.assertEqual(cast_entry.data['role'], 'Narrator')
        self.assertEqual(cast_entry.data['parent_id'], 'movie.550')
        self.assertEqual(cast_entry.data['tmdb_id'], 550)  # the person's own tmdb_id, not the movie's

    def test_get_person_tv_credits_data_uses_tv_type(self):
        fake = FakeCredits()
        person_credits = {
            'cast': [{
                'id': 1396, 'name': 'Breaking Bad', 'first_air_date': '2008-01-20', 'overview': 'plot',
                'vote_average': 9.0, 'vote_count': 200, 'popularity': 80.0, 'genre_ids': [],
                'poster_path': None, 'backdrop_path': None, 'character': 'Chemist', 'order': 0,
                'credit_id': 'c2',
            }],
            'crew': [],
        }
        result = fake.get_person_tv_credits_data(person_credits)
        tvshow_entry = next(i for i in result if i.base == 'tvshow')
        self.assertEqual(tvshow_entry.data['title'], 'Breaking Bad')
        cast_entry = next(i for i in result if i.base == 'castmember')
        self.assertEqual(cast_entry.data['parent_id'], 'tv.1396')


if __name__ == '__main__':
    unittest.main()
