# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
from tmdbhelper.lib.script.method.decorators import is_in_kwargs, get_tmdb_id


@is_in_kwargs({'tmdb_type': ['movie', 'tv']})
@get_tmdb_id
def sync_anilist(tmdb_type=None, tmdb_id=None, season=None, episode=None, sync_type=None, **kwargs):
    """ Open sync AniList menu for item """
    from tmdbhelper.lib.script.sync.anilist.menu import sync_item
    sync_item(tmdb_type=tmdb_type, tmdb_id=tmdb_id, season=season, episode=episode, sync_type=sync_type)


def authenticate_anilist(**kwargs):
    from tmdbhelper.lib.api.anilist.api import AniListAPI
    AniListAPI(force=True)
    invalidate_anilist_sync('all', notification=False, sync=False)


def revoke_anilist(**kwargs):
    from tmdbhelper.lib.api.anilist.api import AniListAPI
    AniListAPI().logout()
    invalidate_anilist_sync('all', notification=False, sync=False)


def invalidate_anilist_sync(invalidate_anilist_sync_type='all', notification=True, sync=True, **kwargs):
    from tmdbhelper.lib.api.anilist.sync.invalidator import SyncInvalidatorAll
    from tmdbhelper.lib.api.anilist.api import AniListAPI
    anilist_api = AniListAPI()
    if not anilist_api.anilist_syncdata:
        return
    invalidator = SyncInvalidatorAll(anilist_api.anilist_syncdata)
    invalidator.invalidate(forced=sync)
    if notification:
        from xbmcgui import Dialog
        Dialog().notification('TMDbHelper', 'AniList sync data cleared')
