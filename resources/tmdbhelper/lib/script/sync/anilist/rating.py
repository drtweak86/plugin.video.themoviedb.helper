from tmdbhelper.lib.script.sync.anilist.item import ItemSync, SAVE_MEDIA_LIST_ENTRY
from tmdbhelper.lib.addon.plugin import get_localized
from tmdbhelper.lib.addon.dialog import busy_decorator
from xbmcgui import Dialog


SAVE_SCORE_MUTATION = '''
mutation ($mediaId: Int, $score: Float) {
    SaveMediaListEntry(mediaId: $mediaId, score: $score) {
        id
        score
    }
}
'''


class ItemRating(ItemSync):
    allow_episodes = False  # AniList scores are per-media, not per-episode
    localized_name_add = 32485  # Rate
    localized_name_rem = 32489  # Change Rating
    anilist_sync_key = 'anilist_score'

    def get_name_remove(self):
        return f'{get_localized(self.localized_name_rem)} ({self.sync_value})'

    @staticmethod
    def refresh_containers():
        pass  # Override - no container refresh needed for ratings

    def get_dialog_header(self):
        score = self.sync_value
        if not score:
            return get_localized(32485)  # Rate
        return f'{get_localized(32489)} ({score})'  # Change Rating (score)

    @busy_decorator
    def _set_score(self, score):
        media_id = self.anilist_media_id
        if not media_id:
            return None
        return self.anilist_api.post_graphql(
            SAVE_SCORE_MUTATION,
            {'mediaId': media_id, 'score': float(score)}
        )

    def get_sync_response(self):
        try:
            x = int(Dialog().numeric(0, f'{self.name} (0-100)'))
        except ValueError:
            return None

        if x < 0 or x > 100:
            return None

        return self._set_score(x)
