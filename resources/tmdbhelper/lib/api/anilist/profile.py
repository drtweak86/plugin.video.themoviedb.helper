from jurialmunkey.ftools import cached_property


VIEWER_QUERY = '''
query {
    Viewer {
        id
        name
    }
}
'''


class AniListProfile:
    def __init__(self, anilist_api):
        self.anilist_api = anilist_api

    @cached_property
    def meta(self):
        if not self.anilist_api.is_authorized:
            return {}
        response = self.anilist_api.post_graphql(VIEWER_QUERY)
        try:
            return response.get('data', {}).get('Viewer', {}) or {}
        except AttributeError:
            return {}

    @cached_property
    def user_id(self):
        return self.meta.get('id')

    @cached_property
    def username(self):
        return self.meta.get('name')
