class SongInfo():

    def __init__(self, vID, title, channelID, thumbnailURL = "") -> None:
        self.vID = vID
        self.title = title
        self.channelID = channelID
        self.thumbnailURL = thumbnailURL

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