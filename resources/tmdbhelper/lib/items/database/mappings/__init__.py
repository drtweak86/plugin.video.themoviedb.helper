#!/usr/bin/python
# -*- coding: utf-8 -*-
from tmdbhelper.lib.api.mapping import _ItemMapper
from tmdbhelper.lib.items.database.mappings.support import ExtendedMap, get_blanks_none


class ItemMapperMethods:
    @staticmethod
    def get_episode_type(i, **kwargs):
        episode_type = i['episode_type']
        season_number = i['season_number']
        episode_number = i['episode_number']
        if season_number == 0:
            return 'special'
        if episode_number == 1:
            return 'series_premiere' if season_number == 1 else 'season_premiere'
        if episode_type == 'finale':
            return 'season_finale'  # TODO: Series finale currently calculated as part of last_aired (checks status as cancelled/ended and assumes last_aired episode is finale)
        if episode_type == 'mid_season':
            return 'mid_season_finale'  # TODO: Calculate mid season premiere (might be a real pain to do)
        return 'standard'

    @staticmethod
    def get_providers(items, service=False, **kwargs):
        if not items:
            return
        results = items.get('results')
        if not results:
            return
        data = []
        for iso, availabilities in results.items():
            for availability, datalist in availabilities.items():
                if availability == 'link':
                    continue
                for provider in datalist:
                    if service:
                        item = {
                            'display_priority': get_blanks_none(provider.get('display_priority')),
                            'name': get_blanks_none(provider.get('provider_name')),
                            'logo': get_blanks_none(provider.get('logo_path')),
                            'tmdb_id': get_blanks_none(provider.get('provider_id')),
                        }
                    else:
                        item = {
                            'iso_country': iso,
                            'availability': get_blanks_none(availability),
                            'tmdb_id': get_blanks_none(provider.get('provider_id')),
                        }
                    data.append(item)
        return data

    @staticmethod
    def get_translations(items, **kwargs):
        if not items:
            return
        results = items.get('translations')
        if not results:
            return
        data = [
            {
                'iso_country': get_blanks_none(translation['iso_3166_1']),
                'iso_language': get_blanks_none(translation['iso_639_1']),
                'title': get_blanks_none(translation['data'].get('title') or translation['data'].get('name')),
                'plot': get_blanks_none(translation['data'].get('overview')),
                'tagline': get_blanks_none(translation['data'].get('tagline')),
            } for translation in results
        ]
        return data

    @staticmethod
    def get_certifications(items, **kwargs):
        if not items:
            return
        results = items.get('results')
        if not results:
            return
        data = []
        tmdb_release_types = {1: 'Premiere', 2: 'Limited', 3: 'Theatrical', 4: 'Digital', 5: 'Physical', 6: 'TV'}
        for release_country in results:
            iso_country = release_country['iso_3166_1']
            for release in (release_country.get('release_dates') or ()):
                data.append({
                    'name': get_blanks_none(release['certification']),
                    'iso_country': get_blanks_none(iso_country),
                    'iso_language': get_blanks_none(release['iso_639_1']),
                    'release_date': get_blanks_none(release['release_date']),
                    'release_type': get_blanks_none(tmdb_release_types.get(release['type'])),
                })
        return data

    def get_belongs_to_collection(self, i, **kwargs):
        data = []

        item_id = f"movie.{self.tmdb_id}"
        collection_id = f"collection.{i['id']}"

        collection_item = ItemMapperMethods.get_configured_item(i, **{
            'tmdb_id': 'id',
            'title': 'name',
        })
        collection_item['id'] = collection_id
        data.append(ExtendedMap('collection', collection_id, False, collection_item))

        ItemMapperMethods.set_default_art(data, i, parent_id=item_id)

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

    def get_creators(self, items, **kwargs):
        data = []

        for i in items:
            item_id = f'person.{i["id"]}'
            tmdb_id = i['id']

            data.append(ExtendedMap('crewmember', item_id, False, {
                'tmdb_id': tmdb_id,
                'role': 'Creator',
                'department': 'Creator',
            }))

            person_item = ItemMapperMethods.get_configured_item(i, **{
                'name': 'name',
                'gender': 'gender',
            })
            person_item['id'] = item_id
            person_item['tmdb_id'] = tmdb_id
            data.append(ExtendedMap('person', item_id, False, person_item))

            ItemMapperMethods.set_default_art(data, i, parent_id=item_id)

            data.append(ExtendedMap('baseitem', item_id, False, {
                'id': item_id,
                'mediatype': 'person',
                'expiry': 0,
                'language': self.language,
            }))

        return data

    def get_episode_to_air(self, i, **kwargs):
        data = []

        item_id = f'tv.{self.tmdb_id}.{i["season_number"]}.{i["episode_number"]}'
        season_id = f'tv.{self.tmdb_id}.{i["season_number"]}'
        tvshow_id = f'tv.{self.tmdb_id}'

        episode_item = ItemMapperMethods.get_configured_item(i, **{
            'episode': 'episode_number',
            'premiered': 'air_date',
            'title': 'name',
            'plot': 'overview',
            'rating': 'vote_average',
            'votes': 'vote_count',
            'status': lambda i: self.get_episode_type(i),
            'duration': lambda i: self.get_runtime(i['runtime'])
        })
        episode_item['id'] = item_id
        episode_item['season_id'] = season_id
        episode_item['tvshow_id'] = tvshow_id

        if not self.data.get('in_production') and not self.data.get('next_episode_to_air'):
            episode_item['status'] = 'series_finale'

        data.append(ExtendedMap('episode', item_id, False, episode_item))

        data.append(ExtendedMap('season', season_id, False, {
            'id': season_id,
            'tvshow_id': tvshow_id,
            'season': i['season_number'],
        }))

        data.append(ExtendedMap('baseitem', item_id, False, {
            'id': item_id,
            'mediatype': 'episode',
            'expiry': 0,
            'language': self.language,
        }))

        data.append(ExtendedMap('baseitem', season_id, False, {
            'id': season_id,
            'mediatype': 'season',
            'expiry': 0,
            'language': self.language,
        }))

        if i.get('still_path'):
            artwork = ItemMapperMethods.add_art_type(
                item_id=item_id,
                image_path=i['still_path'],
                image_type='stills',
                ratio_type='landscape')
            data.append(ExtendedMap('art', artwork['icon'], False, artwork))

        # Use last/next aired duration if available for tvshow duration
        if episode_item.get('duration') and not self.item['item'].get('duration'):
            self.item['item']['duration'] = episode_item['duration']

        return data

    def get_episodes(self, items, **kwargs):
        data = []

        for i in items:
            item_id = f'tv.{self.tmdb_id}.{i["season_number"]}.{i["episode_number"]}'
            season_id = f'tv.{self.tmdb_id}.{i["season_number"]}'
            tvshow_id = f'tv.{self.tmdb_id}'

            episode_item = ItemMapperMethods.get_configured_item(i, **{
                'episode': 'episode_number',
                'year': lambda i: int(i['air_date'][0:4]),
                'premiered': 'air_date',
                'title': 'name',
                'plot': 'overview',
                'rating': 'vote_average',
                'votes': 'vote_count',
                'status': lambda i: self.get_episode_type(i),
                'duration': lambda i: self.get_runtime(i['runtime'])
            })
            episode_item['id'] = item_id
            episode_item['season_id'] = season_id
            episode_item['tvshow_id'] = tvshow_id

            data.append(ExtendedMap('episode', item_id, True, episode_item))

            if i.get('still_path'):
                artwork = ItemMapperMethods.add_art_type(
                    item_id=item_id,
                    image_path=i['still_path'],
                    image_type='stills',
                    ratio_type='landscape')
                data.append(ExtendedMap('art', artwork['icon'], False, artwork))

            data.append(ExtendedMap('baseitem', item_id, False, {
                'id': item_id,
                'mediatype': 'episode',
                'expiry': 0,
                'language': self.language,
            }))

        return data

    def get_seasons(self, items, **kwargs):
        data = []

        for i in items:
            item_id = f'tv.{self.tmdb_id}.{i["season_number"]}'
            tvshow_id = f'tv.{self.tmdb_id}'

            season_item = ItemMapperMethods.get_configured_item(i, **{
                'season': 'season_number',
                'year': lambda i: int(i['air_date'][0:4]),
                'premiered': 'air_date',
                'title': 'name',
                'plot': 'overview',
                'rating': 'vote_average',
            })
            season_item['id'] = item_id
            season_item['tvshow_id'] = tvshow_id

            data.append(ExtendedMap('season', item_id, True, season_item))

            ItemMapperMethods.set_default_art(data, i, parent_id=item_id)

            data.append(ExtendedMap('baseitem', item_id, False, {
                'id': item_id,
                'mediatype': 'season',
                'expiry': 0,
                'language': self.language
            }))

        return data


class BlankNoneDict(dict):
    def __missing__(self, key):
        return None


class ItemMapper(_ItemMapper, ItemMapperMethods):
    def __init__(self, language, tmdb_id):
        self.blacklist = ()
        """ Mapping dictionary
        keys:       list of tuples containing parent and child key to add value. [('parent', 'child')]
                    parent keys: art, unique_ids, infolabels, infoproperties, params
                    use UPDATE_BASEKEY for child key to update parent with a dict
        func:       function to call to manipulate values (omit to skip and pass value directly)
        (kw)args:   list/dict of args/kwargs to pass to func.
                    func is also always passed v as first argument
        type:       int, float, str - convert v to type using try_type(v, type)
        extend:     set True to add to existing list - leave blank to overwrite exiting list
        subkeys:    list of sub keys to get for v - i.e. v.get(subkeys[0], {}).get(subkeys[1]) etc.
                    note that getting subkeys sticks for entire loop so do other ops on base first if needed

        use standard_map for direct one-to-one mapping of v onto single property tuple
        """
        self.advanced_map = {
            'name': [{
                'keys': [('item', 'title')]}, {
                'keys': [('item', 'name')],
            }],
            'release_date': [{
                'keys': [('item', 'premiered')]}, {
                'keys': [('item', 'year')],
                'func': lambda v: int(v[0:4])
            }],
            'first_air_date': [{
                'keys': [('item', 'premiered')]}, {
                'keys': [('item', 'year')],
                'func': lambda v: int(v[0:4])
            }],
            'air_date': [{
                'keys': [('item', 'premiered')]}, {
                'keys': [('item', 'year')],
                'func': lambda v: int(v[0:4])
            }],
            'episode_run_time': [{
                'keys': [('item', 'duration')],
                'func': self.get_runtime
            }],
            'runtime': [{
                'keys': [('item', 'duration')],
                'func': self.get_runtime
            }],
            'genres': [{
                'keys': [('genre', None)],
                'func': self.get_genres
            }],
            'content_ratings': [{
                'keys': [('certification', None)],
                'func': self.split_array,
                'kwargs': {
                    'subkeys': ('results', ),
                    'name': 'rating', 'iso_country': 'iso_3166_1'}
            }],
            'release_dates': [{
                'keys': [('certification', None)],
                'func': self.get_certifications,
            }],
            'translations': [{
                'keys': [('translation', None)],
                'func': self.get_translations,
            }],
            'spoken_languages': [{
                'keys': [('language', None)],
                'func': self.split_array,
                'kwargs': {'iso_language': 'iso_639_1'}}, {
                # ---
                'keys': [('languages', None)],
                'func': self.split_array,
                'kwargs': {'iso_language': 'iso_639_1', 'name': 'name', 'english_name': 'english_name'}
            }],
            'production_countries': [{
                'keys': [('country', None)],
                'func': self.split_array,
                'kwargs': {'iso_country': 'iso_3166_1'}}, {
                # ---
                'keys': [('countries', None)],
                'func': self.split_array,
                'kwargs': {'iso_country': 'iso_3166_1', 'name': 'name'}
            }],
            'production_companies': [{
                'keys': [('studio', None)],
                'func': self.split_array,
                'kwargs': {'tmdb_id': 'id'}}, {
                # ---
                'keys': [('company', None)],
                'func': self.split_array,
                'kwargs': {'tmdb_id': 'id', 'name': 'name', 'logo': 'logo_path', 'country': 'origin_country'}
            }],
            'networks': [{
                'keys': [('network', None)],
                'func': self.split_array,
                'kwargs': {'tmdb_id': 'id'}}, {
                # ---
                'keys': [('broadcaster', None)],
                'func': self.split_array,
                'kwargs': {'tmdb_id': 'id', 'name': 'name', 'logo': 'logo_path', 'country': 'origin_country'}
            }],
            'watch/providers': [{
                'keys': [('provider', None)],
                'func': self.get_providers}, {
                # ---
                'keys': [('service', None)],
                'func': self.get_providers,
                'kwargs': {'service': True}
            }],
            'external_ids': [{
                'keys': [('unique_id', None)],
                'func': self.get_unique_ids,
            }],
            'videos': [{
                'keys': [('video', None)],
                'func': self.get_video,
            }],
            'last_episode_to_air': [{
                'keys': [('item', f'last_episode_to_air_id')],
                'func': lambda i: f'tv.{self.tmdb_id}.{i["season_number"]}.{i["episode_number"]}'
            }],
            'next_episode_to_air': [{
                'keys': [('item', f'next_episode_to_air_id')],
                'func': lambda i: f'tv.{self.tmdb_id}.{i["season_number"]}.{i["episode_number"]}'
            }],
        }

        self.extended_map = {
            'budget': lambda v: self.get_custom_property('budget', f'${float(v):0,.0f}'),
            'revenue': lambda v: self.get_custom_property('revenue', f'${float(v):0,.0f}'),
            'original_language': lambda v: self.get_custom_property('original_language', v),
            'homepage': lambda v: self.get_custom_property('homepage', v),
            'poster_path': lambda v: self.get_default_art(v, 'posters'),
            'backdrop_path': lambda v: self.get_default_art(v, 'backdrops'),
            'profile_path': lambda v: self.get_default_art(v, 'profiles'),
            'images': self.get_art,
            'fanart_tv': self.get_fanart_tv,
            'belongs_to_collection': self.get_belongs_to_collection,
            'collection': self.get_collection,
            'parts': self.get_parts,
            'seasons': self.get_seasons,
            'episodes': self.get_episodes,
            'created_by': self.get_creators,
            'credits': self.get_credits,
            'aggregate_credits': self.get_aggregate_credits,
            'last_episode_to_air': self.get_episode_to_air,  # Also mapped in advanced properties for item id
            'next_episode_to_air': self.get_episode_to_air,  # Also mapped in advanced properties for item id
            'movie_credits': self.get_person_movie_credits_data,
            'tv_credits': self.get_person_tv_credits_data,
        }

        self.standard_map = {
            'id': ('item', 'tmdb_id'),
            'title': ('item', 'title'),
            'tagline': ('item', 'tagline'),
            'overview': ('item', 'plot'),
            'original_title': ('item', 'originaltitle'),
            'original_name': ('item', 'originaltitle'),
            'status': ('item', 'status'),
            'season_number': ('item', 'season'),
            'episode_number': ('item', 'episode'),
            'number_of_seasons': ('item', 'totalseasons'),
            'number_of_episodes': ('item', 'totalepisodes'),
            'biography': ('item', 'biography'),
            'birthday': ('item', 'birthday'),
            'deathday': ('item', 'deathday'),
            'gender': ('item', 'gender'),
            'known_for_department': ('item', 'known_for_department'),
            'place_of_birth': ('item', 'place_of_birth'),
            'vote_average': ('item', 'rating'),
            'vote_count': ('item', 'votes'),
            'popularity': ('item', 'popularity')
        }

        self.language = language
        self.tmdb_id = tmdb_id

    def map_dict(self, item, data):

        map_dict = {}

        for k, v in data.items():

            # Skip blank values
            if v in (None, ''):
                continue

            # Only some values need extended mappings
            if k not in self.extended_map:
                continue

            # Make sure the function outputs data
            output = self.extended_map[k](v)
            if not output:
                continue

            for i in output:

                # Make sure unique_id has a value we can use as an ID
                if not i.unique_id:
                    continue

                dictionary = map_dict.setdefault(i.base, {})

                # Overwrite set so just overwrite and move on
                if i.overwrite:
                    dictionary[i.unique_id] = i.data
                    continue

                # ID not mapped yet so write it and move on
                if i.unique_id not in dictionary:
                    dictionary[i.unique_id] = i.data
                    continue

                # Only write new values
                for ik, iv in i.data.items():
                    if not dictionary[i.unique_id].get(ik):  # Dont write over existing values
                        continue
                    dictionary[i.unique_id][ik] = iv  # No value set so update it

        for key, dictionary in map_dict.items():
            item[key] = tuple([d for d in dictionary.values()])

        return item

    @staticmethod
    def get_empty_item():
        return {

            # Default mappings
            'item': BlankNoneDict(),
            'genre': (),
            'languages': (),
            'language': (),
            'countries': (),
            'country': (),
            'company': (),
            'studio': (),
            'broadcaster': (),
            'network': (),
            'provider': (),
            'certification': (),
            'service': (),
            'video': (),
            'unique_id': (),
            'translation': (),

            # Dictionary mappings
            'custom': (),
            'art': (),
            'default_art': (),
            'baseitem': (),
            'fanart_tv': (),
            'collection': (),
            'movie': (),
            'tvshow': (),
            'season': (),
            'episode': (),
            'person': (),
            'crewmember': (),
            'castmember': (),
            'belongs': (),
        }

    def get_info(self, data, **kwargs):
        self.data = data
        self.item = self.get_empty_item()
        self.item = self.map_item(self.item, data)
        self.item = self.map_dict(self.item, data)

        # from tmdbhelper.lib.files.futils import dumps_to_file
        # dumps_to_file(
        #     {'data': self.data, 'item': self.item},
        #     'log_data', f'mappings_{self.tmdb_id}.json', join_addon_data=True)

        return self.item
