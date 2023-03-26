from const.SongInfo import SongInfo
import requests
import json
from const.config import yt_API_key
from const.DBFields import SongAttr
from const.helper import *

def get_yt_suggestions(vID, force_music = True):
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

def yt_search_all(q, n = 5, force_music = True):
    return yt_search(q, False, force_music = force_music, find_all = True, find_all_limit = n)

def yt_search_single(q, use_vID = False, force_music = True) -> SongInfo:
    return yt_search(q, use_vID, force_music=force_music)

def yt_search(q, use_vID = False, force_music = True, find_all = False, find_all_limit = 5):
    response = get_yt_results(q, use_vID = use_vID, force_music = force_music, max_results = find_all_limit)
    songs = []
    items = response['items']
    # response sanity check
    if use_vID and len(items) == 1: 
        eMess = f"Youtube API search responded >1 result when given vID{q}"
        error_log(eMess)
        raise Exception(eMess)

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
                if use_vID:
                    song.duration = ISO8601_to_duration( item['contentDetails']['duration'] )
                # return single song only
                return song
    
    if find_all: 
        # return list of matches
        return songs
    else:
        # in case of no songs found
        return None


def yt_search_suggestions(vID):
    response = get_yt_suggestions(vID)

    songs = []
    items = response['items']
    for i in range(len(items)):
        item = items[i]
        kind = item['id']['kind'].split('#')[1]
        videoID = item['id'][kind + 'Id']
        # if snippet does not exist, probably means the video is no longer available
        if kind == "video" and "snippet" in item.keys():
            # only add to list if not banned
            title = item['snippet']['title']
            s = SongInfo(
                videoID, 
                title, 
                item['snippet']['channelId'],
                item['snippet']['thumbnails']['default']['url']
            )
            print(s)
            songs.append(s)
    
    return songs


    # 'https://youtube.googleapis.com/youtube/v3/playlistItems?playlistId='
