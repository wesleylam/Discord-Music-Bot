from DJExceptions import DJDBException
from config import dynamodb_table, dynamodb_hist_table
from options import default_init_vol
from SongInfo import SongInfo
import random
from helper import error_log, error_log_e, get_time

# aws
import boto3
from boto3.dynamodb.conditions import Attr


class DJDB():
    class Attr():
        vID = "vID"
        Title = "Title"
        STitle = "STitle" # Search Title (all lower case for search)
        ChannelID = "ChannelID"
        Queries = "Queries"
        DJable = "DJable"
        SongVol = "SongVol"
        Duration = "Duration"
        Qcount = "Qcount"
    class Attr_hist():
        Time = "Time" # KEY
        vID = "vID"
        ServerID = "ServerID"
        ServerName = "ServerName"
        Player = "Player" # DJ or member

    def __init__(self) -> None:
        self.dynamodb = boto3.resource('dynamodb')

    def connect(self):
        self.table = self.dynamodb.Table(dynamodb_table)
        self.hist_table = self.dynamodb.Table(dynamodb_hist_table)

    def disconnect(self):
        # no need disconnect?
        pass

    # ------------------------ PRIVATE: DB direct actions --------------------------- # 
    # ** no longer private (used in DJ/songinfo) **
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
            item = response['Item']
            if DJDB.Attr.SongVol in item:
                item[DJDB.Attr.SongVol] = item[DJDB.Attr.SongVol] / 100 # Scale down from percentage
            return item
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


    def match_query_action(self, query, match_return = None, 
        q_match_break = False, action_after_q_match = (lambda : None), action_after_v_match = (lambda : None)):

        # if match return, cannot reach break
        assert match_return is not None and not q_match_break 

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

            # HEAVY: for each video, for each query O(v*q)
            for v in items:
                for q in v[DJDB.Attr.Queries]:
                    # ensure q in database is sorted
                    if not all(q[i] <= q[i+1] for i in range(len(q)-1)):
                        error_log("Unexpected behaviour: query not sorted \nqueries: " + str(q))
                        q.sort()

                    # match query
                    if q == query_words:

                        # action after each match
                        action_after_q_match()
                        
                        # return > break
                        if match_return: return match_return
                        if q_match_break: break
            
            return None

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
        query_words = self.chop_query(query.lower())

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

    def remove_query_binding(self, vID, query):
        # get all queries
        song = self.db_get(vID, [DJDB.Attr.Queries])
        try: 
            i = song[DJDB.Attr.Queries].index(query)
        except ValueError as e:
            raise DJDBException(f"No query ({query}) binded for video ({vID}): {e.message}")

        # remove the query from vID
        self.table.update_item(
            Key={ 'vID': vID },
            UpdateExpression=f"REMOVE {DJDB.Attr.Queries}[{i}]",
        )



    # insert one song
    def insert_song(self, songInfo, qcount = 0, songVol = default_init_vol, newDJable = True):
        song = self.find_song_match(songInfo.vID)
        if song:
            # skip if song exist
            return  
        print(f"Song not found {songInfo.vID} in DB, inserting to DB")

        # get all info and default parameters
        item = songInfo.dictify_info()    
        item[DJDB.Attr.STitle] = item[DJDB.Attr.Title].lower()
        item[DJDB.Attr.Queries] = []
        item[DJDB.Attr.DJable] = newDJable
        item[DJDB.Attr.SongVol] = int(songVol * 100) # as percentage (need int)
        item[DJDB.Attr.Duration] = 0
        item[DJDB.Attr.Qcount] = qcount

        # add to db
        self.table.put_item(Item = item)

    # remove song and all its queries
    def remove_song(self, vid):
        # delete song entry
        self.table.delete_item( Key = {"vID": vid} )

        # delete related history
        response = self.hist_table.scan(
            FilterExpression = Attr(DJDB.Attr_hist.vID).eq(vid),
        )
        items = response['Items'] # items: list of dict
        for item in items: 
            self.hist_table.delete_item(
                Key = {DJDB.Attr_hist.Time: item[DJDB.Attr_hist.Time]},
            )

    # --------------------------- Song info upate ---------------------------- # 
    def switch_djable(self, vID):
        # flip djable param
        old_djable = self.find_djable(vID)
        assert type(old_djable) == bool
        new_djable = not old_djable

        # update
        self.set_djable(vID, new_djable)

    def set_djable(self, vID, djable = True):
        # update
        self.db_update(vID, DJDB.Attr.DJable, djable)


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

    def change_vol(self, vID, multiplier, setNewVol = None):
        if setNewVol is None:
            original_vol = self.db_get(vID, [DJDB.Attr.SongVol])[DJDB.Attr.SongVol]
            new_vol_percentage = int(float(original_vol * 100) * multiplier)
        else:
            new_vol_percentage = setNewVol
        # update
        self.table.update_item(
            Key = { 'vID': vID },
            UpdateExpression = f'SET {DJDB.Attr.SongVol} = :val',
            ExpressionAttributeValues = { ':val': new_vol_percentage }
        )
        return new_vol_percentage

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

    def find_duration(self, vID) -> int:
        try: 
            return self.db_get(vID, [DJDB.Attr.Duration])[DJDB.Attr.Duration]
        except DJDBException as e:
            return -1

    # query random song
    def find_rand_song(self, dj = True):

        if dj:
            response = self.table.scan(
                # FilterExpression=Attr('Title').contains('back')
                FilterExpression = Attr(DJDB.Attr.DJable).eq(True),
                ProjectionExpression = f'{DJDB.Attr.vID}, {DJDB.Attr.SongVol}'
            )
        else:
            response = self.table.scan(
                ProjectionExpression = f'{DJDB.Attr.vID}, {DJDB.Attr.SongVol}'
            )
        items = response['Items'] # items: list of dict
        chosen = random.choice(items)
        return chosen[DJDB.Attr.vID], chosen[DJDB.Attr.SongVol] / 100 # scale down from percentage


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
            ProjectionExpression=f'{DJDB.Attr.vID}, {DJDB.Attr.Queries}, {DJDB.Attr.SongVol}'
        )
        items = response['Items'] # items: list of dict

        if len(items) <= 0:
            # no songs at all
            return None
        else:
            # current query chopped into words and sorted
            query_words = self.chop_query(query.lower())

            # HEAVY
            for item in items:
                for q in item[DJDB.Attr.Queries]:
                    # ensure q in database is sorted
                    if not all(q[i] <= q[i+1] for i in range(len(q)-1)):
                        error_log("Unexpected behaviour: query not sorted \nqueries: " + str(q))
                        q.sort()

                    # match query
                    if q == query_words:
                        item[DJDB.Attr.SongVol] = item[DJDB.Attr.SongVol] / 100 # Scale down from percentage
                        return item

            # no match
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
            

    # search songs by title and queries
    def search(self, search_term, top = 10):

        ############## search by title
        needed_attr = [ DJDB.Attr.Title, DJDB.Attr.vID, DJDB.Attr.Queries ]
        needed_attr_str = ", ".join(needed_attr)
        # IDEA: can implement multiple search terms?
        response = self.table.scan(
            FilterExpression = Attr(DJDB.Attr.STitle).contains(search_term),
            ProjectionExpression = needed_attr_str
        )
        items = response['Items'] # items: list of dict

        if len(items) <= 0:
            # no songs matching search term at all
            title_searched_vids = []
            title_searched_songs = []
        else:
            title_searched_vids = [ item[DJDB.Attr.vID] for item in items[:top] ]
            title_searched_songs = [ [ item[DJDB.Attr.Title], "https://youtu.be/" + item[DJDB.Attr.vID] ] for item in items[:top] ]
        
        ############## search by queries
        # scan all songs' queries
        response = self.table.scan(
            ProjectionExpression=f'{DJDB.Attr.vID}, {DJDB.Attr.Queries}, {DJDB.Attr.Title}'
        )
        items = response['Items'] # items: list of dict
        if len(items) <= 0:
            # no songs at all
            return title_searched_songs
        else:
            # current query chopped into words and sorted
            query_words = self.chop_query(search_term.lower())
            query_searched_songs = []
            # HEAVY
            for item in items:
                # skip songs matched title
                if item[DJDB.Attr.vID] in title_searched_vids:
                    continue

                for song_query in item[DJDB.Attr.Queries]:
                    # match query
                    if any(word in song_query for word in query_words):
                        query_searched_songs.append([ f"{item[DJDB.Attr.Title]} [{'/'.join(song_query)}]", "https://youtu.be/" + item[DJDB.Attr.vID] ])
                        break

            # no match
            return title_searched_songs + query_searched_songs

# ------------------ History ------------------- # 
    def add_history(self, vID, serverID, serverName, player):
        item = dict()
        item[DJDB.Attr_hist.Time] = str(get_time())
        item[DJDB.Attr_hist.vID] = vID
        item[DJDB.Attr_hist.ServerID] = serverID
        item[DJDB.Attr_hist.ServerName] = serverName
        item[DJDB.Attr_hist.Player] = player

        # add to db
        self.hist_table.put_item(Item = item)

    def get_hist_rank(self, serverID = None, dj = False, top = 20):
        filter = None
        if serverID: 
            filter = Attr(DJDB.Attr_hist.ServerID).eq(serverID) 
        if dj: 
            filter = (filter & Attr(DJDB.Attr_hist.Player).eq("DJ")) if filter else Attr(DJDB.Attr_hist.Player).eq("DJ")
        
        if filter: 
            response = self.hist_table.scan(
                FilterExpression = filter,
                ProjectionExpression = f'{DJDB.Attr_hist.vID}'
            )
        else: 
            response = self.hist_table.scan(
                ProjectionExpression = f'{DJDB.Attr_hist.vID}'
            )
        items = response['Items'] # items: list of dict
        
        if len(items) <= 0:
            # no DJ history at all
            return None
        else:
            rank = {}
            for item in items:
                item_vID = item[DJDB.Attr_hist.vID]
                if item_vID not in rank:
                    rank[item_vID] = 1
                else:
                    rank[item_vID] += 1
            print(rank)
                
            # (vID, song title, times played)
            ranked_DJ_history = [ (vID, self.db_get(vID, [DJDB.Attr.Title])[DJDB.Attr.Title], times ) for vID, times in sorted(rank.items(), key=lambda song: song[1], reverse=True) ]
            return ranked_DJ_history



    def get_hist_count(self, vID, serverID = None, dj = False):
        filter = Attr(DJDB.Attr_hist.vID).eq(vID)
        if serverID: filter = filter & Attr(DJDB.Attr_hist.ServerID).eq(serverID) 
        if dj: filter = filter & Attr(DJDB.Attr_hist.Player).eq("DJ")

        response = self.hist_table.scan(
            FilterExpression = filter
        )

        items = response['Items'] # items: list of dict
        
        return len(items)



if __name__ == "__main__":
    pass
