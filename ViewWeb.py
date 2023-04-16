from ViewBase import ViewBase

class ViewWeb(ViewBase):
    def __init__(self) -> None:
        super().__init__()
        self.control_updated = False
        self.playing_updated = False
        self.song_info_updated = False
        self.queue_updated = False
        
    # sender
    
    # receiver
    def controlUpdated(self):
        self.control_updated = True
    
    def playingUpdated(self):
        self.playing_updated = True
    
    def songInfoUpdated(self):
        self.song_info_updated = True
        
    def songAdded(self, songInfo):
        pass
        
    def queueUpdated(self):
        self.queue_updated = True