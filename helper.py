from options import banned_list, banned_reason, baseboost_list
import datetime


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


def error_log(message):
    now = datetime.datetime.now()
    with open(f"./error_log.log", "a") as f:
        pmessage = f"{now}: {message}"
        f.write(pmessage + "\n")