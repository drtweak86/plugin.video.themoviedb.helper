from tmdbhelper.lib.items.database.mappings.support import get_blanks_none


class TranslationMapperMethods:
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
