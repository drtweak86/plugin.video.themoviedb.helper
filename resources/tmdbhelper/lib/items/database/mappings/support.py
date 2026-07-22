from collections import namedtuple


ExtendedMap = namedtuple("ExtendedMap", "base unique_id overwrite data")


# Consts for wrangling FTV artwork into shape
FTV_WITHOUT_SEASONS = 0
FTV_TVSHOWS_SEASONS = 1
FTV_SEASONS_SEASONS = 2


def get_blanks_none(i):
    """
    Convert empty strings to nulls
    """
    return i if i or i == 0 else None
