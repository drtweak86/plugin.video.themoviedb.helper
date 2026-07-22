import unittest

from tests import _bootstrap  # noqa: F401
from tmdbhelper.lib.items.database.mappings import ItemMapperMethods


class SmokeTest(unittest.TestCase):
    def test_get_runtime_converts_minutes_to_seconds(self):
        self.assertEqual(ItemMapperMethods.get_runtime(90), 5400)


if __name__ == '__main__':
    unittest.main()
