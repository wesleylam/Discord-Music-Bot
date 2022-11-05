import os
import discord
from discord.ext import commands
# from discord_components import ComponentsBot

from VcControl import VcControl
from SourceCompile import SourceCompile
from Views import Views
from API.tenorAPIget import get_tenor_gif

from helper import *
from config import *
from options import *
from DJDynamoDB import DJDB

class DJ(commands.Cog):
    def __init__(self, bot, vcControlManager):
      
        
        self.bot = bot
        self.vcControls = {} # guild.id: vcControl object
        self.manager = vcControlManager

        # mysql
        # self.djdb = DJDB(mysql_host, mysql_user, mysql_password, mysql_db_name)
        # dynamodb
        SourceCompile.djdb = DJDB()
        SourceCompile.djdb.connect()

    # ---------------------------- MESSAGING --------------------------- # 
    async def notify(self, ctx, message, del_sec = 10):
        if str(message) == "": return # prevent err

        m = await ctx.send(message)
        
        # delete the message if needed
        if del_sec: 
            assert type(del_sec) == int
            await m.delete(delay = del_sec)


    @commands.command(aliases=['g'])
    async def gif(self, ctx, *kwords):
        '''Display a random gif from tenor'''
        s = list(kwords)
        if len(s) <= 0 or "".join(s) == "": # throw error when no arg given 
            q = random.choice(opening_gif_search_list + leaving_gif_search_list)
        else: 
            q = " ".join(s)

        await ctx.send(get_tenor_gif(q))

# -------------------------------------------------------------------------------------------- # 
# ------------------------------------- VOICE CONTROL ---------------------------------------- # 
    # -------------------------------------------------------------------------------------------- # 
    @commands.command(aliases=['patch', 'note'])
    async def patchnote(self, ctx):
        '''Show the newest patch note'''
        # get gif
        q = random.choice(opening_gif_search_list)
        gif = get_tenor_gif(q)
        # make embed
        embeded = Views.patch_note_box(gif)
        await ctx.send( embed = embeded)

    # -------------------- Join voice channel -------------------- #
    @commands.command()
    async def join(self, ctx, silence = False):
        '''Let bot join the voice channel (caller's channel / most populated channel)'''
        print(ctx.guild.id)
        if ctx.voice_client is None:
            vc = get_channel_to_join(ctx)
            await vc.connect()
            if not silence:
                # show patch note
                await self.patchnote(ctx)
                await self.notify(ctx, f'DJ2.0 is here!', None)
                
            # create new control instance, send current channel for further messaging
            self.manager.add(
                ctx.guild.id, 
                VcControl(ctx.channel, self, ctx.voice_client, ctx.guild)
            )
        else: 
            n = ctx.voice_client.channel.name
            if not silence:
                await self.notify(ctx, f"I am in voice channel: {n}", del_sec=60)

    # -------------------- Leave voice channel --------------------
    @commands.command(aliases=['l'])
    async def leave(self, ctx, guild_id = None):
        '''Let bot leave voice channel'''
        if guild_id == None:
            guild_id = ctx.guild.id
        if ctx.voice_client is None:
            raise Exception("I am not in any voice channel, use join command instead")
        else: 
            await self.manager.getControl(guild_id).disconnectVC()
            
    # ----------------------------- PLAY VARIANT ------------------------------ # 
    # COMMAND: dj
    @commands.command()
    async def dj(self, ctx, type = True):
        '''Turn on DJ'''
        vc = ctx.voice_client
        if type and vc is None:
            await self.join(ctx)

        # set vccontrol and bot status
        self.manager.getControl(ctx.guild.id).set_dj_type( type )
        await self.bot_status(dj = type)

    # COMMAND: djoff
    @commands.command()
    async def djoff(self, ctx):
        '''Turn off DJ'''
        await self.dj(ctx, type=None)

    # COMMAND: playvideo
    @commands.command(aliases=['pv', 'playv', 'pvid', 'vid', 'playvid', 'pvideo'])
    async def playvideo(self, ctx, *kwords):
        '''Search video (not limited to music) in youtube and play a picked video'''
        s = list(kwords)
        if len(s) <= 0 or "".join(s) == "": # throw error when no arg given 
            raise Exception("No search term(s) given")

        # send search results in Views
        await self.scp_search_choice(ctx, s, force_music = False)

    # COMMAND: playsearch
    @commands.command(aliases=['ps', 'plays', 'psong', 'playsong'])
    async def playsearch(self, ctx, *kwords):
        '''Search songs in youtube and play a picked one'''
        s = list(kwords)
        if len(s) <= 0 or "".join(s) == "": # throw error when no arg given 
            raise Exception("No search term(s) given")

        # send search results in Views
        await self.scp_search_choice(ctx, s, force_music = True)

    # COMMAND: meme
    @commands.command(aliases=['m'])
    async def meme(self, ctx, *kwords):
        '''Play a meme instantly (with high volume)'''
        await self.play(ctx, *kwords, insert = True, loud = True, newDJable = False)
        # skip the current song if there is playing
        if ctx.voice_client is not None and ctx.voice_client.is_playing(): 
            await self.skip(ctx)

    # COMMAND: rape
    @commands.command(aliases=['earrape', 'r'])
    async def rape(self, ctx, *kwords):
        '''Play a song in earrape mode (with high volume and baseboosted)'''
        await self.play(ctx, *kwords, loud = True, baseboost = True, newDJable = False)

    # COMMAND: rapenow
    @commands.command(aliases=['earrapenow', 'rnow', 'rn'])
    async def rapenow(self, ctx, *kwords):
        '''Play a song in earrape mode instantly (with high volume and baseboosted)'''
        await self.play(ctx, *kwords, insert = True, loud = True, baseboost = True, newDJable = False)
        await self.skip(ctx)

    # COMMAND: insert
    @commands.command(aliases=['pn', 'pnow', 'play now'])
    async def insert(self, ctx, *kwords):
        '''Play a song next (top of the queue)'''
        await self.play(ctx, *kwords, insert = True)    
        
    # COMMAND: playonce
    @commands.command(aliases=['p1', 'pone', 'play1', 'ponce', 'po'])
    async def playonce(self, ctx, *kwords):
        '''Play a song with default not-DJable (only apply with its new song)'''
        await self.play(ctx, *kwords, newDJable = False)

    # ----------------------------- BASE PLAY COMMAND  ------------------------------ # 
    # COMMAND: play
    @commands.command(aliases=['p'])
    async def play(self, ctx, *kwords, insert = False, loud = False, baseboost = False, newDJable = True):
        '''Play a song (search in youtube / youtube link)'''
        # search and compile
        source, songInfo = SourceCompile.getSource(kwords, newDJable = newDJable, loud = loud, baseboost = baseboost)
        
        # play
        await self.scp_play(ctx, source, songInfo, insert = insert)

    async def scp_play(self, ctx, source, songInfo, insert = False):
        '''
        scp step 3: play in voice client
        send source to playlist and play in vc
        '''
        vc = ctx.voice_client
        if vc is None:
            await self.join(ctx)
            # vc = ctx.voice_client
        self.manager.getControl(ctx.guild.id).addSong(source, songInfo, ctx.author, insert = insert)

# ------------------------------------ CONTROLS --------------------------------------- # 
    # COMMAND: nowplaying
    @commands.command(aliases = ['np', 'now'])
    async def nowplaying(self, ctx):
        '''Redisplay nowplaying board w/ controls'''
        await self.manager.getControl(ctx.guild.id).display_nowplaying()

    # COMMAND: queue
    @commands.command(aliases=['playlist'])
    async def queue(self, ctx):
        '''List current playlist queue'''
        await self.manager.getControl(ctx.guild.id).list(ctx)

    # COMMAND: skip
    @commands.command()
    async def skip(self, ctx):
        '''Skip the current song'''
        self.manager.getControl(ctx.guild.id).skip(ctx.author)

    # COMMAND: remove
    @commands.command()
    async def remove(self, ctx, *args):
        '''Remove a song from playlist'''
        k = " ".join(args)
        self.manager.getControl(ctx.guild.id).remove(k, ctx.author)

    # COMMAND: clear
    @commands.command()
    async def clear(self, ctx):
        '''Clear playlist'''
        self.manager.getControl(ctx.guild.id).clear()

    # COMMAND: stop
    @commands.command()
    async def stop(self, ctx):
        '''Stop player'''
        self.manager.getControl(ctx.guild.id).stop()

    # COMMAND: vup (doubled)
    @commands.command()
    async def vup(self, ctx, n=2):
        '''Increase current volume'''
        await self.vset(ctx.voice_client, ctx, n)

    # COMMAND: vdown (half)
    @commands.command()
    async def vdown(self, ctx, n=0.5):
        '''Reduce current volume'''
        await self.vset(ctx.voice_client, ctx, n)

    # volume set
    async def vset(self, vc, channel, volume, slient = False):
        if not vc: raise Exception("I am not in any voice channel")

        vc.source = discord.PCMVolumeTransformer(vc.source)
        vc.source.volume = float(volume)
        if not slient:
            await self.notify(channel, f"Volume multiplied by {vc.source.volume}")

# ------------------------------------------------------------------------------------------------- # 
# ------------------------------------- EVENT/ERROR HANDLING --------------------------------------- # 
    # ------------------------------------------------------------------------------------------------- # 
    @commands.Cog.listener()		
    async def on_ready(self, ):
        await self.bot_status(False)
        print(f'Logged in as {self.bot.user} (ID: {self.bot.user.id})')
        print('------')

    
    async def bot_status(self, dj):
        if dj: 
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="DJ"))
        else:
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="play"))



    # always available buttons: 1. encore | 2. reDJ | 3. del
    @commands.Cog.listener()
    async def on_button_click(self, interaction):
        ctx = await self.bot.get_context(interaction.message)
        ctx.author = interaction.author

        id = interaction.component.id
        guild_id, received_action, other_param = Views.decompose_btn_id(id)

        actions = {
            'encore': self.repeat_btn_handler,
            'reDJ': self.reDJ_btn_handler,
            'del': self.del_btn_handler,
            'notdjable': self.notdjable_btn_handler
        }
        try: await actions[received_action](ctx, other_param)
        except KeyError: pass # button not mapped in action above (not global btn)

    # --------- ACTION HANDLERS --------- # 
    # repeat button handler
    async def repeat_btn_handler(self, ctx, p):
        vid = "_".join(p)
        url = vid_to_url(vid)
        await self.play(ctx, url)
    # reDJ button handler
    async def reDJ_btn_handler(self, ctx, _):
        await self.dj(ctx)
    # del button handler (delete song from db)
    async def del_btn_handler(self, ctx, p):
        vid = p[0]
        self.djdb.remove_song(vid)
        await self.notify(ctx, f"Removed song from db ({vid})")

    async def notdjable_btn_handler(self, ctx, p):
        vid = p[0]
        self.djdb.set_djable(vid, False)
        await self.notify(ctx, f"{vid_to_url(vid)} is now not DJable")

    # handle all (command) error
    @commands.Cog.listener()
    async def on_command_error(self, ctx, e):
        try:
            # send error message to text channel
            await self.notify(ctx, e.original, del_sec=None)
            # log to files
            error_log_e(e.original)
        except:
            # send error message to text channel
            await self.notify(ctx, e, del_sec=None)
            # log to files
            error_log_e(e)
        raise e

# -------------------------------------------- MAIN ------------------------------------------------ # 

async def startDJ(manager):
    # set ffmpeg error log file
    os.environ['FFREPORT'] = f'file={ffmpeg_error_log}:level=16'

    # for voice client to work: you need opus and ffmpeg
    # NOT needed for windows environment (neither ubuntu?)
    # discord.opus.load_opus()
    # if not discord.opus.is_loaded():
    #     raise RunTimeError('Opus failed to load')
    
    intents = discord.Intents.all()
    intents.members = True
    bot = commands.Bot(command_prefix="=", case_insensitive=True, 
                        description='DJ', intents=intents)
    
    try: 
        await bot.add_cog(DJ(bot, manager))
        await bot.start(TOKEN) 
    except Exception:
        await bot.close()
    
    
    
    
if __name__ == "__main__":
    startDJ()

