import unittest

from tests import _bootstrap  # noqa: F401
from tmdbhelper.lib.items.database.mappings.support import (
    ExtendedMap, get_blanks_none, FTV_WITHOUT_SEASONS, FTV_TVSHOWS_SEASONS, FTV_SEASONS_SEASONS,
)


class SupportTest(unittest.TestCase):
    def test_get_blanks_none_converts_empty_string_to_none(self):
        self.assertIsNone(get_blanks_none(''))

    def test_get_blanks_none_preserves_zero(self):
        self.assertEqual(get_blanks_none(0), 0)

    def test_get_blanks_none_preserves_truthy_value(self):
        self.assertEqual(get_blanks_none('hello'), 'hello')

    def test_get_blanks_none_converts_none_to_none(self):
        self.assertIsNone(get_blanks_none(None))

    def test_extended_map_has_expected_fields(self):
        m = ExtendedMap('movie', 'movie.550', False, {'title': 'Fight Club'})
        self.assertEqual(m.base, 'movie')
        self.assertEqual(m.unique_id, 'movie.550')
        self.assertFalse(m.overwrite)
        self.assertEqual(m.data, {'title': 'Fight Club'})

    def test_ftv_season_constants(self):
        self.assertEqual(FTV_WITHOUT_SEASONS, 0)
        self.assertEqual(FTV_TVSHOWS_SEASONS, 1)
        self.assertEqual(FTV_SEASONS_SEASONS, 2)


if __name__ == '__main__':
    unittest.main()
