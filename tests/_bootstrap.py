"""
Adds the paths needed to import tmdbhelper modules directly, without a
running Kodi instance. Most tmdbhelper/lib modules have zero xbmc/xbmcgui
imports at module level and can be exercised with plain unittest.

Every test file in this directory must start with:
    from tests import _bootstrap  # noqa: F401
before importing anything from tmdbhelper or jurialmunkey.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_JURIALMUNKEY_MODULES = Path('/home/frankie/.kodi/addons/script.module.jurialmunkey/resources/modules')

for _path in (_JURIALMUNKEY_MODULES, _REPO_ROOT / 'resources'):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)
