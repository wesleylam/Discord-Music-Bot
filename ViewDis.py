import asyncio
from ViewBase import ViewBase
import ViewDisMes
from const import SongInfo
from const.DBFields import SongAttr
import ServersHub
from const.helper import *
import discord
from const import helper
from Chatbot import Chatbot
import time

class ViewDis(ViewBase):
    def __init__(self, id, message_channel, loop) -> None:
        super().__init__()
        self.control_updated = False
        self.playing_updated = False
        self.song_info_updated = False
        self.queue_updated = False
        
        self.message_channel = message_channel
        self.loop = loop
        self.lock = None
        
        self.guild_id = id
        self.Hub: ServersHub.ServersHub = ServersHub.ServersHub
        self.playbox_removed: bool = False
        self.playbox_message: discord.Message = None
        self.playbox_view: discord.ui.View = None
        
    async def removePlaybox(self):
        if self.playbox_message is not None:
            await self.playbox_message.delete()
            self.playbox_message = None
            return 
        
    async def waitAndSendRes(self, timeoutLimit = 20): 
        start = time.time()
        time.sleep(1)
        
        while Chatbot.lastReply == "" and (time.time() - start < timeoutLimit):
            time.sleep(1)
        
        if (Chatbot.lastReply == ""):
            message = "DJ is speechless"
        else:
            message = "DJ: " + Chatbot.lastReply
            
        m = await self.message_channel.send(message)
        if m != None:
            await m.delete(delay=60)
        
    # sender
    async def updatePlaybox(self):
        # release if too long (10s)
        if self.lock != None and (time.time() - self.lock) > 10:
            self.lock = None
        
        if self.lock != None:
            return # skip if locked (another processing)
        
        self.lock = time.time()
        playingInfo: tuple[SongInfo.SongInfo, str] = \
            self.Hub.getControl(self.guild_id).getPlayingInfo()    
        
        if playingInfo is None:
            print("NOTHING IS PLAYING, delete playbox")
            self.lock = None
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
        message = f"{author} playing: {title}\n[{readable_time(duration if duration is not None else 0)}]{url}"
        
        # RECREAET PLAYBOX
        self.playbox_view = ViewDisMes.PlayBox(vID = vID)
        
        suggestions: list[SongInfo.SongInfo] = self.Hub.getControl(self.guild_id).getSuggestions() 
        for suggestion in suggestions:
            label: str = getattr(suggestion, SongAttr.Title)
            sugButton = SuggestionButton(self.Hub, self.guild_id, getattr(suggestion, SongAttr.vID), label=label[:80] if len(label) > 80 else label, )
            print("ADDED BUTTON", suggestion.Title)
            self.playbox_view.add_item(sugButton)
        
        # ALWAYS SEND NEW
        if (self.playbox_message is not None):
            try:
                await self.playbox_message.delete()
            except e:
                error_log_e(e)
                
        # ASYNC CHATBOT
        Chatbot.djUpdate(f"{author} played {title}")
        asyncio.create_task(self.waitAndSendRes())

        ## Send view box
        self.playbox_message = await self.message_channel.send(f"{message}", view=self.playbox_view)
        # Release lock
        self.lock = None
    
    # receiver
    def controlUpdated(self):
        self.control_updated = True
    
    def playingUpdated(self):
        self.playing_updated = True
        asyncio.ensure_future(self.updatePlaybox(), loop=self.loop)
        
    def checkDisplay(self):
        if self.lock == False and self.playbox_message == None:
            print("ViewDis: No playbox found, forcing update")
            self.removePlaybox()
            self.playingUpdated()
        
    def suggestionUpdated(self):
        self.playingUpdated()
    
    def songInfoUpdated(self):
        self.song_info_updated = True
        
    def songAdded(self, songInfo: SongInfo):
        asyncio.ensure_future(self.Hub.DJ_BOT.notify(self.message_channel, f'Queued song: {helper.vid_to_url(songInfo.get(SongAttr.vID))}'), loop=self.loop)
        self.queue_updated = True
        
    def queueUpdated(self):
        asyncio.ensure_future(self.Hub.DJ_BOT.queue(self.message_channel))
        self.queue_updated = True
        
    def disconnected(self):
        asyncio.ensure_future(self.removePlaybox(), loop=self.loop)
        
        
## CUSTOM BUTTON CLASS TO HANDLE SUGGESTION BUTTON CALLBACK
class SuggestionButton(discord.ui.Button):
    def __init__(self, Hub, guild_id, vid, label) -> None:
        super().__init__(label=label)
        self.Hub = Hub
        self.guild_id = guild_id
        self.vid = vid
        
    async def callback(self, interaction: discord.Interaction):
        super().callback(interaction)
        self.Hub.getControl(self.guild_id).play(helper.vid_to_url(self.vid), author=interaction.user)
    