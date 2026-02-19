from tmdbhelper.lib.api.anilist.sync.property_mixins import SyncDataParentProperties
from tmdbhelper.lib.api.anilist.sync.activity import SyncLastActivities
from tmdbhelper.lib.api.anilist.sync.itemdata import MEDIALIST_QUERY
from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.addon.tmdate import set_timestamp, get_timestamp
from tmdbhelper.lib.files.locker import mutexlock
from tmdbhelper.lib.addon.consts import DEFAULT_EXPIRY
from tmdbhelper.lib.addon.thread import ParallelThread


def timerlock(func):
    def wrapper(self, *args, **kwargs):
        interval = 3
        propname = f'syncdecorators.timerlock.sync_anilist.{self.item_type}.{self.method}'
        if get_timestamp(self.window.get_property(propname) or 0, set_int=True):
            return
        self.window.get_property(propname, set_timestamp(interval, set_int=True))
        data = func(self, *args, **kwargs)
        return data
    return wrapper


def progress_bg(func):
    def wrapper(self, *args, **kwargs):
        from tmdbhelper.lib.addon.dialog import DialogProgressSyncBG
        self.dialog_progress_bg = DialogProgressSyncBG()
        self.dialog_progress_bg.heading = f'Syncing AniList {self.item_type} {self.method}'
        self.dialog_progress_bg.create()
        data = func(self, *args, **kwargs)
        self.dialog_progress_bg.close()
        return data
    return wrapper


class AniListDataType(SyncDataParentProperties):
    """Base class for AniList sync data types."""

    sync_kwgs = {}
    lock_name = 'sync_anilist'
    key_prefix = None
    expiry_time = DEFAULT_EXPIRY

    def __init__(self, instance_syncdata, item_type):
        self.instance_syncdata = instance_syncdata
        self._item_type = item_type

    @property
    def mutex_lockname(self):
        return f'{self.cache._db_file}.{self.lock_name}.{self.item_type}.{self.method}.lockfile'

    @cached_property
    def item_type(self):
        if self._item_type in ('movie', 'show', 'season', 'episode'):
            return self._item_type
        raise ValueError(f'Invalid item_type {self._item_type} for AniList {self.method}')

    @cached_property
    def last_activities(self):
        return SyncLastActivities(self.instance_syncdata)

    def store_last_activity(self):
        self.cache.set_activity(
            self.item_type,
            self.method,
            'anilist_synced',
            set_timestamp(self.expiry_time, set_int=True)
        )

    @property
    def is_expired(self):
        timestamp = self.cache.get_activity(self.item_type, self.method, set_timestamp(0, set_int=True))
        return self.last_activities.is_expired(timestamp)

    def clear_columns(self, keys):
        self.cache.del_column_values(keys=keys, item_type=self.item_type)

    @timerlock
    def sync_func(self):
        from tmdbhelper.lib.addon.logger import TimerFunc
        with TimerFunc(
            f'Sync: AniList {self.__class__.__name__} {self.method} {self.item_type}',
            inline=True, log_threshold=0.001
        ):
            return self.get_medialist()

    def get_medialist(self):
        """Fetch the user's AniList media list and resolve TMDb IDs."""
        user_id = self.anilist_api.profile.user_id
        if not user_id:
            return None

        media_type = getattr(self, 'anilist_media_type', 'ANIME')
        variables = {'userId': user_id, 'type': media_type}

        response = self.anilist_api.post_graphql(MEDIALIST_QUERY, variables)
        if not response:
            return None

        try:
            lists = response['data']['MediaListCollection']['lists']
        except (KeyError, TypeError):
            return None

        entries = []
        for lst in (lists or []):
            entries.extend(lst.get('entries') or [])

        if not entries:
            return []

        return self._resolve_tmdb_ids(entries)

    def _resolve_tmdb_ids(self, entries):
        """Resolve AniList media IDs to TMDb IDs and return list of (entry, tmdb_type, tmdb_id) tuples."""
        tmdb_type = 'tv' if self.item_type in ('show', 'season', 'episode') else 'movie'

        def resolve_entry(entry):
            try:
                media = entry.get('media', {})
                anilist_id = media.get('id')
                mal_id = media.get('idMal')
                titles = media.get('title', {})
                title = titles.get('english') or titles.get('romaji') or titles.get('native')
                year = media.get('startDate', {}).get('year')

                if not title:
                    return None

                tmdb_id = self._get_tmdb_id_for_anilist(anilist_id, mal_id, title, year, tmdb_type)
                if not tmdb_id:
                    return None

                return (entry, tmdb_type, tmdb_id)
            except Exception:
                return None

        with ParallelThread(entries, resolve_entry) as pt:
            results = pt.queue

        return [r for r in results if r]

    def _get_tmdb_id_for_anilist(self, anilist_id, mal_id, title, year, tmdb_type):
        """Resolve AniList media to a TMDb ID, using cached results when available."""
        from tmdbhelper.lib.query.database.anilist_id import get_anilist_tmdb_id
        return get_anilist_tmdb_id(anilist_id, mal_id, title, year, tmdb_type)

    @progress_bg
    def sync_data(self, **kwargs):
        self.dialog_progress_bg.update(20, message='Refreshing AniList Data')
        meta = self.sync_func()

        if meta is None:
            return False

        from tmdbhelper.lib.api.anilist.sync.itemdata import AniListSyncItem
        item = AniListSyncItem(self.item_type, meta, self.keys, key_prefix=self.key_prefix)

        self.dialog_progress_bg.update(40, message='Cleaning Data')
        self.clear_columns(item.base_table_keys)

        if not meta:
            return True

        self.dialog_progress_bg.update(60, message='Configuring Data')
        data = item.data

        self.dialog_progress_bg.update(80, message='Updating Data')
        self.cache.set_many_values(keys=item.table_keys, data=data)

        return True

    @mutexlock
    def sync(self, forced=False):
        if not forced and not self.is_expired:
            return
        if not self.sync_data():
            return
        self.store_last_activity()


class SyncAniListMediaListAnime(AniListDataType):
    """Syncs all AniList anime lists (CURRENT, COMPLETED, PLANNING, DROPPED, PAUSED, REPEATING)."""
    keys = ('anilist_status', 'anilist_score', 'anilist_progress', 'anilist_updated_at', 'anilist_listed_at')
    method = 'medialist_anime'
    anilist_media_type = 'ANIME'

    @cached_property
    def item_type(self):
        # AniList anime maps to TV shows
        if self._item_type in ('movie', ):
            return 'movie'
        return 'show'


class SyncAniListMediaListManga(AniListDataType):
    """Syncs all AniList manga lists."""
    keys = ('anilist_status', 'anilist_score', 'anilist_progress', 'anilist_updated_at', 'anilist_listed_at')
    method = 'medialist_manga'
    anilist_media_type = 'MANGA'

    @cached_property
    def item_type(self):
        return 'movie'  # Manga maps to movies in TMDb terms
