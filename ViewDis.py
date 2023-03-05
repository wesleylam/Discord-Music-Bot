import asyncio
from ViewBase import ViewBase
import ViewDisMes
import SongInfo
from DBFields import SongAttr
import ServersHub
from helper import vid_to_url
import discord

class ViewDis(ViewBase):
    def __init__(self, id, message_channel) -> None:
        super().__init__()
        self.control_updated = False
        self.playing_updated = False
        self.song_info_updated = False
        self.queue_updated = False
        
        self.message_channel = message_channel
        
        self.guild_id = id
        self.Hub = ServersHub.ServersHub
        self.playbox: discord.Message = None
        self.playbox_view: discord.ui.View = None
        
    # sender
    async def updatePlaybox(self):
        playingInfo: tuple[SongInfo.SongInfo, str] = \
            self.Hub.getControl(self.guild_id).getPlayingInfo()
        if playingInfo is None and self.playbox is not None:
            print("NOTHING IS PLAYING, delete playbox")
            await self.playbox.delete()
            self.playbox = None
            self.playbox_view = None
            return 
            
        print("playingInfo", playingInfo)
        (songInfo, author) = playingInfo
            
        title = songInfo.get(SongAttr.Title)
        vID = songInfo.get(SongAttr.vID)
        url = vid_to_url(vID)
        
        ## Create message / edit message
        message = f"""
        {author} playing: {title}
        {url}
        """
        if self.playbox_view is None:
            self.playbox_view = ViewDisMes.PlayBox()
        
        if self.playbox is None:
            self.playbox = await self.message_channel.send(message, view=self.playbox_view)
        else:
            self.playbox = await self.playbox.edit(content=message, view=self.playbox_view)
        
        return 
    
    # receiver
    def controlUpdated(self):
        self.control_updated = True
    
    def playingUpdated(self):
        self.playing_updated = True
        
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.updatePlaybox(), loop=loop)
    
    def songInfoUpdated(self):
        self.song_info_updated = True
        
    def queueUpdated(self):
        self.queue_updated = True