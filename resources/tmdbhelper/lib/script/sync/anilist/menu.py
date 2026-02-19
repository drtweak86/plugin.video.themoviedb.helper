from tmdbhelper.lib.script.sync.anilist.basic import (
    ItemAniListWatchlist,
    ItemAniListWatching,
    ItemAniListCompleted,
    ItemAniListDropped,
    ItemAniListPaused,
)
from tmdbhelper.lib.script.sync.anilist.rating import ItemRating
from tmdbhelper.lib.script.sync.menu import Menu as BasicMenu


class Menu(BasicMenu):
    items = {
        'watchlist': ItemAniListWatchlist,
        'watching': ItemAniListWatching,
        'completed': ItemAniListCompleted,
        'dropped': ItemAniListDropped,
        'paused': ItemAniListPaused,
        'rating': ItemRating,
    }


def sync_item(tmdb_type, tmdb_id, season=None, episode=None, sync_type=None):
    menu = Menu(tmdb_type, tmdb_id, season, episode)
    menu.select(sync_type)
