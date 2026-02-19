from jurialmunkey.ftools import cached_property


class AniListPlayData:
    def __init__(self, watchedindicators=False):
        self._watchedindicators = watchedindicators

    @property
    def is_enabled(self):
        if not self._watchedindicators:
            return False
        if self.anilist_api.authenticator.is_authorized:
            return bool(self.anilist_syncdata)
        return False

    def is_sync(func):
        def wrapper(self, *args, **kwargs):
            if not self.is_enabled:
                return
            return func(self, *args, **kwargs)
        return wrapper

    @cached_property
    def anilist_api(self):
        from tmdbhelper.lib.api.anilist.api import AniListAPI
        return AniListAPI()

    @cached_property
    def anilist_syncdata(self):
        return self.anilist_api.anilist_syncdata

    @is_sync
    def pre_sync(self, info=None, tmdb_type=None, **kwargs):
        if tmdb_type in ('movie', 'both',):
            self.anilist_syncdata.sync('movie', ('anilist_status', ))

        if tmdb_type in ('tv', 'season', 'both',):
            self.anilist_syncdata.sync('show', ('anilist_status', 'anilist_progress', ))

    @is_sync
    def pre_sync_start(self, **kwargs):
        from tmdbhelper.lib.addon.thread import SafeThread
        self._pre_sync = SafeThread(target=self.pre_sync, kwargs=kwargs)
        self._pre_sync.start()

    @is_sync
    def pre_sync_join(self):
        try:
            self._pre_sync.join()
        except AttributeError:
            return

    @is_sync
    def get_play_data(self, tmdb_type, tmdb_id, season=None, episode=None):
        """
        Returns a dict of AniList data for the given item suitable for
        setting item properties in the list view.
        """
        status = self.anilist_syncdata.get_value(tmdb_type, tmdb_id, season, episode, 'anilist_status')
        score = self.anilist_syncdata.get_value(tmdb_type, tmdb_id, season, episode, 'anilist_score')
        progress = self.anilist_syncdata.get_value(tmdb_type, tmdb_id, season, episode, 'anilist_progress')
        updated_at = self.anilist_syncdata.get_value(tmdb_type, tmdb_id, season, episode, 'anilist_updated_at')

        if not status:
            return {}

        data = {
            'anilist_status': status,
            'anilist_score': score,
            'anilist_progress': progress,
            'anilist_updated_at': updated_at,
        }

        # Map AniList status to a simple watched boolean for compatibility
        if status in ('COMPLETED', 'REPEATING'):
            data['anilist_watched'] = True
        else:
            data['anilist_watched'] = False

        return data
