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


    # insert query
    def add_query(self, query, songInfo):
        if not self.find_song_match(songInfo.vID):
            # song not exist
            self.insert_song(songInfo)

        sql = "INSERT INTO YtQuery (Query, vID) VALUES (%s, %s)"
        val = (query, songInfo.vID)

        self.cursor.execute(sql, val)
        self.db.commit()


    # change query
    def change_query(self, query, vID):
        pass

    # insert one song
    def insert_song(self, songInfo, qcount = 1, songVol = default_init_vol):
        songVol = songVol * 100 # as percentage (need int)
        sql = f"INSERT INTO YtVideo (vID, Title, ChannelID, Qcount, SongVol) VALUES ({songInfo.stringify_info()}, {qcount}, {songVol})"
        self.cursor.execute(sql)
        self.db.commit()

    # bunch insert songs
    def insert_songs(self, songInfos): # songs = [(vID, title, channelID, qcount, songVol)]
        sql = "INSERT INTO YtVideo (vID, Title, ChannelID, Qcount, SongVol) VALUES (%s, %s, %s, %s, %s)"
        val = []
        # for songInfo in songInfos:
        #     val.append( song)

        self.cursor.executemany(sql, val)
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