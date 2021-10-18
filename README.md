# Discord mini music bot
Built using Python 3.7.7

## Required modules
- discord.py
- discord_components
- discord.py[voice] (pycparser, cffi, six, PyNaCl)
- youtube-dl
- ffmpeg
- opus

## Packages install
# discord
async-timeout, chardet, typing-extensions, multidict, attrs, idna, yarl, aiohttp, discord.py, discord
# discord.py[voice]
six, pycparser, cffi, PyNaCl
# discord_components
# youtube-dl
# ffmpeg
# requests
charset-normalizer, urllib3, certifi, requests

## Configurations
- `config.py`: access keys and file directories
    - `TOKEN`: Your Discord bot access token. Create through [Discord Developer Portal] (https://discord.com/developers/applications)
    - `yt_API_key`: Your Youtube API key, for video/song search
    - `opus_dir`: opus module library path, used with ffmpeg to play audio
    - `mysql_*`: mysql database options for storing songs info
- `options.py`: (Optional, defaulted) Options for ytdl, ffmpeg and other default in-app settings. Change to customise your settings.
    - `cookiefile` options within ytdl options can be added to access premium content
