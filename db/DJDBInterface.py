from abc import ABC, abstractmethod
from exceptions.DJExceptions import DJDBException
from const.options import default_init_vol
from const.SongInfo import SongInfo
from const.DBFields import SongAttr

# aws
import boto3
from boto3.dynamodb.conditions import Attr


class DJDBInterface(ABC):
    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractmethod
    def connect(self):
        pass

    def dbItemToSongInfo(item) -> SongInfo:
        song = SongInfo(item[SongAttr.vID], item[SongAttr.Title], item[SongAttr.ChannelID])
        if SongAttr.SongVol in item:
            item[SongAttr.SongVol] = item[SongAttr.SongVol] / 100 # Scale down from percentage
        for attr in SongAttr.get_all():
            if attr in item:
                setattr(song, attr, item[attr])
        return song


    @abstractmethod
    def db_get(self, vID, get_attrs = None) -> SongInfo:
        """
        may raise KeyError
        """
        pass

    # ------------------------ PUBLIC: DB direct actions --------------------------- #

    @abstractmethod
    def add_query(self, query, songInfo, song_exist = False):
        """
        insert / update search

        use vID to create new songinfo
        MUST have existing entry in db
        """
        pass

    @abstractmethod
    def insert_song(self, songInfo, qcount = 0, songVol = default_init_vol, newDJable = True, query=None):
        """
        insert one song
        """
        pass

    @abstractmethod
    def remove_song(self, vid):
        """
        remove song and all its queries
        """
        pass

    # --------------------------- Song info upate ---------------------------- #
    def switch_djable(self, vID):
        """
        flip djable param
        """
        old_djable = self.find_djable(vID)
        assert type(old_djable) == bool
        new_djable = not old_djable

        # update
        self.set_djable(vID, new_djable)

    @abstractmethod
    def set_djable(self, vID, djable = True):
        """
        update
        """
        pass

    @abstractmethod
    def update_duration(self, vID, duration):
        """
        update duration info

        may raise DJDBException
        """
        pass


    @abstractmethod
    def increment_qcount(self, vID):
        pass


    # ------------------------------- Queries ------------------------------- #

    @abstractmethod
    def find_djable(self, vID) -> bool:
        pass

    def find_duration(self, vID) -> int:
        try:
            returned_song = self.db_get(vID, [SongAttr.Duration])
            return returned_song[SongAttr.Duration]
        except DJDBException as e:
            return -1

    @abstractmethod
    def find_rand_song(self, dj = True):
        """
        query random song
        """
        pass

    @abstractmethod
    def find_rand_songs(self, n=10, dj = True):
        pass


    def find_song_match(self, vID):
        """
        query song
        """
        try:
            return self.db_get(vID)
        except DJDBException as e:
            # vID not in db
            return False

    @abstractmethod
    def find_query_match(self, query):
        """
        try to match query from db
        """
        pass

    @abstractmethod
    def list_all_songs(self, dj = None, top = 10, needed_attr = None, return_song_type = list):
        pass


    @abstractmethod
    def search(self, search_term, top = 10):
        """
        search songs by title and queries
        """
        pass

    # ------------------ History ------------------- #

    @abstractmethod
    def add_history(self, vID, serverID, serverName, player):
        pass

    @abstractmethod
    def get_hist_rank(self, serverID = None, dj = False, top = 20):
        """
        get top history ranked by times played
        """
        pass

    @abstractmethod
    def get_hist_count(self, vID, serverID = None, dj = False):
        pass



if __name__ == "__main__":
    ## TESTING Connection
    a = DJDB()
    a.connect()
    a.db_get("", [SongAttr.Duration])
    pass
