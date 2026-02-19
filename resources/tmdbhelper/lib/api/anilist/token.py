from jurialmunkey.window import get_property
from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.addon.plugin import get_localized, get_setting, ADDONPATH
from tmdbhelper.lib.addon.logger import kodi_log
from tmdbhelper.lib.files.locker import mutexlock
from tmdbhelper.lib.addon.tmdate import get_timestamp


ANILIST_AUTH_URL = 'https://anilist.co/api/v2/oauth/authorize?client_id={client_id}&response_type=token'
ANILIST_CHECK_URL = 'https://graphql.anilist.co'
ANILIST_CHECK_QUERY = '{ Viewer { id name } }'


class AniListStoredAccessToken:

    mutex_lockname = 'AniListCheckingAuthorization'
    access_message = ''

    def __init__(self, anilist_api):
        self.anilist_api = anilist_api

    @property
    def access_token(self):
        return self.anilist_api.user_token.value or None

    @property
    def has_valid_token(self):
        """ AniList tokens do not expire, so just check we have a value """
        return bool(self.access_token)

    @property
    def is_expired(self):
        if not self.access_token:
            self.access_message = '[no access_token]'
            return True
        if not get_timestamp(get_property('AniListIsAuth', is_type=float)):
            self.access_message = '[session token expired]'
            return True
        return False

    def confirm_authorization(self):
        response = self.anilist_api.get_simple_api_request(
            ANILIST_CHECK_URL,
            headers=self.anilist_api.get_headers(self.access_token),
            postdata='{"query":"{ Viewer { id name } }"}',
            method='post'
        )
        try:
            status_code = response.status_code
        except AttributeError:
            return False
        if status_code != 200:
            return False
        self.update_anilistisauth_property()
        kodi_log('AniList authentication token confirmed.')
        return True

    def authorization_check(self):
        if not self.confirm_authorization():
            return
        if get_setting('startup_notifications'):
            from xbmcgui import Dialog
            Dialog().notification(
                'TMDbHelper',
                'AniList authorized',
                icon=f'{ADDONPATH}/icon.png')
        return True

    @cached_property
    def winprop_anilistisauth(self):
        winprop_anilistisauth = get_property('AniListIsAuth', is_type=float)
        winprop_anilistisauth = winprop_anilistisauth or self.authorization_check()
        return winprop_anilistisauth or 0

    def update_anilistisauth_property(self):
        import time
        get_property('AniListIsAuth', set_property=f'{time.time() + 86400}')  # Valid for 24h session

    def delete_stored_authorization(self):
        self.anilist_api.user_token.value = ''
        get_property('AniListIsAuth', clear_property=True)

    @mutexlock
    def get_refreshed_token(self):
        if not self.is_expired:
            return self.access_token

        if not self.access_token:
            return None

        if not self.authorization_check():
            return None

        return self.access_token

    @cached_property
    def authorization(self):
        return {'access_token': self.access_token} if self.get_refreshed_token() else {}

    def logout(self):
        from xbmcgui import Dialog
        head = get_localized(32212)
        self.delete_stored_authorization()
        Dialog().ok(head, get_localized(32216))
