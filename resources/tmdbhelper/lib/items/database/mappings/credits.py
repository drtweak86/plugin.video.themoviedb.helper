from tmdbhelper.lib.items.database.mappings.support import ExtendedMap
from tmdbhelper.lib.items.database.mappings.general import GeneralMapperMethods
from tmdbhelper.lib.items.database.mappings.art import ArtMapperMethods


class CreditsMapperMethods:
    credits_mappings = (
        ('cast', 'castmember', {'ordering': 'order', 'role': 'character', 'appearances': 'total_episode_count'}, 'roles'),
        ('crew', 'crewmember', {'department': 'department', 'role': 'job', 'appearances': 'total_episode_count'}, 'jobs'),
        ('guest_stars', 'castmember', {'ordering': 'order', 'role': 'character', 'appearances': 'total_episode_count', 'guest': lambda i: 1}, 'roles'),
    )

    def get_credits(self, items, **kwargs):
        return self.get_credits_data(items, False)

    def get_aggregate_credits(self, items, **kwargs):
        return self.get_credits_data(items, True)

    def get_credits_data(self, items, aggregrate=False):
        data = []
        for subkey, mapkey, config, jobkey in self.credits_mappings:

            for i in (items.get(subkey) or []):
                item_id = f'person.{i["id"]}'
                tmdb_id = i['id']

                data.append(ExtendedMap('baseitem', item_id, False, {
                    'id': item_id,
                    'mediatype': 'person',
                    'expiry': 0,
                    'language': self.language,
                }))

                jobs = (i.get(jobkey) or []) if aggregrate else [i]

                for j in jobs:
                    credit_item = GeneralMapperMethods.get_configured_item(i, **config)
                    credit_item.update(GeneralMapperMethods.get_configured_item(j, blanks=False, **config))
                    credit_item['tmdb_id'] = tmdb_id
                    data.append(ExtendedMap(mapkey, j.get('credit_id'), False, credit_item))

                person_item = GeneralMapperMethods.get_configured_item(i, **{
                    'name': 'name',
                    'gender': 'gender',
                    'known_for_department': 'known_for_department',
                })
                person_item['id'] = item_id
                person_item['tmdb_id'] = tmdb_id
                data.append(ExtendedMap('person', item_id, False, person_item))

                ArtMapperMethods.set_default_art(data, i, parent_id=item_id)

        return data

    def get_person_movie_credits_data(self, items):
        return self.get_person_credits_data(items, 'movie')

    def get_person_tv_credits_data(self, items):
        return self.get_person_credits_data(items, 'tv')

    def get_person_credits_data(self, items, tmdb_type='movie'):
        data = []

        mappings = (
            ('cast', 'castmember', {'ordering': 'order', 'role': 'character', 'appearances': 'episode_count'}),
            ('crew', 'crewmember', {'department': 'department', 'role': 'job', 'appearances': 'episode_count'}),
        )

        for subkey, mapkey, config in mappings:
            credits = items.get(subkey) or []
            for i in credits:
                data.extend(self.get_media_item_data(i, tmdb_type))

                credit_item = GeneralMapperMethods.get_configured_item(i, **config)
                credit_item['parent_id'] = f'{tmdb_type}.{i["id"]}'
                credit_item['tmdb_id'] = self.tmdb_id
                data.append(ExtendedMap(mapkey, i.get('credit_id'), False, credit_item))

        return data
