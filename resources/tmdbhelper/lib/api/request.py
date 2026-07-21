import jurialmunkey.reqapi
from tmdbhelper.lib.addon.plugin import get_setting
from tmdbhelper.lib.addon.logger import kodi_log
from tmdbhelper.lib.files.bcache import BasicCache


def null_function(*args, **kwargs):
    return


class RequestAPI(jurialmunkey.reqapi.RequestAPI):
    error_notification = get_setting('connection_notifications')
    _basiccache = BasicCache
    last_response = None

    @staticmethod
    def kodi_log(msg, level=0):
        kodi_log(msg, level)

    def get_simple_api_request(self, *args, **kwargs):
        self.last_response = super().get_simple_api_request(*args, **kwargs)
        return self.last_response


class NoCacheRequestAPI(RequestAPI):
    _basiccache = null_function
