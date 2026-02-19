from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.items.database.database import ItemDetailsDatabase
from tmdbhelper.lib.files.dbdata import DatabaseStatements


class AniListSyncItemDetailsDatabase(ItemDetailsDatabase):
    def set_activity(self, item_type, method, value, expiry):
        cursor = self.execute_sql(
            DatabaseStatements.insert_or_replace('lactivities', keys=('id', 'data', 'expiry')),
            (f'{item_type}.anilist.{method}', value, expiry))
        cursor.close() if cursor else None

    def get_activity(self, item_type, method, expiry=0):
        cursor = self.execute_sql(
            DatabaseStatements.select_limit('lactivities', keys=('data', ), conditions='id=? and expiry>=?'),
            (f'{item_type}.anilist.{method}', expiry))
        if not cursor:
            return
        result = cursor.fetchone()
        cursor.close()
        if not result:
            return
        return result[0]


class SyncDataGetterAll:
    """Base getter class for AniList sync data retrieval."""

    operator = 'OR'
    query_clauses = ('item_type=?', )
    query_values = ('', )
    clause_keys = ()
    additional_keys = ()
    query_value_item_argx = 0

    def __init__(self, instance_syncdata):
        self.instance_syncdata = instance_syncdata

    @cached_property
    def item_type(self):
        return self.query_values[self.query_value_item_argx]

    @cached_property
    def base_keys(self):
        if self.item_type == 'episode':
            return ('tmdb_id', 'title', 'season_number', 'episode_number', )
        return ('tmdb_id', 'title', )

    @cached_property
    def clause(self):
        clause = [f'{k} IS NOT NULL' for k in self.clause_keys]
        clause = '({})'.format(f' {self.operator} '.join(clause))
        clause = (*self.query_clauses, clause, )
        clause = ' AND '.join(clause)
        return clause

    @cached_property
    def keys(self):
        return (*(self.base_keys or ()), *(self.clause_keys or ()), *(self.additional_keys or ()), )

    @cached_property
    def items(self):
        return self.get_items()

    def get_items(self):
        self.instance_syncdata.sync(self.item_type, self.keys)
        return self.instance_syncdata.cache.get_list_values(keys=self.keys, values=self.query_values, conditions=self.clause)


class SyncDataGetterAllItems(SyncDataGetterAll):
    @property
    def query_values(self):
        return (self.item_type, )


class SyncDataGetterAllItemsAniListStatus(SyncDataGetterAllItems):
    clause_keys = ('anilist_status', )


class SyncDataGetterAllItemsAniListWatchlist(SyncDataGetterAllItems):
    clause_keys = ('anilist_listed_at', )

    @cached_property
    def clause(self):
        clause = f"anilist_status='PLANNING'"
        clause = ' AND '.join((*self.query_clauses, clause))
        return clause


class SyncDataGetterAllItemsAniListWatching(SyncDataGetterAllItems):
    clause_keys = ('anilist_status', )

    @cached_property
    def clause(self):
        clause = f"anilist_status='CURRENT'"
        clause = ' AND '.join((*self.query_clauses, clause))
        return clause


class SyncDataGetterAllItemsAniListCompleted(SyncDataGetterAllItems):
    clause_keys = ('anilist_status', )

    @cached_property
    def clause(self):
        clause = f"anilist_status IN ('COMPLETED','REPEATING')"
        clause = ' AND '.join((*self.query_clauses, clause))
        return clause


class SyncDataGetterAllItemsAniListDropped(SyncDataGetterAllItems):
    clause_keys = ('anilist_status', )

    @cached_property
    def clause(self):
        clause = f"anilist_status='DROPPED'"
        clause = ' AND '.join((*self.query_clauses, clause))
        return clause


class SyncDataGetterAllItemsAniListPaused(SyncDataGetterAllItems):
    clause_keys = ('anilist_status', )

    @cached_property
    def clause(self):
        clause = f"anilist_status='PAUSED'"
        clause = ' AND '.join((*self.query_clauses, clause))
        return clause


class SyncDataGetters:
    """Add-in class to group getter methods for AniList SyncData class."""

    def get_item_type_getter(self, sync_data_class, item_type):
        sd = sync_data_class(self)
        sd.item_type = item_type
        return sd

    def get_anilist_status_getter(self, item_type):
        return self.get_item_type_getter(SyncDataGetterAllItemsAniListStatus, item_type)

    def get_anilist_watchlist_getter(self, item_type):
        return self.get_item_type_getter(SyncDataGetterAllItemsAniListWatchlist, item_type)

    def get_anilist_watching_getter(self, item_type):
        return self.get_item_type_getter(SyncDataGetterAllItemsAniListWatching, item_type)

    def get_anilist_completed_getter(self, item_type):
        return self.get_item_type_getter(SyncDataGetterAllItemsAniListCompleted, item_type)

    def get_anilist_dropped_getter(self, item_type):
        return self.get_item_type_getter(SyncDataGetterAllItemsAniListDropped, item_type)

    def get_anilist_paused_getter(self, item_type):
        return self.get_item_type_getter(SyncDataGetterAllItemsAniListPaused, item_type)


class SyncData(SyncDataGetters):

    def __init__(self, anilist_api):
        self.anilist_api = anilist_api

    @cached_property
    def routes(self):
        return self.get_routes()

    def get_routes(self):
        return {k: v['sync'] for k, v in self.cache.simplecache_columns.items()}

    @cached_property
    def cache(self):
        return AniListSyncItemDetailsDatabase()

    @cached_property
    def window(self):
        from jurialmunkey.window import WindowPropertySetter
        return WindowPropertySetter()

    @staticmethod
    def get_name(tmdb_type, tmdb_id, season=None, episode=None):
        name = f'{tmdb_type}.{tmdb_id}'
        if season is None:
            return name
        name = f'{name}.{season}'
        if episode is None:
            return name
        name = f'{name}.{episode}'
        return name

    def get_values(self, tmdb_type, tmdb_id, season=None, episode=None, keys=None):
        if tmdb_type not in ('tv', 'movie'):
            return None
        self.sync('show' if tmdb_type == 'tv' else 'movie', keys)
        return self.cache.get_values(item_id=self.get_name(tmdb_type, tmdb_id, season, episode), keys=keys)

    def get_value(self, tmdb_type, tmdb_id, season=None, episode=None, key=None):
        data = self.get_values(tmdb_type, tmdb_id, season, episode, keys=(key,))
        return data[0] if data else None

    def sync(self, item_type, keys, forced=False):
        from jurialmunkey.modimp import importmodule
        for route in set([j for j in (self.routes.get(k) for k in keys) if j]):
            importmodule(*route)(self, item_type).sync(forced=forced)
