# Split ItemMapperMethods God-Class — Design

## Context

`resources/tmdbhelper/lib/items/database/mappings.py` (1059 lines) defines `ItemMapperMethods`, a single class mixing five unrelated concerns — artwork, credits, genres, translations/certifications/providers, movie-only logic (collections), and TV-only logic (episodes/seasons/creators) — plus general formatting utilities. It's consumed as `ItemMapper(_ItemMapper, ItemMapperMethods)` and is load-bearing: every movie/TV/person/episode/season item the addon builds goes through it.

This was flagged as deferred work in an earlier session (not to be bundled into unrelated cleanup passes), and this is the dedicated design session for it.

**Analogy that shaped this design:** `ItemMapper` is the conductor — it calls `self.get_genres()`, `self.get_credits()`, etc., and holds the shared state (`tmdb_id`, `language`, `item`, `data`). `ItemMapperMethods` becomes the seating chart, not a player itself — it just declares which sections make up the orchestra by inheriting all of them. Each section (mixin) only knows its own part; cross-section calls happen the way a cello might follow a cue from the woodwinds — through `self`, never by one section importing another directly.

## Goal

Split `ItemMapperMethods` into one small, single-concern mixin class per file, recombined into a thin aggregate — **zero behavior change, zero external API change**. `ItemMapper.__init__` and every other consumer of `ItemMapper`/`ItemMapperMethods` anywhere in the addon must be completely unaffected. This is purely an internal reorganization for readability and maintainability.

## File structure

New directory `resources/tmdbhelper/lib/items/database/mappings/` (matches the existing convention in this codebase, e.g. `baseitem_factories/concrete_classes/`), containing:

| File | Class | Methods (from the current file, verified against the live 1059-line source) |
|---|---|---|
| `support.py` | *(no class — module-level)* | `ExtendedMap` (namedtuple), `get_blanks_none` (function), `FTV_WITHOUT_SEASONS`/`FTV_TVSHOWS_SEASONS`/`FTV_SEASONS_SEASONS` (constants) |
| `general.py` | `GeneralMapperMethods` | `get_runtime`, `get_configured_item`, `split_array`, `get_custom_time`, `get_custom_date`, `get_custom_property`, `get_unique_ids`, `get_video`, `get_media_item_data` |
| `art.py` | `ArtMapperMethods` | `add_art_type`, `get_art`, `get_aspect_ratio`, `set_default_art`, `get_default_art`, `get_fanart_tv` |
| `genre.py` | `GenreMapperMethods` | `tmdb_database` (property), `genres_map` (cached_property), `get_genre_items`, `get_genres` |
| `credits.py` | `CreditsMapperMethods` | `credits_mappings` (class const), `get_credits`, `get_aggregate_credits`, `get_credits_data`, `get_person_movie_credits_data`, `get_person_tv_credits_data`, `get_person_credits_data` |
| `translations.py` | `TranslationMapperMethods` | `get_providers`, `get_translations`, `get_certifications` |
| `movie.py` | `MovieMapperMethods` | `get_belongs_to_collection`, `get_collection`, `get_parts` |
| `tv.py` | `TVMapperMethods` | `get_episode_type`, `get_episode_to_air`, `get_episodes`, `get_seasons`, `get_creators` |

`resources/tmdbhelper/lib/items/database/mappings.py` (the original file, kept at the same path so nothing importing `from tmdbhelper.lib.items.database.mappings import ItemMapper` needs to change) shrinks to:
- The `BlankNoneDict` class (unchanged, unrelated to the split).
- `ItemMapperMethods(GeneralMapperMethods, ArtMapperMethods, GenreMapperMethods, CreditsMapperMethods, TranslationMapperMethods, MovieMapperMethods, TVMapperMethods)` — a one-line class body (`pass`), the seating chart.
- `ItemMapper(_ItemMapper, ItemMapperMethods)` — completely unchanged from today, including its full `__init__`, `map_dict`, `get_empty_item`, `get_info`.

## Two assignment decisions worth calling out explicitly

**`get_media_item_data` → `general.py`, not `movie.py` or `tv.py`.** It takes `tmdb_type` as a parameter and branches internally (`mediatype = 'movie' if tmdb_type == 'movie' else 'tvshow'`), and it's called from both movie-only code (`MovieMapperMethods.get_collection`/`get_parts`, always passing `'movie'`) and the shared credits dispatcher (`CreditsMapperMethods.get_person_credits_data`, passing whichever type applies). It's genuinely type-agnostic machinery, not movie- or TV-specific logic.

**`get_person_movie_credits_data`/`get_person_tv_credits_data` stay in `credits.py`**, not split into `movie.py`/`tv.py`, despite their names. Both are one-line wrappers around the shared `get_person_credits_data(items, tmdb_type)` dispatcher in the same file — splitting them out would scatter three tightly-coupled lines across three files for no readability benefit. They're about credits first, movie/TV second.

## Cross-mixin calls — how they stay safe

Every cross-concern call in the current code already goes through `self.` (e.g. `MovieMapperMethods.get_belongs_to_collection` calling `self.set_default_art`, which will live in `ArtMapperMethods`) or through the literal class name `ItemMapperMethods.method(...)` (e.g. `ItemMapperMethods.get_configured_item(...)`, used defensively in several places instead of `self.` to guarantee a static-method-style call regardless of instance state).

Both patterns keep working unchanged after the split:
- `self.whatever` resolves through Python's normal MRO lookup on the instance — it doesn't matter which mixin in `ItemMapperMethods`'s bases actually defines the method, only that *some* base does.
- `ItemMapperMethods.get_configured_item(...)` also resolves through the MRO, because `ItemMapperMethods` inherits `get_configured_item` from `GeneralMapperMethods` — the literal class-attribute lookup on `ItemMapperMethods` finds it the same way it would if the method were defined directly on the class.

No call site anywhere in `mappings.py` or in `ItemMapper.__init__`'s `advanced_map`/`extended_map`/`standard_map` dictionaries needs to change.

## Package structure note

No `__init__.py` in the new `mappings/` directory. This codebase's own `baseitem_factories/concrete_classes/` and `basemeta_factories/concrete_classes/` directories (the pattern this design follows) have no `__init__.py`, confirming Python 3 implicit namespace packages resolve imports like `from tmdbhelper.lib.items.database.mappings.art import ArtMapperMethods` without one. (Note: `api/openrouter/` elsewhere in this codebase does have an `__init__.py` — an inconsistency flagged but left as-is in an earlier pass — don't follow that example here; follow the more common no-`__init__.py` convention instead.)

## Import considerations

Several methods do lazy, function-local imports today (e.g. `add_art_type` and `get_aspect_ratio` both do `from tmdbhelper.lib.addon.consts import IMAGEPATH_ASPECTRATIO` inside the method body, not at module level). These stay exactly as-is in their new files — moving a method to a new file doesn't change *when* its internal imports run, so this introduces no new import-cycle risk.

Each mixin file imports `ExtendedMap`/`get_blanks_none`/`FTV_*` from `support.py` as needed. No mixin file imports from another mixin file — cross-concern communication happens only through `self` at runtime (per the section above), never through Python imports at module load time. This keeps the seven files genuinely independent: any one of them could be read and understood without opening the other six.

## Testing

No pytest suite in this repo (`xbmc`/`xbmcgui` only importable inside a running Kodi instance) — verification is `python3 -m py_compile` on every new/changed file, plus a manual live-Kodi check that a representative sample of item types still map correctly: a movie with a collection, a TV show with seasons/episodes/creators, and a person's combined movie+TV credits — since those are exactly the paths that exercise `MovieMapperMethods`, `TVMapperMethods`, and the credits dispatcher respectively. Since this is a pure reorganization with no behavior change, the practical test is "does everything still look the same as before" — any visible difference (missing art, missing genre, missing cast) is a regression.

## Out of scope

- No change to `ItemMapper`'s public behavior, `map_dict`, `get_empty_item`, or `get_info`.
- No change to any file outside `mappings.py` and the new `mappings/` directory — every other consumer imports `ItemMapper` by name from the same module path and is unaffected.
- No renaming of any method — only relocation.
