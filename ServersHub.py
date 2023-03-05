import ServerControl
from DJDynamoDB import DJDB
import youtube_dl
from options import ytdl_format_options

# static class
class ServersHub():
    djdb: DJDB = None
    serverControls = {} # guild.id: vcControl object
    
    # initialise ytdl from youtube_dl library
    ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

    # at the moment this can only be called from discord instance
    # will require reverse vc getter if we want to initiate from web instance
    def add(id: str, vc, guild, message_channel):
        serverControl = ServerControl.ServerControl(id, vc, guild, message_channel)
        ServersHub.serverControls[str(id)] = serverControl

        
    def getControl(id) -> ServerControl.ServerControl:
        return ServersHub.serverControls[str(id)]
        
    def getAllControls() -> dict[str, ServerControl.ServerControl]:
        return ServersHub.serverControls
    