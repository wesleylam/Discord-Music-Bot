import sqlite3
import json
from db.DJDBInterface import DJDBInterface

from exceptions.DJExceptions import DJDBException
from const.options import default_init_vol
from const.SongInfo import SongInfo
from const.DBFields import SongAttr
from const.helper import error_log, get_time, vid_to_thumbnail, chop_query

from const.config import sqlite_db_path

class SqliteDB(DJDBInterface):
    def __init__(self, db_path=sqlite_db_path) -> None:
        self.db_path = db_path
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS songs (
                vID       TEXT PRIMARY KEY,
                Title     TEXT NOT NULL,
                STitle    TEXT NOT NULL,
                ChannelID TEXT NOT NULL,
                DJable    INTEGER NOT NULL DEFAULT 1,
                SongVol   INTEGER NOT NULL DEFAULT 100,
                Duration  INTEGER NOT NULL DEFAULT 0,
                Qcount    INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS queries (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                vID    TEXT NOT NULL REFERENCES songs(vID) ON DELETE CASCADE,
                tokens TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS history (
                Time       TEXT PRIMARY KEY,
                vID        TEXT NOT NULL,
                ServerID   TEXT NOT NULL,
                ServerName TEXT NOT NULL,
                Player     TEXT NOT NULL
            );
        """)
        self.conn.commit()

    def _row_to_dict(self, row):
        d = dict(row)
        if SongAttr.DJable in d and d[SongAttr.DJable] is not None:
            d[SongAttr.DJable] = bool(d[SongAttr.DJable])
        return d

    def _fetch_queries(self, vID):
        cur = self.conn.execute("SELECT tokens FROM queries WHERE vID = ?", (vID,))
        return [json.loads(r["tokens"]) for r in cur.fetchall()]

    def dbItemToSongInfo(item) -> SongInfo:
        song = SongInfo(item[SongAttr.vID], item[SongAttr.Title], item[SongAttr.ChannelID])
        if SongAttr.SongVol in item and item[SongAttr.SongVol] is not None:
            item[SongAttr.SongVol] = item[SongAttr.SongVol] / 100
        for attr in SongAttr.get_all():
            if attr in item and item[attr] is not None:
                setattr(song, attr, item[attr])
        return song

    # ------------------------ PRIVATE: DB direct actions --------------------------- #

    def db_get(self, vID, get_attrs=None) -> SongInfo:
        need_queries = get_attrs is None or SongAttr.Queries in get_attrs

        if get_attrs is not None:
            cols = [a for a in get_attrs if a != SongAttr.Queries]
            for required in (SongAttr.vID, SongAttr.Title, SongAttr.ChannelID):
                if required not in cols:
                    cols.append(required)
        else:
            cols = [a for a in SongAttr.get_all() if a != SongAttr.Queries]

        cur = self.conn.execute(
            f"SELECT {', '.join(cols)} FROM songs WHERE vID = ?", (vID,)
        )
        row = cur.fetchone()
        if row is None:
            raise DJDBException(f"No item for vID: {vID}")

        item = self._row_to_dict(row)
        if need_queries:
            item[SongAttr.Queries] = self._fetch_queries(vID)

        return SqliteDB.dbItemToSongInfo(item)

    def db_scan(self, vID, get_attrs=None):
        pass

    def db_update(self, vID, attr, val):
        if attr == SongAttr.DJable:
            val = 1 if val else 0
        self.conn.execute(f"UPDATE songs SET {attr} = ? WHERE vID = ?", (val, vID))
        self.conn.commit()

    def match_query_action(self, query, match_return=None,
            q_match_break=False, action_after_q_match=lambda: None, action_after_v_match=lambda: None):

        assert match_return is not None and not q_match_break

        query_words = chop_query(query)
        cur = self.conn.execute("SELECT vID, tokens FROM queries")

        for row in cur.fetchall():
            q = json.loads(row["tokens"])
            if not all(q[i] <= q[i + 1] for i in range(len(q) - 1)):
                error_log("Unexpected behaviour: query not sorted\nqueries: " + str(q))
                q.sort()
            if q == query_words:
                action_after_q_match()
                if match_return:
                    return match_return
                if q_match_break:
                    break

        return None

    # ------------------------ PUBLIC: DB direct actions --------------------------- #

    def add_query(self, query, songInfo, song_exist=False):
        if type(songInfo) != SongInfo:
            songInfo = SongInfo(songInfo, "", "")
            song_exist = True

        if not song_exist:
            self.insert_song(songInfo)

        vID = songInfo.vID
        query_words = chop_query(query.lower())

        for q in self._fetch_queries(vID):
            if q == query_words:
                return  # duplicate

        self.conn.execute(
            "INSERT INTO queries (vID, tokens) VALUES (?, ?)",
            (vID, json.dumps(query_words))
        )
        self.conn.commit()

    def remove_query_binding(self, vID, query):
        cur = self.conn.execute(
            "SELECT id, tokens FROM queries WHERE vID = ?", (vID,)
        )
        rows = cur.fetchall()
        for row in rows:
            if json.loads(row["tokens"]) == query:
                self.conn.execute("DELETE FROM queries WHERE id = ?", (row["id"],))
                self.conn.commit()
                return
        raise DJDBException(f"No query ({query}) binded for video ({vID})")

    def insert_song(self, songInfo, qcount=0, songVol=default_init_vol, newDJable=True, query=None):
        song = self.find_song_match(songInfo.vID)
        if song:
            return song, False
        print(f"Song not found {songInfo.vID} in DB, inserting to DB")

        self.conn.execute(
            "INSERT INTO songs (vID, Title, STitle, ChannelID, DJable, SongVol, Duration, Qcount)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (
                songInfo.vID,
                songInfo.Title,
                songInfo.Title.lower(),
                songInfo.ChannelID,
                1 if newDJable else 0,
                int(songVol * 100),
                0,
                qcount,
            )
        )
        self.conn.commit()

        if query is not None:
            self.conn.execute(
                "INSERT INTO queries (vID, tokens) VALUES (?, ?)",
                (songInfo.vID, json.dumps(chop_query(query.lower())))
            )
            self.conn.commit()

        return self.db_get(songInfo.vID), True

    def remove_song(self, vid):
        # queries deleted via ON DELETE CASCADE
        self.conn.execute("DELETE FROM history WHERE vID = ?", (vid,))
        self.conn.execute("DELETE FROM songs WHERE vID = ?", (vid,))
        self.conn.commit()

    # --------------------------- Song info update ---------------------------- #

    def switch_djable(self, vID):
        old_djable = self.find_djable(vID)
        assert type(old_djable) == bool
        self.set_djable(vID, not old_djable)

    def set_djable(self, vID, djable=True):
        self.db_update(vID, SongAttr.DJable, djable)

    def update_duration(self, vID, duration):
        try:
            old_duration = self.db_get(vID, [SongAttr.Duration])[SongAttr.Duration]
        except DJDBException as e:
            error_log("Cannot update duration: " + (e.message if hasattr(e, "message") else str(e)))
            return
        print(f"Updating duration for {vID}: {duration}")
        if old_duration == 0 or old_duration != duration:
            self.db_update(vID, SongAttr.Duration, int(duration))

    def increment_qcount(self, vID):
        self.conn.execute("UPDATE songs SET Qcount = Qcount + 1 WHERE vID = ?", (vID,))
        self.conn.commit()

    def change_vol(self, vID, multiplier, setNewVol=None):
        if setNewVol is None:
            original_vol = self.db_get(vID, [SongAttr.SongVol])[SongAttr.SongVol]
            new_vol_percentage = int(float(original_vol * 100) * multiplier)
        else:
            new_vol_percentage = setNewVol
        self.conn.execute("UPDATE songs SET SongVol = ? WHERE vID = ?", (new_vol_percentage, vID))
        self.conn.commit()
        return new_vol_percentage

    def add_tag(self, vid, tag):
        pass

    def remove_tag(self):
        pass

    # ------------------------------- Queries ------------------------------- #

    def find_djable(self, vID) -> bool:
        try:
            return self.db_get(vID, [SongAttr.DJable])[SongAttr.DJable]
        except DJDBException as e:
            error_log("cannot find djable: " + (e.message if hasattr(e, "message") else str(e)))
            return None

    def find_duration(self, vID) -> int:
        try:
            return self.db_get(vID, [SongAttr.Duration])[SongAttr.Duration]
        except DJDBException:
            return -1

    def find_rand_song(self, dj=True):
        where = "WHERE DJable = 1" if dj else ""
        cur = self.conn.execute(f"SELECT vID FROM songs {where} ORDER BY RANDOM() LIMIT 1")
        row = cur.fetchone()
        return row["vID"] if row else None

    def find_rand_songs(self, n=10, dj=True):
        where = "WHERE DJable = 1" if dj else ""
        cur = self.conn.execute(
            f"SELECT vID, Title, ChannelID, Duration, SongVol FROM songs {where} ORDER BY RANDOM() LIMIT ?",
            (n,)
        )
        return [SqliteDB.dbItemToSongInfo(self._row_to_dict(row)) for row in cur.fetchall()]

    def find_song_match(self, vID):
        try:
            return self.db_get(vID)
        except DJDBException:
            return False

    def find_query_match(self, query):
        query_words = chop_query(query.lower())
        cur = self.conn.execute("SELECT vID, tokens FROM queries")
        for row in cur.fetchall():
            q = json.loads(row["tokens"])
            if not all(q[i] <= q[i + 1] for i in range(len(q) - 1)):
                error_log("Unexpected behaviour: query not sorted\nqueries: " + str(q))
                q.sort()
            if q == query_words:
                return self.db_get(row["vID"])

        return None

    def list_all_songs(self, dj=None, top=10, needed_attr=None, return_song_type=list):
        cols = ", ".join(needed_attr) if needed_attr else "*"
        where, params = ("WHERE DJable = ?", [1 if dj else 0]) if dj is not None else ("", [])
        limit = f"LIMIT {top}" if top is not None else ""

        cur = self.conn.execute(f"SELECT {cols} FROM songs {where} {limit}", params)
        rows = cur.fetchall()
        if not rows:
            return None

        if return_song_type == list:
            return [[row[a] for a in needed_attr] for row in rows]
        else:
            return [self._row_to_dict(row) for row in rows]

    def search(self, search_term, top=10):
        # search by title
        cur = self.conn.execute(
            "SELECT vID, Title, ChannelID FROM songs WHERE STitle LIKE ? LIMIT ?",
            (f"%{search_term.lower()}%", top)
        )
        title_rows = cur.fetchall()
        title_searched_vids = {r["vID"] for r in title_rows}
        title_searched_songs = [
            SongInfo(r["vID"], r["Title"], r["ChannelID"], vid_to_thumbnail(r["vID"]))
            for r in title_rows
        ]

        # search by queries
        query_words = chop_query(search_term.lower())
        cur = self.conn.execute(
            "SELECT q.vID, q.tokens, s.Title, s.ChannelID"
            " FROM queries q JOIN songs s ON q.vID = s.vID"
        )
        query_searched_songs = []
        seen = set(title_searched_vids)
        for row in cur.fetchall():
            if row["vID"] in seen:
                continue
            song_query = json.loads(row["tokens"])
            if any(word in song_query for word in query_words):
                seen.add(row["vID"])
                query_searched_songs.append(
                    SongInfo(
                        row["vID"],
                        f"{row['Title']} [{'/'.join(song_query)}]",
                        row["ChannelID"],
                        vid_to_thumbnail(row["vID"])
                    )
                )

        return title_searched_songs + query_searched_songs

    # ------------------ History ------------------- #

    def add_history(self, vID, serverID, serverName, player):
        self.conn.execute(
            "INSERT INTO history (Time, vID, ServerID, ServerName, Player) VALUES (?,?,?,?,?)",
            (str(get_time()), vID, serverID, serverName, player)
        )
        self.conn.commit()

    def get_hist_rank(self, serverID=None, dj=False, top=20):
        where_parts, params = [], []
        if serverID:
            where_parts.append("ServerID = ?")
            params.append(serverID)
        if dj:
            where_parts.append("Player = 'DJ'")
        where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

        cur = self.conn.execute(
            f"SELECT vID, COUNT(*) as cnt FROM history {where}"
            f" GROUP BY vID ORDER BY cnt DESC LIMIT ?",
            params + [top]
        )
        rows = cur.fetchall()
        if not rows:
            return None

        result = []
        for row in rows:
            try:
                title = self.db_get(row["vID"], [SongAttr.Title])[SongAttr.Title]
            except DJDBException:
                title = "(unknown)"
            result.append((row["vID"], title, row["cnt"]))
        print(result)
        return result

    def get_hist_count(self, vID, serverID=None, dj=False):
        where_parts, params = ["vID = ?"], [vID]
        if serverID:
            where_parts.append("ServerID = ?")
            params.append(serverID)
        if dj:
            where_parts.append("Player = 'DJ'")
        where = "WHERE " + " AND ".join(where_parts)

        cur = self.conn.execute(f"SELECT COUNT(*) as cnt FROM history {where}", params)
        return cur.fetchone()["cnt"]


if __name__ == "__main__":
    a = SqliteDB()
    a.connect()
    a.db_get("", [SongAttr.Duration])
    pass
