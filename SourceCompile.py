from helper import *
from DJExceptions import *
from DJDynamoDB import DJDB
from API.ytAPIget import yt_search, yt_search_all
from YTDLSource import YTDLSource, StaticSource
from youtube_dl.utils import DownloadError
import youtube_dl
from DBFields import SongAttr
from options import ytdl_format_options
import discord

from DJExceptions import DJDBException, DJBannedException, DJSongNotFoundException
from YTDLException import YTDLException


# static class
class SourceCompile():
    
    djdb = None
    # initialise ytdl from youtube_dl library
    ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
    
    
    def getSource(args, newDJable = True, loud = False, baseboost = False):
        # 1. parse and search
        songInfo = SourceCompile.process_song_input(args, newDJable = newDJable)
        
        # DB: INC Qcount
        SourceCompile.djdb.increment_qcount(getattr(songInfo, SongAttr.vID))

        # 2. compile
        source = SourceCompile.scp_compile(getattr(songInfo, SongAttr.vID), 
                                           getattr(songInfo, SongAttr.SongVol), 
                                           loud = loud, baseboost = baseboost)
        return source, songInfo
        
    
    def process_song_input(args, DBonly = False, newDJable = True):
        '''
        Process song input (from link or search terms)
        return vid ONLY if passed url
        '''
        args = list(args)
        if len(args) <= 0 or "".join(args) == "": # throw error when no arg given (alternative: play default source)
            raise DJSongNotFoundException("No url or search term given")
            # source = StaticSource(discord.FFmpegPCMAudio(source=default_play_dir), volume=default_init_vol)
            # source.url = ''

        url = args[0]
        print("SCP URL " + url)
        ### scp: 1. search | 2. compile | 3. play 
        # 1. search -> get url
        if is_ytlink(url): 
            # case 1: url
            vid = yturl_to_vid(url)
            # insert to db if not in db
            match = SourceCompile.djdb.find_song_match(vid)
            # return match if found
            if match: return match
            
            # no match but DBonly 
            if DBonly: raise DJSongNotFoundException(f"No match found for {vid} in Database (Specified not to search from yt)")

            # return match from search            
            return SourceCompile.yt_search_and_insert(vid, use_vID = True, newDJable = newDJable)
            
        # case 2: find in query db (or query yt if none)
        return SourceCompile.scp_search(args, DBonly = DBonly, newDJable = newDJable)

    def scp_search(s, DBonly = False, newDJable = True):
        '''scp step 1: search (in db or youtube)'''
        # search for url in youtube API
        search_term = (" ".join(s)).lower()
        
        # fetch vid from db
        match = SourceCompile.djdb.find_query_match(search_term)
        if match:
            # insert to db if not in db (Depreciated, safety catch)
            if not SourceCompile.djdb.find_song_match(getattr(match, SongAttr.vID)):
                error_log(f"(Unexpected behaviour) Query found but song not in DB: {search_term} -> {vid}")
                SourceCompile.yt_search_and_insert(getattr(match, SongAttr.vID), use_vID = True, newDJable = newDJable)
            return match
                    
        # no DB match entry  
        if DBonly: raise DJDBException(f"No item found for {search_term} in Database (specified not to search in yt)")

        # get info by searching youtube API
        info = SourceCompile.yt_search_and_insert(search_term, insert_after = False, newDJable = newDJable)
        # add query to db
        SourceCompile.djdb.add_query(search_term, info)
        return info # songInfo
        
    def yt_search_and_insert(search_term, use_vID = False, insert_after = True, newDJable = True):
        '''
        [ Helper function for scp_search ]
        youtube search and insert to db
        return: searched song info
        '''
        # SongInfo
        info = yt_search(search_term, use_vID=use_vID)
        # no result from youtube api (by vid)
        if not info: 
            if use_vID: raise DJSongNotFoundException(f"No video found: {vid_to_url(search_term)}")
            else: raise DJSongNotFoundException(f"Nothing found in video form: {search_term}")

        if insert_after: 
            inserted = SourceCompile.djdb.insert_song(info, newDJable = newDJable)
            info.inserted = inserted
        return info


    def scp_compile(vid, vol, loud = False, stream = True, baseboost = False):
        '''
        scp step 2: compile youtube source
        compile YTDLSource (audio source object) from youtube url
        return: source object
        '''

        url = "https://youtube.com/watch?v=" + vid

        try:
            # search yt url
            # data = await self.bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
            data = SourceCompile.ytdl.extract_info(url, download=not stream)
        except DownloadError as e: # youtube dl download error
            SourceCompile.djdb.remove_song(vid)
            raise YTDLException(f"Unable to download {url}, removed ({str(e)})")

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else SourceCompile.ytdl.prepare_filename(data)
        # options for baseboosted or normal
        if baseboost or need_baseboost(data.get('title')):
            ffmpeg_final_options = ffmpeg_options.copy()
            os = "options"
            ffmpeg_final_options[os] = ffmpeg_final_options[os] + " -af bass=g=50"
        else:
            ffmpeg_final_options = ffmpeg_options.copy()

        # Create source object
        if loud:
            vol = vol * loud_vol_factor
        print(vol)
        source = YTDLSource(discord.FFmpegPCMAudio(filename, **ffmpeg_final_options), data=data, volume = vol)
        source.url = url
        source.vid = vid
        source.duration = SourceCompile.djdb.find_duration(vid)

        # check valid song
        banned_reason = is_banned(source.title)
        if banned_reason:
            raise DJBannedException(f"{source.title} banned: {banned_reason}")
        else:
            return source
