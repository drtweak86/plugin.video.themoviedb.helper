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
        # Reads whatever the existing Trakt sync has already populated in simplecache;
        # deliberately doesn't trigger a sync itself. If this row hasn't been synced yet
        # (e.g. right after a DB migration drops simplecache) this returns False, which
        # is the intended fail-open behavior -- a title may briefly slip through unfiltered
        # rather than being wrongly excluded.
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
