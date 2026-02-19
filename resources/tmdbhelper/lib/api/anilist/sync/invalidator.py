from jurialmunkey.ftools import cached_property


ANILIST_SYNC_KEYS = (
    'anilist_status',
    'anilist_score',
    'anilist_progress',
    'anilist_updated_at',
    'anilist_listed_at',
)


class SyncInvalidatorBase:
    item_types = ('movie', 'show', )

    def __init__(self, anilist_syncdata):
        self.anilist_syncdata = anilist_syncdata

    @cached_property
    def cache(self):
        return self.anilist_syncdata.cache

    def invalidate(self, forced=True):
        self._clear_columns()
        self._resync(forced=forced)

    def _clear_columns(self):
        for item_type in self.item_types:
            self.cache.del_column_values(keys=self.keys, item_type=item_type)

    def _resync(self, forced=True):
        for item_type in self.item_types:
            self.anilist_syncdata.sync(item_type, self.keys, forced=forced)


class SyncInvalidatorAll(SyncInvalidatorBase):
    keys = ANILIST_SYNC_KEYS
