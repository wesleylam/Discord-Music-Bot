import asyncio
from ViewBase import ViewBase
import ViewDisMes
import SongInfo
from DBFields import SongAttr
import ServersHub
from helper import *
import discord

class ViewDis(ViewBase):
    def __init__(self, id, message_channel, loop) -> None:
        super().__init__()
        self.control_updated = False
        self.playing_updated = False
        self.song_info_updated = False
        self.queue_updated = False
        
        self.message_channel = message_channel
        self.loop = loop
        
        self.guild_id = id
        self.Hub = ServersHub.ServersHub
        self.playbox_removed: bool = False
        self.playbox_message: discord.Message = None
        self.playbox_view: discord.ui.View = None
        
    async def removePlaybox(self):
        if self.playbox_message is not None:
            await self.playbox_message.delete()
            self.playbox_message = None
            if self.playbox_view.vID != self.vID:
                self.playbox_view = None
            return 
    
    # sender
    async def updatePlaybox(self):
        playingInfo: tuple[SongInfo.SongInfo, str] = \
            self.Hub.getControl(self.guild_id).getPlayingInfo()    
        
        if playingInfo is None:
            print("NOTHING IS PLAYING, delete playbox")
            return await self.removePlaybox()
        
        # print("playingInfo", playingInfo)
        (songInfo, author) = playingInfo
        title = songInfo.get(SongAttr.Title)
        vID = songInfo.get(SongAttr.vID)
        duration = songInfo.get(SongAttr.Duration)
        url = vid_to_url(vID)

        # create playbox buttons view
        if self.playbox_view is None:
            self.playbox_view = ViewDisMes.PlayBox(vID = vID)
        self.playbox_view.setVID(vID)
        
        ## Create message / edit message
        message = f"""
        {author} playing: {title}\n[{readable_time(duration)}]{url}
        """
        
        if self.playbox_message is None:
            self.playbox_message = await self.message_channel.send(message, view=self.playbox_view)
            return 
        
        self.playbox_message = await self.playbox_message.edit(content=message, view=self.playbox_view)
        return 
    
    # receiver
    def controlUpdated(self):
        self.control_updated = True
    
    def playingUpdated(self):
        self.playing_updated = True
        
        asyncio.ensure_future(self.updatePlaybox(), loop=self.loop)
    
    def songInfoUpdated(self):
        self.song_info_updated = True
        
    def queueUpdated(self):
        self.queue_updated = True
        
    def disconnected(self):
        asyncio.ensure_future(self.removePlaybox(), loop=self.loop)