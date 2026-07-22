from tmdbhelper.lib.items.database.mappings.support import ExtendedMap, get_blanks_none


class GeneralMapperMethods:
    @staticmethod
    def get_runtime(i, *args, **kwargs):
        if isinstance(i, list):
            i = i[0]
        try:
            return int(i) * 60
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def get_configured_item(i, blanks=True, **kwargs):

        def get_item(i, v):
            try:
                if not callable(v):
                    return i.get(v)
                return v(i)
            except (TypeError, KeyError, IndexError, ValueError):
                return

        configured_items = {k: get_blanks_none(get_item(i, v)) for k, v in kwargs.items()}
        return configured_items if blanks else {k: v for k, v in configured_items.items() if k and v}

    @staticmethod
    def split_array(items, subkeys=(), haskeys=(), **kwargs):
        if not items:
            return []

        for subkey in subkeys:
            try:
                items = items[subkey]
            except (TypeError, KeyError):
                return []

        if not isinstance(items, list):
            return []

        def check_item(i):
            for k in haskeys:
                try:
                    if not i[k]:
                        return
                except (TypeError, KeyError, IndexError, ValueError):
                    return
            return i

        items = [i for i in items if check_item(i)] if haskeys else items
        return [GeneralMapperMethods.get_configured_item(i, **kwargs) for i in items]

    @staticmethod
    def get_custom_time(duration, name='duration'):
        if not duration:
            return {}
        minutes = duration // 60 % 60
        hours = duration // 60 // 60
        totalmin = duration // 60
        infoproperties = {
            f'{name}.H': hours,
            f'{name}.M': minutes,
            f'{name}.mins': totalmin,
            f'{name}.HHMM': f'{hours:02d}:{minutes:02d}',
        }
        return infoproperties

    @staticmethod
    def get_custom_date(air_date, name):
        # NOTE: this method has a real, traced dependency on Kodi's region/locale
        # formatting (tmdbhelper.lib.addon.tmdate.get_region_date calls a Kodi API
        # that must return a real locale string) and cannot be unit-tested outside
        # a running Kodi instance - confirmed by stubbing xbmc/xbmcaddon/xbmcgui/
        # xbmcplugin/xbmcvfs as MagicMock() and still hitting a failure inside
        # strftime(). This is unchanged, pre-existing behavior from before the
        # mappings.py split, not a new gap. See tests/test_mappings_general.py for
        # what IS covered.
        from tmdbhelper.lib.addon.plugin import get_infolabel
        from tmdbhelper.lib.addon.tmdate import format_date_obj, convert_timestamp, get_days_to_air
        air_date_obj = convert_timestamp(air_date, time_fmt="%Y-%m-%d", time_lim=10, utc_convert=False)

        if not air_date_obj:
            return {}

        infoproperties = {
            f'{name}': format_date_obj(air_date_obj, region_fmt='dateshort'),
            f'{name}.long': format_date_obj(air_date_obj, region_fmt='datelong'),
            f'{name}.short': format_date_obj(air_date_obj, "%d %b"),
            f'{name}.day': format_date_obj(air_date_obj, "%A"),
            f'{name}.day_short': format_date_obj(air_date_obj, "%a"),
            f'{name}.year': format_date_obj(air_date_obj, "%Y"),
            f'{name}.custom': format_date_obj(air_date_obj, get_infolabel('Skin.String(TMDbHelper.Date.Format)') or '%d %b %Y'),
            f'{name}.original': air_date,
        }

        days_to_air, is_aired = get_days_to_air(air_date_obj)
        days_to_air_name = f'{name}.days_from_aired' if is_aired else f'{name}.days_until_aired'

        infoproperties[days_to_air_name] = str(days_to_air)
        return infoproperties

    @staticmethod
    def get_custom_property(key, value):
        return [ExtendedMap('custom', key, False, {'key': key, 'value': value})]

    @staticmethod
    def get_unique_ids(results, **kwargs):
        if not results:
            return
        return [
            {
                'key': get_blanks_none(('tmdb_id' if k == 'id' else k).replace('_id', '')),
                'value': get_blanks_none(f'{v}')
            }
            for k, v in results.items()
        ]

    @staticmethod
    def get_video(items, **kwargs):
        if not items:
            return
        results = items.get('results')
        if not results:
            return
        data = []
        for video in results:
            if video['site'] != 'YouTube':
                continue
            data.append({
                'name': get_blanks_none(video['name']),
                'iso_country': get_blanks_none(video['iso_3166_1']),
                'iso_language': get_blanks_none(video['iso_639_1']),
                'release_date': get_blanks_none(video['published_at']),
                'key': get_blanks_none(video['key']),
                'content': get_blanks_none(video['type']),
                'path': f"plugin://plugin.video.youtube/play/?video_id={video['key']}",
            })
        return data

    def get_media_item_data(self, i, tmdb_type, **additional_params):
        data = []

        item_id = f'{tmdb_type}.{i["id"]}'

        mediatype = 'movie' if tmdb_type == 'movie' else 'tvshow'
        premiered = 'release_date' if mediatype == 'movie' else 'first_air_date'
        titlename = 'title' if mediatype == 'movie' else 'name'

        media_item = GeneralMapperMethods.get_configured_item(i, **{
            'year': lambda i: int(i[premiered][0:4]),
            'premiered': premiered,
            'plot': 'overview',
            'title': titlename,
            'originaltitle': 'original_title',
            'rating': 'vote_average',
            'votes': 'vote_count',
            'popularity': 'popularity'

        })
        media_item['id'] = item_id
        media_item['tmdb_id'] = i['id']
        media_item.update(additional_params)
        data.append(ExtendedMap(mediatype, item_id, False, media_item))

        data.append(ExtendedMap('baseitem', item_id, False, {
            'id': item_id,
            'mediatype': mediatype,
            'expiry': 0,
            'language': self.language,
        }))

        for genre in self.get_genre_items(i.get('genre_ids') or []):
            genre = GeneralMapperMethods.get_configured_item(genre, name='name', tmdb_id='tmdb_id')
            genre['parent_id'] = item_id
            data.append(ExtendedMap('genre', f"{item_id}.genre.{genre['tmdb_id']}", True, genre))

        from tmdbhelper.lib.items.database.mappings.art import ArtMapperMethods
        ArtMapperMethods.set_default_art(data, i, parent_id=item_id)

        return data
