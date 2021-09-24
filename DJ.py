from SongInfo import SongInfo
import discord
from discord.ext import commands
from discord_components import ComponentsBot, component

from VcControl import VcControl
from ytAPIget import yt_search
import youtube_dl
from YTDLSource import YTDLSource, StaticSource

from helper import *
from config import *
from options import ytdl_format_options, ffmpeg_options
from DJDB import DJDB


class DJ(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vcControls = {} # guild.id: vcControl object
        self.djdb = DJDB(mysql_host, mysql_user, mysql_password, mysql_db_name)


    # ---------------------------- MESSAGING --------------------------- # 
    async def notify(self, ctx, message, del_sec = 10):
        m = await ctx.send(message)

        # delete the message if needed
        if del_sec: 
            assert type(del_sec) == int
            await m.delete(delay = del_sec)

    # -------------------------------------------------------------------------------------------- # 
    # ------------------------------------- VOICE CONTROL ---------------------------------------- # 
    # -------------------------------------------------------------------------------------------- # 
    # -------------------- Join voice channel --------------------
    @commands.command()
    async def join(self, ctx):
        if ctx.voice_client is None:
            vc = get_channel_to_join(ctx)
            self.djdb.connect()
            await vc.connect()
            # create new playlist instance, send current channel for further messaging
            self.vcControls[ctx.guild.id] = VcControl(ctx.channel, self)
        else: 
            n = ctx.voice_client.channel.name
            await self.notify(ctx, f"I am in voice channel: {n}", del_sec=60)

    # -------------------- Leave voice channel --------------------
    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client is None:
            raise Exception("I am not in any voice channel, use join command instead")
        else: 
            await ctx.voice_client.disconnect()
            
    # -------------------- play from youtube url / default if no url -------------------- # 
    # COMMAND: dj
    @commands.command()
    async def dj(self, ctx, type = None):
        vc = ctx.voice_client
        if vc is None:
            await self.join(ctx)
            vc = ctx.voice_client
        self.vcControls[ctx.guild.id].dj = True
        await self.vcControls[ctx.guild.id].next(vc)

    # COMMAND: p
    @commands.command()
    async def p(self, ctx, *kwords):
        await self.play(ctx, *kwords)
    # COMMAND: play
    @commands.command()
    async def play(self, ctx, *kwords):
        await self.search_compile_play(ctx, *kwords)

    # compile YTDLSource (audio source object) from youtube url
    # return: source object
    async def compile_yt_source(self, vid, stream = True):
        url = "https://youtube.com/watch?v=" + vid

        try:
            # search yt url
            data = await self.bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        except Exception as e:
            self.djdb.remove_song(vid)
            raise Exception(f"Removed: {url} (URL not found)")

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        # options for baseboosted or normal
        if need_baseboost(data.get('title')):
            ffmpeg_final_options = ffmpeg_options.copy()
            os = "options"
            ffmpeg_final_options[os] = ffmpeg_final_options[os] + " -af bass=g=50"
        else:
            ffmpeg_final_options = ffmpeg_options.copy()
        source = YTDLSource(discord.FFmpegPCMAudio(filename, **ffmpeg_final_options), data=data)
        source.url = url
        source.vid = vid

        # check valid song
        banned_reason = is_banned(source.title)
        if banned_reason:
            raise Exception(banned_reason)
        else:
            return source

    # search url, compile source and play audio
    async def search_compile_play(self, ctx, *kwords):
        s = list(kwords)
        if len(s) <= 0 or "".join(s) == "": # throw error when no arg given (alternative: play default source)
            raise Exception("No url or search term given")
            # # play default when no url
            # source = StaticSource(discord.FFmpegPCMAudio(source=default_play_dir), volume=default_init_vol)
            # source.url = ''
            # await self.play_in_vc(ctx)
        else:    
            # get url
            if ("youtu.be" in s[0] or "youtube.com" in s[0]):
                url = s[0]
                # get vid from url
                vid = yturl_to_vid(url)
                if not self.djdb.find_song_match(vid):
                    info = yt_search(vid, use_vID=True)
                    self.djdb.insert_song(info)
            else:
                # search for url in youtube API
                search_term = (" ".join(s)).lower()
                await self.notify(ctx, f"Searching: {search_term}")
                
                # fetch vid from either db or youtube api search
                match = self.djdb.find_query_match(search_term)
                if match:
                    vid = match
                    if not self.djdb.find_song_match(vid): # no entry in db
                        info = yt_search(vid, use_vID=True)
                        self.djdb.insert_song(info)
                else:                    
                    info = yt_search(search_term)
                    if not info: raise Exception("Nothing found in video form")
                    vid = info.vID
                    # add query to db
                    self.djdb.add_query(search_term, info)

            # DB: INC Qcount

            # compile
            source = await self.compile_yt_source(vid)
            # play
            await self.play_in_vc(ctx, source)

    # send source to playlist and play in vc
    async def play_in_vc(self, ctx, source):
        vc = ctx.voice_client
        if vc is None:
            await self.join(ctx)
            vc = ctx.voice_client
        await self.vcControls[ctx.guild.id].add(vc, source)

    # COMMAND: nowplaying
    @commands.command()
    async def nowplaying(self, ctx):
        await self.vcControls[ctx.guild.id].display_nowplaying(ctx)

    # COMMAND: list
    @commands.command()
    async def list(self, ctx):
        await self.vcControls[ctx.guild.id].list(ctx)

    # COMMAND: skip
    @commands.command()
    async def skip(self, ctx):
        await self.vcControls[ctx.guild.id].skip(ctx.voice_client)

    # COMMAND: remove
    @commands.command()
    async def remove(self, ctx, *args):
        k = " ".join(args)
        await self.vcControls[ctx.guild.id].remove_track(ctx.voice_client, k)

    # COMMAND: clear
    @commands.command()
    async def clear(self, ctx):
        await self.vcControls[ctx.guild.id].clear()

    # COMMAND: stop
    @commands.command()
    async def stop(self, ctx):
        await self.vcControls[ctx.guild.id].stop(ctx.voice_client)

    # COMMAND: vup (doubled)
    @commands.command()
    async def vup(self, ctx, n=2):
        await self.vset(ctx, n)

    # COMMAND: vdown (half)
    @commands.command()
    async def vdown(self, ctx, n=0.5):
        await self.vset(ctx, n)

    # volume set
    async def vset(self, ctx, volume):
        vc = ctx.voice_client
        if not vc: raise Exception("I am not in any voice channel")

        vc.source = discord.PCMVolumeTransformer(vc.source)
        vc.source.volume = float(volume)
        await self.notify(ctx, f"Volume multiply by {ctx.voice_client.source.volume}")



    # -------------------------------------------------------------------------------------------- # 
    # ------------------------------------- DB MODIFICATION --------------------------------------- # 
    # -------------------------------------------------------------------------------------------- # 
    # COMMAND: bind
    @commands.command()
    async def bind(self, ctx, *args):
        try:
            vid = yturl_to_vid(args[-1])
            q = " ".join(args[:-1])
        except: 
            vid = None
            q = " ".join(args)

        if vid:
            # actual binding when url provided
            if not self.djdb.find_song_match(vid):
                info = yt_search(vid, use_vID = True)
            else: # song exist
                info = vid

            self.djdb.add_query(q, info)
            await self.notify(ctx, f"Added binding \n{q} -> https://youtu.be/{vID}", del_sec=None)
        else:
            # query binding if url not provided
            vID = self.djdb.find_query_match(q)
            if vID:
                await self.notify(ctx, f"{q} is bind to https://youtu.be/{vID}", del_sec=None)
            else: 
                await self.notify(ctx, f"{q} is not bind to anything", del_sec=None)

    # COMMAND: tag
    # tag "link" "tag"
    @commands.command()
    async def tag(self, ctx, *args):
        pass

    # -------------------------------------------------------------------------------------------- # 
    # ------------------------------------- EVENT HANDLING --------------------------------------- # 
    # -------------------------------------------------------------------------------------------- # 
    
    # handle all (command) error
    # COMMENT TO ENABLE DETAILED ERROR MESSAGE ON CONSOLE (WHEN DEBUG)
    @commands.Cog.listener()
    async def on_command_error(self, ctx, e):
        # print traceback on console
        print(e)
        # send error message to text channel
        await self.notify(ctx, e.original, del_sec=None)



if __name__ == "__main__":
    # for voice client to work: you need opus and ffmpeg
    discord.opus.load_opus(opus_dir)

    # initialise ytdl from youtube_dl library
    ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

    intents = discord.Intents.default()
    intents.members = True
    client = ComponentsBot(command_prefix="=", case_insensitive=True, 
                    description='DJ', intents=intents)

    @client.event
    async def on_ready():
        print(f'Logged in as {client.user} (ID: {client.user.id})')
        print('------')

    client.add_cog(DJ(client))
    client.run(TOKEN)