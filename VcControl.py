import discord
import asyncio
from options import ffmpeg_error_log
from Views import Views, ViewUpdateType
from DJBannedException import DJBannedException
from YTDLException import YTDLException
import time

class VcControl():
    def __init__(self, mChannel, djo, vc) -> None:
        self.mChannel = mChannel # message channel
        self.nowPlaying = None
        self.dj = None # dj type: string?
        self.djObj = djo
        self.vc = vc # voice client
        self.skip_author = None

        self.ffmpeg_error = None

        # active display messages
        self.playlist = [] # [(source, m), (source, m) ....]
        self.views = Views(mChannel, vc, self)

    # ------------------------- SETTER / UPDATER ------------------------- # 
    # (delete all updatable message when ending sessions)
    async def set_dj_type(self, type, update = ViewUpdateType.EDIT):
        self.dj = type
        # set bot status
        await self.djObj.bot_status(self.dj)

        # update views
        if self.vc.is_playing():
            await self.views.update_playing(update = update)
        else:
            await self.next()
        # update other views (list)
        await self.views.update_list()

    def set_stream_error(self, ffmpeg_err = None, skip_author = "Streaming error"):
        self.ffmpeg_error = ffmpeg_err
        self.skip_author = skip_author


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
                self.views.switch_djable_button(vc, source.vid)
            ]]
        )
        self.playlist.append( (source, m) ) 
        if not vc.is_playing(): 
            await self.next()

    ###  Main playing function  ###
    async def next(self):
        vc = self.vc
        def after_handler(e, set_error):
            # read ffmpeg error
            ffmpeg_err_m = None
            with open(ffmpeg_error_log, "r") as f:
                # get to last line
                for line in f.readlines():
                    pass
            
                # check for possible error
                if "403 Forbidden" in line[-50:]:
                    ffmpeg_err_m = "Access denied"
                elif "Broken pipe" in line[-50:]:
                    ffmpeg_err_m = "Disrupted"

            if ffmpeg_err_m:
                print(f"ffmpeg error: {line}")
                set_error(f"Error in streaming ({ffmpeg_err_m})", ffmpeg_err_m)
            
            # read standard playing error
            if e: 
                print("Error occured in playing")
                raise e
            print("song ended w/o error")

        # prevent replay
        if vc.is_playing(): 
            raise Exception("Already playing songs")

        # queue loop
        while len(self.playlist) > 0 or self.dj:
            # activate dj when no song in queue
            if self.dj and len(self.playlist) <= 0: 
                # query a random vid and compile source
                vid = self.djObj.djdb.find_rand_song()
                
                # must catch exception here, otherwise the play loop will end when yt error occur
                try: source = await self.djObj.compile_yt_source(vid)
                # youtube download/extract error and banned song exception
                except (YTDLException, DJBannedException) as e: 
                    await self.mChannel.send(e.message)
                    self.djObj.djdb.remove_song(vid)
                    continue
                dj_source = True
            else:
                # get the song from the first of the queue
                source, q_message = self.playlist.pop(0)
                # delete the corresponding queuing message
                await q_message.delete()
                dj_source = False

            vid = source.vid
            self.nowPlaying = source
            # actual play
            start = time.time() # start timer for duration
            vc.play(source, after = lambda e: after_handler(e, self.set_stream_error) )
            
            # show playing views for controls
            await self.views.show_playing(dj_source, source)

            # wait until the current track ends
            while vc.is_playing(): 
                await asyncio.sleep(1)

            # end timer and add/update duration
            end = time.time()
            if self.skip_author is None: 
                self.djObj.djdb.update_duration(vid, end - start)

            # ending the playing view and reset skip author
            await self.views.end_playing(source, self.skip_author)
            # reset skip author and ffmpeg error
            self.skip_author = None
            self.ffmpeg_error = None

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
            self.dj = None
            await self.clear(silent = True)
            self.skip_author = "Leaving"
            self.vc.stop()
           
    def insert(self, source):
        pass


    # -------------------- DISCONNECT ------------------- # 
    async def disconnectVC(self):
        # also manage all messages?
        await self.vc.disconnect()