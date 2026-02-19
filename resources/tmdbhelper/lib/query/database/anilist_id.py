from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.addon.logger import kodi_log


class FindQueriesDatabaseAniListID:

    anilist_id_columns = {
        'id': {
            'data': 'TEXT PRIMARY KEY',
            'indexed': True,
        },
        'anilist_id': {
            'data': 'INTEGER',
            'indexed': True,
        },
        'mal_id': {
            'data': 'INTEGER',
            'indexed': True,
        },
        'tmdb_id': {
            'data': 'INTEGER',
            'indexed': True,
        },
        'tmdb_type': {
            'data': 'TEXT',
            'indexed': True,
        },
        'title': {
            'data': 'TEXT',
        },
        'year': {
            'data': 'INTEGER',
        },
    }

    def get_anilist_tmdb_id(self, anilist_id, mal_id=None, title=None, year=None, tmdb_type='tv'):
        """
        Resolve an AniList media ID to a TMDb ID.
        Checks cache first, then queries TMDb if needed.
        """
        table = 'anilist_id'
        item_id = f'anilist_{anilist_id}_{tmdb_type}'

        def get_cached():
            return self.access.get_cached(table=table, item_id=item_id, key='tmdb_id')

        def set_cached():
            if not self.is_expired(f'{table}.{item_id}'):
                return
            tmdb_id = self._resolve_anilist_to_tmdb(anilist_id, mal_id, title, year, tmdb_type)
            if not tmdb_id:
                return
            self.access.set_cached_values(
                table, item_id,
                keys=('id', 'anilist_id', 'mal_id', 'tmdb_id', 'tmdb_type', 'title', 'year'),
                values=(item_id, anilist_id, mal_id, tmdb_id, tmdb_type, title, year)
            )
            self.set_expiry(f'{table}.{item_id}')
            return get_cached()

        return get_cached() or set_cached()

    def _resolve_anilist_to_tmdb(self, anilist_id, mal_id, title, year, tmdb_type):
        """Search TMDb for the matching title and return TMDb ID."""
        if not title:
            return None

        try:
            return self._search_tmdb(title, year, tmdb_type)
        except Exception as exc:
            kodi_log(f'AniList ID resolve error for "{title}": {exc}', 1)
            return None

    def _search_tmdb(self, title, year, tmdb_type):
        """Search TMDb for the title and return the best match ID."""
        tmdb = self.tmdb_api
        search_type = 'tv' if tmdb_type == 'tv' else 'movie'

        # Try with year first for better accuracy
        results = None
        if year:
            kwgs = {'query': title, 'first_air_date_year': year} if search_type == 'tv' else {'query': title, 'year': year}
            try:
                results = tmdb.get_request_sc('search', search_type, **kwgs)
            except Exception:
                pass

        # Fallback without year
        if not results:
            try:
                results = tmdb.get_request_sc('search', search_type, query=title)
            except Exception:
                pass

        if not results:
            return None

        try:
            items = results.get('results') or []
            if not items:
                return None

            # Find best match by title similarity
            best = self._find_best_match(items, title, year, search_type)
            return best
        except (AttributeError, KeyError, TypeError):
            return None

    def _find_best_match(self, items, title, year, search_type):
        """Find the best matching TMDb result for the given title."""
        title_lower = title.casefold()

        name_key = 'name' if search_type == 'tv' else 'title'
        orig_name_key = 'original_name' if search_type == 'tv' else 'original_title'
        date_key = 'first_air_date' if search_type == 'tv' else 'release_date'

        # First pass: exact title match with year
        if year:
            for item in items:
                item_title = (item.get(name_key) or '').casefold()
                orig_title = (item.get(orig_name_key) or '').casefold()
                item_date = item.get(date_key) or ''
                item_year = int(item_date[:4]) if len(item_date) >= 4 else None
                if (item_title == title_lower or orig_title == title_lower) and item_year == year:
                    return item.get('id')

        # Second pass: exact title match without year
        for item in items:
            item_title = (item.get(name_key) or '').casefold()
            orig_title = (item.get(orig_name_key) or '').casefold()
            if item_title == title_lower or orig_title == title_lower:
                return item.get('id')

        # Third pass: return first result (most popular/relevant)
        return items[0].get('id') if items else None


def get_anilist_tmdb_id(anilist_id, mal_id, title, year, tmdb_type):
    """
    Module-level helper to resolve AniList media ID to TMDb ID.
    Uses FindQueriesDatabase to leverage shared caching infrastructure.
    """
    try:
        from tmdbhelper.lib.query.database.database import FindQueriesDatabase
        db = FindQueriesDatabase()
        return db.get_anilist_tmdb_id(anilist_id, mal_id=mal_id, title=title, year=year, tmdb_type=tmdb_type)
    except Exception as exc:
        kodi_log(f'AniList TMDb ID lookup failed: {exc}', 1)
        return None
