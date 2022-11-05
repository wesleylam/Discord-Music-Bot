from xmlrpc.client import boolean
import discord
import asyncio
from API.tenorAPIget import get_tenor_gif
from SongManager import SongManager
from options import ffmpeg_error_log, default_init_vol, leaving_gif_search_list
from helper import *
from SongInfo import SongInfo
from SourceCompile import SourceCompile
from API.ytAPIget import *
import random

from API.ytAPIget import yt_search_suggestions

class VcControl():
    def __init__(self, mChannel, djo, vc, guild) -> None:
        self.vc: discord.VoiceClient = vc
        self.songManager = SongManager()
        # self.nowplaying: bool = False
        self.playingInfo: SongInfo = None
        self.dj = True
        self.started = False
        self.guild = guild
        
        self.djSuggestCount = 0
        self.djSuggestInterval = 2
        
        # updated (prevent fetching all data every second)
        self.updated = False
        
        print("VCcontrol inited")
        print(guild)
        pass
    
    # --------------------------------------------------------------------------- # 
    # ----------------------------- GETTERS ---------------------------------------- # 
    # --------------------------------------------------------------------------- # 
    def getPlayingInfo(self):
        return self.playingInfo
    def getGuildName(self):
        return self.guild.name
    def getGuildId(self):
        return self.guild.id
    def getGuild(self):
        return self.guild
    
    # --------------------------------------------------------------------------- # 
    # ----------------------------- LOOP ---------------------------------------- # 
    # --------------------------------------------------------------------------- # 
    def startPlayLoop(self):
        '''Add exec loop to current asyncio loop'''
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.execLoop(), loop=loop)

    async def execLoop(self):
        '''execute actions periodically, manage conflict actions and terminate vc controls'''
        # prevent multiple exec loop
        if self.started:
            return 
        
        while(True):
            self.exec()
            await asyncio.sleep(1)

    def exec(self):
        # check if vc is still playing (song ended)
        if not self.vc.is_playing():
            self.playingInfo = None
            
        if self.playingInfo is None and len(self.songManager.getPlaylist()) > 0:
                # nothing playing && song exist in playlist 
                source, songInfo, player = self.songManager.next()
                songInfo.player = player
                print("VC.play")
                self.vc.play(source)
                self.playingInfo = songInfo
        else:
            # currently playing
            # do idle task
            
            # dj task
            if len(self.songManager.getPlaylist()) == 0 and self.dj: 
                self.djExec()
                
    # --------------------------------------------------------------------------- # 
    # ----------------------------- DJ ---------------------------------------- # 
    # --------------------------------------------------------------------------- # 
    def djExec(self):
        playingVid = getattr(self.playingInfo, SongAttr.vID) if self.playingInfo else None
        vid = None
        while vid == None:
            self.djSuggestCount += 1
            if self.djSuggestCount >= self.djSuggestInterval and playingVid:
                vid = self.getDJSongFromSuggestions(playingVid)
                print("DJ SUGGESTING yt suggestions:", vid)
                self.djSuggestCount = 0
            else:            
                vid = SourceCompile.djdb.find_rand_song()
                print("DJ SUGGESTING rand db song:", vid)
    
        # search and compile
        source, songInfo = SourceCompile.getSource([vid_to_url(vid)], newDJable = True)    
        # play
        self.addSong(source, songInfo, "DJ")
    
    def getDJSongFromSuggestions(self, vidToSuggestFrom):
        '''Find dj source from youtube suggestions'''
        vid = None
        suggestions_list = yt_search_suggestions(vidToSuggestFrom)
        if len(suggestions_list) > 0:
            suitableVids = VcControl.filterSuitableSuggestion(suggestions_list)
            
            random.shuffle(suitableVids)
            
            for candidateVid in suitableVids:
                # only suggest this if it is djable
                djable = SourceCompile.djdb.find_djable(candidateVid)
                # None: means djdb does not contain that vid (new song, play it with djable as default)
                if djable or djable is None:
                    vid = candidateVid
                    info = SourceCompile.yt_search_and_insert(vid, use_vID = True, newDJable = True)
                    inserted = info.inserted
                    return vid
        return None
        
    def filterSuitableSuggestion(songs, max_mins = 10) -> str:
        '''
        Find the most suitable suggestion from list
        songs: list(SongInfo)   - list of suggested songs
        max_mins: int           - maximum minutes of the suggested song should have
        Returns list of suitable vIDs : [str]
        '''

        suitable = []
        for song in songs:
            # 1. the song cant be banned
            if is_banned(getattr(song, SongAttr.Title)):
                continue
            
            # 2. the song cant be over 10 mins
            #  individual (detailed) search
            song_detailed = yt_search(getattr(song, SongAttr.vID), use_vID = True) # TODO: update and insert detailed song info (in idle operation?)
            if song_detailed.duration > (max_mins * 60):
                continue

            # 3. the song should have similar title
            if song_is_live(getattr(song, SongAttr.Title)):
                continue

            # 3. the song should have similar title
            print("suitable song: " + str(song))
            suitable.append(getattr(song, SongAttr.vID))

        return suitable

    # --------------------------------------------------------------------------- # 
    # ----------------------------- ACTIONS ---------------------------------------- # 
    # --------------------------------------------------------------------------- # 
    async def disconnect(self):
        self.vc.stop()
        await self.vc.disconnect()

    def set_dj_type(self, dj: boolean):
        self.dj = dj
        # initiate loop
        if dj: 
            self.startPlayLoop()
            self.djSuggestCount = 0
        # stop otherwise
        else: self.stop()

    def view():
        pass

    def addSong(self, source, songInfo, player, insert = False):
        print("add song")
        print(source)
        print(player)
        self.songManager.add(source, songInfo, player, insert)
        # start loop
        self.startPlayLoop()

    def getNowplaying(self) -> SongInfo:
        return self.playingInfo

    def getQueue(self):
        '''list/ playlist'''
        return self.songManager.getPlaylist()
    
    def getTitleQueue(self):
        '''list/ playlist'''
        return [ info.Title for source, info, author in self.songManager.getPlaylist() ]

    def skip(self, author):
        self.vc.stop()

    def remove(self, k, author):
        '''remove_track'''
        self.songManager.remove(k)

    def clear(self):
        self.songManager.clear()

    def stop(self):
        self.vc.stop()
        # disconnect
        pass
        
    def disconnect(self):
        pass