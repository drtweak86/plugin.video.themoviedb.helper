import unittest

from tests import _bootstrap  # noqa: F401
from tmdbhelper.lib.items.database.mappings.tv import TVMapperMethods


class FakeTV(TVMapperMethods):
    tmdb_id = 550
    language = 'en'
    data = {}
    item = {'item': {}}

    def get_runtime(self, i, *args, **kwargs):
        if isinstance(i, list):
            i = i[0]
        try:
            return int(i) * 60
        except (TypeError, ValueError):
            return 0


class TVMapperMethodsTest(unittest.TestCase):
    def test_get_episode_type_flags_specials(self):
        self.assertEqual(
            TVMapperMethods.get_episode_type({'episode_type': 'standard', 'season_number': 0, 'episode_number': 3}),
            'special')

    def test_get_episode_type_flags_series_premiere(self):
        self.assertEqual(
            TVMapperMethods.get_episode_type({'episode_type': 'standard', 'season_number': 1, 'episode_number': 1}),
            'series_premiere')

    def test_get_episode_type_flags_standard(self):
        self.assertEqual(
            TVMapperMethods.get_episode_type({'episode_type': 'standard', 'season_number': 1, 'episode_number': 3}),
            'standard')

    def test_get_episodes_builds_episode_entries(self):
        fake = FakeTV()
        result = fake.get_episodes([{
            'season_number': 1, 'episode_number': 1, 'episode_type': 'standard', 'air_date': '2020-01-01',
            'name': 'Ep1', 'overview': 'desc', 'vote_average': 7.0, 'vote_count': 5, 'runtime': 42,
            'still_path': None,
        }])
        episode_entry = next(i for i in result if i.base == 'episode')
        self.assertEqual(episode_entry.unique_id, 'tv.550.1.1')
        self.assertEqual(episode_entry.data['title'], 'Ep1')
        self.assertEqual(episode_entry.data['duration'], 2520)

    def test_get_seasons_builds_season_entries(self):
        fake = FakeTV()
        result = fake.get_seasons([{
            'season_number': 1, 'air_date': '2020-01-01', 'name': 'Season 1',
            'overview': 'desc', 'vote_average': 7.5, 'poster_path': None,
        }])
        season_entry = next(i for i in result if i.base == 'season')
        self.assertEqual(season_entry.unique_id, 'tv.550.1')
        self.assertEqual(season_entry.data['title'], 'Season 1')

    def test_get_creators_builds_crewmember_and_person_entries(self):
        fake = FakeTV()
        result = fake.get_creators([{'id': 100, 'name': 'Creator Name', 'gender': 1, 'profile_path': None}])
        crew_entry = next(i for i in result if i.base == 'crewmember')
        self.assertEqual(crew_entry.data['role'], 'Creator')
        person_entry = next(i for i in result if i.base == 'person')
        self.assertEqual(person_entry.data['name'], 'Creator Name')

    def test_get_episode_to_air_marks_series_finale_when_show_ended(self):
        fake = FakeTV()
        fake.data = {'in_production': False, 'next_episode_to_air': None}
        fake.item = {'item': {}}
        result = fake.get_episode_to_air({
            'season_number': 3, 'episode_number': 10, 'episode_type': 'finale', 'air_date': '2024-01-15',
            'name': 'Finale', 'overview': 'desc', 'vote_average': 8.0, 'vote_count': 20, 'runtime': 50,
            'still_path': None,
        })
        episode_entry = next(i for i in result if i.base == 'episode')
        self.assertEqual(episode_entry.data['status'], 'series_finale')

    def test_get_episode_to_air_updates_item_duration(self):
        fake = FakeTV()
        fake.data = {'in_production': True, 'next_episode_to_air': {'id': 1}}
        fake.item = {'item': {}}
        fake.get_episode_to_air({
            'season_number': 1, 'episode_number': 5, 'episode_type': 'standard', 'air_date': '2024-01-15',
            'name': 'Ep5', 'overview': 'desc', 'vote_average': 7.0, 'vote_count': 10, 'runtime': 45,
            'still_path': None,
        })
        self.assertEqual(fake.item['item']['duration'], 2700)


if __name__ == '__main__':
    unittest.main()
