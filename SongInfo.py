from helper import *
from DBFields import SongAttr
class SongInfo():

    def __init__(self, vID, title, channelID, thumbnailURL = "", duration = None) -> None:
        for attr in SongAttr.get_all():
            setattr(self, attr, None)
            
        setattr(self, SongAttr.SongVol, default_init_vol)
        
        setattr(self, SongAttr.vID, vID)
        setattr(self, SongAttr.Title, title)
        setattr(self, SongAttr.ChannelID, channelID)
        setattr(self, SongAttr.Duration, duration)
        
        # self.thumbnailURL = thumbnailURL
        self.inserted = None # unknown state

    def __str__(self) -> str:
        return self.stringify_info()
    
    def get(self, attr: str):
        return getattr(self, attr)

    def get_all_info(self):
        return getattr(self, SongAttr.vID), getattr(self, SongAttr.Title), getattr(self, SongAttr.ChannelID)

    def stringify_info(self):
        return ", ".join([f"\"{i}\"" for i in self.get_all_info()])
    
    def dictify_info(self):
        return {
            "vID": getattr(self, SongAttr.vID),
            "Title": getattr(self, SongAttr.Title),
            "ChannelID": getattr(self, SongAttr.ChannelID)
        }
        
    def dictify_view_info(self):
        return {
            SongAttr.Title: self.Title,
            SongAttr.vID: self.vID,
            SongAttr.DJable: self.get(SongAttr.DJable),
            SongAttr.Duration: readable_time(self.get(SongAttr.Duration)),
            'thumbnailUrl': vid_to_thumbnail(self.vID),
            'embedUrl': vid_to_embed_url(self.vID)
        }
        
    def __eq__(self, __o: object) -> bool:
        return type(__o) is SongInfo and \
            all([ self.get(attr) == __o.get(attr) for attr in SongAttr.get_all() ]) # all attr match