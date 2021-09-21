from SongInfo import SongInfo
import requests
import json
import os
from config import yt_API_key

def yt_search(q):
    max_results = 5
    url = f"https://youtube.googleapis.com/youtube/v3/search?part=snippet&maxResults={max_results}&q={q}&key={yt_API_key}"
    params = {
        'Authorization': 'Bearer',
        'Accept': 'application/json'
    }
    r = requests.get(url = url, params = params) 
    response = r.json() 

    items = response['items']
    for i in range(len(items)):
        item = items[i]
        kind = item['id']['kind'].split('#')[1]
        if kind == "video":
            return SongInfo(
                item['id'][kind + 'Id'], 
                item['snippet']['title'], 
                item['snippet']['channelId']
            )
    
    return None


if __name__ == "__main__":
    print(yt_search("test"))
    # 'https://youtube.googleapis.com/youtube/v3/playlistItems?playlistId='
