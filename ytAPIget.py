from SongInfo import SongInfo
import requests
import json
import os
from config import yt_API_key

def yt_search(q, use_vID = False):
    max_results = 5
    if use_vID:
        url = f"https://youtube.googleapis.com/youtube/v3/videos?part=snippet&id={q}&key={yt_API_key}"
        print("Searching video with vID:", q)
    else:
        url = f"https://youtube.googleapis.com/youtube/v3/search?part=snippet&maxResults={max_results}&q={q}&key={yt_API_key}"
        print("Searching video with query:", q)

    params = {
        'Authorization': 'Bearer',
        'Accept': 'application/json'
    }
    r = requests.get(url = url, params = params) 
    response = r.json() 

    items = response['items']
    for i in range(len(items)):
        item = items[i]
        kind = (item['kind'].split('#')[1]) if use_vID else (item['id']['kind'].split('#')[1])
        videoID = q if use_vID else item['id'][kind + 'Id']
        if kind == "video":
            return SongInfo(
                videoID, 
                item['snippet']['title'], 
                item['snippet']['channelId']
            )
    
    return None

if __name__ == "__main__":
    print(yt_search("test"))
    # 'https://youtube.googleapis.com/youtube/v3/playlistItems?playlistId='
