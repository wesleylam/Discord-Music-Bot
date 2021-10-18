# for ytdl settings
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False, 
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0', # bind to ipv4 since ipv6 addresses cause issues sometimes
    # add cookie file to access premium links
    # 'cookiefile': '', 
}
ffmpeg_options = {
    "options": "-vn -report",
    # allow reconnect when streaming drops
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
}
ffmpeg_error_log = "./ffreport.log"

# default volume
default_init_vol = 0.1

# banned keyword list and reasons
banned_list = []
banned_reason = "This song is banned"

# baseboost songs keywords
baseboost_list = []




