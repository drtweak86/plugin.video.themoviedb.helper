#!/usr/bin/python
# -*- coding: utf-8 -*-
from tmdbhelper.lib.api.mapping import _ItemMapper
from tmdbhelper.lib.items.database.mappings.general import GeneralMapperMethods
from tmdbhelper.lib.items.database.mappings.art import ArtMapperMethods
from tmdbhelper.lib.items.database.mappings.genre import GenreMapperMethods
from tmdbhelper.lib.items.database.mappings.credits import CreditsMapperMethods
from tmdbhelper.lib.items.database.mappings.translations import TranslationMapperMethods
from tmdbhelper.lib.items.database.mappings.movie import MovieMapperMethods
from tmdbhelper.lib.items.database.mappings.tv import TVMapperMethods


class ItemMapperMethods(
    GeneralMapperMethods,
    ArtMapperMethods,
    GenreMapperMethods,
    CreditsMapperMethods,
    TranslationMapperMethods,
    MovieMapperMethods,
    TVMapperMethods,
):
    pass


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
