# Discord mini music bot
Built using Python 3.7.7

## Required modules
- discord.py
- discord_components
- discord.py[voice] (pycparser, cffi, six, PyNaCl)
- youtube-dl
- ffmpeg
- opus

## Configurations
- `config.py`: access keys and file directories
    - `TOKEN`: Your Discord bot access token. Create through [Discord Developer Portal] (https://discord.com/developers/applications)
    - `yt_API_key`: Your Youtube API key, for video/song search
    - `opus_dir`: opus module library path, used with ffmpeg to play audio
- `options.py`: (Optional, defaulted) Options for ytdl, ffmpeg and other default in-app settings. Change to customise your settings.
    - `cookiefile` options within ytdl options can be added to access premium content
