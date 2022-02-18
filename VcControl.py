import discord
import asyncio
from API.tenorAPIget import get_tenor_gif
from options import ffmpeg_error_log, default_init_vol, leaving_gif_search_list
from Views import Views, ViewUpdateType
from DJExceptions import DJBannedException
from YTDLException import YTDLException
from helper import error_log_e, error_log
from DJDynamoDB import DJDB
import time
import random

from API.ytAPIget import yt_search_suggestions

class VcControl():
    def __init__(self, mChannel, djo, vc, guild) -> None:
        self.mChannel = mChannel # message channel
        self.nowPlaying = None
        self.dj = None # dj type: string?
        self.djObj = djo
        self.vc = vc # voice client
        self.voice_client = vc # for passing ctx
        self.skip_author = None

        self.stream_err = None
        self.guild_name = guild.name
        self.guild_id = guild.id

        # active display messages
        self.playlist = [] # [(source, m), (source, m) ....]
        self.views = Views(mChannel, vc, self, self.guild_id)

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

    def set_stream_error(self, stream_err = None, skip_author = "Streaming error"):
        self.stream_err = stream_err
        self.skip_author = skip_author


    # ---------------------------- MESSAGING --------------------------- # 
    async def notify(self, message, del_sec = 10):
        m = await self.mChannel.send(message)

        # delete the message if needed
        if del_sec: 
            assert type(del_sec) == int
            await m.delete(delay = del_sec)

    # ---------------------------- CONTROLS --------------------------- # 
    async def add(self, vc: discord.VoiceClient, source, player, insert = False):
        print(source.title, source.vid, source.url)
        # append source/queue_item to playlist
        queue_message = await self.views.send_queue_message(vc, source)
        if insert:
          self.playlist.insert(0, (source, queue_message, player) ) 
        else:
          self.playlist.append( (source, queue_message, player) ) 
        
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
                message = f"ffmpeg error: {line}"
                error_log(message)
                print(message)
                set_error(f"Error in streaming ({ffmpeg_err_m})", ffmpeg_err_m)
            
            # read standard playing error
            if e: 
                error_log_e(e)
                print(f"Error occured while playing, {e}")
                set_error(f"Error occured while playing", "Error")
            print("song ended w/o error")

        # prevent replay
        if vc.is_playing(): 
            raise Exception("Already playing songs")

        next_dj_source = None
        dj_next_recommend_count = 0
        dj_recommend_delay = 2 # how many songs in between recommended songs
        # queue loop
        while (len(self.playlist) > 0 or self.dj):
            members = vc.channel.members
            # activate dj when no song in queue
            if self.dj and len(self.playlist) <= 0: 
                if next_dj_source:
                    source = next_dj_source
                else:
                    # find the next dj source
                    source = await self.find_next_dj_source()
                # error in youtube searching
                if source is None: continue
                
                is_dj_source = True
                player = "DJ"
            else:
                # get the song from the first of the queue
                (source, queue_message, player) = self.playlist.pop(0)
                # delete the corresponding queuing message
                await queue_message.delete()
                is_dj_source = False

            vid = source.vid
            self.nowPlaying = source
            # actual play
            self.djObj.djdb.add_history(vid, self.guild_id, self.guild_name, str(player))
            start = time.time() # start timer for duration
            vc.play(source, after = lambda e: after_handler(e, self.set_stream_error) )
            
            # show playing views for controls
            await self.views.show_playing(is_dj_source, source, start_time = start, player = player)
            next_dj_source = None

            # wait until the current track ends
            while vc.is_playing(): 
                a = time.time()
                # decide to search from db or recommend from yt (from last song)
                if next_dj_source == None:
                    if dj_next_recommend_count >= dj_recommend_delay:
                        next_dj_source = await self.find_next_dj_source(suggest_from = vid)
                        dj_next_recommend_count = 0
                    else:
                        next_dj_source = await self.find_next_dj_source()
                        dj_next_recommend_count += 1
                await self.views.update_playing(ViewUpdateType.DURATION)
                b = time.time()
                await asyncio.sleep(1 - (b - a))

            # end timer and add/update duration
            end = time.time()
            if self.skip_author is None: 
                self.djObj.djdb.update_duration(vid, end - start)
            if self.stream_err is not None: 
                await self.notify(self.stream_err)

            # ending the playing view and reset skip author
            await self.views.end_playing(source, self.skip_author)
            # reset skip author and stream error
            self.skip_author = None
            self.stream_err = None

            # auto leave when no one else in vchannel
            if len(members) == 1:
                await self.djObj.leave(self, self.guild_id)
                return

        # end of playlist
        return 

    async def find_next_dj_source(self, suggest_from = None):
        '''Find dj source from database / youtube suggestions'''
        if suggest_from:
            vid = yt_search_suggestions(suggest_from)[0].vID
            
            self.djObj.yt_search_and_insert(vid, use_vID = True)
            vol = self.djObj.djdb.db_get(vid, [DJDB.Attr.SongVol])[DJDB.Attr.SongVol]
        else:
            # query a random vid and compile source
            vid, vol = self.djObj.djdb.find_rand_song()
        
        source = None
        while source == None:
            # must catch exception here, otherwise the play loop will end when yt error occur
            try: 
                source = await self.djObj.scp_compile(vid, vol)
            # youtube download/extract error and banned song exception
            except (YTDLException, DJBannedException) as e: 
                await self.mChannel.send(e.message)
                self.djObj.djdb.remove_song(vid)
        
        return source

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

        for i, (s, queue_message, player) in enumerate(self.playlist): 
            if match(key, s):
                # delete playlist entry and the queue message
                await queue_message.delete()
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

    # -------------------- DISCONNECT ------------------- # 
    async def disconnectVC(self):
        # also manage all messages?
        q = random.choice(leaving_gif_search_list)
        await self.mChannel.send(
            get_tenor_gif(q),
            # handle in DJ.py
            components = [Views.reDJ_button()]
        )
        await self.set_dj_type(None)
        await self.stop()
        await self.vc.disconnect()
        self.djObj.djdb.disconnect()