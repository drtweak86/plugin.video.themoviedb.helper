class SyncDataParentProperties:
    @property
    def cache(self):
        return self.instance_syncdata.cache

    @property
    def window(self):
        return self.instance_syncdata.window

    @property
    def anilist_api(self):
        return self.instance_syncdata.anilist_api
