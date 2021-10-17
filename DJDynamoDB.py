from DJDBException import DJDBException
from options import default_init_vol
from SongInfo import SongInfo
import random
from enum import Enum
import functools

# aws
import boto3
import pickle
from boto3.dynamodb.conditions import Attr


class DJDB():
    class Attr(Enum):
        vID = "vID"
        Title = "Title"
        ChannelID = "ChannelID"
        Queries = "Queries"
        DJable = "DJable"
        SongVol = "SongVol"
        Duration = "Duration"
        Qcount = "Qcount"

    def __init__(self) -> None:
        self.dynamodb = boto3.resource('dynamodb')

    def connect(self):
        self.table = self.dynamodb.Table('DJsongs')

    def disconnect(self):
        # no need disconnect?
        self.table = None

    # ------------------------ PRIVATE: DB direct actions --------------------------- # 
    def db_get(self, vID, get_attrs = None):
        # get        
        if get_attrs:
            response = self.table.get_item( 
                Key={ 'vID': vID }, 
                AttributesToGet = get_attrs 
            )
        else: 
            response = self.table.get_item( Key={ 'vID': vID } )

        try:
            return response['Item']
        except KeyError as e:
            raise DJDBException(f"No item for vID: {vID}")
            

    def db_scan(self, vID, get_attrs = None):
        pass

    # update one attr for a song (vID)
    def db_update(self, vID, attr, val):
        # update
        self.table.update_item(
            Key={ 'vID': vID },
            UpdateExpression=f'SET {attr} = :val',
            ExpressionAttributeValues={
                ':val': val
            }
        )

    def chop_query(self, query):
        words = query.split(" ")
        words.sort()
        return words


    # ------------------------ PUBLIC: DB direct actions --------------------------- # 
    # insert / update search
    def add_query(self, query, songInfo, song_exist = False):
        # use vID to create new songinfo
        # MUST have existing entry in ytvideo
        if type(songInfo) != SongInfo:
            songInfo = SongInfo(songInfo, "", "")
            song_exist = True 

        # add song to db (if not exist)
        if not song_exist: self.insert_song(songInfo)
        vID = songInfo.vID

        song = self.db_get(vID)
        query_words = self.chop_query(query)
        for q in song[DJDB.Attr.Queries]:
            if q == query_words:
                # skip: duplicate
                return 

        # update
        self.table.update_item(
            Key={ 'vID': vID },
            UpdateExpression=f'SET {DJDB.Attr.Queries} = list_append({DJDB.Attr.Queries}, :val)',
            ExpressionAttributeValues={
                ':val': query_words
            }
        )




    # insert one song
    def insert_song(self, songInfo, qcount = 1, songVol = default_init_vol):
        if self.find_song_match(songInfo.vID):
            # skip if song exist
            return

        songVol = songVol * 100 # as percentage (need int)

        item = songInfo.dictify_info()    
        item[DJDB.Attr.Queries] = []
        item[DJDB.Attr.DJable] = True
        item[DJDB.Attr.SongVol] = songVol
        item[DJDB.Attr.Duration] = 0
        item[DJDB.Attr.Qcount] = qcount

        self.table.put_item(Item = item)

    # remove song and all its queries
    def remove_song(self, vid):
        self.table.delete_item( Key = {"vID": vid} )

    # --------------------------- Song info upate ---------------------------- # 
    def switch_djable(self, vID):
        # flip djable param
        old_djable = self.find_djable(vID)
        assert type(old_djable) == bool
        new_djable = not old_djable

        # update
        self.db_update(vID, DJDB.Attr.DJable, new_djable)

    # used when duration is 0
    def add_duration(self, vID, duration):
        self.db_update(vID, DJDB.Attr.Duration, duration)


    def increment_qcount(self, vID):
        # update
        self.table.update_item(
            Key = { 'vID': vID },
            UpdateExpression = f'SET {DJDB.Attr.Qcount} = {DJDB.Attr.Qcount} + :val',
            ExpressionAttributeValues = { ':val': 1 }
        )

    def change_vol(self, vol):
        pass

    def add_tag(self, vid, tag):
        pass

    def remove_tag(self):
        pass

    # ------------------------------- Queries ------------------------------- # 
    def find_djable(self, vID):
        return self.db_get(vID, [DJDB.Attr.DJable])[DJDB.Attr.DJable]

    # query random song
    def find_rand_song(self, dj = True):

        if dj:
            response = self.table.scan(
                # FilterExpression=Attr('Title').contains('back')
                FilterExpression = Attr(DJDB.Attr.DJable).eq(True),
                ProjectionExpression = [DJDB.Attr.vID]
            )
        else:
            response = self.table.scan(
                ProjectionExpression = [DJDB.Attr.vID]
            )
        items = response['Item'] # items: list of dict
        return random.choice(items)[DJDB.Attr.vID]


    # query song
    def find_song_match(self, vID):
        try: 
            return self.db_get(vID)
        except: 
            return False

    # try to match query from db
    def find_query_match(self, query):
        # scan all songs' queries
        response = self.table.scan(
            ProjectionExpression=f'{DJDB.Attr.vID}, {DJDB.Attr.Queries}'
        )
        items = response['Item'] # items: list of dict

        if len(items) <= 0:
            # no songs at all
            return None
        else:
            # current query chopped into words and sorted
            query_words = self.chop_query(query)

            # HEAVY
            for item in items:
                for q in item[DJDB.Attr.Queries]:
                    # ensure q in database is sorted
                    if not all(q[i] <= q[i+1] for i in range(len(q)-1)):
                        print("Unexpected behaviour: query not sorted")
                        print(q)
                        q.sort()

                    # match query
                    if q == query_words:
                        vID = item[DJDB.Attr.vID]
                        self.increment_qcount(vID)
                        return vID

            return None


    def list_all_songs(self, dj=None, top = 10):
        needed_attr = [ DJDB.Attr.Title ]
        needed_attr_str = ", ".join(needed_attr)
        if dj is None:
            response = self.table.scan(
                ProjectionExpression = needed_attr_str
            )
        else:
            response = self.table.scan(
                FilterExpression = Attr(DJDB.Attr.DJable).eq(dj),
                ProjectionExpression = needed_attr_str
            )
        items = response['Item'] # items: list of dict

        if len(items) <= 0:
            # no songs at all
            return None
        else:
            return [ [ item[a] for a in needed_attr ] for item in items[:top] ]
            

    # search songs by title
    def search(self, search_term, top = 10):
        needed_attr = [ DJDB.Attr.Title, DJDB.Attr.vID ]
        needed_attr_str = ", ".join(needed_attr)

        # IDEA: can implement multiple search terms?
        response = self.table.scan(
            FilterExpression = Attr(DJDB.Attr.Title).contains(search_term),
            ProjectionExpression = needed_attr_str
        )
        items = response['Item'] # items: list of dict

        if len(items) <= 0:
            # no songs at all
            return None
        else:
            return [ [ item[a] for a in needed_attr ] for item in items[:top] ]
            

if __name__ == "__main__":
    pass