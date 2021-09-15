import discord
from discord.ext import commands
from discord_components import ComponentsBot

from VcControl import VcControl
from ytAPIget import yt_search
import youtube_dl
from YTDLSource import YTDLSource, StaticSource

from helper import *
from config import *
from options import ytdl_format_options, ffmpeg_options


class DJ(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vcControls = {} # guild.id: vcControl object

    # -------------------- Join voice channel --------------------
    @commands.command()
    async def join(self, ctx):
        if ctx.voice_client is None:
            vc = get_channel_to_join(ctx)
            await vc.connect()
            # create new playlist instance, send current channel for further messaging
            self.vcControls[ctx.guild.id] = VcControl(ctx.channel)
        else: 
            n = ctx.voice_client.channel.name
            await ctx.send("I am in voice channel: " + n)

    # -------------------- Leave voice channel --------------------
    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client is None:
            raise Exception("I am not in any voice channel, use join command instead")
        else: 
            await ctx.voice_client.disconnect()
            
    # -------------------- play from youtube url / default if no url -------------------- # 
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
    async def compile_yt_source(self, url, stream = True, baseBoosted = False):
        try:
            # search yt url
            data = await self.bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        except Exception as e:
            raise Exception("URL not found")

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        if baseBoosted:
            ffmpeg_final_options = ffmpeg_options.copy()
            ffmpeg_final_options.options = ffmpeg_final_options.options + " -af bass=g=50"
        else:
            ffmpeg_final_options = ffmpeg_options.copy()
        source = YTDLSource(discord.FFmpegPCMAudio(filename, **ffmpeg_final_options), data=data)
        source.url = url
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
                vid = None 
                # get vid from url
                if "watch?" in url:
                    GET_req = url.split("watch?")[-1].split("&")
                    for r in GET_req:
                        if r[0] == 'v': vid = r[2:]
                        break
                    if not vid: raise Exception("No video ID in URL")
                else:
                    vid = url.split("/")[-1]
            else:
                # search for url in youtube API
                search_term = (" ".join(s)).lower()
                await ctx.send("Searching: " + search_term)
                vid = yt_search(search_term)
                url = "https://youtube.com/watch?v=" + vid
                if url == None: 
                    raise Exception("Nothing found in video form")

            # compile
            source = await self.compile_yt_source(url)
            source.vid = vid

            # baseboost song
            if need_baseboost(source.title):
                source = await self.compile_yt_source(url, baseBoosted = True)
                source.vid = vid            

            # check valid song
            banned_reason = is_banned(source.title)
            if banned_reason:
                raise Exception(banned_reason)
            else:
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
        await self.vcControls[ctx.guild.id].nowplaying(ctx)

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
        await ctx.send("Volume multiply by " + str(ctx.voice_client.source.volume))

    # -------------------------------------------------------------------------------------------- # 
    # ------------------------------------- EVENT HANDLING --------------------------------------- # 
    # -------------------------------------------------------------------------------------------- # 
    @commands.Cog.listener()
    async def on_button_click(self, interaction):
        ctx = await self.bot.get_context(interaction.message)

        # btnID - eg: remove_xxxxxx
        id = interaction.component.id
        
        actions = {
            'repeat': self.repeat_btn_handler, 
            'remove': self.remove_btn_handler,
        }
        for action, handler in actions.items():
            if action in id[:len(action)]:
                await handler(ctx, id[len(action)+1:])
                await interaction.respond()
                return # maybe break
    
    
    # --------- ACTION HANDLERS --------- # 
    # repeat button handler
    async def repeat_btn_handler(self, ctx, vid):
        url = "youtu.be/" + vid
        await self.search_compile_play(ctx, url)
    
    # remove button handler
    async def remove_btn_handler(self, ctx, vid):
        await self.vcControls[ctx.guild.id].remove_track(ctx.voice_client, vid, vid=True) 


    # handle all (command) error
    # COMMENT TO ENABLE DETAILED ERROR MESSAGE ON CONSOLE (WHEN DEBUG)
    @commands.Cog.listener()
    async def on_command_error(self, ctx, e):
        # print traceback on console
        print(e)
        # send error message to text channel
        await ctx.send(e.original)



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