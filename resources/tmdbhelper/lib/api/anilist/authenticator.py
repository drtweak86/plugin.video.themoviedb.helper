from xbmcgui import Dialog
from jurialmunkey.window import get_property
from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.api.anilist.token import AniListStoredAccessToken, ANILIST_AUTH_URL
from tmdbhelper.lib.addon.plugin import get_localized, KeyGetter
from tmdbhelper.lib.addon.logger import kodi_log
from tmdbhelper.lib.files.locker import mutexlock


class AniListAuthenticator:

    mutex_lockname = 'AniListAskingForLogin'

    def __init__(self, anilist_api):
        self.anilist_api = anilist_api

    def get_key(self, dictionary, key):
        return KeyGetter(dictionary).get_key(key)

    @cached_property
    def anilist_stored_access_token(self):
        return AniListStoredAccessToken(self.anilist_api)

    @cached_property
    def authorization(self):
        return self.anilist_stored_access_token.authorization

    @property
    def access_token(self):
        return self.get_key(self.authorization, 'access_token')

    @property
    def is_authorized(self):
        return bool(self.access_token)

    def authorize(self, forced=False):
        if not self.is_authorized and forced:
            self.ask_to_login()
        return self.is_authorized

    @cached_property
    def dialog_noapikey_header(self):
        return f'{get_localized(32007)} {self.anilist_api.req_api_name} {get_localized(32011)}'

    @cached_property
    def dialog_noapikey_text(self):
        return get_localized(32012)

    @mutexlock
    def ask_to_login(self):
        x = Dialog().yesno(
            self.dialog_noapikey_header,
            self.dialog_noapikey_text,
            nolabel=get_localized(222),
            yeslabel=get_localized(186),
        )
        if x:
            self.login()

    def login(self):
        """
        AniList uses OAuth implicit grant flow.
        Shows a QR code the user scans with their phone to open the auth URL,
        then prompts them to paste the access_token from the AniList pin page.
        """
        client_id = self.anilist_api.client_id
        if not client_id:
            Dialog().ok(
                'AniList',
                'No AniList Client ID configured. Please set your AniList Client ID in settings.'
            )
            return

        auth_url = ANILIST_AUTH_URL.format(client_id=client_id)

        from tmdbhelper.lib.api.anilist.qr import show_qr_auth_dialog
        show_qr_auth_dialog(auth_url)

        token = Dialog().input('Paste your AniList access token here:')
        if not token:
            return

        self.anilist_api.user_token.value = token.strip()
        kodi_log('AniList: Token stored, confirming authorization...')

        if self.anilist_stored_access_token.confirm_authorization():
            kodi_log(u'AniList authenticated successfully!', 1)
            Dialog().notification(
                'TMDbHelper',
                'AniList authenticated successfully!',
            )
        else:
            kodi_log(u'AniList authentication failed - invalid token', 1)
            Dialog().ok('AniList', 'Authentication failed. Please check your token and try again.')
            self.anilist_api.user_token.value = ''

    def logout(self, confirmation=True):
        if confirmation and not Dialog().yesno(get_localized(32212), get_localized(32213)):
            return
        return AniListStoredAccessToken(self.anilist_api).logout()
