from xmlrpc.client import boolean
import discord
import asyncio
from API.tenorAPIget import get_tenor_gif
from SongManager import SongManager
from options import ffmpeg_error_log, default_init_vol, leaving_gif_search_list
from helper import *
from SongInfo import SongInfo
import SourceCompile
from API.ytAPIget import *
import random
import ServersHub

from API.ytAPIget import yt_search_suggestions

class VcControl():
    def __init__(self, id, vc, ) -> None:
        self.vc: discord.VoiceClient = vc
        self.songManager = SongManager()
        # self.nowplaying: bool = False
        self.playingSong: SongInfo = None
        self.playingInfo: tuple[SongInfo, str] = None
        self.dj = True
        self.started = False
        self.djReadied: tuple[str, dict] = None # (yt_link, play_options)
        
        self.djSuggestCount = 0
        self.djSuggestInterval = 2
        
        # updated (prevent fetching all data every second)
        self.updated = False
        
        self.guild_id = id
        self.Hub = ServersHub.ServersHub
        
        print("VCcontrol inited")
        pass
    
    def getServerControl(self):
        return self.Hub.getControl(self.guild_id)
    
    # --------------------------------------------------------------------------- # 
    # ----------------------------- GETTERS ---------------------------------------- # 
    # --------------------------------------------------------------------------- # 
    def getPlayingInfo(self) -> SongInfo:
        return self.playingInfo
    
    def getNowplaying(self) -> (SongInfo):
        return self.playingSong

    def getQueue(self):
        '''list/ playlist'''
        return self.songManager.getPlaylist()
    
    def getTitleQueue(self):
        '''list/ playlist'''
        return [ info.Title for source, info, author in self.songManager.getPlaylist() ]

    
    # --------------------------------------------------------------------------- # 
    # ----------------------------- LOOP ---------------------------------------- # 
    # --------------------------------------------------------------------------- # 
    def startPlayLoop(self):
        '''Add exec loop to current asyncio loop'''
        asyncio.create_task(self.execLoop())

    async def execLoop(self):
        '''execute actions periodically, manage conflict actions and terminate vc controls'''
        # prevent multiple exec loop
        if self.started:
            return 
        
        self.started = True
        
        while(self.vc):
            self.exec()
            await asyncio.sleep(1)
            
        print("Exec Loop ended")
        
        self.started = False

    def exec(self):
        ''' Executed per second '''
        # check if vc is still playing (song ended)
        if not self.vc.is_playing():
            
            # trigger song ended on server control
            if self.playingSong is not None: self.getServerControl().songEnded()
            
            self.playingSong = None
            self.playingInfo = None
            
        if self.playingSong is None and len(self.songManager.getPlaylist()) > 0:
            # nothing playing && song exist in playlist 
            
            # Get next queued song and PLAY
            source, songInfo, player = self.songManager.next()
            # songInfo.player = player # DO NOT INCLUDE PLAYER IN SONG INFO
            self.playingSong = songInfo
            self.playingInfo = (songInfo, player)
            self.vc.play(source)
            # trigger song started on server control
            self.getServerControl().songStarted()
        else:
            # nothing playing && queue empty && dj enabled && dj readied song
            if (self.dj and self.djReadied != None and self.playingSong is None 
                and len(self.songManager.getPlaylist()) == 0):
                
                # CHANGE TO TOP LEVEL REQUEST
                # self.addSong(*self.djReadied)
                (yt_link, options) = self.djReadied
                self.getServerControl().play(yt_link, **options)
                self.djReadied = None
                
            # currently playing
            # do idle task
            
            # dj task
            if len(self.songManager.getPlaylist()) == 0 and self.dj and self.djReadied == None: 
                self.djReadied = self.djExec()
                
    # --------------------------------------------------------------------------- # 
    # ----------------------------- DJ ---------------------------------------- # 
    # --------------------------------------------------------------------------- # 
    def getDJNext(self):
        return self.djReadied
    
    def djExec(self):
        playingVid = getattr(self.playingSong, SongAttr.vID) if self.playingSong else None
        vid = None
        while vid == None:
            self.djSuggestCount += 1
            if self.djSuggestCount >= self.djSuggestInterval and playingVid:
                vid = self.getDJSongFromSuggestions(playingVid)
                print("DJ SUGGESTING yt suggestions:", vid)
                self.djSuggestCount = 0
            else:            
                vid = self.Hub.djdb.find_rand_song()
                print("DJ SUGGESTING rand db song:", vid)
    
        return (
            vid_to_url(vid),
            {
                "newDJable": True,
                "author": "DJ"
            }
        )
        # # search and compile
        # source, songInfo = SourceCompile.getSource(, newDJable = True)    
        # # play
        # return [source, songInfo, "DJ"]
    
    def getDJSongFromSuggestions(self, vidToSuggestFrom):
        '''Find dj source from youtube suggestions'''
        vid = None
        suggestions_list = yt_search_suggestions(vidToSuggestFrom)
        if len(suggestions_list) > 0:
            suitableVids = VcControl.filterSuitableSuggestion(suggestions_list)
            
            random.shuffle(suitableVids)
            
            for candidateVid in suitableVids:
                # only suggest this if it is djable
                djable = self.Hub.djdb.find_djable(candidateVid)
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

    def addSong(self, source, songInfo, player, insert = False):
        print("add song")
        print(source)
        print(player)
        self.songManager.add(source, songInfo, player, insert)
        # start loop
        self.startPlayLoop()

    def skip(self, author=None):
        self.vc.stop()
        self.playingInfo = None
        self.playingSong = None

    def remove(self, title_substr, author):
        '''remove_track'''
        self.songManager.remove(title_substr)

    def clear(self):
        self.songManager.clear()

    def stop(self):
        self.vc.stop()
        self.playingInfo = None
        self.playingSong = None
        # clear all queue?? 
        # disconnect??
        pass
        
    def disconnect(self):
        self.dj = None
        self.stop()
        # disconnect vc
        asyncio.get_event_loop().create_task(self.vc.disconnect())
        self.vc = None