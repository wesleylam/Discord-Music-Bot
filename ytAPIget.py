from urllib import response
from SongInfo import SongInfo
import requests
import json
import os
from config import yt_API_key

def get_yt_results(q, use_vID = False, force_music = True):
    print(f"Using Youtube API: {q}")

    max_results = 10
    if use_vID:
        url = f"https://youtube.googleapis.com/youtube/v3/videos?part=snippet&id={q}&key={yt_API_key}"
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
    with open('yt_search.json', 'w') as f:
        json.dump(response, f)

    return response

def yt_search_all(q, n = 5, force_music = True):
    # must not use vID (need multiple results)
    use_vID = False
    songs = []

    response = get_yt_results(q, force_music = force_music)
    items = response['items']
    
    for i in range(len(items)):
        item = items[i]
        kind = (item['kind'].split('#')[1]) if use_vID else (item['id']['kind'].split('#')[1])
        videoID = q if use_vID else item['id'][kind + 'Id']
        if kind == "video":
            songs.append(
                SongInfo(
                    videoID, 
                    item['snippet']['title'], 
                    item['snippet']['channelId'], 
                    item['snippet']['thumbnails']['default']['url'], 
                )
            )
        # only take the first n items
        if (i + 1) >= n: break
    
    return songs

def yt_search(q, use_vID = False):
    response = get_yt_results(q, use_vID)

    items = response['items']
    for i in range(len(items)):
        item = items[i]
        kind = (item['kind'].split('#')[1]) if use_vID else (item['id']['kind'].split('#')[1])
        videoID = q if use_vID else item['id'][kind + 'Id']
        if kind == "video":
            return SongInfo(
                videoID, 
                item['snippet']['title'], 
                item['snippet']['channelId'],
                item['snippet']['thumbnails']['default']['url'], 
            )
    
    return None

if __name__ == "__main__":
    print(yt_search("test"))
    # 'https://youtube.googleapis.com/youtube/v3/playlistItems?playlistId='
