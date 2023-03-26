import discord
from const.options import default_init_vol

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=default_init_vol):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

# voice source object playing from local directory
class StaticSource(discord.PCMVolumeTransformer):
    def __init__(self, source, volume=default_init_vol, title="No title"):
        super().__init__(source, volume)
        self.title = title