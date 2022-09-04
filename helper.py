from operator import truediv
from options import *
import datetime
import traceback
import pytz
import random
import re

# debug printing function 
def help(o):
    print("HELP")
    print("dir:", dir(o))
    print("type:", type(o))
    print(f"str: '{o}'")

# determine is the song banned using its title: return reason or None
def is_banned(title: str):
    # IDEA: sorted list to reduce searching in half
    # MORE OPTIMISED: refer to searching complexity
    title = title.lower()
    for (reason, keywords) in banned_list.items():
        for key in keywords:
            words = re.findall(f"[a-zA-Z]*", title)
            for word in words:
                if word == key.lower():
                    return reason
    return None
    
# determine is the song need to be trolled using its title: return bool
def need_baseboost(title: str) -> bool:
    title = title.lower()
    for i in baseboost_list:
        if i.lower() in title: return True
    return False

# get the voice channel to join by author's current channel, otherwise
# find the most populated channel: return discord.voice_channel
def get_channel_to_join(ctx):
    vcs = ctx.guild.voice_channels
    assert len(vcs) > 0
    max_member, max_member_c = 0, None
    for i, c in enumerate(vcs):
        ms = c.members
        ms_count = len(ms)
        if ms_count > max_member: max_member_c = c
        if ctx.author in ms:
            return c

    return max_member_c if max_member_c else vcs[0]


# ----------------------------------------- PARSING INPUT ----------------------------------------------- # 

def is_ytlink(link):
    '''determine if input is a youtube link'''
    return ("youtu.be" in link or "youtube.com" in link)
    

def yturl_to_vid(url):
    if "watch?" in url:
        GET_req = url.split("watch?")[-1].split("&")
        for r in GET_req:
            if r[0] == 'v': vid = r[2:]
            break
        if not vid: raise Exception("No video ID in URL")
        return vid
    elif "youtu.be" in url:
        vid = url.split("/")[-1]
        return vid
    else: raise Exception("Not youtube link")

def vid_to_url(vid):
    return f"https://youtu.be/{vid}"

def vid_to_thumbnail(vid):
    return f"https://i.ytimg.com/vi/{vid}/default.jpg"

def rand_color():
    return random.randint(0, 16**6)

def parse_patch_note_log(limit = 5):
    notes = {} # date: commit 
    with open(patch_note_log) as f:
        for line in f.readlines():
            tokens = line.split('\t')
            if len(tokens) > 1 and ("ignore" not in tokens[1]):
                notes[tokens[0]] = tokens[1]
                if len(notes) >= limit:
                    break

    return notes


# ----------------------------------------- TIME RELATED ----------------------------------------------- # 
def get_time():
    tz = pytz.timezone('Australia/Melbourne')
    return datetime.datetime.now(tz=tz)

def readable_time(sec):
    s = ""
    min = int(sec / 60)
    sec = sec % 60
    if min > 0: 
        s += f"{min} min"
        if min > 1: s += "s"
        s += " "
        
    s += f"{sec} sec"
    if sec > 1: s += "s"
    return s

def readable_duration(sec):
    min = int(sec / 60)
    sec = int(int(sec % 60) + 0.5)
    s = f"{min}:"
    if sec < 10: s += "0"
    s += f"{sec}"
    return s

def ISO8601_to_duration(ISO8601 : str) -> int:
    '''Convert ISO8601 time string (used in youtube duration) into duration in seconds, eg: PT1H15M33S => 933'''
    if 'T' in ISO8601:
        tokens = ISO8601.split('T')
    else:
        tokens = ISO8601.split('P')
    p, temp = tokens[0], tokens[1]
    hour, min, sec = 0,0,0
    if 'H' in temp:
        tokens = temp.split('H')
        hour, temp = int(tokens[0]), tokens[1]
    if 'M' in temp:
        tokens = temp.split('M')
        min, temp = int(tokens[0]), tokens[1]
    if 'S' in temp:
        tokens = temp.split('S')
        sec, temp = int(tokens[0]), tokens[1]

    return hour * 60 * 60 + min * 60 + sec


def song_is_live(title):
    title = title.lower()
    tokens = title.split()
    # re.search(".*live.*", title)
    if ("(live)" in title) or ("live!" in title) or ("live" in tokens) or ("concert" in tokens):
        return True 
    return False


# ----------------------------------------- ERROR LOGGING -------------------------------------------- # 

def error_log(err_m):
    '''Simply log the error to error log'''
    now = get_time()
    print("Logging error: " + err_m)
    with open(default_error_log, "a", encoding="utf-8") as f:
        m = f"{now}: {err_m}\n"
        f.write(m)

def error_log_e(e):
    '''Reproduce error and traceback (will not throw error)'''
    now = get_time()
    with open(default_error_log, "a") as f:
        m = f"{now}:"
        f.write(m)
        try:
            raise e
        except:
            traceback.print_exc(file=f)


def play_after_handler(e, set_error):
    # read ffmpeg error
    ffmpeg_err_m = None
    with open(ffmpeg_error_log, "r") as f:
        # get to last line
        for line in f.readlines():
            pass
        # check for possible error
        if "403 Forbidden" in line[-50:]:
            ffmpeg_err_m = "Access denied"
        elif "Broken pipe" in line[-50:]:
            ffmpeg_err_m = "Disrupted"

    if ffmpeg_err_m:
        message = f"ffmpeg error: {line}"
        error_log(message)
        print(message)
        set_error(f"Error in streaming ({ffmpeg_err_m})", ffmpeg_err_m)
    
    # read standard playing error
    if e: 
        error_log_e(e)
        print(f"Error occured while playing, {e}")
        set_error(f"Error occured while playing", "Error")
    print("song ended w/o error")

if __name__ == "__main__":
    a = ISO8601_to_duration('PT15M33S')
    print(a)