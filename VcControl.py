import discord
import asyncio
from Views import Views, ViewUpdateType
import time

class VcControl():
    def __init__(self, mChannel, vc) -> None:
        self.mChannel = mChannel # message channel
        self.nowPlaying = None
        self.vc = vc # voice client
        self.skip_author = None

        # active display messages
        self.playlist = [] # [(source, m), (source, m) ....]
        self.views = Views(mChannel, vc, self)


    # ---------------------------- MESSAGING --------------------------- # 
    async def notify(self, message, del_sec = 10):
        m = await self.mChannel.send(message)

        # delete the message if needed
        if del_sec: 
            assert type(del_sec) == int
            await m.delete(delay = del_sec)

    # ---------------------------- CONTROLS --------------------------- # 
    async def add(self, vc: discord.VoiceClient = None, source = None):
        print(source.title, source.vid, source.url)
        m = await self.mChannel.send(
            "Queued: " + source.title,
            components=[[
                self.views.remove_button(vc, source.vid, label = "Remove"),
            ]]
        )
        self.playlist.append( (source, m) ) 
        if not vc.is_playing(): 
            await self.next()

    ###  Main playing function  ###
    async def next(self):
        vc = self.vc
        def after_handler(e):
            if e: 
                print("Error occured in streaming")
                raise e
            print("song ended w/o error")

        # prevent replay
        if vc.is_playing(): 
            raise Exception("Already playing songs")

        # queue loop
        while len(self.playlist) > 0:
            # get the song from the first of the queue
            source, q_message = self.playlist.pop(0)
            # delete the corresponding queuing message
            await q_message.delete()

            vid = source.vid
            self.nowPlaying = source
            # actual play
            vc.play(source, after = after_handler )
            
            # show playing views for controls
            await self.views.show_playing(source)

            # wait until the current track ends
            while vc.is_playing(): 
                await asyncio.sleep(1)

            # ending the playing view and reset skip author
            await self.views.end_playing(source, self.skip_author)
            self.skip_author = None

        # end of playlist
        return 
                

    # skip current song
    async def skip(self, vc: discord.VoiceClient, author):
        if not vc: raise Exception("I am not in any voice channel")

        if vc.is_playing(): 
            self.skip_author = author
            vc.stop()
 
    # remove song from playlist
    async def remove_track(self, vc, key, author, silent = False, exact = False, vid = False):
        if vid: exact = True
        def match(k, source):
            # url or title
            target = (source.vid if vid else source.title).lower()
            k = k.lower()
            if exact: return k == target
            else: return k in target

        if match(key, self.nowPlaying):
            await self.skip(vc, author)
            # if not silent: await self.notify("Removed: " + self.nowPlaying.title)
            return self.nowPlaying.url

        for i, (s, m) in enumerate(self.playlist): 
            if match(key, s):
                # delete playlist entry and the queue message
                await m.delete()
                del self.playlist[i]

                if not silent: await self.notify(f"Removed by {author}: {s.title}")
                return s.url

        if not silent: await self.notify("No matching result for: " + key)
        return None
 

    # display nowplaying 
    async def display_nowplaying(self):
        if not self.vc: raise Exception("I am not in any voice channel")
        if not self.vc.is_playing(): raise Exception("No song playing")
        # add play a random song?

        await self.views.update_playing(ViewUpdateType.REPOST)


    # list playlist
    async def list(self, ctx):
        await self.views.show_list()
        
    # clear playlist
    async def clear(self, silent = False):
        self.playlist = []
        if not silent: await self.mChannel.send("Playlist cleared")

    # stop and clear playlist
    async def stop(self):
        if not self.vc: raise Exception("I am not in any voice channel")

        if self.vc.is_playing():
            await self.clear(silent = True)
            self.skip_author = "Leaving"
            self.vc.stop()
           
    def insert(self, source):
        pass


    # -------------------- DISCONNECT ------------------- # 
    async def disconnectVC(self):
        # also manage all messages?
        await self.vc.disconnect()