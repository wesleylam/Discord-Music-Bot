import mysql.connector
from options import default_init_vol
from SongInfo import SongInfo

class DJDB():
    def __init__(self, host, user, password, db_name) -> None:
        self.db = mysql.connector.connect(
            host = host,
            user = user,
            password = password,
            database = db_name,
        )
        self.cursor = self.db.cursor()

    # ---- PRIVATE ------ # 
    def db_query(self, q):
        self.cursor.execute(q)
        result = self.cursor.fetchall()
        return result


    # insert / update query
    def add_query(self, query, songInfo):
        # add song to db (if not exist)
        self.insert_song(songInfo)

        vID = self.find_query_match(query)
        if vID is None:
            # add if no entry
            sql = f"INSERT INTO YtQuery (Query, vID) VALUES ('{query}', '{songInfo.vID}')"
        elif vID == songInfo.vID:
            # skip if duplicate
            return
        else:
            # no duplicate but different vID -> update
            sql = f"UPDATE YtQuery SET vID = '{songInfo.vID}' WHERE Query = '{query}'"

        self.cursor.execute(sql)
        self.db.commit()

    # insert one song
    def insert_song(self, songInfo, qcount = 1, songVol = default_init_vol):
        if self.find_song_match(songInfo.vID):
            # skip if song exist
            return

        songVol = songVol * 100 # as percentage (need int)
        sql = f"INSERT INTO YtVideo (vID, Title, ChannelID, Qcount, SongVol) VALUES ({songInfo.stringify_info()}, {qcount}, {songVol})"
        self.cursor.execute(sql)
        self.db.commit()




    # query song
    def find_song_match(self, vID, exist = False):
        result = self.db_query(f"SELECT * FROM YtVideo WHERE vID = '{vID}'")
        if len(result) <= 0: # no result
            return None
        else: 
            return result

    # try to match query from db
    def find_query_match(self, query):
        result = self.db_query(f"SELECT vID FROM YtQuery WHERE Query = '{query}'")
        if len(result) <= 0: # no result
            return None
        else: 
            # update qcount
            vID = result[0][0]
            self.update_qcount(vID)
            return vID

    def update_qcount(self, vID):
        pass


if __name__ == "__main__":
    pass