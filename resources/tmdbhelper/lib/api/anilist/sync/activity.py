from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.addon.tmdate import set_timestamp, get_timestamp
from tmdbhelper.lib.addon.consts import DEFAULT_EXPIRY


ANILIST_LAST_SYNC_PROPERTY = 'AniListLastSync'


class SyncLastActivities:
    """
    AniList does not have a last_activities endpoint like Trakt.
    Instead we use a simple timestamp-based expiry.
    """

    expiry_time = DEFAULT_EXPIRY

    def __init__(self, instance_syncdata):
        self.instance_syncdata = instance_syncdata

    @property
    def window(self):
        return self.instance_syncdata.window

    def is_expired(self, timestamp, keys=None):
        """
        Returns True if the cached data should be considered expired.
        timestamp: the stored expiry timestamp (epoch int)
        """
        return not get_timestamp(timestamp, set_int=True)
