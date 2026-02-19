from tmdbhelper.lib.api.api_keys.tokenhandler import TokenHandler


CLIENT_ID = ''  # Users must create their own AniList OAuth app at https://anilist.co/settings/developer
USER_TOKEN = TokenHandler('anilist_token', store_as='setting')
