import asyncio
import ServerControl
from DJDynamoDB import DJDB
import youtube_dl
from const.options import ytdl_format_options

# static class for global
class ServersHub():
    djdb: DJDB = None
    serverControls = {} # guild.id: vcControl object
    DJ_BOT = None
    
    # initialise ytdl from youtube_dl library
    ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
    
    # asyncio loop: for async func
    loop = None

    # at the moment this can only be called from discord instance
    # will require reverse vc getter if we want to initiate from web instance
    def add(guild, vc, message_channel):
        g_id: str = guild.id 
        serverControl = ServerControl.ServerControl(vc, guild, message_channel, ServersHub.loop)
        ServersHub.serverControls[str(g_id)] = serverControl

        
    def getControl(id) -> ServerControl.ServerControl:
        return ServersHub.serverControls[str(id)] if str(id) in ServersHub.serverControls else None
        
    def getAllControls() -> dict[str, ServerControl.ServerControl]:
        return ServersHub.serverControls
    