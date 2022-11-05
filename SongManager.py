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

    def remove(self, k):
        '''remove song based on title (exact match)'''
        for i, item in enumerate(self.playlist):
            song = item[1] # songInfo
            if getattr(song, SongAttr.Title) == k:
                self.playlist.pop(i)
                break

    def getPlaylist(self):
        return self.playlist

    def clear(self):
        self.playlist = []