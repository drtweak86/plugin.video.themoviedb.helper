from tmdbhelper.lib.items.directories.base.basedir_item import BaseDirItem


class BaseDirItemAniListAuthorised(BaseDirItem):
    @property
    def enabled(self):
        from jurialmunkey.window import get_property
        return bool(get_property('AniListIsAuth'))


class BaseDirItemAniListWatchlist(BaseDirItemAniListAuthorised):
    priority = 500
    label_type = 'reversed'
    label_localized = 32193  # Watchlist
    types = ('tv', 'movie', 'both', )
    params = {'info': 'anilist_watchlist'}
    sorting = True
    art_icon = 'resources/icons/trakt/watchlist.png'
    group = 32193


class BaseDirItemAniListWatching(BaseDirItemAniListAuthorised):
    priority = 510
    label_type = 'reversed'
    label_localized = 32041  # In Progress / Currently Watching
    types = ('tv', 'movie', 'both', )
    params = {'info': 'anilist_watching'}
    sorting = True
    art_icon = 'resources/icons/trakt/inprogress.png'
    group = 32041


class BaseDirItemAniListCompleted(BaseDirItemAniListAuthorised):
    priority = 520
    label_type = 'reversed'
    label_localized = 16103  # Watched/Completed
    types = ('tv', 'movie', 'both', )
    params = {'info': 'anilist_completed'}
    sorting = True
    art_icon = 'resources/icons/trakt/recentlywatched.png'
    group = 16103


class BaseDirItemAniListDropped(BaseDirItemAniListAuthorised):
    priority = 530
    label_type = 'reversed'
    label_localized = 32048  # Dropped
    types = ('tv', 'movie', 'both', )
    params = {'info': 'anilist_dropped'}
    art_icon = 'resources/icons/trakt/watchlist.png'
    group = 32048


class BaseDirItemAniListPaused(BaseDirItemAniListAuthorised):
    priority = 540
    label_type = 'reversed'
    label_localized = 32196  # Paused
    types = ('tv', 'movie', 'both', )
    params = {'info': 'anilist_paused'}
    art_icon = 'resources/icons/trakt/inprogress.png'
    group = 32196
