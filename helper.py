from options import banned_list, banned_reason, baseboost_list, default_error_log
import datetime
import traceback
import pytz

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
    reason = banned_reason
    for i in banned_list:
        if i.lower() in title: return reason
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
    sec = int((sec % 60) + 0.5)
    s = f"{min}:"
    if sec < 10: s += "0"
    s += f"{sec}"
    return s


# ----------------------------------------- ERROR LOGGING -------------------------------------------- # 

def error_log(err_m):
    now = get_time()
    with open(default_error_log, "a") as f:
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