import discord
import asyncio
from discord_components import Button, ButtonStyle

class VcControl():
    def __init__(self, mChannel) -> None:
        self.playlist = []
        self.mChannel = mChannel # message channel
        self.nowPlaying = None


    async def add(self, vc: discord.VoiceClient = None, source = None):
        self.playlist.append(source)
        print(source.title, source.vid, source.url)
        if not vc.is_playing(): 
            await self.next(vc)
        else:
            await self.mChannel.send(
                "Queued: " + source.title,
                components=[[
                    Button(style=ButtonStyle.red, label="Remove", id="remove_" + source.vid),
                ],]
            )


    async def next(self, vc: discord.VoiceClient):

        def after_handler(e):
            if e: 
                m = "Error occured in streaming"
                print(m + "\n" + e)
                raise Exception(m)
            print("song ended w/o error")

        while len(self.playlist) > 0:
            source = self.playlist.pop(0)
            self.nowPlaying = source
            vc.play(source, after = after_handler )
            
            # send message on text channel with action buttons
            await self.mChannel.send(
                "Playing: " + source.title,
                components=[[
                    Button(style=ButtonStyle.blue, label="Encore", id="repeat_" + source.vid),
                    Button(style=ButtonStyle.red, label="Remove", id="remove_" + source.vid),
                ],]
            )

            # wait until the current track ends
            while vc.is_playing(): 
                await asyncio.sleep(1)
                

    # skip current song
    async def skip(self, vc: discord.VoiceClient):
        if not vc: raise Exception("I am not in any voice channel")

        if vc.is_playing(): 
            vc.stop()
 
    # remove song from playlist
    async def remove_track(self, vc, key, silent = False, exact = False, vid = False):
        if vid: exact = True
        def match(k, source):
            # url or title
            target = (source.vid if vid else source.title).lower()
            k = k.lower()
            if exact: return k == target
            else: return k in target

        if match(key, self.nowPlaying):
            await self.skip(vc)
            if not silent: await self.mChannel.send("Removed: " + self.nowPlaying.title)
            return self.nowPlaying.url

        for i, s in enumerate(self.playlist): 
            if match(key, s):
                del self.playlist[i]
                if not silent: await self.mChannel.send("Removed: " + s.title)
                return s.url

        if not silent: await self.mChannel.send("No matching result for: " + key)
        return None
 

    # display nowplaying 
    async def nowplaying(self, ctx):
        await ctx.send(f"Now playing: {self.nowPlaying.title} \n{self.nowPlaying.url}")

    # list playlist
    async def list(self, ctx):
        m = f"Up Next ({len(self.playlist)}): \n"

        for i, s in enumerate(self.playlist):
            m += f"{s.title} \n"

        await ctx.send(m)

    # clear playlist
    async def clear(self, silent = False):
        self.playlist = []
        if not silent: await self.mChannel.send("Playlist cleared")

    # stop and clear playlist
    async def stop(self, vc: discord.VoiceClient):
        if not vc: raise Exception("I am not in any voice channel")

        if vc.is_playing():
            await self.clear(silent = True)
            vc.stop()
           
    def insert(self, source):
        pass

    def remove(self, name):
        pass