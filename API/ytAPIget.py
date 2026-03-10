from const.SongInfo import SongInfo
import requests
import json
import yt_dlp
from const.config import yt_API_key
from const.DBFields import SongAttr
from const.helper import *

def get_yt_suggestions(vID, force_music = True):
    return None
    # TODO: YT KILLED SUGGESTIONS
    categoryID_get = f"&videoCategoryId={10}"
    url = f"https://youtube.googleapis.com/youtube/v3/search?part=snippet&relatedToVideoId={vID}&type=video&key={yt_API_key}"
    if force_music: url += categoryID_get
    
    params = {
        'Authorization': 'Bearer',
        'Accept': 'application/json'
    }
    r = requests.get(url = url, params = params) 
    return r.json() 

def get_yt_results(q, use_vID = False, force_music = True, max_results = 10):
    print(f"Using Youtube API: {q}")

    if use_vID:
        url = f"https://youtube.googleapis.com/youtube/v3/videos?part=snippet%2CcontentDetails&id={q}&key={yt_API_key}"
        print("Searching video with vID:", q)
    else:
        categoryID_get = f"&videoCategoryId={10}"
        url = f"https://youtube.googleapis.com/youtube/v3/search?part=snippet&maxResults={max_results}&q={q}&type=video&key={yt_API_key}"
        if force_music:
            url += categoryID_get

        print("Searching video with query:", q)

    params = {
        'Authorization': 'Bearer',
        'Accept': 'application/json'
    }
    r = requests.get(url = url, params = params) 
    response = r.json() 
    with open('./logs/yt_search.json', 'w') as f:
        json.dump(response, f)

    return response

def yt_search_all(q, n = 5, force_music = True) -> list[SongInfo]:
    return yt_search(q, False, force_music = force_music, find_all = True, find_all_limit = n)

def yt_search_single(q, use_vID = False, force_music = True) -> SongInfo | None:
    return yt_search(q, use_vID, force_music=force_music)

def yt_search(q, use_vID = False, force_music = True, find_all = False, find_all_limit = 5):
    response = get_yt_results(q, use_vID = use_vID, force_music = force_music, max_results = find_all_limit)
    songs = []
    items = response['items']
    # response sanity check
    # if use_vID and len(items) == 1: 
    #     eMess = f"Youtube API search responded >1 result when given vID{q}"
    #     error_log(eMess)
    #     raise Exception(eMess)

    for i in range(len(items)):
        item = items[i]
        kind = (item['kind'].split('#')[1]) if use_vID else (item['id']['kind'].split('#')[1])
        videoID = q if use_vID else item['id'][kind + 'Id']
        # if snippet does not exist, probably means the video is no longer available
        if kind == "video" and "snippet" in item.keys():
            song = SongInfo(
                videoID, 
                item['snippet']['title'], 
                item['snippet']['channelId'], 
                item['snippet']['thumbnails']['default']['url'], 
            )
            if find_all:
                songs.append(song)
            else:
                if use_vID or ('contentDetails' in item and 'duration' in item['contentDetails']):
                    song.duration = ISO8601_to_duration( item['contentDetails']['duration'] )
                # return single song only
                return song
    
    if find_all: 
        # return list of matches
        return songs
    else:
        # in case of no songs found
        return None


def yt_search_suggestions(songInfo: SongInfo) -> list[SongInfo]:
    # --- New Method: Use yt-dlp to find YouTube's "Mix" playlist ---
    vID = getattr(songInfo, SongAttr.vID)
    # Construct a URL that forces YouTube to generate a "Mix" playlist (Radio).
    url = f"https://www.youtube.com/watch?v={vID}&list=RD{vID}"
    ydl_opts = {
        'extract_flat': 'in_playlist', # Fast, gets playlist entries without processing them
        'quiet': True,
        'noplaylist': False, # We explicitly want the playlist, so ensure this is not True.
    }

    try:
        print(f"Attempting to extract suggestions using yt-dlp for video {vID} with URL: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)
            print(f"yt-dlp extracted data for {vID}: {data.get('title', 'No title')} with {len(data.get('entries', []))} entries")

        if 'entries' in data and data['entries']:
            suggestions = []
            # The first entry is the song itself. We take the next 10.
            for entry in data['entries'][1:11]: 
                if entry and entry.get('id') and entry.get('title'):
                    song = SongInfo(
                        entry.get('id'),
                        entry.get('title'),
                        entry.get('channel_id'),
                        entry.get('thumbnail'),
                    )
                    if entry.get('duration'):
                        song.duration = int(entry.get('duration'))
                    suggestions.append(song)
            
            if suggestions:
                print(f"Found {len(suggestions)} suggestions from yt-dlp mix for {vID}")
                return suggestions
    except Exception as e:
        print(f"yt-dlp suggestion extraction failed for {vID}: {e}")
        # Fallback to the old method if yt-dlp fails
        
    # --- Fallback to existing method if yt-dlp doesn't yield a mix ---
    print(f"yt-dlp did not find a mix, falling back to API search for {vID}")
    if songInfo:
        # Improve the fallback search query to get more variety
        query = f"{songInfo.Title} radio"
        results = yt_search_all(query, n=10, force_music=True)
        if results:
            # Filter out the original song and any potential duplicates
            seen_vids = {songInfo.vID}
            unique_results = []
            for s in results:
                if s.vID not in seen_vids:
                    unique_results.append(s)
                    seen_vids.add(s.vID)
            return unique_results
            
    return []


    # 'https://youtube.googleapis.com/youtube/v3/playlistItems?playlistId='
