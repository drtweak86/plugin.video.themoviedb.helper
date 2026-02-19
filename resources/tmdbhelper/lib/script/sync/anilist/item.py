from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.addon.dialog import busy_decorator
from tmdbhelper.lib.script.sync.item import ItemSync as BasicItemSync


ANILIST_GRAPHQL_URL = 'https://graphql.anilist.co'

# AniList GraphQL mutations
SAVE_MEDIA_LIST_ENTRY = '''
mutation ($mediaId: Int, $status: MediaListStatus, $score: Float, $progress: Int) {
    SaveMediaListEntry(mediaId: $mediaId, status: $status, score: $score, progress: $progress) {
        id
        status
        score
        progress
        updatedAt
    }
}
'''

DELETE_MEDIA_LIST_ENTRY = '''
mutation ($id: Int) {
    DeleteMediaListEntry(id: $id) {
        deleted
    }
}
'''

GET_MEDIA_LIST_ENTRY = '''
query ($mediaId: Int, $userId: Int) {
    MediaList(mediaId: $mediaId, userId: $userId) {
        id
        status
        score
        progress
        updatedAt
        createdAt
    }
}
'''

SEARCH_MEDIA_QUERY = '''
query ($search: String, $type: MediaType) {
    Media(search: $search, type: $type) {
        id
        title {
            romaji
            english
        }
    }
}
'''


class ItemSync(BasicItemSync):
    anilist_sync_key = None
    anilist_sync_status = None  # The AniList status to set when adding

    @cached_property
    def anilist_api(self):
        from tmdbhelper.lib.api.anilist.api import AniListAPI
        return AniListAPI()

    @cached_property
    def anilist_syncdata(self):
        return self.anilist_api.anilist_syncdata

    @cached_property
    def anilist_media_id(self):
        """Get the AniList media ID by reverse-lookup from TMDb ID."""
        return self._resolve_anilist_id()

    def _resolve_anilist_id(self):
        """
        Reverse-lookup: given TMDb ID, find AniList media ID.
        We do this by fetching the user's MediaListCollection and finding the entry.
        """
        if not self.anilist_api.is_authorized:
            return None

        user_id = self.anilist_api.profile.user_id
        if not user_id:
            return None

        # Get from our sync cache if available
        sync = self.anilist_syncdata
        if not sync:
            return None

        # We need to search AniList by title to get the media ID
        try:
            item = self.item_details
            title = item.get('label') or item.get('infolabels', {}).get('title')
            if not title:
                return None

            media_type = 'ANIME' if self.tmdb_type == 'tv' else 'MANGA'
            result = self.anilist_api.post_graphql(
                SEARCH_MEDIA_QUERY,
                {'search': title, 'type': media_type}
            )
            return result.get('data', {}).get('Media', {}).get('id')
        except Exception:
            return None

    @cached_property
    def anilist_list_entry(self):
        """Get the current AniList list entry for this item."""
        if not self.anilist_media_id:
            return None
        user_id = self.anilist_api.profile.user_id
        if not user_id:
            return None
        result = self.anilist_api.post_graphql(
            GET_MEDIA_LIST_ENTRY,
            {'mediaId': self.anilist_media_id, 'userId': user_id}
        )
        try:
            return result.get('data', {}).get('MediaList')
        except AttributeError:
            return None

    @cached_property
    def anilist_entry_id(self):
        """Get the AniList list entry ID (for deletions)."""
        if not self.anilist_list_entry:
            return None
        return self.anilist_list_entry.get('id')

    def get_sync_value(self):
        if not self.anilist_syncdata or not self.anilist_sync_key:
            return None
        return self.anilist_syncdata.get_value(
            self.tmdb_type,
            self.tmdb_id,
            self.season,
            self.episode,
            self.anilist_sync_key
        )

    def _invalidate_cache(self):
        """Force re-sync of AniList data."""
        if not self.anilist_syncdata:
            return
        item_type = 'show' if self.tmdb_type == 'tv' else 'movie'
        method = 'medialist_anime' if self.tmdb_type == 'tv' else 'medialist_manga'
        self.anilist_syncdata.cache.del_item(
            table='lactivities',
            item_id=f'{item_type}.anilist.{method}'
        )

    @busy_decorator
    def get_sync_response(self):
        """Execute the AniList sync action."""
        raise NotImplementedError('Subclasses must implement get_sync_response')

    def sync(self):
        self._invalidate_cache()
        super().sync()

    def get_is_successful_sync(self):
        """AniList uses GraphQL so we check for errors in response, not status codes."""
        if not self.sync_response:
            return False
        if not isinstance(self.sync_response, dict):
            return False
        return 'errors' not in self.sync_response

    def get_status_code_message(self):
        if not self.sync_response:
            return 'No response'
        errors = self.sync_response.get('errors', [])
        if errors:
            return errors[0].get('message', 'AniList error')
        return 'OK'
