from tmdbhelper.lib.api.anilist.sync.itemlist import ItemListSyncDataFactory
from tmdbhelper.lib.items.directories.lists_default import ListProperties, ListDefault
from tmdbhelper.lib.items.itemlist import ItemListPagination
from tmdbhelper.lib.addon.plugin import convert_type, get_setting
from jurialmunkey.ftools import cached_property
from jurialmunkey.parser import try_int


class ListAniListSyncProperties(ListProperties):

    next_page = True
    sync_type = ''
    item_type = None
    item_keys = None
    filters = None
    sort_by = None
    sort_how = None
    params_def = None

    @cached_property
    def sync_data(self):
        return ItemListSyncDataFactory(
            self.sync_type,
            self.anilist_api,
            sort_by=self.sort_by,
            sort_how=self.sort_how,
            item_type=self.item_type,
            item_keys=self.item_keys,
            tmdb_id=self.tmdb_id).items

    @cached_property
    def response(self):
        if not self.sync_data:
            return
        return ItemListPagination(
            meta={self.item_type: self.sync_data},
            page=self.page,
            limit=self.limit,
            params_def=self.params_def,
            filters=self.filters)

    @property
    def items(self):
        if not self.response:
            return
        return self.response.items

    @property
    def finalised_items(self):
        if not self.items:
            return
        if not self.next_page or self.sort_by == 'random':
            return self.items
        return self.items + self.response.next_page


class ListStandardAniListSync(ListDefault):

    list_properties_class = ListAniListSyncProperties

    def configure_list_properties(self, list_properties):
        list_properties.limit = 20 * max(get_setting('pagemulti_sync', 'int'), 1)
        list_properties.plugin_name = '{plural} {localized}'
        list_properties.anilist_api = self.anilist_api
        return list_properties

    def get_items(self, tmdb_type, page=1, sort_by=None, sort_how=None, tmdb_id=None, **kwargs):
        self.list_properties.tmdb_id = tmdb_id
        self.list_properties.tmdb_type = tmdb_type
        self.list_properties.item_type = self.list_properties.item_type or convert_type(tmdb_type, 'trakt')
        self.list_properties.page = try_int(page) or 1
        self.list_properties.sort_by = sort_by or self.list_properties.sort_by
        self.list_properties.sort_how = sort_how or self.list_properties.sort_how
        return self.get_items_finalised()


class ListAniListWatchlist(ListStandardAniListSync):
    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.sync_type = 'anilist_watchlist'
        list_properties.sort_by = 'listed'
        list_properties.sort_how = 'desc'
        list_properties.localize = 32193  # Watchlist
        return list_properties


class ListAniListWatching(ListStandardAniListSync):
    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.sync_type = 'anilist_watching'
        list_properties.sort_by = 'updated'
        list_properties.sort_how = 'desc'
        list_properties.localize = 32041  # In Progress
        return list_properties


class ListAniListCompleted(ListStandardAniListSync):
    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.sync_type = 'anilist_completed'
        list_properties.sort_by = 'updated'
        list_properties.sort_how = 'desc'
        list_properties.localize = 16103  # Watched/Completed
        return list_properties


class ListAniListDropped(ListStandardAniListSync):
    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.sync_type = 'anilist_dropped'
        list_properties.sort_by = 'updated'
        list_properties.sort_how = 'desc'
        list_properties.localize = 32048  # Dropped
        return list_properties


class ListAniListPaused(ListStandardAniListSync):
    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.sync_type = 'anilist_paused'
        list_properties.sort_by = 'updated'
        list_properties.sort_how = 'desc'
        list_properties.localize = 32196  # Paused
        return list_properties
