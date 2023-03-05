from tokenize import String
from SongInfo import SongInfo
from DBFields import SongAttr

class SongManager():
    def __init__(self) -> None:
        self.playlist = [] # list of (source, songinfo, player)
        self.dj: bool = False

    def add(self, source, songInfo, player, insert = False):
        if insert:
            self.playlist.insert(0, (source, songInfo, player) ) 
        else:
            self.playlist.append( (source, songInfo, player) )

    def next(self):
        '''Get next from playlist'''
        # (source, songInfo, player)
        return self.playlist.pop(0)

    def remove(self, title_substr) -> SongInfo:
        '''remove song based on title (exact match)'''
        for i, item in enumerate(self.playlist):
            song = item[1] # songInfo
            if title_substr in getattr(song, SongAttr.Title):
                self.playlist.pop(i)
                return song
        return None

    def getPlaylist(self):
        return self.playlist

    def clear(self):
        self.playlist = []