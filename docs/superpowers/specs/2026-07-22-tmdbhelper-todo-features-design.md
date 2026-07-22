# TMDb Helper: TODO-Derived Feature Pass — Design

## Context

A review of TODO/FIXME comments left by the original author (jurialmunkey) across `plugin.video.themoviedb.helper` surfaced several genuinely feature-shaped ideas — things the author flagged as worth doing but never got to, as opposed to engineering-debt notes. Of those, four were confirmed achievable and in-scope for this pass. A fifth item — an AI-provider fallback for the existing Gemini recommendation feature — was added mid-session after a tangent about whether Gemini is still the right model choice for that feature; it isn't a TODO-derived item, but it ships through the same plan since it's small, self-contained, and touches the same corner of the codebase (Ask Gemini).

Explicitly out of scope, by prior decision:
- **PVR extra-info TODO** — user doesn't use the PVR feature.
- **Fanart slideshow mode** (`fanart.py:63`) — flagged as "investigate first, decide later," not committed to this pass.
- **`mappings.py`'s `ItemMapperMethods` split** — confirmed separable but scoped as its own future project with its own design.

Branch: `refactor/tmdb-helper-cleanup` (the active, ongoing working branch — kept unmerged, no PR).

---

## Feature 1: Skin-configurable art refresh interval

**Source:** `resources/tmdbhelper/lib/monitor/imgmon.py:55`
```python
_next_refresh_increment = 10  # Reupdate idle item every ten seconds for extrafanart TODO: Allow skin to set value?
```

**What it does today:** `ImagesMonitor` (a background thread) re-checks and reapplies blur/crop/desaturate/colour artwork properties for the current list item every `_next_refresh_increment` seconds while the item sits idle (waiting for extrafanart etc. to become available). The value is a hardcoded class attribute.

**Design:** Convert `_next_refresh_increment` from a class attribute to a property that reads a skin string, following the exact pattern already used three times in the sibling module `monitor/images.py` (`Skin.String(TMDbHelper.Blur.Size)`, `.Blur.Radius`, `.Corner.Radius` — each `try_int(get_infolabel('Skin.String(...)')) or <default>`):

```python
@property
def _next_refresh_increment(self):
    return try_int(get_infolabel('Skin.String(TMDbHelper.ArtRefreshInterval)')) or 10
```

Requires importing `get_infolabel` (from `tmdbhelper.lib.addon.plugin`, already imported for `get_condvisibility` in this file) and `try_int` (from `jurialmunkey.parser`, used the same way in `images.py`).

**Why a skin string, not an addon setting:** this value is meaningless without matching skin behaviour (it only affects how eagerly the skin's blur/crop overlays refresh) — the existing three related tunables (blur size/radius, corner radius) are all skin strings for the same reason. An addon `settings.xml` entry would be a User Interface control living in the wrong place. No TMDb Helper code changes needed beyond the property; the skin side (setting `Skin.SetString(TMDbHelper.ArtRefreshInterval, ...)` somewhere in skin settings) is optional follow-up work, not required for this feature to be correct — omitting it just means the default of 10 keeps applying, identical to today.

**Risk:** minimal. Class attribute → property is a transparent change to every existing call site (`self._next_refresh_increment` is read the same way either way).

---

## Feature 2: Configurable cast-list limit

**Source:** `resources/tmdbhelper/lib/items/database/basemeta_factories/concrete_classes/credits.py:8`
```python
conditions = 'parent_id=? GROUP BY castmember.tmdb_id ORDER BY IFNULL(ordering, 9999) ASC LIMIT 100'  # TODO: Move limit to settings ???
```

**What it does today:** `CastMember.conditions` is a raw SQL WHERE-clause fragment with `LIMIT 100` baked in as a literal. `CrewMember` (the sibling class, line 31) has its own separate `LIMIT 100` — the TODO is only on `CastMember`, and this feature only touches that one class; crew-list limiting is not part of this pass.

**Design:** Convert `conditions` from a class attribute to a property, reading a new integer setting:

```python
@property
def conditions(self):
    limit = get_setting('castmember_limit', 'int') or 100
    return f'parent_id=? GROUP BY castmember.tmdb_id ORDER BY IFNULL(ordering, 9999) ASC LIMIT {limit}'
```

Verified safe: `self.conditions` is read as a plain instance attribute everywhere it's consumed (`baseclass.py`, 6 call sites, all `self.conditions` or `f'... {self.conditions}'`) — never string-formatted at class-definition time — so a class attribute → property swap is transparent.

**New setting** — `castmember_limit`, in the `expert` category, group 1 (alongside the existing `dummy_duration`/`dummy_delay` spinners), following the exact pattern of the existing `artwork_quality` integer spinner:

```xml
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
```

New localized string `32544`: "Cast list limit".

**Risk:** minimal, single-file change plus one settings.xml entry. `credits.py` needs a new import: `from tmdbhelper.lib.addon.plugin import get_setting`.

---

## Feature 3: Dynamic related-list naming

**Source:** `resources/tmdbhelper/lib/items/directories/tmdb/lists_related.py`, four identical-shaped TODOs:
```python
list_properties.plugin_name = '{localized}'  # TODO: BASED ON {item}
```
at lines 34 (`ListRecommendations`), 47 (`ListSimilar`), 58 (`ListReviews`), 73 (`ListKeywords`).

**What it does today:** Each of these four directory classes builds a list of related content (recommendations/similar/reviews/keywords) for a given `tmdb_id`/`tmdb_type`, and labels the resulting container generically — "Recommended", "Similar", "Reviews", "Keywords" — with no indication of *which* movie/show the list is related to.

**Design:** Pre-interpolate the source item's title into the `plugin_name` template at configure-time, leaving `{localized}` as a literal placeholder for the later `.format(localized=..., plural=...)` call that already happens in the base class (`lists_default.py:148`). This is an established pattern already used elsewhere in the codebase — e.g. `lists_static.py:141`: `self.list_properties.plugin_name = f'{{localized}} ({user_slug})'`.

Confirmed format from earlier brainstorming (example: **"Similar to Inception"**). Applying the same "to"/"for" structure across all four lists:

```python
# ListRecommendations
list_properties.plugin_name = f'{{localized}} for {item_title}'   # "Recommended for Inception"

# ListSimilar
list_properties.plugin_name = f'{{localized}} to {item_title}'    # "Similar to Inception"

# ListReviews
list_properties.plugin_name = f'{{localized}} for {item_title}'   # "Reviews for Inception"

# ListKeywords
list_properties.plugin_name = f'{{localized}} for {item_title}'   # "Keywords for Inception"
```

(Exact preposition per list is a cosmetic detail, easily adjusted at implementation time if any of these reads awkwardly in practice — the approved reference point is specifically "Similar to Inception".)

**Resolving `item_title`:** `list_properties` already carries `tmdb_type`/`tmdb_id` for the source item (used today to build `url` and `cache_name_tuple`). Resolve the title via `BaseItemFactory(mediatype, ...)` — `resources/tmdbhelper/lib/items/database/baseitem_factories/factory.py` — the same factory the addon already uses everywhere else to turn a `tmdb_id`/`tmdb_type` pair into a full item (it reads from local cache first, falling back to a TMDb API call only on a genuine cache miss). This happens once per directory-list build (not once per result row), so the added cost is one extra local-cache read per list open, not a network call in the common case.

**Risk:** low-to-moderate. Touches 4 configure methods in one file plus one shared title-resolution helper (likely a small method on `ListRelatedProperties`, since all 4 subclasses share that base and all need the same `tmdb_type`/`tmdb_id` → title resolution). Worth a `cached_property` on `ListRelatedProperties` so the lookup happens at most once per request even though multiple `configure_list_properties` calls could theoretically read it.

---

## Feature 4: Multi-season "next episodes" playlist

**Source:** `resources/tmdbhelper/lib/player/action/episodes.py:33-34`
```python
# sync = BaseViewFactory('flatseasons', 'tv', self.tmdb_id)
sync = BaseViewFactory('episodes', 'tv', self.tmdb_id, season=self.season)  # Only get current season to avoid massive playlists TODO: Make optional get more than one season / all seasons?
```

**What it does today:** When Kodi auto-queues "next episodes" after a playback ends, `PlayerNextEpisodes.all_episodes` only ever fetches the *current season's* episode list, then `next_episodes`/`is_future_episode()` filter that list down to unwatched-and-later episodes. If you're on the last episode of a season, the queue is empty — Kodi won't roll into season 2.

**Confirmed scope (from earlier brainstorming):** queue **all remaining episodes to the end of the series**, not just the next season, gated by **a global setting** (not per-show).

**Design:** Swap the data source based on a new boolean setting. `is_future_episode()` (lines 74-83) already does cross-season comparison correctly — `s_number < self.season` excludes past seasons, `s_number > self.season` includes all of any future season, same-season rows compare by episode number — so **no change needed there**; it was already written to be cross-season-aware, the author just never wired it to a data source that spans seasons. This is the lowest-risk feature of the four despite sounding the biggest.

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

**New setting** — `player_queue_all_seasons`, boolean, in the `players` category (matches the domain — this is playback-queue behaviour), following the existing `combined_players`/`bundled_players` toggle pattern in group 2:

```xml
<setting id="player_queue_all_seasons" type="boolean" label="32545" help="">
    <level>0</level>
    <default>False</default>
    <control type="toggle"/>
</setting>
```

New localized string `32545`: "Queue episodes from all remaining seasons" (default off — preserves today's current-season-only behaviour unless explicitly enabled).

**Risk:** low. One conditional branch in an already-cross-season-aware method, one settings.xml entry. `flatseasons` is existing, already-working infrastructure (used elsewhere in the addon for cross-season episode views) — this isn't new query logic, just pointing an existing consumer at it.

---

## Feature 5: OpenRouter fallback when Gemini rate-limits

**Not TODO-derived** — added after a mid-session tangent about whether Gemini is the right model for the existing "Ask Gemini" recommendation feature. Decision: keep Gemini as the primary provider (no reason to abandon a working integration), but add a silent, automatic fallback to OpenRouter when Gemini's free tier rate-limits, so a 429 doesn't dead-end the feature.

**Refactor (prerequisite):** `resources/tmdbhelper/lib/api/gemini/api.py` currently has one `Gemini(RequestAPI)` class mixing provider-specific request mechanics (headers, request body shape, response parsing) with provider-agnostic logic (prompt template, JSON extraction, TMDb-matching via `get_tmdb_item`/`get_tmdb_items`). Split out a `BaseAIRecommender(RequestAPI)` base class in the same file, containing everything that doesn't depend on which provider is being called: `QUERY_PROMPT_TEMPLATE` and friends, `get_prompt_query`, `get_json_from_candidate`, `get_tmdb_item`, `get_tmdb_items`, `get_prompt_recommendations`, `get_prompt_items`, and the `last_error_message`/`get_error_message` skeleton. `Gemini(BaseAIRecommender)` keeps only what's actually Gemini-specific: `headers` (`x-goog-api-key`), `get_prompt_postdata` (Gemini's `contents`/`parts` request shape), `get_candidates` (parses `candidates[0].content.parts`), `req_api_url`, and its own `api_key` setting (`gemini_apikey`).

This mirrors the shared-base-class refactor pattern already used in this session's cleanup pass (`lists_view_db.py`'s `ListPersonListViewBase`/`ListImageViewBase`/etc.) — same technique, same file, new sibling subclass added rather than duplicating ~150 lines.

**New `OpenRouter` class** in a new `resources/tmdbhelper/lib/api/openrouter/api.py`, subclassing `BaseAIRecommender` from `gemini/api.py`:
- `req_api_url`: `https://openrouter.ai/api/v1/chat/completions` (OpenAI-compatible surface)
- `headers`: `Authorization: Bearer <api_key>` instead of Gemini's `x-goog-api-key`
- `get_prompt_postdata`: OpenAI-style `{"model": "openrouter/free", "messages": [{"role": "user", "content": prompt_text}]}` — using OpenRouter's `openrouter/free` auto-router model ID (it picks a working free-tier model itself), rather than hardcoding a specific model that could later be deprecated or renamed.
- `get_candidates`: parses `data['choices'][0]['message']['content']` (OpenAI response shape) rather than Gemini's `candidates[0].content.parts`.

**Caveats to verify at implementation time, not asserted here:** the exact `openrouter/free` slug and behaviour, and whether OpenRouter requires `HTTP-Referer`/`X-Title` attribution headers on requests — these are live-API details that should be checked against OpenRouter's current docs when this task is actually implemented, not trusted from this design doc.

**Trigger logic** — lives in `ListGemini.get_prompt_items()` (`lists_gemini.py`), not inside `Gemini` itself, since "try a backup provider" is an orchestration policy, not something a single provider class should know about:

```python
def get_prompt_items(self):
    from tmdbhelper.lib.addon.dialog import BusyDialog
    with BusyDialog():
        data = self.gemini.get_prompt_items(self.query)
        if not data and self.gemini.is_rate_limited and self.openrouter.api_key:
            data = self.openrouter.get_prompt_items(self.query)
    return data
```

`is_rate_limited` is a new property on `BaseAIRecommender`: `getattr(self.last_response, 'status_code', None) == 429` — a real status-code check rather than string-matching the localized error message (which would break if a translation changes the text). `self.openrouter` is a new `cached_property` on `ListGemini`, mirroring the existing `self.gemini` one.

**On total failure** (Gemini rate-limited, OpenRouter unset or also fails): `ListGemini.get_items()`'s existing `Dialog().ok('Gemini', self.gemini.get_error_message())` call is unchanged — it shows Gemini's original rate-limit message either way. The fallback attempt failing doesn't get its own distinct error message; this keeps behaviour identical to today for anyone who never sets up an OpenRouter key.

**Settings** — new `openrouter_apikey` string field, in the `api keys` category, new group 8 (groups 6/7 are hidden internal-token groups; 8 is the next free visible slot), following the exact `gemini_apikey` pattern (group 4):

```xml
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
```

New localized strings: `32542` "OpenRouter API", `32543` "OpenRouter API key". No separate enable/disable toggle — an empty key means the fallback is inert, same as how an empty `gemini_apikey` already disables the whole feature.

**Testing limitation, stated honestly:** there's no way to force a genuine Gemini 429 without actually exhausting real quota. Verification for this feature leans on code review plus the fallback quietly proving itself the next time a real rate limit is hit in normal use — not something that can be exercised end-to-end in a test pass.

**Risk:** moderate — new file, new provider integration, refactor of an existing working class (though the refactor is mechanical: split, don't rewrite). The Gemini-only code paths (headers, postdata shape, candidate parsing) are untouched in content, only relocated.

---

## Summary of new settings.xml entries

| Setting | Category | Type | Default |
|---|---|---|---|
| `castmember_limit` | expert, group 1 | integer spinner (25/50/100/150/200) | 100 |
| `player_queue_all_seasons` | players, group 2 | boolean toggle | False |
| `openrouter_apikey` | api keys, new group 8 | string | empty |

(Feature 1's art-refresh interval is a skin string, not an addon setting — no settings.xml entry.)

## Summary of new localized strings (`strings.po`, next free ID block starting 32542)

| ID | Text |
|---|---|
| 32542 | OpenRouter API |
| 32543 | OpenRouter API key |
| 32544 | Cast list limit |
| 32545 | Queue episodes from all remaining seasons |

## Out of scope for this pass (confirmed by prior decision, not re-litigated here)
- PVR extra-info TODO
- Fanart slideshow mode (`fanart.py:63`)
- `mappings.py`'s `ItemMapperMethods` split
