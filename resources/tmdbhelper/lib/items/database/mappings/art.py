from tmdbhelper.lib.items.database.mappings.support import (
    ExtendedMap, get_blanks_none, FTV_WITHOUT_SEASONS, FTV_TVSHOWS_SEASONS, FTV_SEASONS_SEASONS,
)


class ArtMapperMethods:
    @staticmethod
    def add_art_type(item_id, image_path, image_type, ratio_type):
        from tmdbhelper.lib.addon.consts import IMAGEPATH_ASPECTRATIO
        return {
            'parent_id': item_id,
            'aspect_ratio': IMAGEPATH_ASPECTRATIO.index(ratio_type),
            'icon': get_blanks_none(image_path),
            'type': image_type,
            'extension': get_blanks_none(image_path.split('.')[-1] if image_path else None),
        }

    def get_fanart_tv(self, items, **kwargs):
        if not items:
            return

        # FTV artwork key name, type to map it to, art_has_seasons
        # Set art_has_seasons to FTV_TVSHOWS_SEASONS for artwork where fanarttv intends "season=all" to be "tvshow" artwork
        # Set art_has_seasons to FTV_SEASONS_SEASONS for artwork where fanarttv intends "season=all" to be "season" artwork
        art_types = {
            'movieposter': ('poster', FTV_WITHOUT_SEASONS),
            'moviebackground': ('fanart', FTV_WITHOUT_SEASONS),
            'moviethumb': ('landscape', FTV_WITHOUT_SEASONS),
            'moviebanner': ('banner', FTV_WITHOUT_SEASONS),
            'hdmovieclearart': ('clearart', FTV_WITHOUT_SEASONS),
            'movieclearart': ('clearart', FTV_WITHOUT_SEASONS),
            'hdmovielogo': ('clearlogo', FTV_WITHOUT_SEASONS),
            'movielogo': ('clearlogo', FTV_WITHOUT_SEASONS),
            'moviedisc': ('discart', FTV_WITHOUT_SEASONS),
            'tvposter': ('poster', FTV_WITHOUT_SEASONS),
            'tvthumb': ('landscape', FTV_WITHOUT_SEASONS),
            'tvbanner': ('banner', FTV_WITHOUT_SEASONS),
            'hdclearart': ('clearart', FTV_WITHOUT_SEASONS),
            'clearart': ('clearart', FTV_WITHOUT_SEASONS),
            'hdtvlogo': ('clearlogo', FTV_WITHOUT_SEASONS),
            'clearlogo': ('clearlogo', FTV_WITHOUT_SEASONS),
            'characterart': ('characterart', FTV_WITHOUT_SEASONS),
            'showbackground': ('fanart', FTV_TVSHOWS_SEASONS),
            'seasonposter': ('poster', FTV_SEASONS_SEASONS),
            'seasonbanner': ('banner', FTV_SEASONS_SEASONS),
            'seasonthumb': ('landscape', FTV_SEASONS_SEASONS),
        }

        data = []
        for art_type, art_list in items.items():

            if not isinstance(art_list, list):
                continue

            quality = 1 if art_type.startswith('hd') else 0

            art_type = art_types.get(art_type)
            if not art_type:
                continue

            art_type, art_has_seasons = art_type

            for art_item in art_list:
                icon = get_blanks_none(art_item['url'])

                if not icon:
                    continue

                item = {
                    'icon': icon,
                    'iso_language': get_blanks_none(art_item.get('lang')),
                    'likes': get_blanks_none(art_item.get('likes')),
                    'type': get_blanks_none(art_type),
                    'quality': get_blanks_none(quality),
                    'extension': get_blanks_none(icon.split('.')[-1] if icon else None),
                }

                if art_has_seasons:
                    # Some artwork on FanartTV uses season=all to indicate tvshow artwork
                    # While other artwork types use season=all to indicate season artwork for an "all" season...
                    # Do some gymnastics here to workaround this mess of conflated types
                    snum = (art_item.get('season') or 'all')

                    # Set "All Seasons" artwork to -1 season so we dont pull it in for a tvshow if it is really intended to be an "all" season type
                    if snum == 'all' and art_has_seasons == FTV_SEASONS_SEASONS:
                        snum = -1

                    # Set season artwork with a number ot season type
                    if snum != 'all':
                        parent_id = f'tv.{self.tmdb_id}.{snum}'

                        item['parent_id'] = parent_id

                        data.append(ExtendedMap('baseitem', parent_id, False, {
                            'id': parent_id,
                            'mediatype': 'season',
                            'expiry': 0,
                            'language': self.language,
                        }))

                data.append(ExtendedMap('fanart_tv', icon, True, item))

        return data

    @staticmethod
    def get_aspect_ratio(aspect_ratio):
        from tmdbhelper.lib.addon.consts import IMAGEPATH_ASPECTRATIO
        if aspect_ratio < 1:
            return IMAGEPATH_ASPECTRATIO.index('poster')
        if aspect_ratio == 1:
            return IMAGEPATH_ASPECTRATIO.index('square')
        if 1.7 <= aspect_ratio <= 1.8:
            return IMAGEPATH_ASPECTRATIO.index('landscape')
        if aspect_ratio < 1.7:
            return IMAGEPATH_ASPECTRATIO.index('thumb')
        if aspect_ratio > 1.8:
            return IMAGEPATH_ASPECTRATIO.index('wide')
        return IMAGEPATH_ASPECTRATIO.index('other')

    @staticmethod
    def get_art(items, **kwargs):
        if not items:
            return []

        data = []

        for artwork_type, artworks in items.items():
            for artwork in artworks:
                path = artwork['file_path']
                data.append(
                    ExtendedMap('art', get_blanks_none(path), True, {
                        'aspect_ratio': ArtMapperMethods.get_aspect_ratio(artwork['aspect_ratio']),
                        'quality': int((artwork['width'] * artwork['height']) // 200000),  # Quality integer to nearest fifth of a megapixel
                        'iso_language': get_blanks_none(artwork['iso_639_1']),
                        'iso_country': get_blanks_none(artwork['iso_3166_1']),
                        'icon': get_blanks_none(path),
                        'type': get_blanks_none(artwork_type),
                        'extension': get_blanks_none(path.split('.')[-1] if path else None),
                        'rating': int(artwork['vote_average'] * 100),
                        'votes': get_blanks_none(artwork['vote_count'])
                    })
                )

        return data

    @staticmethod
    def set_default_art(data, item, parent_id=None):
        for path, art_type in (
            ('poster_path', 'posters',),
            ('backdrop_path', 'backdrops',),
            ('profile_path', 'profiles',),
        ):
            path = item.get(path)
            if not path:
                continue
            data.extend(ArtMapperMethods.get_default_art(path, art_type, parent_id=parent_id))
        return data

    @staticmethod
    def get_default_art(path, art_type, parent_id=None):
        item = {
            'icon': path,
            'type': art_type,
        }
        if parent_id:
            item['parent_id'] = parent_id
        data = [ExtendedMap('default_art', path, False, item)]
        item = item.copy()
        item['extension'] = get_blanks_none(path.split('.')[-1] if path else None)
        data.append(ExtendedMap('art', path, False, item))
        return data
