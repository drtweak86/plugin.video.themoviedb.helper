from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.api.request import NoCacheRequestAPI
from tmdbhelper.lib.api.api_keys.anilist import CLIENT_ID, USER_TOKEN
from tmdbhelper.lib.api.anilist.authenticator import AniListAuthenticator
from tmdbhelper.lib.api.anilist.profile import AniListProfile
from tmdbhelper.lib.files.futils import json_dumps as data_dumps


API_URL = 'https://graphql.anilist.co'
_HEADERS_BASE = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}


class AniListAPI(NoCacheRequestAPI):

    client_id = CLIENT_ID
    user_token = USER_TOKEN

    def __init__(
            self,
            client_id=None,
            user_token=None,
            login_if_required=False,
            force=False):
        super(AniListAPI, self).__init__(req_api_url=API_URL, req_api_name='AniListAPI', timeout=20)

        AniListAPI.client_id = client_id or self.client_id
        AniListAPI.user_token = user_token or self.user_token
        self.login_if_required = login_if_required
        self.login() if force else self.authorize()

    @property
    def headers(self):
        return self.get_headers(self.access_token)

    def get_headers(self, access_token=None):
        if access_token:
            return {**_HEADERS_BASE, 'Authorization': f'Bearer {access_token}'}
        return dict(_HEADERS_BASE)

    @headers.setter
    def headers(self, value):
        """ Ignore base class req_api attempting to set headers """
        return

    @property
    def access_token(self):
        if not self.authenticator.access_token:
            return
        if not self.authenticator.anilist_stored_access_token.has_valid_token:
            self.refresh_authenticator()
        return self.authenticator.access_token

    @cached_property
    def authenticator(self):
        return AniListAuthenticator(self)

    def refresh_authenticator(self):
        self.authenticator = AniListAuthenticator(self)

    @property
    def is_authorized(self):
        return self.authorize(forced=True)

    def authorize(self, forced=False):
        return self.authenticator.authorize(forced or self.login_if_required)

    def logout(self):
        self.refresh_authenticator()
        self.authenticator.logout()

    def login(self):
        self.refresh_authenticator()
        self.authenticator.login()

    @cached_property
    def profile(self):
        return AniListProfile(self)

    def post_graphql(self, query, variables=None):
        """Execute a GraphQL query against the AniList API."""
        postdata = {'query': query}
        if variables:
            postdata['variables'] = variables
        response = self.get_simple_api_request(
            API_URL,
            headers=self.headers,
            postdata=data_dumps(postdata),
            method='post'
        )
        try:
            return response.json()
        except (ValueError, AttributeError):
            return {}

    def get_response_json(self, *args, **kwargs):
        try:
            return self.get_api_request(self.get_request_url(*args, **kwargs), headers=self.headers).json()
        except ValueError:
            return {}
        except AttributeError:
            return {}

    def post_response(self, *args, postdata=None, response_method='post', **kwargs):
        return self.get_simple_api_request(
            self.get_request_url(*args, **kwargs),
            headers=self.headers,
            postdata=data_dumps(postdata) if postdata else None,
            method=response_method)

    @cached_property
    def anilist_syncdata(self):
        return self.get_anilist_syncdata()

    def get_anilist_syncdata(self):
        if not self.is_authorized:
            return
        from tmdbhelper.lib.api.anilist.sync.datasync import SyncData
        return SyncData(self)
