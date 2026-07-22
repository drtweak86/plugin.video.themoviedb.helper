# Ask Gemini: Exclude Already-Watched Titles (Trakt) — Design

## Context

The Ask Gemini feature (built earlier in this branch's history) recommends up to 10 movie/TV items per query, split into two 5-item panels. It currently has no awareness of what the user has already watched — Gemini/OpenRouter can and does suggest titles the user has already seen.

This addon already has a deep, first-party Trakt integration with watch data synced locally (not a live API call per check). Tying "already watched" awareness into Ask Gemini is a small, self-contained addition that reuses this existing data.

**Explicitly out of scope for this design:** AniList watched-list integration. AniList has no existing integration in this addon at all — it uses its own GraphQL API and its own IDs, with no native TMDb ID field, so tying it in would require a new API client, a new local sync mechanism, and a cross-service ID-mapping step (e.g. via a community-maintained mapping list like Fribb's anime-lists). This is a substantially bigger, separate project — deliberately deferred, same pattern as the `mappings.py` split and fanart slideshow mode. Don't bundle it into this pass.

## Confirmed decisions (from brainstorming)

- **Scope:** Trakt only, now. AniList later, as its own project.
- **"Watched" definition for TV shows:** any episode watched at all (not "fully watched"). Ask Gemini is for discovering new things, not resurfacing shows already started.
- **Filter mechanism:** silent post-filter only. No prompt-side "avoid these titles" enrichment — keeps the change small, reuses all existing plumbing, and stays correct without adding prompt size/cost or a second failure mode. Accepted tradeoff: a panel can show fewer than 5 items if the user has watched heavily in that genre — this already happens today when Gemini itself skews toward one media type, so it's consistent, not a new class of behavior.
- **Setting:** a new boolean, default **on**, so it can be disabled later without a code change.

## Data source

Trakt watch status is already synced locally into a `simplecache` table (not a live Trakt API call), keyed by a composite `id` column in `{tmdb_type}.{tmdb_id}` format (e.g. `movie.550`, `tv.1396` — matches the `get_base_id(tmdb_type, tmdb_id)` convention already used elsewhere in `items/database/basedata.py`). Relevant columns already populated by the existing Trakt sync:

- `plays` — play count. For a **movie**, `plays > 0` means watched.
- `watched_episodes` — episode-watched count. For a **show**, `watched_episodes > 0` means at least one episode watched.

No new Trakt API calls, no new sync job, no new local cache table — this is a read against data the addon already maintains for other purposes (e.g. showing playcount badges on list items).

## Where the filter runs

`ListGemini`'s pipeline currently looks like:

1. `get_cached_response()` — returns the cached (or freshly fetched) Gemini/OpenRouter recommendation list, already resolved to TMDb items via `get_tmdb_item`/`get_tmdb_items`. Cached for 6 hours via `ItemCache`.
2. `get_items()` — filters the returned list by `tmdb_type` (movie vs tv) and caps to `limit` (5).

The new watched-filter step is inserted **between these two**, applied to the full pool (up to 10 items) *before* the type-split-and-cap, and runs **every time `get_items()` is called** — not baked into the cached response. This is deliberate: the raw AI recommendation list is expensive to produce (API call) and safe to cache for hours, but "have I watched this" can change at any moment, so it's checked fresh against current local data on every request, cache hit or not.

Concretely: for each item in the cached/fetched list, resolve `tmdb_type`/`tmdb_id` (already present in the item's `params`/`unique_ids` from the existing `get_tmdb_item` shape), query the `simplecache` row for that composite id, and drop the item if the relevant watched-count column is greater than zero. Items with no `simplecache` row at all (never synced, or never watched) are kept.

## Setting

A new boolean setting, `gemini_exclude_watched`, default `True`. Placed in the existing "Gemini API" group (api keys category, group 4) alongside `gemini_apikey` — this is already the addon's de-facto home for Gemini-specific settings (the OpenRouter fallback's `openrouter_apikey` setting from the prior feature pass followed the same "AI-provider settings live in api keys" convention). The setting is only meaningful when Trakt is connected, so it's conditionally visible only when `trakt_token` is set — mirroring the existing precedent at `seasons_upnext` (settings.xml, general category group 4), which uses the same `<dependency type="visible"><condition operator="!is" setting="trakt_token"/></condition></dependency>` pattern to hide itself when Trakt isn't connected. When off (or hidden because Trakt isn't connected), no filtering happens and behavior is identical to today.

## Error handling

If the `simplecache` lookup fails for any reason (missing table row, DB error), treat the item as **not watched** (i.e., fail open — keep the item) rather than dropping it. Excluding a title incorrectly because of a lookup hiccup is worse than occasionally showing something already watched.

## Testing note

Same limitation as the rest of this branch's work: no pytest suite, `xbmc` only importable inside a running Kodi instance. Verification will be `py_compile` plus a manual live check — mark a test movie/show as watched in Trakt, ask Gemini for something in that genre, confirm it doesn't appear (or confirm the panel shows fewer than 5 if that's genuinely all that's left after filtering).
