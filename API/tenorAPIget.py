import requests
from config import tenor_API_key
import random

# https://g.tenor.com/v1/search?q=hellopeter&key=SFH88A4GZYO2&limit=5


def get_tenor_gif(q, limit = 10):
    url = f"https://g.tenor.com/v1/search?q={q}&key={tenor_API_key}&limit={limit}"    
    params = {
        'Authorization': 'Bearer',
        'Accept': 'application/json'
    }

    r = requests.get(url = url, params = params) 
    results = r.json()['results']
    result = random.choice(results)
    gif = result['media'][0]['mediumgif']['url']
    return gif


if __name__ == "__main__":
    print(get_tenor_gif("hello peter"))