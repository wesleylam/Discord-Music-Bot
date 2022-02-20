class SongInfo():

    def __init__(self, vID, title, channelID, thumbnailURL = "", duration = None) -> None:
        self.vID = vID
        self.title = title
        self.channelID = channelID
        self.thumbnailURL = thumbnailURL
        # in seconds
        self.duration = duration

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