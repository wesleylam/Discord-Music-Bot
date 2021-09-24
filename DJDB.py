import mysql.connector
from options import default_init_vol
from SongInfo import SongInfo
import random

class DJDB():
    def __init__(self, host, user, password, db_name) -> None:
        self.host = host
        self.user = user
        self.password = password
        self.db_name = db_name
        self.connect()

    def connect(self):
        self.db = mysql.connector.connect(
            host = self.host,
            user = self.user,
            password = self.password,
            database = self.db_name,

            # use unicode (eg: emoji)
            use_unicode = True,
            charset = 'utf8mb4',
            collation = 'utf8mb4_unicode_520_ci',
        )
        self.cursor = self.db.cursor()

    # ------------------------ PRIVATE: DB direct actions --------------------------- # 
    def db_query(self, q):
        self.cursor.execute(q)
        result = self.cursor.fetchall()
        return result
    def db_update(self, sql):
        self.cursor.execute(sql)
        self.db.commit()


    # insert / update query
    def add_query(self, query, songInfo, song_exist = False):
        # use vID to create new songinfo
        # MUST have existing entry in ytvideo
        if type(songInfo) != SongInfo:
            songInfo = SongInfo(songInfo, "", "")
            song_exist = True 

        # add song to db (if not exist)
        if not song_exist: self.insert_song(songInfo)

        vID = self.find_query_match(query)
        if vID is None:
            # add if no entry
            sql = f"INSERT INTO YtQuery (Query, vID) VALUES (\"{query}\", \"{songInfo.vID}\")"
        elif vID == songInfo.vID:
            # skip if duplicate
            return
        else:
            # no duplicate but different vID -> update
            sql = f"UPDATE YtQuery SET vID = '{songInfo.vID}' WHERE Query = '{query}'"

        self.db_update(sql)

    # insert one song
    def insert_song(self, songInfo, qcount = 1, songVol = default_init_vol):
        if self.find_song_match(songInfo.vID):
            # skip if song exist
            return

        songVol = songVol * 100 # as percentage (need int)
        sql = f"INSERT INTO YtVideo (vID, Title, ChannelID, Qcount, SongVol) VALUES ({songInfo.stringify_info()}, {qcount}, {songVol})"
        self.db_update(sql)

    # remove song and all its queries
    def remove_song(self, vid):
        try: 
            sql = f"DELETE FROM YtQuery WHERE vID = '{vid}'"
            self.db_update(sql)
        except: 
            pass
        try: 
            sql = f"DELETE FROM YtVideo WHERE vID = '{vid}'"
            self.db_update(sql)
        except: 
            pass

    # --------------------------- Song info upate ---------------------------- # 
    def switch_djable(self, vid):
        # flip djable param
        new_djable = 0 if self.find_djable(vid) else 1
        sql = f"UPDATE YtVideo SET DJable = '{new_djable}' WHERE vID = '{vid}'"
        self.db_update(sql)

    def update_qcount(self, vID):
        pass

    def change_vol():
        pass

    def add_tag(self, vid, tag):
        sql = f"INSERT INTO Tag (Tag, vID) VALUES ({tag}, {vid})"
        self.db_update(sql)
        pass

    def remove_tag(self):
        pass

    # ------------------------------- Queries ------------------------------- # 
    def find_djable(self, vid):
        result = self.db_query(f"SELECT DJable FROM YtVideo WHERE vID = '{vid}'")
        return result[0][0] == 1

    # query random song
    def find_rand_song(self, dj = True):
        if dj:
            result = self.db_query(f"SELECT vID FROM YtVideo ORDER BY RAND() LIMIT 1")
        else: 
            result = self.db_query(f"SELECT vID FROM YtVideo WHERE DJable = '{1}' ORDER BY RAND() LIMIT 1")
        return result[0][0]


    # query song
    def find_song_match(self, vID, exist = False):
        result = self.db_query(f"SELECT * FROM YtVideo WHERE vID = \"{vID}\"")
        if len(result) <= 0: # no result
            return None
        else: 
            return result[0]

    # try to match query from db
    def find_query_match(self, query):
        result = self.db_query(f"SELECT vID FROM YtQuery WHERE Query = \"{query}\"")
        if len(result) <= 0: # no result
            return None
        else: 
            # update qcount
            vID = result[0][0]
            self.update_qcount(vID)
            return vID



if __name__ == "__main__":
    pass