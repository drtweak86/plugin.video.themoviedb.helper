from tmdbhelper.lib.items.container import ContainerDefaultCacheDirectory, ContainerCacheOnlyDirectory
from tmdbhelper.lib.items.database.baseview_factories.factory import BaseViewFactory
from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.addon.plugin import convert_type, get_setting
from jurialmunkey.parser import try_int


class ListConfigureOffset:
    def __init__(self, func):
        self.func = func

    @cached_property
    def offset(self):
        if not self.limit:
            return
        if not self.page:
            return
        return ((self.limit * self.page) - self.limit)

    @cached_property
    def items(self):
        limit = None if not self.limit else (self.limit + 1)
        return self.func(self.inst, *self.args, limit=limit, offset=self.offset, **self.kwgs)

    @cached_property
    def finalised_items(self):
        if not self.items:
            return
        if not self.limit or len(self.items) <= self.limit:
            return self.items
        self.items[-1] = {'next_page': self.page + 1}
        return self.items

    @cached_property
    def limit(self):
        return (
            self.pmax if self.inst.is_cacheonly else
            min((20 * get_setting('pagemulti_sync', 'int')), self.pmax)
        )

    def __get__(self, obj, obj_type):
        """Support instance methods."""
        import functools
        return functools.partial(self.__call__, obj)

    def __call__(self, inst, *args, limit=None, page=None, **kwgs):
        self.inst = inst
        self.args = args
        self.kwgs = kwgs
        self.page = try_int(page, fallback=1)
        self.pmax = try_int(limit, fallback=None) or 250
        return self.finalised_items


class ListImageViewBase(ContainerCacheOnlyDirectory):
    view_name = None

    def get_items(self, tmdb_id, tmdb_type, season=None, episode=None, limit=None, sort_by=None, sort_how=None, **kwargs):
        sync = BaseViewFactory(self.view_name, tmdb_type, tmdb_id, season, episode, filters=self.filters, limit=limit, sort_by=sort_by, sort_how=sort_how)
        self.container_content = convert_type('image', 'container')
        return sync.data


class ListFanart(ListImageViewBase):
    view_name = 'fanart'


class ListPoster(ListImageViewBase):
    view_name = 'poster'


class ListImage(ListImageViewBase):
    view_name = 'image'


class ListThumb(ListImageViewBase):
    view_name = 'thumb'


class ListPersonListViewBase(ContainerCacheOnlyDirectory):
    view_name = None

    @ListConfigureOffset
    def get_items(self, tmdb_id, tmdb_type, season=None, episode=None, limit=None, sort_by=None, sort_how=None, offset=None, **kwargs):
        sync = BaseViewFactory(self.view_name, tmdb_type, tmdb_id, season, episode, filters=self.filters, limit=limit, offset=offset, sort_by=sort_by, sort_how=sort_how)
        self.container_content = convert_type('person', 'container')
        return sync.data


class ListCast(ListPersonListViewBase):
    view_name = 'castmember'


class ListCrew(ListPersonListViewBase):
    view_name = 'crewmember'


class ListPersonOrCollectionViewBase(ContainerDefaultCacheDirectory):
    view_name = None
    base_tmdb_type = 'person'
    kodi_db_type = 'movie'
    content_type = 'movie'

    @ListConfigureOffset
    def get_items(self, tmdb_id, limit=None, sort_by=None, sort_how=None, offset=None, **kwargs):
        sync = BaseViewFactory(self.view_name, self.base_tmdb_type, tmdb_id, filters=self.filters, limit=limit, offset=offset, sort_by=sort_by, sort_how=sort_how)
        self.kodi_db = self.get_kodi_database(self.kodi_db_type)
        self.container_content = convert_type(self.content_type, 'container')
        return sync.data


class ListSeries(ListPersonOrCollectionViewBase):
    view_name = 'seriesmovies'
    base_tmdb_type = 'collection'


class ListStarredMovies(ListPersonOrCollectionViewBase):
    view_name = 'starredmovies'


class ListStarredTvshows(ListPersonOrCollectionViewBase):
    view_name = 'starredtvshows'
    kodi_db_type = 'tv'
    content_type = 'tv'


class ListCombinedViewBase(ContainerDefaultCacheDirectory):
    view_name = None

    @ListConfigureOffset
    def get_items(self, tmdb_id, limit=None, sort_by=None, sort_how=None, offset=None, **kwargs):
        sync = BaseViewFactory(self.view_name, 'person', tmdb_id, filters=self.filters, limit=limit, offset=offset, sort_by=sort_by, sort_how=sort_how)
        try:
            movie_count = len([i for i in sync.data if i and i['infoproperties'].get('tmdb_type') == 'movie'])
            shows_count = len(sync.data) - movie_count
        except TypeError:
            return
        self.kodi_db = self.get_kodi_database('both')
        self.container_content = convert_type('tv', 'container') if shows_count > movie_count else convert_type('movie', 'container')
        return sync.data


class ListStarredCombined(ListCombinedViewBase):
    view_name = 'starredcombined'


class ListCrewedMovies(ListPersonOrCollectionViewBase):
    view_name = 'crewedmovies'


class ListCrewedTvshows(ListPersonOrCollectionViewBase):
    view_name = 'crewedtvshows'
    kodi_db_type = 'tv'
    content_type = 'tv'


class ListCrewedCombined(ListCombinedViewBase):
    view_name = 'crewedcombined'


class ListCreditsCombined(ListCombinedViewBase):
    view_name = 'creditscombined'


class ListVideos(ContainerCacheOnlyDirectory):
    def get_items(self, tmdb_id, tmdb_type, season=None, episode=None, limit=None, sort_by=None, sort_how=None, **kwargs):
        sync = BaseViewFactory('videos', tmdb_type, tmdb_id, season, episode, filters=self.filters, limit=limit, sort_by=sort_by, sort_how=sort_how)
        self.container_content = convert_type('video', 'container')
        return sync.data
