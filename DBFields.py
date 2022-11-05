
class SongAttr():
    vID = "vID"
    Title = "Title"
    STitle = "STitle" # Search Title (all lower case for search)
    ChannelID = "ChannelID"
    Queries = "Queries"
    DJable = "DJable"
    SongVol = "SongVol"
    Duration = "Duration"
    Qcount = "Qcount"
    
    def get_all():
        return [SongAttr.vID, SongAttr.Title, SongAttr.STitle, 
        SongAttr.ChannelID, SongAttr.Queries, SongAttr.DJable, 
        SongAttr.SongVol, SongAttr.Duration, SongAttr.Qcount, ]

class HistAttr():
    Time = "Time" # KEY
    vID = "vID"
    ServerID = "ServerID"
    ServerName = "ServerName"
    Player = "Player" # DJ or member