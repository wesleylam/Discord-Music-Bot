from xmlrpc.client import boolean
import discord
import asyncio
from API.tenorAPIget import get_tenor_gif
from SongManager import SongManager
from options import ffmpeg_error_log, default_init_vol, leaving_gif_search_list
from Views import Views, ViewUpdateType
from DJExceptions import DJBannedException
from YTDLException import YTDLException
from helper import error_log_e, error_log, is_banned, play_after_handler, song_is_live
from DJDynamoDB import DJDB
from SongInfo import SongInfo
from API.ytAPIget import *
import time
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
            
        if self.playingInfo is None:
            print(self.songManager.getPlaylist())
            if len(self.songManager.getPlaylist()) > 0:
                # nothing playing && song exist in playlist 
                source, songInfo, player = self.songManager.next()
                songInfo.player = player
                print("VC.play")
                self.vc.play(source)
                self.playingInfo = songInfo
            else:
                if self.dj: self.djExec()
                print("no song in playlist")
                # no song in playlist
                pass
        else:
            # currently playing
            # do idle task
            print("idle")
            pass
    # --------------------------------------------------------------------------- # 
    # ----------------------------- DJ ---------------------------------------- # 
    # --------------------------------------------------------------------------- # 
    def djExec(self):
        
        return 

    # --------------------------------------------------------------------------- # 
    # ----------------------------- ACTIONS ---------------------------------------- # 
    # --------------------------------------------------------------------------- # 
    async def disconnect(self):
        self.vc.stop()
        await self.vc.disconnect()

    def set_dj_type(self, dj: boolean):
        self.dj = dj
        # initiate loop
        if dj: self.startPlayLoop()
        # stop otherwise
        else: self.stop()

    def view():
        pass

    def add(self, source, songInfo, player, insert = False):
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