import unittest

from tests import _bootstrap  # noqa: F401
from tmdbhelper.lib.items.database.mappings import ItemMapperMethods


EXPECTED_METHODS = (
    # General
    'get_runtime', 'get_configured_item', 'split_array', 'get_custom_time', 'get_custom_date',
    'get_custom_property', 'get_unique_ids', 'get_video', 'get_media_item_data',
    # Art
    'add_art_type', 'get_art', 'get_aspect_ratio', 'set_default_art', 'get_default_art', 'get_fanart_tv',
    # Genre
    'tmdb_database', 'genres_map', 'get_genre_items', 'get_genres',
    # Credits
    'get_credits', 'get_aggregate_credits', 'get_credits_data', 'get_person_movie_credits_data',
    'get_person_tv_credits_data', 'get_person_credits_data',
    # Translations
    'get_providers', 'get_translations', 'get_certifications',
    # Movie
    'get_belongs_to_collection', 'get_collection', 'get_parts',
    # TV
    'get_episode_type', 'get_episode_to_air', 'get_episodes', 'get_seasons', 'get_creators',
)


class ItemMapperMethodsAggregateTest(unittest.TestCase):
    def test_aggregate_has_every_original_method(self):
        for name in EXPECTED_METHODS:
            self.assertTrue(hasattr(ItemMapperMethods, name), f'ItemMapperMethods is missing {name}')

    def test_cross_mixin_call_chain_works_through_the_real_aggregate(self):
        # Exercises Movie -> General -> Genre in one call, through the actual
        # combined class - not a hand-built Fake like the per-mixin tests use.
        class RealMapper(ItemMapperMethods):
            tmdb_id = 550
            language = 'en'
            genres_map = {28: 'Action'}

        mapper = RealMapper()
        result = mapper.get_parts([{
            'id': 551, 'title': 'Part 2', 'release_date': '2001-01-01', 'overview': 'p',
            'vote_average': 7, 'vote_count': 5, 'popularity': 10, 'genre_ids': [28],
            'poster_path': None, 'backdrop_path': None,
        }])
        genre_entry = next(i for i in result if i.base == 'genre')
        self.assertEqual(genre_entry.data['name'], 'Action')
        belongs_entry = next(i for i in result if i.base == 'belongs')
        self.assertEqual(belongs_entry.data['parent_id'], 'collection.550')

    def test_item_mapper_import_unaffected(self):
        # ItemMapper itself must still import and construct exactly as before -
        # this is the "zero external API change" guarantee for this whole refactor.
        from tmdbhelper.lib.items.database.mappings import ItemMapper
        mapper = ItemMapper(language='en', tmdb_id=550)
        self.assertEqual(mapper.tmdb_id, 550)
        self.assertEqual(mapper.language, 'en')
        self.assertIn('genres', mapper.advanced_map)
        self.assertIn('belongs_to_collection', mapper.extended_map)


if __name__ == '__main__':
    unittest.main()
