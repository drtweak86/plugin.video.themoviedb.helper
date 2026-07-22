# Split ItemMapperMethods God-Class Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the 1059-line `ItemMapperMethods` class in `mappings.py` into 7 single-concern mixin classes plus a support module, recombined into a thin aggregate — zero behavior change, zero external API change — verified with real unit tests, not just syntax checks.

**Architecture:** New package `resources/tmdbhelper/lib/items/database/mappings/` holds one file per concern (`support.py`, `general.py`, `art.py`, `genre.py`, `credits.py`, `translations.py`, `movie.py`, `tv.py`). `resources/tmdbhelper/lib/items/database/mappings/__init__.py` shrinks to `BlankNoneDict` + a one-line `ItemMapperMethods` aggregate + the unchanged `ItemMapper` class. Every method moves verbatim; cross-mixin calls already go through `self.` or the literal `ItemMapperMethods.` class name, both of which resolve correctly through the aggregate's inherited MRO regardless of which mixin actually defines the method.

**Tech Stack:** Python 3, stdlib `unittest` (pytest is not installed on this machine — confirmed via `python3 -m pytest` → `ModuleNotFoundError`). Most of `mappings.py` has zero `xbmc`/`xbmcgui` imports at module level and was confirmed to import and run correctly in a plain Python process via `sys.path` manipulation — this is genuine TDD, not just `py_compile`.

## Global Constraints

- Spec source of truth: `docs/superpowers/specs/2026-07-22-mappings-split-design.md`.
- Branch: `refactor/tmdb-helper-cleanup` (already checked out, working tree clean at plan-writing time). Commit after every task.
- Zero behavior change, zero external API change. `ItemMapper.__init__`, `map_dict`, `get_empty_item`, `get_info` are never edited. No method is renamed — only relocated.
- The new `mappings/` package directory's `__init__.py` **is** the old `mappings.py` — Python cannot resolve a `mappings.py` module and a same-named sibling `mappings/` package directory at once (verified empirically: the `.py` file wins import resolution and the directory becomes entirely unreachable as a subpackage). The original spec assumed no `__init__.py` was needed, following the `baseitem_factories/concrete_classes/`-style implicit-namespace-package convention used elsewhere in this codebase — that assumption was wrong for this specific case, since `mappings.py` must keep existing as *something* importable at `tmdbhelper.lib.items.database.mappings` for `ItemMapper` to stay reachable at its unchanged path. `mappings/__init__.py` is that something. All mixin files (`support.py`, `general.py`, etc.) remain plain sibling modules with no `__init__.py` of their own — only the aggregate file needed the rename.
- Test runner: stdlib `unittest`, invoked as `python3 -m unittest discover -s tests -v` (or `python3 -m unittest tests.test_X -v` for one file) from the repo root `/home/frankie/GitHub/plugin.video.themoviedb.helper`.
- Every test file starts with `from tests import _bootstrap  # noqa: F401` (a shared module created in Task 1) before any `tmdbhelper` import — this sets up `sys.path` so `tmdbhelper.lib.*` and `jurialmunkey.*` resolve without a running Kodi instance. Verified working pattern — do not invent a different import-path trick.
- `get_custom_date` (moves to `general.py` in Task 3) has **no unit test** — it has a real, traced dependency on Kodi's region/locale formatting (`tmdbhelper.lib.addon.tmdate.get_region_date` calls a Kodi API that needs a real locale string back; stubbing `xbmc`/`xbmcaddon`/`xbmcgui`/`xbmcplugin`/`xbmcvfs` as `MagicMock()` still fails inside `strftime()`). This is unchanged, pre-existing behavior — not a new gap from this refactor. Verify with `py_compile` only, and note this explicitly in a code comment at the method.
- `tmdb_database` (moves to `genre.py` in Task 5) is a one-line property (`return FindQueriesDatabase()`) with no logic of its own — not worth a dedicated test. The real logic (`get_genre_items`/`get_genres`) gets real tests via a `genres_map` class-attribute override (see Task 5).
- Final verification command for every task: `python3 -m py_compile <every touched .py file>` plus the task's own `python3 -m unittest` run.

---

### Task 1: Test infrastructure

**Files:**
- Create: `tests/_bootstrap.py`
- Create: `tests/test_smoke.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `tests/_bootstrap.py`, imported by every later test file as `from tests import _bootstrap  # noqa: F401`. Importing it has the side effect of adding `/home/frankie/.kodi/addons/script.module.jurialmunkey/resources/modules` and `<repo_root>/resources` to `sys.path`.

- [ ] **Step 1: Create the bootstrap module**

Create `tests/_bootstrap.py`:

```python
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
```

- [ ] **Step 2: Write the smoke test**

Create `tests/test_smoke.py`:

```python
import unittest

from tests import _bootstrap  # noqa: F401
from tmdbhelper.lib.items.database.mappings import ItemMapperMethods


class SmokeTest(unittest.TestCase):
    def test_get_runtime_converts_minutes_to_seconds(self):
        self.assertEqual(ItemMapperMethods.get_runtime(90), 5400)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 3: Run it and verify it passes**

Run (from repo root `/home/frankie/GitHub/plugin.video.themoviedb.helper`): `python3 -m unittest discover -s tests -v`
Expected:
```
test_get_runtime_converts_minutes_to_seconds (tests.test_smoke.SmokeTest.test_get_runtime_converts_minutes_to_seconds) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.00Xs

OK
```

- [ ] **Step 4: Commit**

```bash
git add tests/_bootstrap.py tests/test_smoke.py
git commit -m "test: add unittest bootstrap for tmdbhelper without a running Kodi instance"
```

---

### Task 2: Extract `support.py`

**Files:**
- Create: `resources/tmdbhelper/lib/items/database/mappings/support.py`
- Create: `tests/test_mappings_support.py`
- Modify: `resources/tmdbhelper/lib/items/database/mappings/__init__.py:1-14` (remove what moved, replace with an import)

**Interfaces:**
- Consumes: nothing.
- Produces: `ExtendedMap` (namedtuple, fields `base unique_id overwrite data`), `get_blanks_none(i)` (function), `FTV_WITHOUT_SEASONS`/`FTV_TVSHOWS_SEASONS`/`FTV_SEASONS_SEASONS` (int constants: `0`/`1`/`2`) — all importable from `tmdbhelper.lib.items.database.mappings.support`. Every later task's mixin file does `from tmdbhelper.lib.items.database.mappings.support import ExtendedMap, get_blanks_none` (and the `FTV_*` constants where needed, in `art.py` only).

- [ ] **Step 1: Write the failing test**

Create `tests/test_mappings_support.py`:

```python
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_mappings_support -v`
Expected: `ModuleNotFoundError: No module named 'tmdbhelper.lib.items.database.mappings.support'`

- [ ] **Step 3: Create the support module**

Create `resources/tmdbhelper/lib/items/database/mappings/support.py`:

```python
from collections import namedtuple


ExtendedMap = namedtuple("ExtendedMap", "base unique_id overwrite data")


# Consts for wrangling FTV artwork into shape
FTV_WITHOUT_SEASONS = 0
FTV_TVSHOWS_SEASONS = 1
FTV_SEASONS_SEASONS = 2


def get_blanks_none(i):
    """
    Convert empty strings to nulls
    """
    return i if i or i == 0 else None
```

- [ ] **Step 4: Run it to verify it passes**

Run: `python3 -m unittest tests.test_mappings_support -v`
Expected: `OK` (6 tests passed).

- [ ] **Step 5: Update `mappings.py` to import from the new module**

In `resources/tmdbhelper/lib/items/database/mappings/__init__.py`, replace lines 1-21:

```python
#!/usr/bin/python
# -*- coding: utf-8 -*-
from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.api.mapping import _ItemMapper
from collections import namedtuple


ExtendedMap = namedtuple("ExtendedMap", "base unique_id overwrite data")


# Consts for wrangling FTV artwork into shape
FTV_WITHOUT_SEASONS = 0
FTV_TVSHOWS_SEASONS = 1
FTV_SEASONS_SEASONS = 2


def get_blanks_none(i):
    """
    Convert empty strings to nulls
    """
    return i if i or i == 0 else None
```

with:

```python
#!/usr/bin/python
# -*- coding: utf-8 -*-
from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.api.mapping import _ItemMapper
from tmdbhelper.lib.items.database.mappings.support import ExtendedMap, get_blanks_none
```

Do not touch anything else in the file yet — the rest of `ItemMapperMethods` still lives in `mappings.py` at this point and still uses `ExtendedMap`/`get_blanks_none` (now imported instead of defined locally), which works identically either way in Python.

- [ ] **Step 6: Verify the whole file still compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/items/database/mappings/__init__.py resources/tmdbhelper/lib/items/database/mappings/support.py`
Expected: no output, exit code 0.

- [ ] **Step 7: Re-run the smoke test to confirm nothing broke**

Run: `python3 -m unittest discover -s tests -v`
Expected: `OK` (7 tests total: 1 smoke + 6 support).

- [ ] **Step 8: Commit**

```bash
git add resources/tmdbhelper/lib/items/database/mappings/support.py resources/tmdbhelper/lib/items/database/mappings/__init__.py tests/test_mappings_support.py
git commit -m "refactor(mappings): extract ExtendedMap/get_blanks_none/FTV consts into support.py"
```

---

### Task 3: Extract `general.py`

**Files:**
- Create: `resources/tmdbhelper/lib/items/database/mappings/general.py`
- Create: `tests/test_mappings_general.py`
- Modify: `resources/tmdbhelper/lib/items/database/mappings/__init__.py` (remove the moved methods from `ItemMapperMethods`)

**Interfaces:**
- Consumes: `ExtendedMap`, `get_blanks_none` from `tmdbhelper.lib.items.database.mappings.support` (Task 2).
- Produces: `GeneralMapperMethods` class with `get_runtime`, `get_configured_item`, `split_array`, `get_custom_time`, `get_custom_date`, `get_custom_property`, `get_unique_ids`, `get_video`, `get_media_item_data`. Task 10's aggregate inherits this class. `get_media_item_data(self, i, tmdb_type, **additional_params)` calls `self.get_genre_items(...)` — a method this class does not define itself (it will come from `GenreMapperMethods` in Task 5, via the final aggregate) — this is expected and correct; do not add a stub or import for it here.

- [ ] **Step 1: Write the failing test**

Create `tests/test_mappings_general.py`:

```python
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_mappings_general -v`
Expected: `ModuleNotFoundError: No module named 'tmdbhelper.lib.items.database.mappings.general'`

- [ ] **Step 3: Create the module**

Create `resources/tmdbhelper/lib/items/database/mappings/general.py`:

```python
from tmdbhelper.lib.items.database.mappings.support import ExtendedMap, get_blanks_none


class GeneralMapperMethods:
    @staticmethod
    def get_runtime(i, *args, **kwargs):
        if isinstance(i, list):
            i = i[0]
        try:
            return int(i) * 60
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def get_configured_item(i, blanks=True, **kwargs):

        def get_item(i, v):
            try:
                if not callable(v):
                    return i.get(v)
                return v(i)
            except (TypeError, KeyError, IndexError, ValueError):
                return

        configured_items = {k: get_blanks_none(get_item(i, v)) for k, v in kwargs.items()}
        return configured_items if blanks else {k: v for k, v in configured_items.items() if k and v}

    @staticmethod
    def split_array(items, subkeys=(), haskeys=(), **kwargs):
        if not items:
            return []

        for subkey in subkeys:
            try:
                items = items[subkey]
            except (TypeError, KeyError):
                return []

        if not isinstance(items, list):
            return []

        def check_item(i):
            for k in haskeys:
                try:
                    if not i[k]:
                        return
                except (TypeError, KeyError, IndexError, ValueError):
                    return
            return i

        items = [i for i in items if check_item(i)] if haskeys else items
        return [GeneralMapperMethods.get_configured_item(i, **kwargs) for i in items]

    @staticmethod
    def get_custom_time(duration, name='duration'):
        if not duration:
            return {}
        minutes = duration // 60 % 60
        hours = duration // 60 // 60
        totalmin = duration // 60
        infoproperties = {
            f'{name}.H': hours,
            f'{name}.M': minutes,
            f'{name}.mins': totalmin,
            f'{name}.HHMM': f'{hours:02d}:{minutes:02d}',
        }
        return infoproperties

    @staticmethod
    def get_custom_date(air_date, name):
        # NOTE: this method has a real, traced dependency on Kodi's region/locale
        # formatting (tmdbhelper.lib.addon.tmdate.get_region_date calls a Kodi API
        # that must return a real locale string) and cannot be unit-tested outside
        # a running Kodi instance - confirmed by stubbing xbmc/xbmcaddon/xbmcgui/
        # xbmcplugin/xbmcvfs as MagicMock() and still hitting a failure inside
        # strftime(). This is unchanged, pre-existing behavior from before the
        # mappings.py split, not a new gap. See tests/test_mappings_general.py for
        # what IS covered.
        from tmdbhelper.lib.addon.plugin import get_infolabel
        from tmdbhelper.lib.addon.tmdate import format_date_obj, convert_timestamp, get_days_to_air
        air_date_obj = convert_timestamp(air_date, time_fmt="%Y-%m-%d", time_lim=10, utc_convert=False)

        if not air_date_obj:
            return {}

        infoproperties = {
            f'{name}': format_date_obj(air_date_obj, region_fmt='dateshort'),
            f'{name}.long': format_date_obj(air_date_obj, region_fmt='datelong'),
            f'{name}.short': format_date_obj(air_date_obj, "%d %b"),
            f'{name}.day': format_date_obj(air_date_obj, "%A"),
            f'{name}.day_short': format_date_obj(air_date_obj, "%a"),
            f'{name}.year': format_date_obj(air_date_obj, "%Y"),
            f'{name}.custom': format_date_obj(air_date_obj, get_infolabel('Skin.String(TMDbHelper.Date.Format)') or '%d %b %Y'),
            f'{name}.original': air_date,
        }

        days_to_air, is_aired = get_days_to_air(air_date_obj)
        days_to_air_name = f'{name}.days_from_aired' if is_aired else f'{name}.days_until_aired'

        infoproperties[days_to_air_name] = str(days_to_air)
        return infoproperties

    @staticmethod
    def get_custom_property(key, value):
        return [ExtendedMap('custom', key, False, {'key': key, 'value': value})]

    @staticmethod
    def get_unique_ids(results, **kwargs):
        if not results:
            return
        return [
            {
                'key': get_blanks_none(('tmdb_id' if k == 'id' else k).replace('_id', '')),
                'value': get_blanks_none(f'{v}')
            }
            for k, v in results.items()
        ]

    @staticmethod
    def get_video(items, **kwargs):
        if not items:
            return
        results = items.get('results')
        if not results:
            return
        data = []
        for video in results:
            if video['site'] != 'YouTube':
                continue
            data.append({
                'name': get_blanks_none(video['name']),
                'iso_country': get_blanks_none(video['iso_3166_1']),
                'iso_language': get_blanks_none(video['iso_639_1']),
                'release_date': get_blanks_none(video['published_at']),
                'key': get_blanks_none(video['key']),
                'content': get_blanks_none(video['type']),
                'path': f"plugin://plugin.video.youtube/play/?video_id={video['key']}",
            })
        return data

    def get_media_item_data(self, i, tmdb_type, **additional_params):
        data = []

        item_id = f'{tmdb_type}.{i["id"]}'

        mediatype = 'movie' if tmdb_type == 'movie' else 'tvshow'
        premiered = 'release_date' if mediatype == 'movie' else 'first_air_date'
        titlename = 'title' if mediatype == 'movie' else 'name'

        media_item = GeneralMapperMethods.get_configured_item(i, **{
            'year': lambda i: int(i[premiered][0:4]),
            'premiered': premiered,
            'plot': 'overview',
            'title': titlename,
            'originaltitle': 'original_title',
            'rating': 'vote_average',
            'votes': 'vote_count',
            'popularity': 'popularity'

        })
        media_item['id'] = item_id
        media_item['tmdb_id'] = i['id']
        media_item.update(additional_params)
        data.append(ExtendedMap(mediatype, item_id, False, media_item))

        data.append(ExtendedMap('baseitem', item_id, False, {
            'id': item_id,
            'mediatype': mediatype,
            'expiry': 0,
            'language': self.language,
        }))

        for genre in self.get_genre_items(i.get('genre_ids') or []):
            genre = GeneralMapperMethods.get_configured_item(genre, name='name', tmdb_id='tmdb_id')
            genre['parent_id'] = item_id
            data.append(ExtendedMap('genre', f"{item_id}.genre.{genre['tmdb_id']}", True, genre))

        from tmdbhelper.lib.items.database.mappings.art import ArtMapperMethods
        ArtMapperMethods.set_default_art(data, i, parent_id=item_id)

        return data
```

Note the local import of `ArtMapperMethods` inside `get_media_item_data` — `set_default_art` will live in `art.py` (Task 4, not yet created). This is a genuine cross-mixin call at the source level (unlike the `self.X` pattern used everywhere else), so it needs an explicit import; kept local (inside the method) rather than at module level to avoid a two-way import between `general.py` and `art.py` at load time — `art.py` never imports from `general.py`. This mirrors the existing codebase's own convention of local imports for cross-module calls (e.g. `get_belongs_to_collection` in the original file already does the equivalent by calling `ItemMapperMethods.set_default_art`, relying on the aggregate; here we import the concrete mixin directly since `GeneralMapperMethods` alone doesn't have `set_default_art` in its own MRO).

- [ ] **Step 4: Run it to verify it passes**

Run: `python3 -m unittest tests.test_mappings_general -v`
Expected: `OK` (16 tests passed). This will fail at `test_get_media_item_data_builds_movie_entry` with `ModuleNotFoundError: No module named 'tmdbhelper.lib.items.database.mappings.art'` until Task 4 lands — **that's expected and correct for this task**; note it as a known, temporary failure in this task's report (Task 4 will make it pass). Every other test in this file must pass now.

- [ ] **Step 5: Remove the moved methods from `mappings.py`**

In `resources/tmdbhelper/lib/items/database/mappings/__init__.py`, remove the `get_runtime`, `get_configured_item`, `split_array`, `get_custom_time`, `get_custom_date`, `get_custom_property`, `get_unique_ids`, `get_video`, and `get_media_item_data` method definitions from `ItemMapperMethods` (they now live in `general.py`). Leave every other method in the class untouched for now — `mappings.py` still has the rest of `ItemMapperMethods` until Tasks 4-9 extract them too.

- [ ] **Step 6: Verify everything still compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/items/database/mappings/__init__.py resources/tmdbhelper/lib/items/database/mappings/general.py`
Expected: no output, exit code 0.

- [ ] **Step 7: Commit**

```bash
git add resources/tmdbhelper/lib/items/database/mappings/general.py resources/tmdbhelper/lib/items/database/mappings/__init__.py tests/test_mappings_general.py
git commit -m "refactor(mappings): extract GeneralMapperMethods into general.py"
```

---

### Task 4: Extract `art.py`

**Files:**
- Create: `resources/tmdbhelper/lib/items/database/mappings/art.py`
- Create: `tests/test_mappings_art.py`
- Modify: `resources/tmdbhelper/lib/items/database/mappings/__init__.py` (remove the moved methods)

**Interfaces:**
- Consumes: `ExtendedMap`, `get_blanks_none` from `support.py` (Task 2); `FTV_WITHOUT_SEASONS`/`FTV_TVSHOWS_SEASONS`/`FTV_SEASONS_SEASONS` also from `support.py`.
- Produces: `ArtMapperMethods` class with `add_art_type`, `get_art`, `get_aspect_ratio`, `set_default_art`, `get_default_art`, `get_fanart_tv`. Task 3's `general.py` imports `set_default_art` from this class (local import inside `get_media_item_data`) — this task landing is what makes `test_get_media_item_data_builds_movie_entry` (Task 3) pass.

- [ ] **Step 1: Write the failing test**

Create `tests/test_mappings_art.py`:

```python
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_mappings_art -v`
Expected: `ModuleNotFoundError: No module named 'tmdbhelper.lib.items.database.mappings.art'`

- [ ] **Step 3: Create the module**

Create `resources/tmdbhelper/lib/items/database/mappings/art.py`:

```python
from tmdbhelper.lib.items.database.mappings.support import (
    ExtendedMap, get_blanks_none, FTV_WITHOUT_SEASONS, FTV_TVSHOWS_SEASONS, FTV_SEASONS_SEASONS,
)


class ArtMapperMethods:
    @staticmethod
    def add_art_type(item_id, image_path, image_type, ratio_type):
        from tmdbhelper.lib.addon.consts import IMAGEPATH_ASPECTRATIO
        return {
            'parent_id': item_id,
            'aspect_ratio': IMAGEPATH_ASPECTRATIO.index(ratio_type),
            'icon': get_blanks_none(image_path),
            'type': image_type,
            'extension': get_blanks_none(image_path.split('.')[-1] if image_path else None),
        }

    def get_fanart_tv(self, items, **kwargs):
        if not items:
            return

        # FTV artwork key name, type to map it to, art_has_seasons
        # Set art_has_seasons to FTV_TVSHOWS_SEASONS for artwork where fanarttv intends "season=all" to be "tvshow" artwork
        # Set art_has_seasons to FTV_SEASONS_SEASONS for artwork where fanarttv intends "season=all" to be "season" artwork
        art_types = {
            'movieposter': ('poster', FTV_WITHOUT_SEASONS),
            'moviebackground': ('fanart', FTV_WITHOUT_SEASONS),
            'moviethumb': ('landscape', FTV_WITHOUT_SEASONS),
            'moviebanner': ('banner', FTV_WITHOUT_SEASONS),
            'hdmovieclearart': ('clearart', FTV_WITHOUT_SEASONS),
            'movieclearart': ('clearart', FTV_WITHOUT_SEASONS),
            'hdmovielogo': ('clearlogo', FTV_WITHOUT_SEASONS),
            'movielogo': ('clearlogo', FTV_WITHOUT_SEASONS),
            'moviedisc': ('discart', FTV_WITHOUT_SEASONS),
            'tvposter': ('poster', FTV_WITHOUT_SEASONS),
            'tvthumb': ('landscape', FTV_WITHOUT_SEASONS),
            'tvbanner': ('banner', FTV_WITHOUT_SEASONS),
            'hdclearart': ('clearart', FTV_WITHOUT_SEASONS),
            'clearart': ('clearart', FTV_WITHOUT_SEASONS),
            'hdtvlogo': ('clearlogo', FTV_WITHOUT_SEASONS),
            'clearlogo': ('clearlogo', FTV_WITHOUT_SEASONS),
            'characterart': ('characterart', FTV_WITHOUT_SEASONS),
            'showbackground': ('fanart', FTV_TVSHOWS_SEASONS),
            'seasonposter': ('poster', FTV_SEASONS_SEASONS),
            'seasonbanner': ('banner', FTV_SEASONS_SEASONS),
            'seasonthumb': ('landscape', FTV_SEASONS_SEASONS),
        }

        data = []
        for art_type, art_list in items.items():

            if not isinstance(art_list, list):
                continue

            quality = 1 if art_type.startswith('hd') else 0

            art_type = art_types.get(art_type)
            if not art_type:
                continue

            art_type, art_has_seasons = art_type

            for art_item in art_list:
                icon = get_blanks_none(art_item['url'])

                if not icon:
                    continue

                item = {
                    'icon': icon,
                    'iso_language': get_blanks_none(art_item.get('lang')),
                    'likes': get_blanks_none(art_item.get('likes')),
                    'type': get_blanks_none(art_type),
                    'quality': get_blanks_none(quality),
                    'extension': get_blanks_none(icon.split('.')[-1] if icon else None),
                }

                if art_has_seasons:
                    # Some artwork on FanartTV uses season=all to indicate tvshow artwork
                    # While other artwork types use season=all to indicate season artwork for an "all" season...
                    # Do some gymnastics here to workaround this mess of conflated types
                    snum = (art_item.get('season') or 'all')

                    # Set "All Seasons" artwork to -1 season so we dont pull it in for a tvshow if it is really intended to be an "all" season type
                    if snum == 'all' and art_has_seasons == FTV_SEASONS_SEASONS:
                        snum = -1

                    # Set season artwork with a number ot season type
                    if snum != 'all':
                        parent_id = f'tv.{self.tmdb_id}.{snum}'

                        item['parent_id'] = parent_id

                        data.append(ExtendedMap('baseitem', parent_id, False, {
                            'id': parent_id,
                            'mediatype': 'season',
                            'expiry': 0,
                            'language': self.language,
                        }))

                data.append(ExtendedMap('fanart_tv', icon, True, item))

        return data

    @staticmethod
    def get_aspect_ratio(aspect_ratio):
        from tmdbhelper.lib.addon.consts import IMAGEPATH_ASPECTRATIO
        if aspect_ratio < 1:
            return IMAGEPATH_ASPECTRATIO.index('poster')
        if aspect_ratio == 1:
            return IMAGEPATH_ASPECTRATIO.index('square')
        if 1.7 <= aspect_ratio <= 1.8:
            return IMAGEPATH_ASPECTRATIO.index('landscape')
        if aspect_ratio < 1.7:
            return IMAGEPATH_ASPECTRATIO.index('thumb')
        if aspect_ratio > 1.8:
            return IMAGEPATH_ASPECTRATIO.index('wide')
        return IMAGEPATH_ASPECTRATIO.index('other')

    @staticmethod
    def get_art(items, **kwargs):
        if not items:
            return []

        data = []

        for artwork_type, artworks in items.items():
            for artwork in artworks:
                path = artwork['file_path']
                data.append(
                    ExtendedMap('art', get_blanks_none(path), True, {
                        'aspect_ratio': ArtMapperMethods.get_aspect_ratio(artwork['aspect_ratio']),
                        'quality': int((artwork['width'] * artwork['height']) // 200000),  # Quality integer to nearest fifth of a megapixel
                        'iso_language': get_blanks_none(artwork['iso_639_1']),
                        'iso_country': get_blanks_none(artwork['iso_3166_1']),
                        'icon': get_blanks_none(path),
                        'type': get_blanks_none(artwork_type),
                        'extension': get_blanks_none(path.split('.')[-1] if path else None),
                        'rating': int(artwork['vote_average'] * 100),
                        'votes': get_blanks_none(artwork['vote_count'])
                    })
                )

        return data

    @staticmethod
    def set_default_art(data, item, parent_id=None):
        for path, art_type in (
            ('poster_path', 'posters',),
            ('backdrop_path', 'backdrops',),
            ('profile_path', 'profiles',),
        ):
            path = item.get(path)
            if not path:
                continue
            data.extend(ArtMapperMethods.get_default_art(path, art_type, parent_id=parent_id))
        return data

    @staticmethod
    def get_default_art(path, art_type, parent_id=None):
        item = {
            'icon': path,
            'type': art_type,
        }
        if parent_id:
            item['parent_id'] = parent_id
        data = [ExtendedMap('default_art', path, False, item)]
        item = item.copy()
        item['extension'] = get_blanks_none(path.split('.')[-1] if path else None)
        data.append(ExtendedMap('art', path, False, item))
        return data
```

- [ ] **Step 4: Run it to verify it passes**

Run: `python3 -m unittest tests.test_mappings_art -v`
Expected: `OK` (9 tests passed).

- [ ] **Step 5: Re-run Task 3's test to confirm the cross-mixin import now resolves**

Run: `python3 -m unittest tests.test_mappings_general -v`
Expected: `OK` (16 tests passed) — `test_get_media_item_data_builds_movie_entry` now passes since `art.py` exists.

- [ ] **Step 6: Remove the moved methods from `mappings.py`**

In `resources/tmdbhelper/lib/items/database/mappings/__init__.py`, remove the `add_art_type`, `get_fanart_tv`, `get_aspect_ratio`, `get_art`, `set_default_art`, `get_default_art` method definitions from `ItemMapperMethods`.

- [ ] **Step 7: Verify everything still compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/items/database/mappings/__init__.py resources/tmdbhelper/lib/items/database/mappings/art.py`
Expected: no output, exit code 0.

- [ ] **Step 8: Commit**

```bash
git add resources/tmdbhelper/lib/items/database/mappings/art.py resources/tmdbhelper/lib/items/database/mappings/__init__.py tests/test_mappings_art.py
git commit -m "refactor(mappings): extract ArtMapperMethods into art.py"
```

---

### Task 5: Extract `genre.py`

**Files:**
- Create: `resources/tmdbhelper/lib/items/database/mappings/genre.py`
- Create: `tests/test_mappings_genre.py`
- Modify: `resources/tmdbhelper/lib/items/database/mappings/__init__.py` (remove the moved methods)

**Interfaces:**
- Consumes: `GeneralMapperMethods` from `general.py` (Task 3) — `get_genres` calls `GeneralMapperMethods.split_array(...)` directly (see the note after the code block in Step 3 for why this one call uses the class name instead of `self.`).
- Produces: `GenreMapperMethods` class with `tmdb_database` (property), `genres_map` (cached_property), `get_genre_items`, `get_genres`. Task 3's `GeneralMapperMethods.get_media_item_data` calls `self.get_genre_items(...)` — this class is what supplies that method once the aggregate (Task 10) combines everything; Task 3's own test stubs it independently and does not depend on this task.

- [ ] **Step 1: Write the failing test**

Create `tests/test_mappings_genre.py`:

```python
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
```

Note: overriding `genres_map` with a plain class-level `dict` on a test subclass works even though the real `genres_map` is a `cached_property` — this is a verified pattern: Python resolves the plain attribute on the more-derived subclass before falling back to the base class's descriptor, so the real `FindQueriesDatabase`/Kodi-DB chain behind `tmdb_database` is never touched in these tests.

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_mappings_genre -v`
Expected: `ModuleNotFoundError: No module named 'tmdbhelper.lib.items.database.mappings.genre'`

- [ ] **Step 3: Create the module**

Create `resources/tmdbhelper/lib/items/database/mappings/genre.py`:

```python
from jurialmunkey.ftools import cached_property

from tmdbhelper.lib.items.database.mappings.general import GeneralMapperMethods


class GenreMapperMethods:
    @property
    def tmdb_database(self):
        from tmdbhelper.lib.query.database.database import FindQueriesDatabase
        return FindQueriesDatabase()

    @cached_property
    def genres_map(self):
        genres_map = {}
        genres_map.update(self.tmdb_database.get_genres('movie'))
        genres_map.update(self.tmdb_database.get_genres('tv'))
        genres_map = {v: k for k, v in genres_map.items()}
        return genres_map

    def get_genre_items(self, genre_ids):

        def get_genre_item(tmdb_id):
            try:
                return {'name': self.genres_map[tmdb_id], 'tmdb_id': tmdb_id}
            except (KeyError, TypeError):
                return

        return [j for j in (get_genre_item(i) for i in genre_ids if i) if j]

    def get_genres(self, items, **kwargs):

        def get_genre_id(i):
            try:
                return i['id']
            except (KeyError, TypeError):
                return

        genre_items = self.get_genre_items([j for j in (get_genre_id(i) for i in items if i) if j])
        return GeneralMapperMethods.split_array(genre_items, name='name', tmdb_id='tmdb_id')
```

Note: `get_genres` calls `GeneralMapperMethods.split_array(...)` directly (the class, not `self.`) — the original code called `ItemMapperMethods.split_array(...)`, which resolved through the aggregate's MRO. Since `GenreMapperMethods` doesn't itself inherit from `GeneralMapperMethods`, it needs an explicit import to reach `split_array` — this is the one place in this split where a mixin imports another mixin directly rather than relying on `self.`, because `split_array` is a `@staticmethod` being called in a context where `self` isn't the natural spelling. This is a deliberate, narrow exception — every other cross-mixin call in this refactor goes through `self.`.

- [ ] **Step 4: Run it to verify it passes**

Run: `python3 -m unittest tests.test_mappings_genre -v`
Expected: `OK` (4 tests passed).

- [ ] **Step 5: Remove the moved methods from `mappings.py`**

In `resources/tmdbhelper/lib/items/database/mappings/__init__.py`, remove the `tmdb_database`, `genres_map`, `get_genre_items`, `get_genres` definitions from `ItemMapperMethods`. Also remove the now-unused `from jurialmunkey.ftools import cached_property` import from the top of `mappings.py` if nothing else in the file still uses `cached_property` — check with `grep -n cached_property resources/tmdbhelper/lib/items/database/mappings/__init__.py` first; if `ItemMapper` or `BlankNoneDict` don't reference it, remove the import.

- [ ] **Step 6: Verify everything still compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/items/database/mappings/__init__.py resources/tmdbhelper/lib/items/database/mappings/genre.py`
Expected: no output, exit code 0.

- [ ] **Step 7: Commit**

```bash
git add resources/tmdbhelper/lib/items/database/mappings/genre.py resources/tmdbhelper/lib/items/database/mappings/__init__.py tests/test_mappings_genre.py
git commit -m "refactor(mappings): extract GenreMapperMethods into genre.py"
```

---

### Task 6: Extract `credits.py`

**Files:**
- Create: `resources/tmdbhelper/lib/items/database/mappings/credits.py`
- Create: `tests/test_mappings_credits.py`
- Modify: `resources/tmdbhelper/lib/items/database/mappings/__init__.py` (remove the moved methods)

**Interfaces:**
- Consumes: `ExtendedMap` from `support.py` (Task 2); `GeneralMapperMethods` from `general.py` (Task 3, for `get_configured_item` and `get_media_item_data`); `ArtMapperMethods` from `art.py` (Task 4, for `set_default_art`).
- Produces: `CreditsMapperMethods` class with `credits_mappings` (class const), `get_credits`, `get_aggregate_credits`, `get_credits_data`, `get_person_movie_credits_data`, `get_person_tv_credits_data`, `get_person_credits_data`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_mappings_credits.py`:

```python
import unittest

from tests import _bootstrap  # noqa: F401
from tmdbhelper.lib.items.database.mappings.credits import CreditsMapperMethods


class FakeCredits(CreditsMapperMethods):
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_mappings_credits -v`
Expected: `ModuleNotFoundError: No module named 'tmdbhelper.lib.items.database.mappings.credits'`

- [ ] **Step 3: Create the module**

Create `resources/tmdbhelper/lib/items/database/mappings/credits.py`:

```python
from tmdbhelper.lib.items.database.mappings.support import ExtendedMap
from tmdbhelper.lib.items.database.mappings.general import GeneralMapperMethods
from tmdbhelper.lib.items.database.mappings.art import ArtMapperMethods


class CreditsMapperMethods:
    credits_mappings = (
        ('cast', 'castmember', {'ordering': 'order', 'role': 'character', 'appearances': 'total_episode_count'}, 'roles'),
        ('crew', 'crewmember', {'department': 'department', 'role': 'job', 'appearances': 'total_episode_count'}, 'jobs'),
        ('guest_stars', 'castmember', {'ordering': 'order', 'role': 'character', 'appearances': 'total_episode_count', 'guest': lambda i: 1}, 'roles'),
    )

    def get_credits(self, items, **kwargs):
        return self.get_credits_data(items, False)

    def get_aggregate_credits(self, items, **kwargs):
        return self.get_credits_data(items, True)

    def get_credits_data(self, items, aggregrate=False):
        data = []
        for subkey, mapkey, config, jobkey in self.credits_mappings:

            for i in (items.get(subkey) or []):
                item_id = f'person.{i["id"]}'
                tmdb_id = i['id']

                data.append(ExtendedMap('baseitem', item_id, False, {
                    'id': item_id,
                    'mediatype': 'person',
                    'expiry': 0,
                    'language': self.language,
                }))

                jobs = (i.get(jobkey) or []) if aggregrate else [i]

                for j in jobs:
                    credit_item = GeneralMapperMethods.get_configured_item(i, **config)
                    credit_item.update(GeneralMapperMethods.get_configured_item(j, blanks=False, **config))
                    credit_item['tmdb_id'] = tmdb_id
                    data.append(ExtendedMap(mapkey, j.get('credit_id'), False, credit_item))

                person_item = GeneralMapperMethods.get_configured_item(i, **{
                    'name': 'name',
                    'gender': 'gender',
                    'known_for_department': 'known_for_department',
                })
                person_item['id'] = item_id
                person_item['tmdb_id'] = tmdb_id
                data.append(ExtendedMap('person', item_id, False, person_item))

                ArtMapperMethods.set_default_art(data, i, parent_id=item_id)

        return data

    def get_person_movie_credits_data(self, items):
        return self.get_person_credits_data(items, 'movie')

    def get_person_tv_credits_data(self, items):
        return self.get_person_credits_data(items, 'tv')

    def get_person_credits_data(self, items, tmdb_type='movie'):
        data = []

        mappings = (
            ('cast', 'castmember', {'ordering': 'order', 'role': 'character', 'appearances': 'episode_count'}),
            ('crew', 'crewmember', {'department': 'department', 'role': 'job', 'appearances': 'episode_count'}),
        )

        for subkey, mapkey, config in mappings:
            credits = items.get(subkey) or []
            for i in credits:
                data.extend(self.get_media_item_data(i, tmdb_type))

                credit_item = GeneralMapperMethods.get_configured_item(i, **config)
                credit_item['parent_id'] = f'{tmdb_type}.{i["id"]}'
                credit_item['tmdb_id'] = self.tmdb_id
                data.append(ExtendedMap(mapkey, i.get('credit_id'), False, credit_item))

        return data
```

Note: `get_person_credits_data` calls `self.get_media_item_data(i, tmdb_type)` — this comes from `GeneralMapperMethods` (Task 3) via the aggregate's MRO, same `self.`-based cross-mixin pattern used throughout. `CreditsMapperMethods` doesn't need to inherit from `GeneralMapperMethods` for this to work at runtime (only the final aggregate needs to combine both) — but the test above provides `get_genre_items` directly on `FakeCredits` since `get_media_item_data` needs it and the test doesn't go through the real aggregate.

- [ ] **Step 4: Run it to verify it passes**

Run: `python3 -m unittest tests.test_mappings_credits -v`
Expected: `OK` (3 tests passed).

- [ ] **Step 5: Remove the moved methods from `mappings.py`**

In `resources/tmdbhelper/lib/items/database/mappings/__init__.py`, remove the `credits_mappings` class constant and the `get_credits`, `get_aggregate_credits`, `get_credits_data`, `get_person_movie_credits_data`, `get_person_tv_credits_data`, `get_person_credits_data` method definitions from `ItemMapperMethods`.

- [ ] **Step 6: Verify everything still compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/items/database/mappings/__init__.py resources/tmdbhelper/lib/items/database/mappings/credits.py`
Expected: no output, exit code 0.

- [ ] **Step 7: Commit**

```bash
git add resources/tmdbhelper/lib/items/database/mappings/credits.py resources/tmdbhelper/lib/items/database/mappings/__init__.py tests/test_mappings_credits.py
git commit -m "refactor(mappings): extract CreditsMapperMethods into credits.py"
```

---

### Task 7: Extract `translations.py`

**Files:**
- Create: `resources/tmdbhelper/lib/items/database/mappings/translations.py`
- Create: `tests/test_mappings_translations.py`
- Modify: `resources/tmdbhelper/lib/items/database/mappings/__init__.py` (remove the moved methods)

**Interfaces:**
- Consumes: `get_blanks_none` from `support.py` (Task 2).
- Produces: `TranslationMapperMethods` class with `get_providers`, `get_translations`, `get_certifications`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_mappings_translations.py`:

```python
import unittest

from tests import _bootstrap  # noqa: F401
from tmdbhelper.lib.items.database.mappings.translations import TranslationMapperMethods


class TranslationMapperMethodsTest(unittest.TestCase):
    def test_get_providers_maps_flatrate_availability(self):
        items = {'results': {'US': {'flatrate': [
            {'provider_id': 8, 'provider_name': 'Netflix', 'logo_path': '/n.jpg', 'display_priority': 1},
        ]}}}
        result = TranslationMapperMethods.get_providers(items)
        self.assertEqual(result, [{'iso_country': 'US', 'availability': 'flatrate', 'tmdb_id': 8}])

    def test_get_providers_service_mode_maps_provider_details(self):
        items = {'results': {'US': {'flatrate': [
            {'provider_id': 8, 'provider_name': 'Netflix', 'logo_path': '/n.jpg', 'display_priority': 1},
        ]}}}
        result = TranslationMapperMethods.get_providers(items, service=True)
        self.assertEqual(result, [{'display_priority': 1, 'name': 'Netflix', 'logo': '/n.jpg', 'tmdb_id': 8}])

    def test_get_providers_returns_none_for_falsy_input(self):
        self.assertIsNone(TranslationMapperMethods.get_providers(None))

    def test_get_translations_maps_title_and_plot(self):
        items = {'translations': [{
            'iso_3166_1': 'US', 'iso_639_1': 'en',
            'data': {'title': 'Fight Club', 'overview': 'A plot', 'tagline': 'Tag'},
        }]}
        result = TranslationMapperMethods.get_translations(items)
        self.assertEqual(result, [{
            'iso_country': 'US', 'iso_language': 'en', 'title': 'Fight Club', 'plot': 'A plot', 'tagline': 'Tag',
        }])

    def test_get_certifications_maps_release_dates(self):
        items = {'results': [{'iso_3166_1': 'US', 'release_dates': [
            {'certification': 'R', 'iso_639_1': 'en', 'release_date': '1999-10-15', 'type': 3},
        ]}]}
        result = TranslationMapperMethods.get_certifications(items)
        self.assertEqual(result, [{
            'name': 'R', 'iso_country': 'US', 'iso_language': 'en',
            'release_date': '1999-10-15', 'release_type': 'Theatrical',
        }])

    def test_get_certifications_returns_none_for_falsy_input(self):
        self.assertIsNone(TranslationMapperMethods.get_certifications(None))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_mappings_translations -v`
Expected: `ModuleNotFoundError: No module named 'tmdbhelper.lib.items.database.mappings.translations'`

- [ ] **Step 3: Create the module**

Create `resources/tmdbhelper/lib/items/database/mappings/translations.py`:

```python
from tmdbhelper.lib.items.database.mappings.support import get_blanks_none


class TranslationMapperMethods:
    @staticmethod
    def get_providers(items, service=False, **kwargs):
        if not items:
            return
        results = items.get('results')
        if not results:
            return
        data = []
        for iso, availabilities in results.items():
            for availability, datalist in availabilities.items():
                if availability == 'link':
                    continue
                for provider in datalist:
                    if service:
                        item = {
                            'display_priority': get_blanks_none(provider.get('display_priority')),
                            'name': get_blanks_none(provider.get('provider_name')),
                            'logo': get_blanks_none(provider.get('logo_path')),
                            'tmdb_id': get_blanks_none(provider.get('provider_id')),
                        }
                    else:
                        item = {
                            'iso_country': iso,
                            'availability': get_blanks_none(availability),
                            'tmdb_id': get_blanks_none(provider.get('provider_id')),
                        }
                    data.append(item)
        return data

    @staticmethod
    def get_translations(items, **kwargs):
        if not items:
            return
        results = items.get('translations')
        if not results:
            return
        data = [
            {
                'iso_country': get_blanks_none(translation['iso_3166_1']),
                'iso_language': get_blanks_none(translation['iso_639_1']),
                'title': get_blanks_none(translation['data'].get('title') or translation['data'].get('name')),
                'plot': get_blanks_none(translation['data'].get('overview')),
                'tagline': get_blanks_none(translation['data'].get('tagline')),
            } for translation in results
        ]
        return data

    @staticmethod
    def get_certifications(items, **kwargs):
        if not items:
            return
        results = items.get('results')
        if not results:
            return
        data = []
        tmdb_release_types = {1: 'Premiere', 2: 'Limited', 3: 'Theatrical', 4: 'Digital', 5: 'Physical', 6: 'TV'}
        for release_country in results:
            iso_country = release_country['iso_3166_1']
            for release in (release_country.get('release_dates') or ()):
                data.append({
                    'name': get_blanks_none(release['certification']),
                    'iso_country': get_blanks_none(iso_country),
                    'iso_language': get_blanks_none(release['iso_639_1']),
                    'release_date': get_blanks_none(release['release_date']),
                    'release_type': get_blanks_none(tmdb_release_types.get(release['type'])),
                })
        return data
```

- [ ] **Step 4: Run it to verify it passes**

Run: `python3 -m unittest tests.test_mappings_translations -v`
Expected: `OK` (6 tests passed).

- [ ] **Step 5: Remove the moved methods from `mappings.py`**

In `resources/tmdbhelper/lib/items/database/mappings/__init__.py`, remove the `get_providers`, `get_translations`, `get_certifications` method definitions from `ItemMapperMethods`.

- [ ] **Step 6: Verify everything still compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/items/database/mappings/__init__.py resources/tmdbhelper/lib/items/database/mappings/translations.py`
Expected: no output, exit code 0.

- [ ] **Step 7: Commit**

```bash
git add resources/tmdbhelper/lib/items/database/mappings/translations.py resources/tmdbhelper/lib/items/database/mappings/__init__.py tests/test_mappings_translations.py
git commit -m "refactor(mappings): extract TranslationMapperMethods into translations.py"
```

---

### Task 8: Extract `movie.py`

**Files:**
- Create: `resources/tmdbhelper/lib/items/database/mappings/movie.py`
- Create: `tests/test_mappings_movie.py`
- Modify: `resources/tmdbhelper/lib/items/database/mappings/__init__.py` (remove the moved methods)

**Interfaces:**
- Consumes: `ExtendedMap` from `support.py` (Task 2); `ArtMapperMethods` from `art.py` (Task 4, for `set_default_art`); `GeneralMapperMethods` from `general.py` (Task 3, for `get_configured_item`; also relies on `self.get_media_item_data`, present via the aggregate).
- Produces: `MovieMapperMethods` class with `get_belongs_to_collection`, `get_collection`, `get_parts`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_mappings_movie.py`:

```python
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_mappings_movie -v`
Expected: `ModuleNotFoundError: No module named 'tmdbhelper.lib.items.database.mappings.movie'`

- [ ] **Step 3: Create the module**

Create `resources/tmdbhelper/lib/items/database/mappings/movie.py`:

```python
from tmdbhelper.lib.items.database.mappings.support import ExtendedMap
from tmdbhelper.lib.items.database.mappings.general import GeneralMapperMethods
from tmdbhelper.lib.items.database.mappings.art import ArtMapperMethods


class MovieMapperMethods:
    def get_belongs_to_collection(self, i, **kwargs):
        data = []

        item_id = f"movie.{self.tmdb_id}"
        collection_id = f"collection.{i['id']}"

        collection_item = GeneralMapperMethods.get_configured_item(i, **{
            'tmdb_id': 'id',
            'title': 'name',
        })
        collection_item['id'] = collection_id
        data.append(ExtendedMap('collection', collection_id, False, collection_item))

        ArtMapperMethods.set_default_art(data, i, parent_id=item_id)

        data.append(ExtendedMap('belongs', item_id, False, {
            'id': item_id,
            'parent_id': collection_id,
        }))

        data.append(ExtendedMap('baseitem', collection_id, False, {
            'id': collection_id,
            'mediatype': 'set',
            'expiry': 0,
            'language': self.language,
        }))

        return data

    def get_collection(self, collection_object, **kwargs):
        data = []

        if not collection_object:
            return data

        collection_id = f"collection.{collection_object['id']}"

        for i in (collection_object.get('parts') or []):
            data.extend(self.get_media_item_data(i, 'movie'))
            data.append(ExtendedMap('belongs', f'movie.{i["id"]}', False, {
                'id': f'movie.{i["id"]}',
                'parent_id': collection_id,
            }))

        return data

    def get_parts(self, parts, **kwargs):
        data = []

        if not parts:
            return data

        collection_id = f"collection.{self.tmdb_id}"

        for i in parts:
            data.extend(self.get_media_item_data(i, 'movie'))
            data.append(ExtendedMap('belongs', f'movie.{i["id"]}', False, {
                'id': f'movie.{i["id"]}',
                'parent_id': collection_id,
            }))

        return data
```

- [ ] **Step 4: Run it to verify it passes**

Run: `python3 -m unittest tests.test_mappings_movie -v`
Expected: `OK` (4 tests passed).

- [ ] **Step 5: Remove the moved methods from `mappings.py`**

In `resources/tmdbhelper/lib/items/database/mappings/__init__.py`, remove the `get_belongs_to_collection`, `get_collection`, `get_parts` method definitions from `ItemMapperMethods`.

- [ ] **Step 6: Verify everything still compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/items/database/mappings/__init__.py resources/tmdbhelper/lib/items/database/mappings/movie.py`
Expected: no output, exit code 0.

- [ ] **Step 7: Commit**

```bash
git add resources/tmdbhelper/lib/items/database/mappings/movie.py resources/tmdbhelper/lib/items/database/mappings/__init__.py tests/test_mappings_movie.py
git commit -m "refactor(mappings): extract MovieMapperMethods into movie.py"
```

---

### Task 9: Extract `tv.py`

**Files:**
- Create: `resources/tmdbhelper/lib/items/database/mappings/tv.py`
- Create: `tests/test_mappings_tv.py`
- Modify: `resources/tmdbhelper/lib/items/database/mappings/__init__.py` (remove the moved methods)

**Interfaces:**
- Consumes: `ExtendedMap` from `support.py` (Task 2); `GeneralMapperMethods` from `general.py` (Task 3, for `get_configured_item`, and relies on `self.get_runtime`/`self.get_episode_type` present via the aggregate); `ArtMapperMethods` from `art.py` (Task 4, for `add_art_type` and `set_default_art`).
- Produces: `TVMapperMethods` class with `get_episode_type`, `get_episode_to_air`, `get_episodes`, `get_seasons`, `get_creators`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_mappings_tv.py`:

```python
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_mappings_tv -v`
Expected: `ModuleNotFoundError: No module named 'tmdbhelper.lib.items.database.mappings.tv'`

- [ ] **Step 3: Create the module**

Create `resources/tmdbhelper/lib/items/database/mappings/tv.py`:

```python
from tmdbhelper.lib.items.database.mappings.support import ExtendedMap
from tmdbhelper.lib.items.database.mappings.general import GeneralMapperMethods
from tmdbhelper.lib.items.database.mappings.art import ArtMapperMethods


class TVMapperMethods:
    @staticmethod
    def get_episode_type(i, **kwargs):
        episode_type = i['episode_type']
        season_number = i['season_number']
        episode_number = i['episode_number']
        if season_number == 0:
            return 'special'
        if episode_number == 1:
            return 'series_premiere' if season_number == 1 else 'season_premiere'
        if episode_type == 'finale':
            return 'season_finale'  # TODO: Series finale currently calculated as part of last_aired (checks status as cancelled/ended and assumes last_aired episode is finale)
        if episode_type == 'mid_season':
            return 'mid_season_finale'  # TODO: Calculate mid season premiere (might be a real pain to do)
        return 'standard'

    def get_creators(self, items, **kwargs):
        data = []

        for i in items:
            item_id = f'person.{i["id"]}'
            tmdb_id = i['id']

            data.append(ExtendedMap('crewmember', item_id, False, {
                'tmdb_id': tmdb_id,
                'role': 'Creator',
                'department': 'Creator',
            }))

            person_item = GeneralMapperMethods.get_configured_item(i, **{
                'name': 'name',
                'gender': 'gender',
            })
            person_item['id'] = item_id
            person_item['tmdb_id'] = tmdb_id
            data.append(ExtendedMap('person', item_id, False, person_item))

            ArtMapperMethods.set_default_art(data, i, parent_id=item_id)

            data.append(ExtendedMap('baseitem', item_id, False, {
                'id': item_id,
                'mediatype': 'person',
                'expiry': 0,
                'language': self.language,
            }))

        return data

    def get_episode_to_air(self, i, **kwargs):
        data = []

        item_id = f'tv.{self.tmdb_id}.{i["season_number"]}.{i["episode_number"]}'
        season_id = f'tv.{self.tmdb_id}.{i["season_number"]}'
        tvshow_id = f'tv.{self.tmdb_id}'

        episode_item = GeneralMapperMethods.get_configured_item(i, **{
            'episode': 'episode_number',
            'premiered': 'air_date',
            'title': 'name',
            'plot': 'overview',
            'rating': 'vote_average',
            'votes': 'vote_count',
            'status': lambda i: self.get_episode_type(i),
            'duration': lambda i: self.get_runtime(i['runtime'])
        })
        episode_item['id'] = item_id
        episode_item['season_id'] = season_id
        episode_item['tvshow_id'] = tvshow_id

        if not self.data.get('in_production') and not self.data.get('next_episode_to_air'):
            episode_item['status'] = 'series_finale'

        data.append(ExtendedMap('episode', item_id, False, episode_item))

        data.append(ExtendedMap('season', season_id, False, {
            'id': season_id,
            'tvshow_id': tvshow_id,
            'season': i['season_number'],
        }))

        data.append(ExtendedMap('baseitem', item_id, False, {
            'id': item_id,
            'mediatype': 'episode',
            'expiry': 0,
            'language': self.language,
        }))

        data.append(ExtendedMap('baseitem', season_id, False, {
            'id': season_id,
            'mediatype': 'season',
            'expiry': 0,
            'language': self.language,
        }))

        if i.get('still_path'):
            artwork = ArtMapperMethods.add_art_type(
                item_id=item_id,
                image_path=i['still_path'],
                image_type='stills',
                ratio_type='landscape')
            data.append(ExtendedMap('art', artwork['icon'], False, artwork))

        # Use last/next aired duration if available for tvshow duration
        if episode_item.get('duration') and not self.item['item'].get('duration'):
            self.item['item']['duration'] = episode_item['duration']

        return data

    def get_episodes(self, items, **kwargs):
        data = []

        for i in items:
            item_id = f'tv.{self.tmdb_id}.{i["season_number"]}.{i["episode_number"]}'
            season_id = f'tv.{self.tmdb_id}.{i["season_number"]}'
            tvshow_id = f'tv.{self.tmdb_id}'

            episode_item = GeneralMapperMethods.get_configured_item(i, **{
                'episode': 'episode_number',
                'year': lambda i: int(i['air_date'][0:4]),
                'premiered': 'air_date',
                'title': 'name',
                'plot': 'overview',
                'rating': 'vote_average',
                'votes': 'vote_count',
                'status': lambda i: self.get_episode_type(i),
                'duration': lambda i: self.get_runtime(i['runtime'])
            })
            episode_item['id'] = item_id
            episode_item['season_id'] = season_id
            episode_item['tvshow_id'] = tvshow_id

            data.append(ExtendedMap('episode', item_id, True, episode_item))

            if i.get('still_path'):
                artwork = ArtMapperMethods.add_art_type(
                    item_id=item_id,
                    image_path=i['still_path'],
                    image_type='stills',
                    ratio_type='landscape')
                data.append(ExtendedMap('art', artwork['icon'], False, artwork))

            data.append(ExtendedMap('baseitem', item_id, False, {
                'id': item_id,
                'mediatype': 'episode',
                'expiry': 0,
                'language': self.language,
            }))

        return data

    def get_seasons(self, items, **kwargs):
        data = []

        for i in items:
            item_id = f'tv.{self.tmdb_id}.{i["season_number"]}'
            tvshow_id = f'tv.{self.tmdb_id}'

            season_item = GeneralMapperMethods.get_configured_item(i, **{
                'season': 'season_number',
                'year': lambda i: int(i['air_date'][0:4]),
                'premiered': 'air_date',
                'title': 'name',
                'plot': 'overview',
                'rating': 'vote_average',
            })
            season_item['id'] = item_id
            season_item['tvshow_id'] = tvshow_id

            data.append(ExtendedMap('season', item_id, True, season_item))

            ArtMapperMethods.set_default_art(data, i, parent_id=item_id)

            data.append(ExtendedMap('baseitem', item_id, False, {
                'id': item_id,
                'mediatype': 'season',
                'expiry': 0,
                'language': self.language
            }))

        return data
```

Note: `get_episode_to_air`/`get_episodes` call `self.get_episode_type(i)` and `self.get_runtime(i['runtime'])` — both come from the aggregate (`get_episode_type` from this same class, `get_runtime` from `GeneralMapperMethods`) at runtime. The test's `FakeTV` provides its own `get_runtime` directly since `FakeTV` only inherits `TVMapperMethods`, not the full aggregate.

- [ ] **Step 4: Run it to verify it passes**

Run: `python3 -m unittest tests.test_mappings_tv -v`
Expected: `OK` (8 tests passed).

- [ ] **Step 5: Remove the moved methods from `mappings.py`**

In `resources/tmdbhelper/lib/items/database/mappings/__init__.py`, remove the `get_episode_type`, `get_episode_to_air`, `get_episodes`, `get_seasons`, `get_creators` method definitions from `ItemMapperMethods`. After this step, `ItemMapperMethods` in `mappings.py` should have **no method bodies left** — every method has moved to one of the seven mixin files. Only the class statement itself remains (see Task 10 for what replaces it).

- [ ] **Step 6: Verify everything still compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/items/database/mappings/__init__.py resources/tmdbhelper/lib/items/database/mappings/tv.py`
Expected: no output, exit code 0.

- [ ] **Step 7: Commit**

```bash
git add resources/tmdbhelper/lib/items/database/mappings/tv.py resources/tmdbhelper/lib/items/database/mappings/__init__.py tests/test_mappings_tv.py
git commit -m "refactor(mappings): extract TVMapperMethods into tv.py"
```

---

### Task 10: Rebuild `mappings.py` as a thin aggregate and verify the whole suite

**Files:**
- Modify: `resources/tmdbhelper/lib/items/database/mappings/__init__.py` (replace the now-empty `ItemMapperMethods` class body with the aggregate)
- Create: `tests/test_mappings_aggregate.py`

**Interfaces:**
- Consumes: `GeneralMapperMethods`, `ArtMapperMethods`, `GenreMapperMethods`, `CreditsMapperMethods`, `TranslationMapperMethods`, `MovieMapperMethods`, `TVMapperMethods` (Tasks 3-9).
- Produces: `ItemMapperMethods` in `mappings.py` — the final aggregate every real caller (`ItemMapper`) uses. No new interface beyond what already existed before this whole refactor started — this task's job is to prove that's true.

- [ ] **Step 1: Write the failing test**

Create `tests/test_mappings_aggregate.py` — this test proves the aggregate genuinely has every method the original 1059-line class had, and that a representative cross-mixin call chain (the one exercised by `MovieMapperMethods.get_collection` → `self.get_media_item_data` → `self.get_genre_items`, spanning Movie, General, and Genre) works end-to-end through the real aggregate, not just through hand-built fakes:

```python
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_mappings_aggregate -v`
Expected: `AssertionError: ItemMapperMethods is missing get_runtime` (or similar — `ItemMapperMethods` in `mappings.py` currently has an empty body after Task 9 removed its last methods, so it has none of these attributes yet).

- [ ] **Step 3: Replace the empty `ItemMapperMethods` class with the aggregate**

In `resources/tmdbhelper/lib/items/database/mappings/__init__.py`, the file should currently look like (imports plus an empty `ItemMapperMethods` class, plus `BlankNoneDict` and `ItemMapper` unchanged below). Replace the imports and the `ItemMapperMethods` class definition with:

```python
#!/usr/bin/python
# -*- coding: utf-8 -*-
from tmdbhelper.lib.api.mapping import _ItemMapper
from tmdbhelper.lib.items.database.mappings.general import GeneralMapperMethods
from tmdbhelper.lib.items.database.mappings.art import ArtMapperMethods
from tmdbhelper.lib.items.database.mappings.genre import GenreMapperMethods
from tmdbhelper.lib.items.database.mappings.credits import CreditsMapperMethods
from tmdbhelper.lib.items.database.mappings.translations import TranslationMapperMethods
from tmdbhelper.lib.items.database.mappings.movie import MovieMapperMethods
from tmdbhelper.lib.items.database.mappings.tv import TVMapperMethods


class ItemMapperMethods(
    GeneralMapperMethods,
    ArtMapperMethods,
    GenreMapperMethods,
    CreditsMapperMethods,
    TranslationMapperMethods,
    MovieMapperMethods,
    TVMapperMethods,
):
    pass
```

Do not remove the `ExtendedMap`/`get_blanks_none` import from Task 2 if anything else in `mappings.py` still references them directly — check with `grep -n "ExtendedMap\|get_blanks_none" resources/tmdbhelper/lib/items/database/mappings/__init__.py` after this edit; if the only remaining references were inside the now-removed `ItemMapperMethods` method bodies, remove that import line too (it would be unused and `py_compile` won't catch an unused import, but leave the codebase clean).

Everything below this point in the file — `BlankNoneDict` and the entire `ItemMapper` class (`__init__`, `map_dict`, `get_empty_item`, `get_info`) — is **completely unchanged**, byte-for-byte, from before this whole refactor started.

- [ ] **Step 4: Run it to verify it passes**

Run: `python3 -m unittest tests.test_mappings_aggregate -v`
Expected: `OK` (3 tests passed).

- [ ] **Step 5: Run the entire test suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: `OK` — every test from Tasks 1-10 passes (60 tests total: 1 smoke + 6 support + 16 general + 9 art + 4 genre + 3 credits + 6 translations + 4 movie + 8 tv + 3 aggregate).

- [ ] **Step 6: Verify every file compiles**

Run:
```bash
python3 -m py_compile resources/tmdbhelper/lib/items/database/mappings/__init__.py \
  resources/tmdbhelper/lib/items/database/mappings/support.py \
  resources/tmdbhelper/lib/items/database/mappings/general.py \
  resources/tmdbhelper/lib/items/database/mappings/art.py \
  resources/tmdbhelper/lib/items/database/mappings/genre.py \
  resources/tmdbhelper/lib/items/database/mappings/credits.py \
  resources/tmdbhelper/lib/items/database/mappings/translations.py \
  resources/tmdbhelper/lib/items/database/mappings/movie.py \
  resources/tmdbhelper/lib/items/database/mappings/tv.py
```
Expected: no output, exit code 0.

- [ ] **Step 7: Verify no other file in the addon references anything that moved**

Run: `grep -rn "from tmdbhelper.lib.items.database.mappings import\|from tmdbhelper.lib.items.database import mappings" resources/tmdbhelper/lib/ --include="*.py" | grep -v "resources/tmdbhelper/lib/items/database/mappings"`
Expected: every result imports only `ItemMapper` (or nothing that changed) — since `ItemMapperMethods` itself was never imported by name from outside `mappings.py` in the original codebase (only `ItemMapper` is a real external dependency), this should show no call site needing any change. If any result imports something that no longer exists at that path, stop and report before continuing.

- [ ] **Step 8: Commit**

```bash
git add resources/tmdbhelper/lib/items/database/mappings/__init__.py tests/test_mappings_aggregate.py
git commit -m "refactor(mappings): rebuild ItemMapperMethods as a thin aggregate of the 7 split mixins"
```

---

## Verification (manual, post-implementation)

The full test suite (Task 10, Step 5) is real, executable verification — not a stand-in for live testing, but a strong safety net most of this branch's other work didn't have. Still verify live in Kodi, since the test suite doesn't exercise the skin-rendering side or `get_custom_date`'s Kodi-region-dependent formatting:

1. Open a movie that belongs to a collection (exercises `MovieMapperMethods` + `get_media_item_data` + `GenreMapperMethods` together) — confirm the collection/related-movies data still displays correctly.
2. Open a TV show with multiple seasons and confirm seasons/episodes/creators still display (exercises `TVMapperMethods`).
3. Open a person's info page who has both movie and TV credits (exercises `CreditsMapperMethods`'s `get_person_movie_credits_data`/`get_person_tv_credits_data`).
4. Confirm episode air-date formatting (`get_custom_date`, e.g. "days until aired" on an upcoming episode) still renders correctly — this is the one method with no unit test coverage.
5. Check `kodi.log` for any new tracebacks under `tmdbhelper` after exercising the above.
