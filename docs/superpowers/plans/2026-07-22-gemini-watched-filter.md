# Ask Gemini Watched-Titles Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exclude titles the user has already watched (per Trakt's locally-synced watch data) from Ask Gemini's recommendation results.

**Architecture:** A small `TraktWatchedChecker` class reads the addon's existing `simplecache` local database table (already populated by the addon's Trakt sync, no new API calls) to answer "has this tmdb_id been watched?". `ListGemini.get_items()` runs this check against the cached/fetched AI recommendation list, after the raw response is retrieved but before the movie/TV split-and-cap-to-5 step, gated by a new setting.

**Tech Stack:** Python 3, existing `DatabaseAccess`/`ItemDetailsDatabase` local-cache read path (`resources/tmdbhelper/lib/files/dbfunc.py` + `resources/tmdbhelper/lib/items/database/database.py`) — no new dependencies, no new database, no network calls.

## Global Constraints

- Spec source of truth: `docs/superpowers/specs/2026-07-22-gemini-watched-filter-design.md`.
- Branch: `refactor/tmdb-helper-cleanup` (already checked out, working tree clean at plan-writing time). Commit after the task.
- "Watched" for TV shows means *any episode watched at all*, not "fully watched" — per the approved design.
- The filter must run **fresh on every `get_items()` call**, never baked into the 6-hour-cached raw AI response — watch status can change at any time, the AI recommendation list is what's expensive to produce and safe to cache.
- On a DB lookup failure of any kind, **fail open** (treat as not-watched, keep the item) — never silently drop an item because of a lookup error.
- New setting `gemini_exclude_watched`: boolean, default `true`, placed in the existing "Gemini API" settings group (api keys category, group id `4`, label `32147`) — the addon's existing home for Gemini-specific settings — visible only when Trakt is connected (`trakt_token` is set), mirroring the exact dependency pattern already used by the existing `seasons_upnext` setting (`resources/settings.xml`, general category group 4).
- New localized string id: `32546` (the highest currently-used id is `32545`, confirmed via `grep -oP '(?<=msgctxt "#)\d+' resources/language/resource.language.en_gb/strings.po | sort -n | tail -1`) — insert immediately after the existing `#32545` block, before the unrelated Kodi-core `#30030` language-name block, exactly as prior tasks in this branch's history have done.
- No pytest suite in this repo — `xbmc`/`xbmcgui` modules only exist inside a running Kodi instance. Verification is `python3 -m py_compile` for syntax and `python3 -c "import xml.dom.minidom; xml.dom.minidom.parse(...)"` for settings.xml well-formedness, same as every other task on this branch.

---

### Task 1: Trakt watched-filter for Ask Gemini

**Files:**
- Modify: `resources/tmdbhelper/lib/items/directories/tmdb/lists_gemini.py` (entire file)
- Modify: `resources/settings.xml` (api keys category, group 4)
- Modify: `resources/language/resource.language.en_gb/strings.po`

**Interfaces:**
- Consumes: `DatabaseAccess` from `tmdbhelper.lib.files.dbfunc` (existing, verified: `get_cached_values(table, item_id, keys)` returns a raw sqlite row tuple or `None`); `ItemDetailsDatabase` from `tmdbhelper.lib.items.database.database` (existing, zero-arg constructor, points at the addon's `ItemDetails.db` file which contains the Trakt-synced `simplecache` table).
- Produces: `TraktWatchedChecker.is_watched(tmdb_type, tmdb_id) -> bool` — nothing else in this plan depends on it, this is a single, self-contained task.

- [ ] **Step 1: Replace the whole file**

Verified data facts this step relies on (already confirmed against the live codebase, not guessed):
- The `simplecache` table's composite row key is `{tmdb_type}.{tmdb_id}` (e.g. `movie.550`), matching the `get_base_id(tmdb_type, tmdb_id)` convention used elsewhere in `items/database/basedata.py`.
- Column `plays` is the movie play-count (from Trakt's synced watched history) — `plays > 0` means watched.
- Column `watched_episodes` is the show episode-watched count — `watched_episodes > 0` means at least one episode watched (matches the design's "started it at all" definition).
- `DatabaseAccess.get_cached_values(table, item_id, keys)` (in `resources/tmdbhelper/lib/files/dbfunc.py`) returns `cursor.fetchone()` — either `None` (no matching row, or the DB couldn't be opened) or a tuple like `(3,)` / `(None,)` / `(0,)`. A safe truthy check is `values and values[0]` — short-circuiting means this never indexes into `None`.
- `Gemini.get_tmdb_item()` (the method that builds each recommendation item, in `resources/tmdbhelper/lib/api/gemini/api.py`) always includes `item['params']['tmdb_type']` and `item['params']['tmdb_id']` — confirmed present on every item this file's `get_items()` receives from `get_cached_response()`.

Replace the entire contents of `resources/tmdbhelper/lib/items/directories/tmdb/lists_gemini.py`:

```python
from xbmcgui import Dialog, INPUT_ALPHANUM
from tmdbhelper.lib.addon.plugin import get_localized, convert_type, get_setting
from tmdbhelper.lib.addon.logger import kodi_log
from jurialmunkey.ftools import cached_property
from jurialmunkey.parser import try_int

from tmdbhelper.lib.items.container import ContainerDefaultCacheDirectory
from tmdbhelper.lib.items.directories.lists_default import ItemCache
from tmdbhelper.lib.files.dbfunc import DatabaseAccess


class TraktWatchedChecker(DatabaseAccess):

    @cached_property
    def cache(self):
        from tmdbhelper.lib.items.database.database import ItemDetailsDatabase
        return ItemDetailsDatabase()

    def is_watched(self, tmdb_type, tmdb_id):
        key = 'plays' if tmdb_type == 'movie' else 'watched_episodes'
        item_id = f'{tmdb_type}.{tmdb_id}'
        values = self.get_cached_values('simplecache', item_id, (key,))
        return bool(values and values[0])


class ListGemini(ContainerDefaultCacheDirectory):

    cache_days = 0.25  # 6 hours default cache

    @cached_property
    def cache_name(self):
        return '_'.join(map(str, self.cache_name_tuple))

    @cached_property
    def cache_name_tuple(self):
        return (f'{self.__class__.__name__}', self.query, )

    @cached_property
    def gemini(self):
        from tmdbhelper.lib.api.gemini.api import Gemini
        return Gemini()

    @cached_property
    def openrouter(self):
        from tmdbhelper.lib.api.openrouter.api import OpenRouter
        return OpenRouter()

    @cached_property
    def watched_checker(self):
        return TraktWatchedChecker()

    @ItemCache('ItemContainer.db')
    def get_cached_response(self):
        return self.get_prompt_items()

    def get_prompt_items(self):
        from tmdbhelper.lib.addon.dialog import BusyDialog
        with BusyDialog():
            data = self.gemini.get_prompt_items(self.query)
            if data:
                kodi_log(f'Ask Gemini: served by Gemini for query "{self.query}"', 1)
            elif self.openrouter.api_key:
                status = getattr(self.gemini.last_response, 'status_code', None)
                reason = 'rate-limited (429)' if self.gemini.is_rate_limited else f'status={status}'
                kodi_log(f'Ask Gemini: Gemini failed ({reason}), falling back to OpenRouter for query "{self.query}"', 1)
                data = self.openrouter.get_prompt_items(self.query)
                if data:
                    kodi_log(f'Ask Gemini: served by OpenRouter for query "{self.query}"', 1)
        return data

    def is_item_watched(self, item):
        params = item.get('params') or {}
        tmdb_type = params.get('tmdb_type')
        tmdb_id = params.get('tmdb_id')
        if not tmdb_type or not tmdb_id:
            return False
        try:
            return self.watched_checker.is_watched(tmdb_type, tmdb_id)
        except Exception as exc:
            kodi_log(f'Ask Gemini: watched-status lookup failed for {tmdb_type}.{tmdb_id}: {exc}', 1)
            return False

    def filter_watched(self, items):
        if not get_setting('gemini_exclude_watched'):
            return items
        return [i for i in items if not self.is_item_watched(i)]

    def get_items(self, query=None, tmdb_type=None, limit=None, **kwargs):
        if not self.gemini.api_key:
            Dialog().ok('Gemini', f"{get_localized(32150)}[CR]{get_localized(32151).format('https://aistudio.google.com/app/api-keys')}")
            return
        self.query = query or Dialog().input(get_localized(32044), type=INPUT_ALPHANUM)
        if not self.query:
            return
        items = self.get_cached_response()
        if not items:
            Dialog().ok('Gemini', self.gemini.get_error_message())
            return
        items = self.filter_watched(items)
        if tmdb_type:
            mediatype = 'movie' if tmdb_type == 'movie' else 'tvshow'
            items = [i for i in items if i.get('infolabels', {}).get('mediatype') == mediatype]
        if limit:
            items = items[:try_int(limit)]
        self.container_content = convert_type(tmdb_type or 'both', 'container', items=items)
        self.plugin_category = 'Gemini'
        return items
```

Key points for whoever implements this:
- The watched-filter (`filter_watched`) runs *after* `get_cached_response()` — meaning it re-evaluates on every call, cache hit or miss, exactly per the design's "check fresh, cache the AI response but not the filter result" requirement.
- The `if not items: Dialog().ok(...)` check happens **before** `filter_watched` — that dialog is for "Gemini/OpenRouter genuinely returned nothing", not for "everything got filtered as watched". If filtering removes every item, `items` becomes `[]`, no dialog fires, and the panel just renders empty — this is the accepted "fewer than 5 items" tradeoff from the design doc, not a new error case to handle.
- `is_item_watched` fails open (returns `False`, i.e. "not watched", i.e. keep the item) both when `tmdb_type`/`tmdb_id` are missing from an item's `params` and when the DB lookup itself raises — per the design's explicit fail-open requirement.

- [ ] **Step 2: Verify it compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/items/directories/tmdb/lists_gemini.py`
Expected: no output, exit code 0.

- [ ] **Step 3: Add the new setting to settings.xml**

In `resources/settings.xml`, find the "Gemini API" group (api keys category, group 4):

```xml
            <group id="4" label="32147">
                <setting id="gemini_apikey" type="string" label="32148" help="">
                    <level>0</level>
                    <default/>
                    <constraints>
                        <allowempty>true</allowempty>
                    </constraints>
                    <control type="edit" format="string">
                        <heading>32148</heading>
                    </control>
                </setting>
            </group>
```

Replace with:

```xml
            <group id="4" label="32147">
                <setting id="gemini_apikey" type="string" label="32148" help="">
                    <level>0</level>
                    <default/>
                    <constraints>
                        <allowempty>true</allowempty>
                    </constraints>
                    <control type="edit" format="string">
                        <heading>32148</heading>
                    </control>
                </setting>
                <setting id="gemini_exclude_watched" type="boolean" label="32546" help="">
                    <level>0</level>
                    <default>true</default>
                    <control type="toggle"/>
                    <dependencies>
                        <dependency type="visible">
                            <condition operator="!is" setting="trakt_token"/>
                        </dependency>
                    </dependencies>
                </setting>
            </group>
```

The `<dependency type="visible"><condition operator="!is" setting="trakt_token"/></dependency>` block is copied verbatim from the existing `seasons_upnext` setting (`resources/settings.xml`, general category group 4) — it hides this setting entirely unless Trakt is connected, since the setting does nothing without Trakt.

- [ ] **Step 4: Verify settings.xml is well-formed**

Run: `python3 -c "import xml.dom.minidom; xml.dom.minidom.parse('resources/settings.xml'); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Add the new string to strings.po**

In `resources/language/resource.language.en_gb/strings.po`, find the end of the `#32545` block:

```
#: /resources/settings.xml
msgctxt "#32545"
msgid "Queue episodes from all remaining seasons"
msgstr ""

msgctxt "#30030"
```

Replace with:

```
#: /resources/settings.xml
msgctxt "#32545"
msgid "Queue episodes from all remaining seasons"
msgstr ""

#: /resources/settings.xml
msgctxt "#32546"
msgid "Exclude titles you've already watched"
msgstr ""

msgctxt "#30030"
```

- [ ] **Step 6: Verify the new string entry**

Run: `grep -A2 'msgctxt "#32546"' resources/language/resource.language.en_gb/strings.po`
Expected:
```
msgctxt "#32546"
msgid "Exclude titles you've already watched"
msgstr ""
```

- [ ] **Step 7: Commit**

```bash
git add resources/tmdbhelper/lib/items/directories/tmdb/lists_gemini.py resources/settings.xml resources/language/resource.language.en_gb/strings.po
git commit -m "feat(gemini): exclude already-watched titles using Trakt watch data"
```

---

## Verification (manual, post-implementation)

No pytest suite exists for this repo — verify live in Kodi:

1. With "Exclude titles you've already watched" on (default) and Trakt connected: mark a movie or show as watched in Trakt (or use one you already have watched history for). Ask Gemini for recommendations in that title's genre/category and confirm it doesn't appear in the results, even though it would plausibly be a relevant Gemini suggestion.
2. Turn the setting off and repeat the same query (a *new* query, since responses are cached for 6 hours) — confirm previously-watched titles can now appear again.
3. Disconnect Trakt (or check on a profile with no `trakt_token` set) and confirm the setting itself is hidden from Settings > API Keys > Gemini API.
4. Check `kodi.log` for the new `Ask Gemini: watched-status lookup failed for ...` line — it should never appear under normal operation; if it does, the fail-open behavior should still have kept the item in results rather than dropping it.
