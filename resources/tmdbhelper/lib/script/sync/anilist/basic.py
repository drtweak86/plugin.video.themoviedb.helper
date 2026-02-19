from tmdbhelper.lib.script.sync.anilist.item import ItemSync, SAVE_MEDIA_LIST_ENTRY, DELETE_MEDIA_LIST_ENTRY
from tmdbhelper.lib.addon.dialog import busy_decorator


class ItemAniListWatchlist(ItemSync):
    """Add/remove from AniList PLANNING list (watchlist equivalent)."""
    localized_name_add = 32291  # Add to watchlist
    localized_name_rem = 32292  # Remove from watchlist
    anilist_sync_key = 'anilist_listed_at'
    anilist_sync_status = 'PLANNING'

    @busy_decorator
    def get_sync_response(self):
        media_id = self.anilist_media_id
        if not media_id:
            return None

        if self.remove:
            entry_id = self.anilist_entry_id
            if not entry_id:
                return None
            return self.anilist_api.post_graphql(
                DELETE_MEDIA_LIST_ENTRY,
                {'id': entry_id}
            )
        else:
            return self.anilist_api.post_graphql(
                SAVE_MEDIA_LIST_ENTRY,
                {'mediaId': media_id, 'status': 'PLANNING'}
            )


class ItemAniListWatching(ItemSync):
    """Mark as currently watching on AniList (CURRENT status)."""
    localized_name_add = 32041  # In progress / Currently watching
    localized_name_rem = 32045  # Remove in progress
    anilist_sync_key = 'anilist_status'

    def get_remove(self):
        """Remove means switching away from CURRENT status, not deleting."""
        return self.sync_value == 'CURRENT'

    @busy_decorator
    def get_sync_response(self):
        media_id = self.anilist_media_id
        if not media_id:
            return None

        if self.remove:
            # Switch to PAUSED if removing from watching
            return self.anilist_api.post_graphql(
                SAVE_MEDIA_LIST_ENTRY,
                {'mediaId': media_id, 'status': 'PAUSED'}
            )
        else:
            return self.anilist_api.post_graphql(
                SAVE_MEDIA_LIST_ENTRY,
                {'mediaId': media_id, 'status': 'CURRENT'}
            )


class ItemAniListCompleted(ItemSync):
    """Mark as completed on AniList."""
    localized_name_add = 16103  # Watched / Completed
    localized_name_rem = 16104  # Unwatched
    anilist_sync_key = 'anilist_status'

    def get_remove(self):
        status = self.sync_value
        return status in ('COMPLETED', 'REPEATING')

    @busy_decorator
    def get_sync_response(self):
        media_id = self.anilist_media_id
        if not media_id:
            return None

        if self.remove:
            # Remove from completed - set back to CURRENT
            return self.anilist_api.post_graphql(
                SAVE_MEDIA_LIST_ENTRY,
                {'mediaId': media_id, 'status': 'CURRENT'}
            )
        else:
            return self.anilist_api.post_graphql(
                SAVE_MEDIA_LIST_ENTRY,
                {'mediaId': media_id, 'status': 'COMPLETED'}
            )


class ItemAniListDropped(ItemSync):
    """Mark as dropped on AniList."""
    allow_movies = False
    allow_shows = True
    localized_name_add = 32046  # Drop
    localized_name_rem = 32047  # Un-drop
    anilist_sync_key = 'anilist_status'

    def get_remove(self):
        return self.sync_value == 'DROPPED'

    @busy_decorator
    def get_sync_response(self):
        media_id = self.anilist_media_id
        if not media_id:
            return None

        if self.remove:
            return self.anilist_api.post_graphql(
                SAVE_MEDIA_LIST_ENTRY,
                {'mediaId': media_id, 'status': 'PLANNING'}
            )
        else:
            return self.anilist_api.post_graphql(
                SAVE_MEDIA_LIST_ENTRY,
                {'mediaId': media_id, 'status': 'DROPPED'}
            )


class ItemAniListPaused(ItemSync):
    """Mark as paused/on-hold on AniList."""
    localized_name_add = 32196  # Paused
    localized_name_rem = 32196  # Paused
    anilist_sync_key = 'anilist_status'

    def get_remove(self):
        return self.sync_value == 'PAUSED'

    @busy_decorator
    def get_sync_response(self):
        media_id = self.anilist_media_id
        if not media_id:
            return None

        if self.remove:
            return self.anilist_api.post_graphql(
                SAVE_MEDIA_LIST_ENTRY,
                {'mediaId': media_id, 'status': 'CURRENT'}
            )
        else:
            return self.anilist_api.post_graphql(
                SAVE_MEDIA_LIST_ENTRY,
                {'mediaId': media_id, 'status': 'PAUSED'}
            )
