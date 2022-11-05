from DBFields import SongAttr
class SongInfo():

    def __init__(self, vID, title, channelID, thumbnailURL = "", duration = None) -> None:
        for attr in SongAttr.get_all():
            setattr(self, attr, None)
            
        
        setattr(self, SongAttr.vID, vID)
        setattr(self, SongAttr.Title, title)
        setattr(self, SongAttr.ChannelID, channelID)
        setattr(self, SongAttr.Duration, duration)
        
        # self.thumbnailURL = thumbnailURL
        self.inserted = None # unknown state

    def __str__(self) -> str:
        return self.stringify_info()

    def get_all_info(self):
        return self.vID, self.title, self.channelID

    def stringify_info(self):
        return ", ".join([f"\"{i}\"" for i in self.get_all_info()])
    
    def dictify_info(self):
        return {
            "vID": self.vID,
            "Title": self.title,
            "ChannelID": self.channelID
        }