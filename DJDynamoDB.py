from DJExceptions import DJDBException
from botocore.exceptions import ClientError
from config import dynamodb_table, dynamodb_hist_table
from options import default_init_vol
from SongInfo import SongInfo
import random
from DBFields import SongAttr, HistAttr
from helper import error_log, error_log_e, get_time, vid_to_thumbnail

# aws
import boto3
from boto3.dynamodb.conditions import Attr


class DJDB():
    def __init__(self) -> None:
        self.dynamodb = boto3.resource('dynamodb')

    def connect(self):
        self.table = self.dynamodb.Table(dynamodb_table)
        self.hist_table = self.dynamodb.Table(dynamodb_hist_table)

    def disconnect(self):
        # no need disconnect?
        pass
    
    def dbItemToSongInfo(item):
        song = SongInfo(item[SongAttr.vID], item[SongAttr.Title], item[SongAttr.ChannelID])
        for attr in SongAttr.get_all():
            setattr(song, attr, item[attr])
        return song
            

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
            if SongAttr.SongVol in item:
                item[SongAttr.SongVol] = item[SongAttr.SongVol] / 100 # Scale down from percentage
            return DJDB.dbItemToSongInfo(item)
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
            ProjectionExpression=f'{SongAttr.vID}, {SongAttr.Queries}'
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
                for q in v[SongAttr.Queries]:
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
        song = self.db_get(vID, [SongAttr.Queries])

        # transform query into tokens
        query_words = self.chop_query(query.lower())

        # check for duplicate
        for q in song[SongAttr.Queries]:
            if q == query_words:
                # skip: duplicate
                return 

        # append the query if it is not duplicate
        self.table.update_item(
            Key={ 'vID': vID },
            UpdateExpression=f'SET {SongAttr.Queries} = list_append({SongAttr.Queries}, :val)',
            ExpressionAttributeValues={
                ':val': [query_words]
            }
        )

    def remove_query_binding(self, vID, query):
        # get all queries
        song = self.db_get(vID, [SongAttr.Queries])
        try: 
            i = song[SongAttr.Queries].index(query)
        except ValueError as e:
            raise DJDBException(f"No query ({query}) binded for video ({vID}): {e.message}")

        # remove the query from vID
        self.table.update_item(
            Key={ 'vID': vID },
            UpdateExpression=f"REMOVE {SongAttr.Queries}[{i}]",
        )



    # insert one song
    def insert_song(self, songInfo, qcount = 0, songVol = default_init_vol, newDJable = True):
        song = self.find_song_match(songInfo.vID)
        if song:
            # skip if song exist
            return False
        print(f"Song not found {songInfo.vID} in DB, inserting to DB")

        # get all info and default parameters
        item = songInfo.dictify_info()    
        item[SongAttr.STitle] = item[SongAttr.Title].lower()
        item[SongAttr.Queries] = []
        item[SongAttr.DJable] = newDJable
        item[SongAttr.SongVol] = int(songVol * 100) # as percentage (need int)
        item[SongAttr.Duration] = 0
        item[SongAttr.Qcount] = qcount

        # add to db
        self.table.put_item(Item = item)
        return True

    # remove song and all its queries
    def remove_song(self, vid):
        # delete song entry
        self.table.delete_item( Key = {"vID": vid} )

        # delete related history
        response = self.hist_table.scan(
            FilterExpression = Attr(HistAttr.vID).eq(vid),
        )
        items = response['Items'] # items: list of dict
        for item in items: 
            self.hist_table.delete_item(
                Key = {HistAttr.Time: item[HistAttr.Time]},
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
        self.db_update(vID, SongAttr.DJable, djable)


    # update duration info
    def update_duration(self, vID, duration):
        try:
            old_duration = self.db_get(vID, [SongAttr.Duration])[SongAttr.Duration]
        except DJDBException as e:
            # possible cause: delete from db and try to update
            error_log("Cannot update duration: " + e.message)
            return 

        print(f"Updating duration for {vID}: {duration}")
        if old_duration == 0 or old_duration != duration:
            self.db_update(vID, SongAttr.Duration, int(duration))


    def increment_qcount(self, vID):
        # update
        self.table.update_item(
            Key = { 'vID': vID },
            UpdateExpression = f'SET {SongAttr.Qcount} = {SongAttr.Qcount} + :val',
            ExpressionAttributeValues = { ':val': 1 }
        )

    def change_vol(self, vID, multiplier, setNewVol = None):
        if setNewVol is None:
            original_vol = self.db_get(vID, [SongAttr.SongVol])[SongAttr.SongVol]
            new_vol_percentage = int(float(original_vol * 100) * multiplier)
        else:
            new_vol_percentage = setNewVol
        # update
        self.table.update_item(
            Key = { 'vID': vID },
            UpdateExpression = f'SET {SongAttr.SongVol} = :val',
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
            return self.db_get(vID, [SongAttr.DJable])[SongAttr.DJable]
        except (DJDBException, ClientError) as e:
            error_log("cannot find djable: " + str(e.message if hasattr(e, 'message') else e))
            return None

    def find_duration(self, vID) -> int:
        try: 
            return self.db_get(vID, [SongAttr.Duration])[SongAttr.Duration]
        except DJDBException as e:
            return -1

    # query random song
    def find_rand_song(self, dj = True):

        if dj:
            response = self.table.scan(
                # FilterExpression=Attr('Title').contains('back')
                FilterExpression = Attr(SongAttr.DJable).eq(True),
                ProjectionExpression = f'{SongAttr.vID}, {SongAttr.SongVol}'
            )
        else:
            response = self.table.scan(
                ProjectionExpression = f'{SongAttr.vID}, {SongAttr.SongVol}'
            )
        items = response['Items'] # items: list of dict
        chosen = random.choice(items)
        return chosen[SongAttr.vID]


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
            ProjectionExpression=f'{SongAttr.vID}, {SongAttr.Queries}, {SongAttr.SongVol}'
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
                # bug: only with {'vID': 'QS'}
                if SongAttr.Queries not in item.keys():
                    self.remove_song(item[SongAttr.vID])
                    break

                for q in item[SongAttr.Queries]:
                    # ensure q in database is sorted
                    if not all(q[i] <= q[i+1] for i in range(len(q)-1)):
                        error_log("Unexpected behaviour: query not sorted \nqueries: " + str(q))
                        q.sort()

                    # match query
                    if q == query_words:
                        return self.db_get(item[SongAttr.vID])

            # no match
            return None


    def list_all_songs(self, dj = None, top = 10, needed_attr = None, return_song_type = list):

        scan_params = {}

        if dj is not None:
            scan_params["FilterExpression"] = Attr(SongAttr.DJable).eq(dj)
        
        # get all attr if not specified
        if needed_attr is not None and len(needed_attr) > 0:
            needed_attr_str = ", ".join( needed_attr )
            scan_params["ProjectionExpression"] = needed_attr_str

        response = self.table.scan(**scan_params)
        items = response['Items'] # items: list of dict

        if len(items) <= 0:
            # no songs at all
            return None
        else:
            topItems = items if top is None else items[:top]
            if return_song_type == list: # list of list
                return [ [ item[a] for a in needed_attr ] for item in topItems ]
            else: # list of dictionary
                return topItems
            

    # search songs by title and queries
    def search(self, search_term, top = 10):

        ############## search by title
        needed_attr = [ SongAttr.Title, SongAttr.vID, SongAttr.Queries, SongAttr.ChannelID]
        needed_attr_str = ", ".join(needed_attr)
        # IDEA: can implement multiple search terms?
        response = self.table.scan(
            FilterExpression = Attr(SongAttr.STitle).contains(search_term),
            ProjectionExpression = needed_attr_str
        )
        items = response['Items'] # items: list of dict

        if len(items) <= 0:
            # no songs matching search term at all
            title_searched_vids = []
            title_searched_songs = []
        else:
            title_searched_vids = [ item[SongAttr.vID] for item in items[:top] ]
            title_searched_songs = [ SongInfo(item[SongAttr.vID], item[SongAttr.Title], item[SongAttr.ChannelID], vid_to_thumbnail(item[SongAttr.vID])) for item in items[:top] ]
        
        ############## search by queries
        # scan all songs' queries
        response = self.table.scan(
            ProjectionExpression=f'{SongAttr.vID}, {SongAttr.Queries}, {SongAttr.Title}, {SongAttr.ChannelID}'
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
                if item[SongAttr.vID] in title_searched_vids:
                    continue
                
                if SongAttr.Queries in item:
                    for song_query in item[SongAttr.Queries]:
                        # match query
                        if any(word in song_query for word in query_words):
                            query_searched_songs.append( 
                                SongInfo(
                                    item[SongAttr.vID], 
                                    f"{item[SongAttr.Title]} [{'/'.join(song_query)}]", 
                                    item[SongAttr.ChannelID], 
                                    vid_to_thumbnail(item[SongAttr.vID])
                                )
                            )
                            break
                else:
                    print(f"no queries in item: ")
                    print(item)

            # no match
            return title_searched_songs + query_searched_songs

# ------------------ History ------------------- # 
    def add_history(self, vID, serverID, serverName, player):
        item = dict()
        item[HistAttr.Time] = str(get_time())
        item[HistAttr.vID] = vID
        item[HistAttr.ServerID] = serverID
        item[HistAttr.ServerName] = serverName
        item[HistAttr.Player] = player

        # add to db
        self.hist_table.put_item(Item = item)

    # get top history ranked by times played
    def get_hist_rank(self, serverID = None, dj = False, top = 20):
        filter = None
        if serverID: 
            filter = Attr(HistAttr.ServerID).eq(serverID) 
        if dj: 
            filter = (filter & Attr(HistAttr.Player).eq("DJ")) if filter else Attr(HistAttr.Player).eq("DJ")
        
        if filter: 
            response = self.hist_table.scan(
                FilterExpression = filter,
                ProjectionExpression = f'{HistAttr.vID}'
            )
        else: 
            response = self.hist_table.scan(
                ProjectionExpression = f'{HistAttr.vID}'
            )
        items = response['Items'] # items: list of dict
        
        if len(items) <= 0:
            # no DJ history at all
            return None
        else:
            rank = {}
            for item in items:
                item_vID = item[HistAttr.vID]
                if item_vID not in rank:
                    rank[item_vID] = 1
                else:
                    rank[item_vID] += 1
            print(rank)
                
            # (vID, song title, times played)
            ranked_DJ_history = [ (vID, self.db_get(vID, [SongAttr.Title])[SongAttr.Title], times ) for vID, times in sorted(rank.items(), key=lambda song: song[1], reverse=True) ]
            return ranked_DJ_history



    def get_hist_count(self, vID, serverID = None, dj = False):
        filter = Attr(HistAttr.vID).eq(vID)
        if serverID: filter = filter & Attr(HistAttr.ServerID).eq(serverID) 
        if dj: filter = filter & Attr(HistAttr.Player).eq("DJ")

        response = self.hist_table.scan(
            FilterExpression = filter
        )

        items = response['Items'] # items: list of dict
        
        return len(items)



if __name__ == "__main__":
    pass
