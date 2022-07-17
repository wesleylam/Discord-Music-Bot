# Discord mini music bot
Built using Python 3.7.7 with AWS DynamoDB

## Required modules
- boto3
- discord.py
- discord_components
- discord.py[voice] (pycparser, cffi, six, PyNaCl)
- youtube-dl
- ffmpeg
- opus (Not required in windows environment: https://discordpy.readthedocs.io/en/latest/api.html#discord.opus.load_opus)
- pytz (timezone)

## Packages install
- discord (async-timeout, chardet, typing-extensions, multidict, attrs, idna, yarl, aiohttp, discord.py, discord)
- discord.py[voice] (six, pycparser, cffi, PyNaCl)
- discord_components
- youtube-dl
- ffmpeg
- pytz
- requests (charset-normalizer, urllib3, certifi, requests)
- boto3 (jmespath, botocore, s3transfer, boto3)

## Configurations
- Configure AWS connection `aws configure`
    - Require key pair (ID, secret key)
- `config.py`: access keys and file directories
    - `TOKEN`: Your Discord bot access token. Create through [Discord Developer Portal] (https://discord.com/developers/applications)
    - `yt_API_key`: Your Youtube API key, for video/song search
    - `opus_dir`: opus module library path, used with ffmpeg to play audio
    - `dynamodb_table`: table name of dynamodb for song info
    - `dynamodb_hist_table`: table name of dynamodb for played histories
- `options.py`: (Optional, defaulted) Options for ytdl, ffmpeg and other default in-app settings. Change to customise your settings.
    - `cookiefile` options within ytdl options can be added to access premium content
