from tmdbhelper.lib.items.database.mappings.support import ExtendedMap
from tmdbhelper.lib.items.database.mappings.general import GeneralMapperMethods
from tmdbhelper.lib.items.database.mappings.art import ArtMapperMethods


class TVMapperMethods:
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

            person_item = GeneralMapperMethods.get_configured_item(i, **{
                'name': 'name',
                'gender': 'gender',
            })
            person_item['id'] = item_id
            person_item['tmdb_id'] = tmdb_id
            data.append(ExtendedMap('person', item_id, False, person_item))

            ArtMapperMethods.set_default_art(data, i, parent_id=item_id)

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

        episode_item = GeneralMapperMethods.get_configured_item(i, **{
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
            artwork = ArtMapperMethods.add_art_type(
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

            episode_item = GeneralMapperMethods.get_configured_item(i, **{
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
                artwork = ArtMapperMethods.add_art_type(
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

            season_item = GeneralMapperMethods.get_configured_item(i, **{
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

            ArtMapperMethods.set_default_art(data, i, parent_id=item_id)

            data.append(ExtendedMap('baseitem', item_id, False, {
                'id': item_id,
                'mediatype': 'season',
                'expiry': 0,
                'language': self.language
            }))

        return data
