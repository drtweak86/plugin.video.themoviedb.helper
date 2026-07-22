from tmdbhelper.lib.items.directories.tmdb.lists_standard import ListStandard, ListStandardProperties
from tmdbhelper.lib.items.directories.tmdb.lists_allitems import ItemKeywords, ItemReviews
from jurialmunkey.ftools import cached_property


class ListRelatedProperties(ListStandardProperties):
    title_preposition = 'for'

    @cached_property
    def url(self):
        return self.request_url.format(tmdb_type=self.tmdb_type, tmdb_id=self.tmdb_id)

    @cached_property
    def cache_name_tuple(self):
        return (
            self.class_name,
            self.tmdb_type,
            self.tmdb_id,
            self.page,
            self.pmax
        )

    @cached_property
    def item_title(self):
        from tmdbhelper.lib.items.database.baseitem_factories.factory import BaseItemFactory
        mediatype = 'movie' if self.tmdb_type == 'movie' else 'tvshow'
        sync = BaseItemFactory(mediatype)
        sync.tmdb_id = self.tmdb_id
        try:
            return sync.data['infolabels']['title']
        except (KeyError, TypeError, AttributeError):
            return ''

    @cached_property
    def plugin_category(self):
        base = self.plugin_name.format(localized=self.localized, plural=self.plural)
        if self.item_title:
            return f'{base} {self.title_preposition} {self.item_title}'
        return base


class ListRelated(ListStandard):
    list_properties_class = ListRelatedProperties

    def get_items(self, *args, tmdb_id=None, **kwargs):
        self.list_properties.tmdb_id = tmdb_id
        return super().get_items(*args, **kwargs)


class ListRecommendations(ListRelated):

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.plugin_name = '{localized}'
        list_properties.dbid_sorted = True
        list_properties.request_url = '{tmdb_type}/{tmdb_id}/recommendations'
        list_properties.localize = 32223
        list_properties.page_length = 2  # Recommendations only have 2 pages
        list_properties.length = 2
        return list_properties


class ListSimilar(ListRelated):

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.plugin_name = '{localized}'
        list_properties.title_preposition = 'to'
        list_properties.dbid_sorted = True
        list_properties.request_url = '{tmdb_type}/{tmdb_id}/similar'
        list_properties.localize = 32224
        return list_properties


class ListReviews(ListRelated):

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.plugin_name = '{localized}'
        list_properties.dbid_sorted = True
        list_properties.request_url = '{tmdb_type}/{tmdb_id}/reviews'
        list_properties.tmdb_type = 'review'
        list_properties.localize = 32188
        return list_properties

    def get_mapped_item(self, item, *args, **kwargs):
        return ItemReviews(**item).item


class ListKeywords(ListRelated):

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.plugin_name = '{localized}'
        list_properties.request_url = 'movie/{tmdb_id}/keywords'
        list_properties.results_key = 'keywords'
        list_properties.tmdb_type = 'keyword'
        list_properties.localize = 21861
        return list_properties

    def get_mapped_item(self, item, *args, **kwargs):
        return ItemKeywords(**item).item
