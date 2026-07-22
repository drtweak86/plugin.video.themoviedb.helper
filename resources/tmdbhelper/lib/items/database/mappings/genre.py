from jurialmunkey.ftools import cached_property

from tmdbhelper.lib.items.database.mappings.general import GeneralMapperMethods


class GenreMapperMethods:
    @property
    def tmdb_database(self):
        from tmdbhelper.lib.query.database.database import FindQueriesDatabase
        return FindQueriesDatabase()

    @cached_property
    def genres_map(self):
        genres_map = {}
        genres_map.update(self.tmdb_database.get_genres('movie'))
        genres_map.update(self.tmdb_database.get_genres('tv'))
        genres_map = {v: k for k, v in genres_map.items()}
        return genres_map

    def get_genre_items(self, genre_ids):

        def get_genre_item(tmdb_id):
            try:
                return {'name': self.genres_map[tmdb_id], 'tmdb_id': tmdb_id}
            except (KeyError, TypeError):
                return

        return [j for j in (get_genre_item(i) for i in genre_ids if i) if j]

    def get_genres(self, items, **kwargs):

        def get_genre_id(i):
            try:
                return i['id']
            except (KeyError, TypeError):
                return

        genre_items = self.get_genre_items([j for j in (get_genre_id(i) for i in items if i) if j])
        return GeneralMapperMethods.split_array(genre_items, name='name', tmdb_id='tmdb_id')
