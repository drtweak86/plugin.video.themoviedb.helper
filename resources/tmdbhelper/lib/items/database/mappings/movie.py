from tmdbhelper.lib.items.database.mappings.support import ExtendedMap
from tmdbhelper.lib.items.database.mappings.general import GeneralMapperMethods
from tmdbhelper.lib.items.database.mappings.art import ArtMapperMethods


class MovieMapperMethods:
    def get_belongs_to_collection(self, i, **kwargs):
        data = []

        item_id = f"movie.{self.tmdb_id}"
        collection_id = f"collection.{i['id']}"

        collection_item = GeneralMapperMethods.get_configured_item(i, **{
            'tmdb_id': 'id',
            'title': 'name',
        })
        collection_item['id'] = collection_id
        data.append(ExtendedMap('collection', collection_id, False, collection_item))

        ArtMapperMethods.set_default_art(data, i, parent_id=item_id)

        data.append(ExtendedMap('belongs', item_id, False, {
            'id': item_id,
            'parent_id': collection_id,
        }))

        data.append(ExtendedMap('baseitem', collection_id, False, {
            'id': collection_id,
            'mediatype': 'set',
            'expiry': 0,
            'language': self.language,
        }))

        return data

    def get_collection(self, collection_object, **kwargs):
        data = []

        if not collection_object:
            return data

        collection_id = f"collection.{collection_object['id']}"

        for i in (collection_object.get('parts') or []):
            data.extend(self.get_media_item_data(i, 'movie'))
            data.append(ExtendedMap('belongs', f'movie.{i["id"]}', False, {
                'id': f'movie.{i["id"]}',
                'parent_id': collection_id,
            }))

        return data

    def get_parts(self, parts, **kwargs):
        data = []

        if not parts:
            return data

        collection_id = f"collection.{self.tmdb_id}"

        for i in parts:
            data.extend(self.get_media_item_data(i, 'movie'))
            data.append(ExtendedMap('belongs', f'movie.{i["id"]}', False, {
                'id': f'movie.{i["id"]}',
                'parent_id': collection_id,
            }))

        return data
