from jurialmunkey.ftools import cached_property
from collections import namedtuple


class ItemListSyncDataProperties:
    @cached_property
    def items(self):
        if not self.anilist_syncdata:
            return
        return self.get_items()

    @cached_property
    def additional_keys(self):
        return self.get_additional_keys()

    @cached_property
    def sort_method(self):
        return self.get_sort_method()

    @cached_property
    def sort_key(self):
        return self.get_sort_key()

    @cached_property
    def nonetype(self):
        return self.get_nonetype()

    @cached_property
    def reverse(self):
        return self.get_reverse()

    @property
    def anilist_syncdata(self):
        return self.anilist_api.anilist_syncdata

    @cached_property
    def namedtuple_basic(self):
        return namedtuple("BasicTuple", "item mediatype")

    @property
    def item_types(self):
        if self.item_type == 'both':
            return ('movie', 'show', )
        return (self.item_type, )


class ItemListSyncDataMethods:
    def sort_data(self, data):
        if self.sort_by == 'random':
            import random
            random.shuffle(data)
            return data
        if not self.additional_keys:
            return data
        return sorted(
            data,
            key=lambda x: x[0][self.sort_key] if x[0][self.sort_key] is not None else self.nonetype,
            reverse=self.reverse
        )

    def make_list(self, sd_func):
        data = []
        for item_type in self.item_types:
            sd = sd_func(item_type)
            sd.additional_keys = self.additional_keys
            data += [self.namedtuple_basic(i, item_type, ) for i in sd.items] if sd.items else []

        if not data:
            return

        data = sorted(data, key=lambda x: x.item[sd.clause_keys[0]] or '', reverse=True)
        return [self.make_item(i) for i in self.sort_data(data) if i]

    def make_item(self, i):
        item = {'id': i.item['tmdb_id'], 'mediatype': i.mediatype, 'title': i.item['title']}
        for k in (self.item_keys or ()):
            try:
                item.setdefault('infoproperties', {})[k] = i.item[k]
            except (KeyError, IndexError):
                pass
        return item


class ItemListSyncData(ItemListSyncDataProperties, ItemListSyncDataMethods):

    sort = {
        'title': ('title', False, '', ),
        'updated': ('anilist_updated_at', True, '', ),
        'listed': ('anilist_listed_at', True, '', ),
        'score': ('anilist_score', True, 0, ),
        'progress': ('anilist_progress', True, 0, ),
        'unsorted': None,
    }

    def __init__(self, anilist_api, item_type=None, sort_by=None, sort_how=None, item_keys=None, tmdb_id=None):
        self.anilist_api = anilist_api
        self.sort_by, self.sort_how = sort_by, sort_how
        self.item_keys = item_keys or ()
        self.item_type = item_type
        self.tmdb_id = tmdb_id

    def get_sort_method(self):
        try:
            return self.sort[self.sort_by]
        except KeyError:
            return

    def get_sort_key(self):
        try:
            return self.sort_method[0]
        except TypeError:
            return

    def get_additional_keys(self):
        try:
            return (self.sort_method[0], *self.item_keys)
        except TypeError:
            return

    def get_reverse(self):
        try:
            reverse = self.sort_method[1]
        except TypeError:
            return
        if self.sort_how != 'asc':
            return reverse
        return not reverse

    def get_nonetype(self):
        try:
            return self.sort_method[2]
        except TypeError:
            return


class ItemListSyncDataWatchlist(ItemListSyncData):
    """Items with PLANNING status (AniList watchlist equivalent)."""

    def get_items(self):
        return self.make_list(self.anilist_syncdata.get_anilist_watchlist_getter)


class ItemListSyncDataWatching(ItemListSyncData):
    """Items with CURRENT status (currently watching)."""

    def get_items(self):
        return self.make_list(self.anilist_syncdata.get_anilist_watching_getter)


class ItemListSyncDataCompleted(ItemListSyncData):
    """Items with COMPLETED or REPEATING status."""

    def get_items(self):
        return self.make_list(self.anilist_syncdata.get_anilist_completed_getter)


class ItemListSyncDataDropped(ItemListSyncData):
    """Items with DROPPED status."""

    def get_items(self):
        return self.make_list(self.anilist_syncdata.get_anilist_dropped_getter)


class ItemListSyncDataPaused(ItemListSyncData):
    """Items with PAUSED status."""

    def get_items(self):
        return self.make_list(self.anilist_syncdata.get_anilist_paused_getter)


def ItemListSyncDataFactory(sync_type, *args, **kwargs):
    routes = {
        'anilist_watchlist': ItemListSyncDataWatchlist,
        'anilist_watching': ItemListSyncDataWatching,
        'anilist_completed': ItemListSyncDataCompleted,
        'anilist_dropped': ItemListSyncDataDropped,
        'anilist_paused': ItemListSyncDataPaused,
    }
    return routes[sync_type](*args, **kwargs)
