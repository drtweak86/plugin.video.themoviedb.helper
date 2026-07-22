# TMDb Helper TODO-Derived Feature Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship 5 small, independent features in `plugin.video.themoviedb.helper`: a skin-configurable art refresh interval, a configurable cast-list limit, dynamic naming for related-content lists, a multi-season next-episodes playlist option, and an automatic OpenRouter fallback for the Ask Gemini feature when Gemini's free tier rate-limits.

**Architecture:** Each feature is a small, targeted change to existing classes, following patterns already established elsewhere in the codebase (skin-string reads, integer spinner settings, `plugin_name` template pre-interpolation, and a shared-base-class provider split matching this session's earlier `lists_view_db.py` refactor). No new architecture is introduced — Feature 5 adds one new file (`api/openrouter/api.py`) as a sibling to the existing `api/gemini/api.py`.

**Tech Stack:** Python 3 (Kodi addon, no pytest suite in this repo — `xbmc`/`xbmcgui` modules are only importable inside the Kodi runtime). Verification throughout is `python3 -m py_compile` for syntax correctness plus `python3 -c "import xml.dom.minidom; xml.dom.minidom.parse(...)"` for settings.xml well-formedness — the same verification approach used in this branch's earlier 18-task cleanup pass, since a real test run requires a live Kodi instance.

## Global Constraints

- Spec source of truth: `docs/superpowers/specs/2026-07-22-tmdbhelper-todo-features-design.md`.
- Branch: `refactor/tmdb-helper-cleanup` (already checked out, working tree clean at plan-writing time). Commit after every task.
- New localized strings go in `resources/language/resource.language.en_gb/strings.po`, inserted immediately after the existing `#32541` block (the file's addon-string region ends there; entries after that point are an unrelated Kodi-core language-name block starting at `#30030` — new entries MUST go before that block, not after it).
- New string IDs, in order: `32542` "OpenRouter API", `32543` "OpenRouter API key", `32544` "Cast list limit", `32545` "Queue episodes from all remaining seasons".
- Settings.xml indentation: 8 spaces for `<category>`, 12 for `<group>`, 16 for `<setting>`, 20 for tags inside a `<setting>`. Match exactly — Kodi's settings parser is whitespace-tolerant but every existing entry in this file uses this indentation consistently.
- Feature 3's exact list-naming prepositions ("Similar to X", "Recommended for X", "Reviews for X", "Keywords for X") are as specified in the design doc — do not change wording without checking with the user first, since "Similar to Inception" was an explicitly approved reference example.
- Feature 5's `openrouter/free` model slug and any required attribution headers (`HTTP-Referer`/`X-Title`) are unverified against OpenRouter's live docs — Task 6 includes an explicit verification step before finalizing that code.

---

### Task 1: Skin-configurable art refresh interval

**Files:**
- Modify: `resources/tmdbhelper/lib/monitor/imgmon.py:1-7` (imports), `imgmon.py:55` (attribute → property)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing other tasks depend on. `ImagesMonitor._next_refresh_increment` remains readable as `self._next_refresh_increment` exactly as before (now a property instead of a class attribute) — no external caller changes.

- [ ] **Step 1: Update imports**

In `resources/tmdbhelper/lib/monitor/imgmon.py`, replace lines 1-7:

```python
from tmdbhelper.lib.monitor.images import ImageManipulations
from tmdbhelper.lib.monitor.poller import Poller, POLL_MIN_INCREMENT
from tmdbhelper.lib.monitor.listitemgetter import ListItemInfoGetter
from tmdbhelper.lib.addon.plugin import get_condvisibility
from tmdbhelper.lib.addon.tmdate import set_timestamp, get_timestamp
from tmdbhelper.lib.addon.logger import kodi_try_except
from tmdbhelper.lib.addon.thread import SafeThread
```

with:

```python
from tmdbhelper.lib.monitor.images import ImageManipulations
from tmdbhelper.lib.monitor.poller import Poller, POLL_MIN_INCREMENT
from tmdbhelper.lib.monitor.listitemgetter import ListItemInfoGetter
from tmdbhelper.lib.addon.plugin import get_condvisibility, get_infolabel
from tmdbhelper.lib.addon.tmdate import set_timestamp, get_timestamp
from tmdbhelper.lib.addon.logger import kodi_try_except
from tmdbhelper.lib.addon.thread import SafeThread
from jurialmunkey.parser import try_int
```

- [ ] **Step 2: Convert `_next_refresh_increment` to a skin-driven property**

In the same file, replace line 55:

```python
    _next_refresh_increment = 10  # Reupdate idle item every ten seconds for extrafanart TODO: Allow skin to set value?
```

with:

```python
    @property
    def _next_refresh_increment(self):
        return try_int(get_infolabel('Skin.String(TMDbHelper.ArtRefreshInterval)')) or 10
```

The surrounding class attributes (`_this_refresh_increment = 3`, etc.) are untouched — only this one line changes.

- [ ] **Step 3: Verify it compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/monitor/imgmon.py`
Expected: no output, exit code 0 (compiled OK).

- [ ] **Step 4: Verify no other reader assumes a class attribute**

Run: `grep -rn "_next_refresh_increment" resources/tmdbhelper/lib/`
Expected: exactly two matches — the property definition itself (`imgmon.py:55`, now the `@property` line) and its one read site at `imgmon.py:126` (`self._next_refresh = set_timestamp(self._next_refresh_increment)`). If any other file assigns to `ImagesMonitor._next_refresh_increment` or a subclass overrides it as a plain value, stop and report — a property with no setter breaks that call.

- [ ] **Step 5: Commit**

```bash
git add resources/tmdbhelper/lib/monitor/imgmon.py
git commit -m "feat(imgmon): read art refresh interval from Skin.String(TMDbHelper.ArtRefreshInterval)"
```

---

### Task 2: Configurable cast-list limit

**Files:**
- Modify: `resources/tmdbhelper/lib/items/database/basemeta_factories/concrete_classes/credits.py:1-8`
- Modify: `resources/settings.xml` (expert category, group 1)
- Modify: `resources/language/resource.language.en_gb/strings.po`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing other tasks depend on. New setting id `castmember_limit` (integer), new string id `32544`.

- [ ] **Step 1: Add the `get_setting` import and convert `conditions` to a property**

In `resources/tmdbhelper/lib/items/database/basemeta_factories/concrete_classes/credits.py`, replace lines 1-18:

```python
from tmdbhelper.lib.items.database.basemeta_factories.concrete_classes.baseclass import ItemDetailsList


class CastMember(ItemDetailsList):
    table = 'castmember'
    keys = ('tmdb_id', 'role', 'ordering', 'appearances', 'guest', 'parent_id')
    conflict_constraint = 'tmdb_id, role, parent_id'
    conditions = 'parent_id=? GROUP BY castmember.tmdb_id ORDER BY IFNULL(ordering, 9999) ASC LIMIT 100'  # WHERE conditions  # TODO: Move limit to settings ???
    cached_data_keys = (
        'castmember.tmdb_id', 'GROUP_CONCAT(role, " / ") as role', 'ordering', 'appearances', 'guest',
        'name', 'gender', 'biography', 'known_for_department',
        (
            '(    SELECT art.icon FROM art'
            '     WHERE art.parent_id=\'person.\' || castmember.tmdb_id AND art.type=\'profiles\' '
            '     ORDER BY art.rating DESC LIMIT 1'
            ') as thumb'
        ),
    )

    def image_path_func(self, v):
```

with:

```python
from tmdbhelper.lib.addon.plugin import get_setting
from tmdbhelper.lib.items.database.basemeta_factories.concrete_classes.baseclass import ItemDetailsList


class CastMember(ItemDetailsList):
    table = 'castmember'
    keys = ('tmdb_id', 'role', 'ordering', 'appearances', 'guest', 'parent_id')
    conflict_constraint = 'tmdb_id, role, parent_id'
    cached_data_keys = (
        'castmember.tmdb_id', 'GROUP_CONCAT(role, " / ") as role', 'ordering', 'appearances', 'guest',
        'name', 'gender', 'biography', 'known_for_department',
        (
            '(    SELECT art.icon FROM art'
            '     WHERE art.parent_id=\'person.\' || castmember.tmdb_id AND art.type=\'profiles\' '
            '     ORDER BY art.rating DESC LIMIT 1'
            ') as thumb'
        ),
    )

    @property
    def conditions(self):
        limit = get_setting('castmember_limit', 'int') or 100
        return f'parent_id=? GROUP BY castmember.tmdb_id ORDER BY IFNULL(ordering, 9999) ASC LIMIT {limit}'

    def image_path_func(self, v):
```

Everything below `image_path_func` (the `cached_data_table` property, `CrewMember` and its subclasses, `Person`) is unchanged — `CrewMember.conditions` (line 31 in the original file) keeps its own separate hardcoded `LIMIT 100`, untouched by this task.

- [ ] **Step 2: Verify it compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/items/database/basemeta_factories/concrete_classes/credits.py`
Expected: no output, exit code 0.

- [ ] **Step 3: Add the new setting to settings.xml**

In `resources/settings.xml`, find the `expert` category's group 1 (currently ending with the `only_resolve_strm` setting):

```xml
                <setting id="only_resolve_strm" type="boolean" label="32373" help="">
                    <level>0</level>
                    <default>False</default>
                    <control type="toggle"/>
                </setting>
            </group>
```

Replace with:

```xml
                <setting id="only_resolve_strm" type="boolean" label="32373" help="">
                    <level>0</level>
                    <default>False</default>
                    <control type="toggle"/>
                </setting>
                <setting id="castmember_limit" type="integer" label="32544" help="">
                    <level>0</level>
                    <default>100</default>
                    <constraints>
                        <options>
                            <option>25</option>
                            <option>50</option>
                            <option>100</option>
                            <option>150</option>
                            <option>200</option>
                        </options>
                    </constraints>
                    <control type="spinner" format="string"/>
                </setting>
            </group>
```

- [ ] **Step 4: Verify settings.xml is well-formed**

Run: `python3 -c "import xml.dom.minidom; xml.dom.minidom.parse('resources/settings.xml'); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Add the new string to strings.po**

In `resources/language/resource.language.en_gb/strings.po`, find the end of the `#32541` block:

```
#: /resources/tmdbhelper/lib/api/gemini/api.py
msgctxt "#32541"
msgid "Gemini responded, but no results could be matched in your local database."
msgstr ""

msgctxt "#30030"
```

Replace with:

```
#: /resources/tmdbhelper/lib/api/gemini/api.py
msgctxt "#32541"
msgid "Gemini responded, but no results could be matched in your local database."
msgstr ""

#: /resources/settings.xml
msgctxt "#32544"
msgid "Cast list limit"
msgstr ""

msgctxt "#30030"
```

(String IDs `32542`/`32543` are reserved for Task 7's OpenRouter settings — they are added in that task, not here, to keep each task's diff scoped to what it actually needs. Leaving a gap between `32541` and `32544` in this task's commit is expected and fine; the full block is only contiguous once Task 7 lands.)

- [ ] **Step 6: Verify the new string entry**

Run: `grep -A2 'msgctxt "#32544"' resources/language/resource.language.en_gb/strings.po`
Expected:
```
msgctxt "#32544"
msgid "Cast list limit"
msgstr ""
```

- [ ] **Step 7: Commit**

```bash
git add resources/tmdbhelper/lib/items/database/basemeta_factories/concrete_classes/credits.py resources/settings.xml resources/language/resource.language.en_gb/strings.po
git commit -m "feat(credits): make cast list limit configurable via settings"
```

---

### Task 3: Dynamic related-list naming

**Files:**
- Modify: `resources/tmdbhelper/lib/items/directories/tmdb/lists_related.py` (entire file)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing other tasks depend on. `ListRelatedProperties.item_title` is a new `cached_property` returning a `str` (empty string if the source item's title can't be resolved).

- [ ] **Step 1: Add `item_title` to `ListRelatedProperties` and apply it to all 4 subclasses**

Replace the entire contents of `resources/tmdbhelper/lib/items/directories/tmdb/lists_related.py`:

```python
from tmdbhelper.lib.items.directories.tmdb.lists_standard import ListStandard, ListStandardProperties
from tmdbhelper.lib.items.directories.tmdb.lists_allitems import ItemKeywords, ItemReviews
from jurialmunkey.ftools import cached_property


class ListRelatedProperties(ListStandardProperties):
    @cached_property
    def url(self):
        return self.request_url.format(tmdb_type=self.tmdb_type, tmdb_id=self.tmdb_id)

    @cached_property
    def cache_name_tuple(self):
        return (
            self.class_name,
            self.tmdb_type,
            self.tmdb_id,
            self.page,
            self.pmax
        )

    @cached_property
    def item_title(self):
        from tmdbhelper.lib.items.database.baseitem_factories.factory import BaseItemFactory
        mediatype = 'movie' if self.tmdb_type == 'movie' else 'tvshow'
        sync = BaseItemFactory(mediatype)
        sync.tmdb_id = self.tmdb_id
        try:
            return sync.data['infolabels']['title']
        except (KeyError, TypeError, AttributeError):
            return ''


class ListRelated(ListStandard):
    list_properties_class = ListRelatedProperties

    def get_items(self, *args, tmdb_id=None, **kwargs):
        self.list_properties.tmdb_id = tmdb_id
        return super().get_items(*args, **kwargs)


class ListRecommendations(ListRelated):

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.plugin_name = f'{{localized}} for {list_properties.item_title}' if list_properties.item_title else '{localized}'
        list_properties.dbid_sorted = True
        list_properties.request_url = '{tmdb_type}/{tmdb_id}/recommendations'
        list_properties.localize = 32223
        list_properties.page_length = 2  # Recommendations only have 2 pages
        list_properties.length = 2
        return list_properties


class ListSimilar(ListRelated):

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.plugin_name = f'{{localized}} to {list_properties.item_title}' if list_properties.item_title else '{localized}'
        list_properties.dbid_sorted = True
        list_properties.request_url = '{tmdb_type}/{tmdb_id}/similar'
        list_properties.localize = 32224
        return list_properties


class ListReviews(ListRelated):

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.plugin_name = f'{{localized}} for {list_properties.item_title}' if list_properties.item_title else '{localized}'
        list_properties.dbid_sorted = True
        list_properties.request_url = '{tmdb_type}/{tmdb_id}/reviews'
        list_properties.tmdb_type = 'review'
        list_properties.localize = 32188
        return list_properties

    def get_mapped_item(self, item, *args, **kwargs):
        return ItemReviews(**item).item


class ListKeywords(ListRelated):

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.plugin_name = f'{{localized}} for {list_properties.item_title}' if list_properties.item_title else '{localized}'
        list_properties.request_url = 'movie/{tmdb_id}/keywords'
        list_properties.results_key = 'keywords'
        list_properties.tmdb_type = 'keyword'
        list_properties.localize = 21861
        return list_properties

    def get_mapped_item(self, item, *args, **kwargs):
        return ItemKeywords(**item).item
```

Note on `ListReviews`: its `configure_list_properties` sets `list_properties.tmdb_type = 'review'` on line 5 of that method (after the `plugin_name` line, which is what matters — `item_title` must be read from `list_properties.item_title` while `list_properties.tmdb_type` is still the *source* item's type, i.e. before that override). The plugin_name line above is placed correctly, before the `tmdb_type` override, exactly matching the original TODO's position. `ListKeywords` similarly overrides `tmdb_type = 'keyword'` after its `plugin_name` line — same ordering preserved.

- [ ] **Step 2: Verify it compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/items/directories/tmdb/lists_related.py`
Expected: no output, exit code 0.

- [ ] **Step 3: Verify the TODO comments are gone and no other file references the old exact strings**

Run: `grep -n "TODO: BASED ON" resources/tmdbhelper/lib/items/directories/tmdb/lists_related.py`
Expected: no output (all 4 TODOs replaced).

- [ ] **Step 4: Commit**

```bash
git add resources/tmdbhelper/lib/items/directories/tmdb/lists_related.py
git commit -m "feat(lists_related): name related-content lists after their source item"
```

---

### Task 4: Multi-season next-episodes playlist

**Files:**
- Modify: `resources/tmdbhelper/lib/player/action/episodes.py:30-35`
- Modify: `resources/settings.xml` (players category, group 2)
- Modify: `resources/language/resource.language.en_gb/strings.po`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing other tasks depend on. New setting id `player_queue_all_seasons` (boolean, default `False`), new string id `32545`.

- [ ] **Step 1: Add the `get_setting` import and branch `all_episodes` on the new setting**

In `resources/tmdbhelper/lib/player/action/episodes.py`, replace lines 30-35:

```python
    @cached_property
    def all_episodes(self):
        from tmdbhelper.lib.items.database.baseview_factories.factory import BaseViewFactory
        # sync = BaseViewFactory('flatseasons', 'tv', self.tmdb_id)
        sync = BaseViewFactory('episodes', 'tv', self.tmdb_id, season=self.season)  # Only get current season to avoid massive playlists TODO: Make optional get more than one season / all seasons?
        return sync.data
```

with:

```python
    @cached_property
    def all_episodes(self):
        from tmdbhelper.lib.items.database.baseview_factories.factory import BaseViewFactory
        from tmdbhelper.lib.addon.plugin import get_setting
        if get_setting('player_queue_all_seasons'):
            sync = BaseViewFactory('flatseasons', 'tv', self.tmdb_id)
        else:
            sync = BaseViewFactory('episodes', 'tv', self.tmdb_id, season=self.season)
        return sync.data
```

`is_future_episode()` (further down the same file) is unchanged — it already compares `season`/`episode` numbers correctly across seasons (rows from a later season always pass, rows from the current season are filtered by episode number, rows from an earlier season are always excluded), so it works unmodified against the wider `flatseasons` result set.

- [ ] **Step 2: Verify it compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/player/action/episodes.py`
Expected: no output, exit code 0.

- [ ] **Step 3: Add the new setting to settings.xml**

In `resources/settings.xml`, find the `players` category's group 2 (currently containing `combined_players` then `bundled_players` then `players_url`):

```xml
                <setting id="bundled_players" type="boolean" label="32037" help="">
                    <level>0</level>
                    <default>True</default>
                    <control type="toggle"/>
                </setting>
                <setting id="players_url" type="string" label="32016" help="">
```

Replace with:

```xml
                <setting id="bundled_players" type="boolean" label="32037" help="">
                    <level>0</level>
                    <default>True</default>
                    <control type="toggle"/>
                </setting>
                <setting id="player_queue_all_seasons" type="boolean" label="32545" help="">
                    <level>0</level>
                    <default>False</default>
                    <control type="toggle"/>
                </setting>
                <setting id="players_url" type="string" label="32016" help="">
```

- [ ] **Step 4: Verify settings.xml is well-formed**

Run: `python3 -c "import xml.dom.minidom; xml.dom.minidom.parse('resources/settings.xml'); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Add the new string to strings.po**

In `resources/language/resource.language.en_gb/strings.po`, find the entry added by Task 2 (`#32544`, "Cast list limit"):

```
#: /resources/settings.xml
msgctxt "#32544"
msgid "Cast list limit"
msgstr ""

msgctxt "#30030"
```

Replace with:

```
#: /resources/settings.xml
msgctxt "#32544"
msgid "Cast list limit"
msgstr ""

#: /resources/settings.xml
msgctxt "#32545"
msgid "Queue episodes from all remaining seasons"
msgstr ""

msgctxt "#30030"
```

(This task depends on Task 2 having landed first, since it anchors on Task 2's `#32544` block. Run Task 2 before Task 4.)

- [ ] **Step 6: Verify the new string entry**

Run: `grep -A2 'msgctxt "#32545"' resources/language/resource.language.en_gb/strings.po`
Expected:
```
msgctxt "#32545"
msgid "Queue episodes from all remaining seasons"
msgstr ""
```

- [ ] **Step 7: Commit**

```bash
git add resources/tmdbhelper/lib/player/action/episodes.py resources/settings.xml resources/language/resource.language.en_gb/strings.po
git commit -m "feat(episodes): add setting to queue next episodes across all remaining seasons"
```

---

### Task 5: Split `Gemini` into `BaseAIRecommender` + `Gemini`

**Files:**
- Modify: `resources/tmdbhelper/lib/api/gemini/api.py` (entire file)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `BaseAIRecommender(RequestAPI)` in `tmdbhelper.lib.api.gemini.api`, with:
  - `last_response` (inherited from `RequestAPI`, already set by `get_simple_api_request`)
  - `last_error_message = None` (class attribute)
  - `api_key = None` (class attribute, overridden per-subclass)
  - `is_rate_limited` (property, `bool`) — `True` when the last HTTP response had status 429
  - `get_error_message(self)` — returns a localized error string based on `last_response`/`last_error_message`
  - `get_prompt_query(self, prompt_text)` — returns the filled `QUERY_PROMPT_TEMPLATE` string
  - `get_prompt_request(self, prompt_text)` — abstract-ish: calls `self.get_api_request_json(self.req_api_url, postdata=self.get_prompt_postdata(prompt_text), headers=self.headers, method='json')` (subclasses supply `req_api_url`/`get_prompt_postdata`/`headers`)
  - `get_prompt_recommendations(self, prompt_text)`, `get_prompt_items(self, prompt_text)`, `get_prompt_text(self, prompt_text)` — orchestration, unchanged behavior
  - `get_tmdb_item(self, i)`, `get_tmdb_items(self, data)` — unchanged behavior
  - `get_json_from_candidate(text)` (staticmethod) — unchanged behavior
  - `get_candidates(data)` (staticmethod) — **NOT** provided by the base; each subclass must define its own (Gemini's and OpenRouter's response shapes differ)
  - `database` (cached_property) — unchanged
  - `parse_bold`/`parse_italics`/`parse_regex`/`parse_string` (unchanged, used by callers outside this refactor)
  - `GEMINI_ERROR_UNAUTHORIZED`, `GEMINI_ERROR_RATE_LIMIT`, `GEMINI_ERROR_NETWORK`, `GEMINI_ERROR_GENERIC`, `GEMINI_ERROR_NO_MATCHES` — kept as module-level constants (unchanged names, despite the "GEMINI\_" prefix now describing shared error codes — renaming them is out of scope for this task to keep the diff mechanical and avoid touching every call site of these constants)
  - `Gemini(BaseAIRecommender)` — keeps `headers`, `get_prompt_postdata`, `get_candidates`, `__init__`, `req_api_url` construction, `api_key = get_setting('gemini_apikey', 'str')`

- [ ] **Step 1: Replace the whole file with the split version**

Replace the entire contents of `resources/tmdbhelper/lib/api/gemini/api.py`:

```python
from json import loads
from tmdbhelper.lib.addon.plugin import get_setting, get_localized
from tmdbhelper.lib.addon.logger import kodi_log
from tmdbhelper.lib.api.request import RequestAPI
from jurialmunkey.ftools import cached_property
import re


GEMINI_DEFAULT_MODEL_ID = "gemini-2.5-flash-lite"  # "gemini-2.5-flash-lite", "gemini-2.5-flash"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

GEMINI_ERROR_UNAUTHORIZED = 32537
GEMINI_ERROR_RATE_LIMIT = 32538
GEMINI_ERROR_NETWORK = 32539
GEMINI_ERROR_GENERIC = 32540
GEMINI_ERROR_NO_MATCHES = 32541

QUERY_PROMPT_TEMPLATE_JSON_SHAPE = '''
{
  "recommendations": [
    {
      "title": "Name or Title 1",
      "year": 2000,
      "type": "Movie" | "Show",
      "reason": "Description for why this item is recommended"
    }
  ]
}
'''

QUERY_PROMPT_TEMPLATE_FIELD_RULES = '''
- Each recommendation MUST have a "type":
  - "Movie"  => a film / movie
  - "Show"   => a TV series / TV mini-series

- "year" SHOULD be a single 4-digit integer year when known.

- "reason" SHOULD be a sentence describing why you have made this recommendation

'''


QUERY_PROMPT_TEMPLATE = '''
You are a movie/TV recommendations engine.

You always respond with ONE JSON object, nothing else.

JSON OUTPUT SHAPE (MUST follow exactly):

{json_shape}

Field rules:

{field_rules}

LIMITS:

- You MUST NOT return more than 10 items.
- For general recommendation prompts ("recommend some...", "movies similar to..."),
  try to return 10 items, but fewer is allowed if appropriate.
- Unless the prompt explicitly asks for only Movies or only Shows, aim for a
  roughly even mix of "Movie" and "Show" types (e.g. around 5 of each out of 10)
  so that separate Movie and Show result lists can both be populated. If the
  subject matter genuinely only fits one type, an uneven mix is fine.

PROMPT (the original user text to answer):

{prompt_text}

Now:

1. Produce ONE JSON object exactly in the shape above.
2. Do NOT include any explanation, comments, or extra text outside the JSON object.
'''


class BaseAIRecommender(RequestAPI):

    api_key = None
    last_error_message = None

    @property
    def is_rate_limited(self):
        return getattr(self.last_response, 'status_code', None) == 429

    def get_error_message(self):
        if self.last_error_message:
            return self.last_error_message
        response = self.last_response
        if response is None:
            return get_localized(GEMINI_ERROR_NETWORK)
        status = getattr(response, 'status_code', None)
        if status in (401, 403):
            return get_localized(GEMINI_ERROR_UNAUTHORIZED)
        if status == 429:
            return get_localized(GEMINI_ERROR_RATE_LIMIT)
        return get_localized(GEMINI_ERROR_GENERIC)

    def get_prompt_query(self, prompt_text):
        return QUERY_PROMPT_TEMPLATE.format(
            json_shape=QUERY_PROMPT_TEMPLATE_JSON_SHAPE,
            field_rules=QUERY_PROMPT_TEMPLATE_FIELD_RULES,
            prompt_text=prompt_text
        )

    def get_prompt_request(self, prompt_text):
        return self.get_api_request_json(
            self.req_api_url,
            postdata=self.get_prompt_postdata(prompt_text),
            headers=self.headers,
            method='json'
        )

    def get_prompt_recommendations(self, prompt_text):
        data = self.get_prompt_text(self.get_prompt_query(prompt_text))
        if not data:
            return
        data = self.get_json_from_candidate(data)
        return data

    def get_prompt_items(self, prompt_text):
        self.last_error_message = None
        data = self.get_prompt_recommendations(prompt_text)
        if not data:
            return
        data = self.get_tmdb_items(data)
        if not data:
            self.last_error_message = get_localized(GEMINI_ERROR_NO_MATCHES)
        return data

    def get_prompt_text(self, prompt_text):
        data = self.get_prompt_request(prompt_text)
        if not data:
            return
        return self.get_candidates(data)

    def get_prompt_text_parsed(self, prompt_text):
        data = self.get_prompt_text(prompt_text)
        if not data:
            return
        return self.parse_string(data)

    @staticmethod
    def parse_bold(string):
        return BaseAIRecommender.parse_regex(string, r'\*\*(.+?)\*\*', '[B]{}[/B]')

    @staticmethod
    def parse_italics(string):
        return BaseAIRecommender.parse_regex(string, r'\*(.+?)\*', '[I]{}[/I]')

    @staticmethod
    def parse_regex(string, regex, restr):
        match = re.search(regex, string)
        if not match:
            return string
        string = string.replace(match.group(0), restr.format(match.group(1)))
        return BaseAIRecommender.parse_regex(string, regex, restr)

    @staticmethod
    def parse_string(string):
        string = string.replace('*  ', '•  ')
        string = BaseAIRecommender.parse_bold(string)
        string = BaseAIRecommender.parse_italics(string)
        string = string.replace('\n', '[CR]')
        return string

    @cached_property
    def database(self):
        from tmdbhelper.lib.query.database.database import FindQueriesDatabase
        return FindQueriesDatabase()

    def get_tmdb_item(self, i):

        try:
            name = i['title']
            year = i['year']
            mode = i['type']
        except (TypeError, KeyError):
            kodi_log(f'AI recommender INVALID SPEC: {i}', 1)
            return

        if mode not in ('Movie', 'Show'):
            kodi_log(f'AI recommender INVALID SPEC: {i}', 1)
            return

        tmdb_type = 'movie' if mode == 'Movie' else 'tv'
        try:
            tmdb_id = self.database.get_tmdb_id(tmdb_type=tmdb_type, query=name, year=year)
            tmdb_id = tmdb_id or self.database.get_tmdb_id(tmdb_type=tmdb_type, query=name)  # Try again without year
        except Exception as exc:
            kodi_log(f'AI recommender DB LOOKUP ERROR for {name}: {exc}', 1)
            tmdb_id = None

        if not tmdb_id:
            kodi_log(f'AI recommender UNKNOWN ITEM: {i}', 1)
            return

        reason = i.get('reason') or ''

        item = {
            'infolabels': {
                'mediatype': 'movie' if tmdb_type == 'movie' else 'tvshow',
            },
            'infoproperties': {
                'plot_affix': f'[B]Gemini {get_localized(32223)}:[/B] {reason}[CR]',
                'reason': reason,
            },
            'unique_ids': {
                'tmdb': tmdb_id,
            },
            'params': {
                'info': 'details',
                'tmdb_type': tmdb_type,
                'tmdb_id': tmdb_id,
            }
        }

        return item

    def get_tmdb_items(self, data):

        try:
            data = data['recommendations']
        except (TypeError, KeyError):
            kodi_log(f'AI recommender FAILED: Unable to locate recommendations data', 1)
            return

        from tmdbhelper.lib.addon.thread import ParallelThread
        with ParallelThread(data, self.get_tmdb_item) as pt:
            items = pt.queue

        return [i for i in items if i]

    @staticmethod
    def get_json_from_candidate(text):
        """
        Given raw text from the model, find the first {...} block and parse it as JSON.
        This lets us ignore any accidental extra text or markdown fences.
        """
        if not text:
            return
        # Clean up common markdown block formatting
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```[a-zA-Z]*\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned).strip()

        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            kodi_log(f'AI recommender FAILED: Unable to find json data in response', 1)
            return
        try:
            return loads(cleaned[start:end + 1])
        except Exception as exc:
            kodi_log(f'AI recommender FAILED: JSON parse error: {exc}', 1)
            return


class Gemini(BaseAIRecommender):

    api_key = get_setting('gemini_apikey', 'str')

    def __init__(self, api_key=None):
        api_key = api_key or self.api_key

        super(Gemini, self).__init__(
            req_api_name='Gemini',
            req_api_url=f"{GEMINI_API_BASE}/models/{GEMINI_DEFAULT_MODEL_ID}:generateContent",
            timeout=30,
        )

        Gemini.api_key = api_key

    @property
    def headers(self):
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

    @headers.setter
    def headers(self, value):
        """ Ignore base class req_api attempting to set headers """
        return

    def get_prompt_postdata(self, prompt_text):
        return {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt_text}]
                }
            ]
        }

    @staticmethod
    def get_candidates(data):
        try:
            parts = data['candidates'][0]['content']['parts']
        except (TypeError, IndexError, KeyError):
            kodi_log(f'Gemini FAILED: Unable to get parts', 1)
            return
        if not parts:
            kodi_log(f'Gemini FAILED: Unable to get parts', 1)
            return
        return "".join(part.get("text", "") for part in parts).strip()
```

Two intentional, narrow behavior notes (both acceptable — flag if either turns out to matter in review):
- Log messages that previously said `'Gemini FAILED: ...'` / `'Gemini INVALID SPEC: ...'` / `'Gemini UNKNOWN ITEM: ...'` / `'Gemini DB LOOKUP ERROR ...'` inside methods that moved to the shared base (`get_tmdb_item`, `get_tmdb_items`, `get_json_from_candidate`) are renamed to `'AI recommender ...'` since those methods now run for both Gemini and OpenRouter — a log line reading "Gemini FAILED" when OpenRouter actually failed would be misleading. The two `get_candidates` log lines that stay Gemini-specific (`'Gemini FAILED: Unable to get parts'`) correctly keep the `Gemini` prefix since that method itself stays in the `Gemini` subclass.
- `get_tmdb_item`'s `plot_affix` line still hardcodes the literal text `Gemini {get_localized(32223)}` regardless of which provider actually served the recommendation. This is deliberate: string `32223` is "Recommended" (a content-facing label unrelated to which AI produced it), and changing the visible "Gemini" branding text on every recommendation card is a bigger, separate decision than this refactor — out of scope here. Leave it as-is.

- [ ] **Step 2: Verify it compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/api/gemini/api.py`
Expected: no output, exit code 0.

- [ ] **Step 3: Verify no other file imports something this refactor removed**

Run: `grep -rn "from tmdbhelper.lib.api.gemini.api import\|from tmdbhelper.lib.api.gemini import" resources/tmdbhelper/lib/ | grep -v "resources/tmdbhelper/lib/api/gemini/api.py"`

Expected: any results must import only `Gemini` (the class name is unchanged) — if any result imports a name that no longer exists at module level (there shouldn't be any, since all module-level constants and the `Gemini` class name are preserved), stop and report before continuing.

- [ ] **Step 4: Commit**

```bash
git add resources/tmdbhelper/lib/api/gemini/api.py
git commit -m "refactor(gemini): split BaseAIRecommender out of Gemini for provider fallback support"
```

---

### Task 6: Add the `OpenRouter` provider class

**Files:**
- Create: `resources/tmdbhelper/lib/api/openrouter/__init__.py` (empty, package marker)
- Create: `resources/tmdbhelper/lib/api/openrouter/api.py`

**Interfaces:**
- Consumes: `BaseAIRecommender` from `tmdbhelper.lib.api.gemini.api` (produced by Task 5).
- Produces: `OpenRouter(BaseAIRecommender)` in `tmdbhelper.lib.api.openrouter.api`, with `api_key` reading setting `openrouter_apikey`, and the same `get_prompt_items(self, prompt_text)` inherited entry point Task 7 calls.

- [ ] **Step 1: Verify the `openrouter/free` routing model and required headers before writing final code**

Before finalizing `get_prompt_postdata` and `headers` below, check OpenRouter's current API documentation (`https://openrouter.ai/docs`) to confirm:
1. The exact slug for auto-routing to a free model (this plan uses `openrouter/free` per the design doc, but confirm it's still current — OpenRouter's routing/model catalog changes over time).
2. Whether `HTTP-Referer` and/or `X-Title` headers are required or merely recommended on chat completion requests.

If the slug has changed, substitute the correct current value in Step 2 below. If the attribution headers are required, add them to the `headers` property in Step 2 (a reasonable placeholder value for `X-Title` would be `"TMDb Helper"`; `HTTP-Referer` is typically a URL identifying your application — use the addon's GitHub repo URL, `https://github.com/jurialmunkey/plugin.video.themoviedb.helper`, if a value is required).

- [ ] **Step 2: Create the package marker**

Create `resources/tmdbhelper/lib/api/openrouter/__init__.py` (empty file):

```python
```

- [ ] **Step 3: Create the OpenRouter provider class**

Create `resources/tmdbhelper/lib/api/openrouter/api.py`:

```python
from tmdbhelper.lib.addon.plugin import get_setting
from tmdbhelper.lib.addon.logger import kodi_log
from tmdbhelper.lib.api.gemini.api import BaseAIRecommender


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_FREE_MODEL_ID = "openrouter/free"  # auto-routes to a currently-available free model


class OpenRouter(BaseAIRecommender):

    api_key = get_setting('openrouter_apikey', 'str')

    def __init__(self, api_key=None):
        api_key = api_key or self.api_key

        super(OpenRouter, self).__init__(
            req_api_name='OpenRouter',
            req_api_url=OPENROUTER_API_URL,
            timeout=30,
        )

        OpenRouter.api_key = api_key

    @property
    def headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    @headers.setter
    def headers(self, value):
        """ Ignore base class req_api attempting to set headers """
        return

    def get_prompt_postdata(self, prompt_text):
        return {
            "model": OPENROUTER_FREE_MODEL_ID,
            "messages": [
                {"role": "user", "content": prompt_text}
            ]
        }

    @staticmethod
    def get_candidates(data):
        try:
            return data['choices'][0]['message']['content'].strip()
        except (TypeError, IndexError, KeyError, AttributeError):
            kodi_log(f'OpenRouter FAILED: Unable to get message content', 1)
            return
```

This mirrors `Gemini`'s `__init__`/`headers`/`get_prompt_postdata`/`get_candidates` shape exactly, differing only in the OpenAI-compatible request/response format instead of Gemini's `contents`/`parts` format.

- [ ] **Step 4: Verify it compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/api/openrouter/api.py`
Expected: no output, exit code 0.

- [ ] **Step 5: Commit**

```bash
git add resources/tmdbhelper/lib/api/openrouter/__init__.py resources/tmdbhelper/lib/api/openrouter/api.py
git commit -m "feat(openrouter): add OpenRouter provider class for AI recommendation fallback"
```

---

### Task 7: Wire the OpenRouter fallback into `ListGemini` + settings

**Files:**
- Modify: `resources/tmdbhelper/lib/items/directories/tmdb/lists_gemini.py`
- Modify: `resources/settings.xml` (api keys category, new group 8)
- Modify: `resources/language/resource.language.en_gb/strings.po`

**Interfaces:**
- Consumes: `OpenRouter` from `tmdbhelper.lib.api.openrouter.api` (produced by Task 6), `BaseAIRecommender.is_rate_limited` (produced by Task 5).
- Produces: nothing other tasks depend on. New setting id `openrouter_apikey` (string), new string ids `32542`/`32543`.

- [ ] **Step 1: Add the `openrouter` cached_property and fallback logic**

In `resources/tmdbhelper/lib/items/directories/tmdb/lists_gemini.py`, replace the full file contents:

```python
from xbmcgui import Dialog, INPUT_ALPHANUM
from tmdbhelper.lib.addon.plugin import get_localized, convert_type
from jurialmunkey.ftools import cached_property
from jurialmunkey.parser import try_int

from tmdbhelper.lib.items.container import ContainerDefaultCacheDirectory
from tmdbhelper.lib.items.directories.lists_default import ItemCache


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

    @ItemCache('ItemContainer.db')
    def get_cached_response(self):
        return self.get_prompt_items()

    def get_prompt_items(self):
        from tmdbhelper.lib.addon.dialog import BusyDialog
        with BusyDialog():
            data = self.gemini.get_prompt_items(self.query)
            if not data and self.gemini.is_rate_limited and self.openrouter.api_key:
                data = self.openrouter.get_prompt_items(self.query)
        return data

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
        if tmdb_type:
            mediatype = 'movie' if tmdb_type == 'movie' else 'tvshow'
            items = [i for i in items if i.get('infolabels', {}).get('mediatype') == mediatype]
        if limit:
            items = items[:try_int(limit)]
        self.container_content = convert_type(tmdb_type or 'both', 'container', items=items)
        self.plugin_category = 'Gemini'
        return items
```

The only changes from the original file: the new `openrouter` cached_property, and `get_prompt_items` gaining the fallback branch. `get_items` is untouched — on total failure it still shows `self.gemini.get_error_message()`, which is unchanged behavior for anyone without an OpenRouter key configured, and still shows Gemini's original rate-limit message even if the OpenRouter fallback also failed (per the design doc's explicit decision not to give the fallback its own distinct failure message).

- [ ] **Step 2: Verify it compiles**

Run: `python3 -m py_compile resources/tmdbhelper/lib/items/directories/tmdb/lists_gemini.py`
Expected: no output, exit code 0.

- [ ] **Step 3: Add the new group and setting to settings.xml**

In `resources/settings.xml`, find the end of the `api keys` category's group 7 (the last group before `</category>`):

```xml
                <setting id="tmdb_user_token_access" type="boolean" label="32483" help="" parent="">
                    <level>0</level>
                    <default>false</default>
                    <control type="toggle"/>
                    <visible>false</visible>
                    <enable>false</enable>
                </setting>
            </group>
        </category>
        <category id="accounts" label="32470" help="">
```

Replace with:

```xml
                <setting id="tmdb_user_token_access" type="boolean" label="32483" help="" parent="">
                    <level>0</level>
                    <default>false</default>
                    <control type="toggle"/>
                    <visible>false</visible>
                    <enable>false</enable>
                </setting>
            </group>
            <group id="8" label="32542">
                <setting id="openrouter_apikey" type="string" label="32543" help="">
                    <level>0</level>
                    <default/>
                    <constraints>
                        <allowempty>true</allowempty>
                    </constraints>
                    <control type="edit" format="string">
                        <heading>32543</heading>
                    </control>
                </setting>
            </group>
        </category>
        <category id="accounts" label="32470" help="">
```

(Group 8 is added as a new, visible group — unlike groups 6/7, which are hidden internal-token groups (`<visible>false</visible>`), this one should be visible so the user can actually enter their OpenRouter key.)

- [ ] **Step 4: Verify settings.xml is well-formed**

Run: `python3 -c "import xml.dom.minidom; xml.dom.minidom.parse('resources/settings.xml'); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Add the new strings to strings.po**

In `resources/language/resource.language.en_gb/strings.po`, find the `#32541` block (immediately before the `#32544` block Task 2 added):

```
#: /resources/tmdbhelper/lib/api/gemini/api.py
msgctxt "#32541"
msgid "Gemini responded, but no results could be matched in your local database."
msgstr ""

#: /resources/settings.xml
msgctxt "#32544"
```

Replace with:

```
#: /resources/tmdbhelper/lib/api/gemini/api.py
msgctxt "#32541"
msgid "Gemini responded, but no results could be matched in your local database."
msgstr ""

#: /resources/settings.xml
msgctxt "#32542"
msgid "OpenRouter API"
msgstr ""

#: /resources/settings.xml
msgctxt "#32543"
msgid "OpenRouter API key"
msgstr ""

#: /resources/settings.xml
msgctxt "#32544"
```

(This task depends on Task 2 having landed first, since it anchors on the `#32544` block Task 2 created. Run Task 2 before Task 7. Task 4 also depends on Task 2 for the same reason — Tasks 2, 4, and 7 must run in that relative order even though they touch different features, purely because they all edit the same region of `strings.po`.)

- [ ] **Step 6: Verify the new string entries and full final block ordering**

Run: `grep -A2 'msgctxt "#3254[2-5]"' resources/language/resource.language.en_gb/strings.po`
Expected:
```
msgctxt "#32542"
msgid "OpenRouter API"
msgstr ""
--
msgctxt "#32543"
msgid "OpenRouter API key"
msgstr ""
--
msgctxt "#32544"
msgid "Cast list limit"
msgstr ""
--
msgctxt "#32545"
msgid "Queue episodes from all remaining seasons"
msgstr ""
```

- [ ] **Step 7: Commit**

```bash
git add resources/tmdbhelper/lib/items/directories/tmdb/lists_gemini.py resources/settings.xml resources/language/resource.language.en_gb/strings.po
git commit -m "feat(gemini): fall back to OpenRouter when Gemini rate-limits"
```

---

## Verification (manual, post-implementation)

Automated verification throughout this plan is limited to `py_compile` and XML well-formedness — this addon has no pytest suite and depends on the `xbmc`/`xbmcgui`/`xbmcplugin` modules that only exist inside a running Kodi instance. After all 7 tasks are committed, verify live in Kodi:

1. **Task 1:** No skin string set — confirm artwork blur/crop still refreshes with the default ~10s cadence (i.e. nothing regresses with no skin change). Optional: set `Skin.SetString(TMDbHelper.ArtRefreshInterval, 5)` via a temporary skin action and confirm faster refresh.
2. **Task 2:** Open a movie/TV show's cast list, confirm exactly 100 cast members still show by default. Change the new "Cast list limit" setting (Settings > Expert) to 25, clear the relevant local cache if needed, and confirm the list shortens.
3. **Task 3:** Open a movie's Recommendations/Similar/Reviews/Keywords lists, confirm each container's displayed name now includes the source movie's title in the approved phrasing ("Similar to X", etc.).
4. **Task 4:** With "Queue episodes from all remaining seasons" off (default), confirm playing the last episode of a season still doesn't auto-queue into the next season (unchanged behavior). Turn it on, confirm it now does.
5. **Tasks 5-7:** Ask Gemini a query with a valid Gemini key and no OpenRouter key — confirm identical behavior to before this plan (this is the regression check for the refactor). If/when a real Gemini 429 is hit with an OpenRouter key configured, confirm results still come back instead of an error dialog — this specific path can't be forced in testing, per the design doc's stated limitation, so this is an opportunistic check, not a required gate.
6. Check `kodi.log` after exercising all of the above for any new tracebacks under `tmdbhelper`.
