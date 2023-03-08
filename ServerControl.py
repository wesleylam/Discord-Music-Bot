import VcControl
from DJDynamoDB import DJDB
from ViewBase import ViewBase
import SourceCompile
import ServersHub 
import YTDLException
from SongInfo import SongInfo
from ViewWeb import ViewWeb
from ViewDis import ViewDis

class ServerControl():
    def __init__(self, id: str, vc, guild, message_channel, loop):
        self.id = id
        self.guild = guild
        self.vcControl = VcControl.VcControl(id, vc)
        self.viewsList: ViewsList = ViewsList()
        self.addView(ViewWeb())
        self.addView(ViewDis(id, message_channel, loop))
        
    def getGuildName(self):
        return self.guild.name
    def getGuildId(self):
        return self.guild.id
    def getGuild(self):
        return self.guild
        
        
    # ----------------------------- ACTIONS ------------------------------ # 
    def addView(self, views: ViewBase):
        self.viewsList.add(views)
        
    def join():
        pass
    
    def disconnect(self):
        self.leave()
        
    def leave(self):
        self.vcControl.disconnect()
        self.viewsList.disconnected() # control updated?
        # DESTROY CURRENT CONTROL INSTANCE FROM HUB??
        # self.vcControl = None
        
    def dj(self, dj_type=True):
        self.vcControl.set_dj_type(dj_type)
        self.viewsList.controlUpdated()
        # self.viewsList.changedDjType(dj/_type)
        
    def play(self, *kwords, author=None, insert = False, loud = False, baseboost = False, newDJable = True):
        '''Play a song (search in youtube / youtube link)'''
        # search and compile
        # also add to db when needed
        try:
            source, song_info = SourceCompile.getSource(kwords, newDJable = newDJable, loud = loud, baseboost = baseboost)
        except YTDLException.YTDLException as e:
            print(e)
            return # ignore play command 
        
        # Voice client Control
        self.vcControl.addSong(source, song_info, author, insert = insert)

        # View control
        self.viewsList.queueUpdated()
        # self.viewsList.songAdded(song_info)

    def skip(self, author=None):
        self.vcControl.skip(author)
        self.viewsList.playingUpdated()
        self.viewsList.queueUpdated()
        
    def stop(self):
        self.vcControl.stop()
        self.viewsList.playingUpdated()
        self.viewsList.queueUpdated()
        
        
    def remove(self, song_info):
        self.vcControl.remove(song_info, author=None)
        self.viewsList.queueUpdated()
        
    def clear(self):
        self.vcControl.clear()
        self.viewsList.queueUpdated()
        
    def djable(self, vID, djable=True):
        ServersHub.ServersHub.djdb.set_djable(vID, djable)
        self.viewsList.songInfoUpdated()
        
        
    def songVolumeSet(self, song_id, new_volume):
        self.viewsList.songInfoUpdated()
        pass
    
                
    # ----------------------------- RECEIVE UPDATE ------------------------------ # 
    def songStarted(self):
        self.viewsList.playingUpdated()
    
    def songEnded(self):
        self.viewsList.playingUpdated()
    
    # ----------------------------- REQUEST INFO ------------------------------ # 
    def getNowplaying(self):
        return self.vcControl.getNowplaying()
    
    def getPlayingInfo(self):
        return self.vcControl.getPlayingInfo()
    
    def getQueue(self):
        return self.vcControl.getQueue()




        

# COULD INHERIT VIEWBASE ??
class ViewsList():
    def __init__(self) -> None:
        self.views: list[ViewBase] = []    
    
    def add(self, view: ViewBase):
        self.views.append(view)
    
    # sender
    
    # receiver
    def controlUpdated(self):
        print("CONTROL UPDATED")
        for v in self.views:
            v.controlUpdated()
        pass
    
    def playingUpdated(self):
        print("PLAYING UPDATED")
        for v in self.views:
            v.playingUpdated()
        pass
    
    def songInfoUpdated(self):
        print("SONG INFO UPDATED")
        for v in self.views:
            v.songInfoUpdated()
        
        pass
    
    def queueUpdated(self):
        print("QUEUE UPDATED")
        for v in self.views:
            v.queueUpdated()
        
        pass
    
    
    
    
    def updateSec(self):
        pass
    
    def changedSong(self, song=None):
        if song == None:
            # no song playing
            pass
        pass
    
    def disconnected(self):
        for v in self.views:
            v.disconnected()
            
    def changedDjType(self, dj_type):
        pass
    
    def songAdded(self, song: SongInfo):
        pass
    
    def updateSongInfo(self, new_song_info: SongInfo):
        pass