from jurialmunkey.ftools import cached_property
from datetime import datetime, timezone


MEDIALIST_QUERY = '''
query ($userId: Int, $type: MediaType) {
    MediaListCollection(userId: $userId, type: $type) {
        lists {
            entries {
                status
                score(format: POINT_100)
                progress
                updatedAt
                createdAt
                media {
                    id
                    idMal
                    title {
                        romaji
                        english
                        native
                    }
                    startDate {
                        year
                    }
                    type
                    format
                }
            }
        }
    }
}
'''


class AniListSyncItemData:
    """
    Processes a single AniList MediaList entry into a form suitable for DB storage.
    The item is expected to already have tmdb_id resolved.
    """

    def __init__(self, item, tmdb_type, tmdb_id):
        self.item = item
        self._tmdb_type = tmdb_type
        self._tmdb_id = tmdb_id

    @cached_property
    def tmdb_type(self):
        return self._tmdb_type

    @cached_property
    def tmdb_id(self):
        return self._tmdb_id

    @cached_property
    def item_type(self):
        if self.tmdb_type == 'tv':
            return 'show'
        return 'movie'

    @cached_property
    def item_id(self):
        return f'{self.tmdb_type}.{self.tmdb_id}'

    @cached_property
    def anilist_status(self):
        return self.item.get('status')

    @cached_property
    def anilist_score(self):
        score = self.item.get('score')
        return score if score else None

    @cached_property
    def anilist_progress(self):
        return self.item.get('progress')

    @cached_property
    def anilist_updated_at(self):
        updated = self.item.get('updatedAt')
        if not updated:
            return None
        try:
            return datetime.fromtimestamp(int(updated), tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        except (ValueError, TypeError, OSError):
            return None

    @cached_property
    def anilist_listed_at(self):
        created = self.item.get('createdAt')
        if not created:
            return None
        try:
            return datetime.fromtimestamp(int(created), tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        except (ValueError, TypeError, OSError):
            return None

    @cached_property
    def title(self):
        try:
            media = self.item.get('media', {})
            titles = media.get('title', {})
            return titles.get('english') or titles.get('romaji') or titles.get('native')
        except (AttributeError, TypeError):
            return None

    @cached_property
    def year(self):
        try:
            return self.item['media']['startDate']['year']
        except (KeyError, TypeError):
            return None

    @cached_property
    def anilist_media_id(self):
        try:
            return self.item['media']['id']
        except (KeyError, TypeError):
            return None

    @cached_property
    def mal_id(self):
        try:
            return self.item['media']['idMal']
        except (KeyError, TypeError):
            return None


class AniListSyncItem:
    """
    Processes a list of AniList MediaList entries into a dict keyed by item_id
    for batch DB storage.
    """

    _base_keys = ('anilist_status', 'anilist_score', 'anilist_progress', 'anilist_updated_at', 'anilist_listed_at')
    _additional_keys = ('item_type', 'tmdb_type', 'tmdb_id', 'title', 'year')

    def __init__(self, item_type, meta, keys, key_prefix=None):
        self.item_type = item_type  # 'show' or 'movie'
        self.meta = meta  # list of (entry, tmdb_type, tmdb_id) tuples
        self.base_keys = keys
        self.key_prefix = key_prefix

    @property
    def additional_keys(self):
        return self._additional_keys

    @property
    def keys(self):
        return (*self.base_keys, *self.additional_keys)

    @property
    def base_table_keys(self):
        if not self.key_prefix:
            return self.base_keys
        return tuple([f'{self.key_prefix}_{k}' for k in self.base_keys])

    @property
    def table_keys(self):
        return (*self.base_table_keys, *self.additional_keys)

    @cached_property
    def data(self):
        return self.get_data()

    def get_data(self):
        data = {}
        for entry, tmdb_type, tmdb_id in self.meta:
            if not tmdb_id:
                continue
            item_data = AniListSyncItemData(entry, tmdb_type, tmdb_id)
            data[item_data.item_id] = [getattr(item_data, k) for k in self.keys]
        return data
