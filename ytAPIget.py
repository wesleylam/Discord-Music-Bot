import requests
import json
import os
from config import res_store_dir, yt_API_key

def yt_search(q):
    need_search = True

    dirs = os.listdir(res_store_dir)
    for fname in dirs:
        if (q + '.json') == fname:
            with open(f'{res_store_dir}/{fname}') as f:
                response = json.load(f)
            need_search = False

    if need_search:
        max_results = 5
        url = f"https://youtube.googleapis.com/youtube/v3/search?part=snippet&maxResults={max_results}&q={q}&key={yt_API_key}"
        params = {
            'Authorization': 'Bearer',
            'Accept': 'application/json'
        }
        r = requests.get(url = url, params = params) 
        response = r.json() 

        res_json_fname = f'{res_store_dir}/{q}.json'
        with open(res_json_fname, 'w') as json_file:
            json.dump(response, json_file)

    items = response['items']
    for i in range(len(items)):
        item = items[i]
        kind = item['id']['kind'].split('#')[1]
        if kind == "video":
            # item['snippet']['title'], 
            return item['id'][kind + 'Id']
    
    return None


if __name__ == "__main__":
    print(yt_search("hunter king ost"))
