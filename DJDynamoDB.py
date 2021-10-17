from DJDBException import DJDBException
from options import default_init_vol
from SongInfo import SongInfo
import random
from helper import error_log

# aws
import boto3
from boto3.dynamodb.conditions import Attr


class DJDB():
    class Attr():
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
        pass

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
            UpdateExpression='SET #a = :val',
            ExpressionAttributeNames={ '#a': attr },
            ExpressionAttributeValues={ ':val': val }
        )

    def chop_query(self, query):
        words = query.split(" ")
        words.sort()
        return words


    # ------------------------ PUBLIC: DB direct actions --------------------------- # 
    # insert / update search
    def add_query(self, query, songInfo, song_exist = False):
        # use vID to create new songinfo
        # MUST have existing entry in db
        if type(songInfo) != SongInfo:
            songInfo = SongInfo(songInfo, "", "")
            song_exist = True 

        # add song to db (if not exist)
        if not song_exist: self.insert_song(songInfo)
        vID = songInfo.vID

        # get song query (must find song, cannot cause error, song added above)
        song = self.db_get(vID, [DJDB.Attr.Queries])

        # transform query into tokens
        query_words = self.chop_query(query)

        # check for duplicate
        for q in song[DJDB.Attr.Queries]:
            if q == query_words:
                # skip: duplicate
                return 

        # append the query if it is not duplicate
        self.table.update_item(
            Key={ 'vID': vID },
            UpdateExpression=f'SET {DJDB.Attr.Queries} = list_append({DJDB.Attr.Queries}, :val)',
            ExpressionAttributeValues={
                ':val': [query_words]
            }
        )


    # insert one song
    def insert_song(self, songInfo, qcount = 1, songVol = default_init_vol):
        song = self.find_song_match(songInfo.vID)
        if song:
            # skip if song exist
            return  
        print(f"Song not found {songInfo.vID}, inserting to db")

        # get all info and default parameters
        item = songInfo.dictify_info()    
        item[DJDB.Attr.Queries] = []
        item[DJDB.Attr.DJable] = True
        item[DJDB.Attr.SongVol] = int(songVol * 100) # as percentage (need int)
        item[DJDB.Attr.Duration] = 0
        item[DJDB.Attr.Qcount] = qcount

        # add to db
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

    # update duration info
    def update_duration(self, vID, duration):
        try:
            old_duration = self.db_get(vID, [DJDB.Attr.Duration])[DJDB.Attr.Duration]
        except DJDBException as e:
            # possible cause: delete from db and try to update
            error_log("Cannot update duration: " + e.message)
            return 

        print(f"Updating duration for {vID}: {duration}")
        if old_duration == 0 or old_duration != duration:
            self.db_update(vID, DJDB.Attr.Duration, int(duration))


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
    def find_djable(self, vID) -> bool:
        try: 
            return self.db_get(vID, [DJDB.Attr.DJable])[DJDB.Attr.DJable]
        except DJDBException as e:
            error_log("cannot find djable: " + e.message)
            return False

    # query random song
    def find_rand_song(self, dj = True):

        if dj:
            response = self.table.scan(
                # FilterExpression=Attr('Title').contains('back')
                FilterExpression = Attr(DJDB.Attr.DJable).eq(True),
                ProjectionExpression = DJDB.Attr.vID
            )
        else:
            response = self.table.scan(
                ProjectionExpression = [DJDB.Attr.vID]
            )
        items = response['Items'] # items: list of dict
        return random.choice(items)[DJDB.Attr.vID]


    # query song
    def find_song_match(self, vID):
        try: 
            return self.db_get(vID)
        except DJDBException as e:
            # vID not in db
            return False

    # try to match query from db
    def find_query_match(self, query):
        # scan all songs' queries
        response = self.table.scan(
            ProjectionExpression=f'{DJDB.Attr.vID}, {DJDB.Attr.Queries}'
        )
        items = response['Items'] # items: list of dict

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
        needed_attr_str = ", ".join( needed_attr )
        if dj is None:
            response = self.table.scan(
                ProjectionExpression = needed_attr_str
            )
        else:
            response = self.table.scan(
                FilterExpression = Attr(DJDB.Attr.DJable).eq(dj),
                ProjectionExpression = needed_attr_str
            )
        items = response['Items'] # items: list of dict

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
        items = response['Items'] # items: list of dict

        if len(items) <= 0:
            # no songs at all
            return None
        else:
            return [ [ item[DJDB.Attr.Title], "https://youtu.be/" + item[DJDB.Attr.vID] ] for item in items[:top] ]
            

if __name__ == "__main__":
    pass