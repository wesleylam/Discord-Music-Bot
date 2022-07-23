import os
import discord
from discord.ext import commands
from discord_components import ComponentsBot

from VcControl import VcControl
from Views import Views
from API.ytAPIget import yt_search, yt_search_all
from API.tenorAPIget import get_tenor_gif
import youtube_dl
from YTDLSource import YTDLSource, StaticSource
from youtube_dl.utils import DownloadError

from helper import *
from config import *
from options import *
from DJDynamoDB import DJDB
from DJExceptions import DJDBException, DJBannedException, DJSongNotFoundException
from YTDLException import YTDLException

class DJ(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vcControls = {} # guild.id: vcControl object

        # mysql
        # self.djdb = DJDB(mysql_host, mysql_user, mysql_password, mysql_db_name)
        # dynamodb
        self.djdb = DJDB()

        self.djdb.connect()

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
            self.djdb.connect()
            await vc.connect()
            if not silence:
                # show patch note
                await self.patchnote(ctx)
                
            # create new control instance, send current channel for further messaging
            self.vcControls[ctx.guild.id] = VcControl(ctx.channel, self, ctx.voice_client, ctx.guild)
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
            await self.vcControls[guild_id].disconnectVC()
            
    # ----------------------------- PLAY VARIANT ------------------------------ # 
    # COMMAND: dj
    @commands.command()
    async def dj(self, ctx, type = True):
        '''Turn on DJ'''
        vc = ctx.voice_client
        if type and vc is None:
            await self.join(ctx)

        # set vccontrol and bot status
        await self.vcControls[ctx.guild.id].set_dj_type( type )
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
        r = await self.process_song_input(ctx, kwords, newDJable = newDJable)

        if r:
            vid, vol = r
            # 2 & 3
            await self.compile_and_play(ctx, vid, vol = vol, insert = insert, loud = loud, baseboost = baseboost)


    async def process_song_input(self, ctx, args, DBonly = False, newDJable = True, search = False):
        '''
        Process song input (from link or search terms)
        return vid ONLY if passed url
        '''
        args = list(args)
        if len(args) <= 0 or "".join(args) == "": # throw error when no arg given (alternative: play default source)
            raise DJSongNotFoundException("No url or search term given")
            # source = StaticSource(discord.FFmpegPCMAudio(source=default_play_dir), volume=default_init_vol)
            # source.url = ''

        url = args[0]
        ### scp: 1. search | 2. compile | 3. play 
        # 1. search -> get url
        if is_ytlink(url): 
            # case 1: url
            vid = yturl_to_vid(url)
            # insert to db if not in db
            match = self.djdb.find_song_match(vid)
            if not DBonly and not match:
                self.yt_search_and_insert(vid, use_vID = True, newDJable = newDJable)
                vol = None
            else: 
                if DBonly: raise DJSongNotFoundException(f"No match found for {vid}")
                else: vol = match[DJDB.Attr.SongVol]
        else: 
            if not search:
                # case 2: find in query db (or query yt if none)
                vid, vol = await self.scp_search(ctx, args, DBonly = DBonly, newDJable = newDJable)
            else:
                # search and display youtube top choices
                await self.scp_search_choice(ctx, args)
                return None

        return vid, vol
        


    async def compile_and_play(self, ctx, vid, vol = None, insert = False, loud = False, baseboost = False):
        '''Step 2 & 3'''
        # DB: INC Qcount
        self.djdb.increment_qcount(vid)

        # 2. compile
        source = await self.scp_compile(vid, vol, loud = loud, baseboost = baseboost)
        # 3. play
        await self.scp_play(ctx, source, insert = insert)

# ---------------------------- SEARCH COMPILE PLAY --------------------------------- #     

    async def scp_search_choice(self, ctx, s, force_music = True):
        '''search (youtube API only) and show options to pick'''
        # search for url in youtube API
        search_term = (" ".join(s)).lower()
        await self.notify(ctx, f"Searching: {search_term}")
        # get songs list by searching youtube API
        songs = yt_search_all(search_term, n = 5, force_music = force_music)
        
        # join vChannel to get views and vcControl
        await self.join(ctx, silence = True)
        # show option views
        await self.vcControls[ctx.guild.id].views.send_search_options(search_term, songs)

    async def scp_search(self, ctx, s, DBonly = False, newDJable = True):
        '''scp step 1: search (in db or youtube)'''
        # search for url in youtube API
        search_term = (" ".join(s)).lower()
        await self.notify(ctx, f"Searching: {search_term}")
        
        # fetch vid from either db or youtube api search
        match = self.djdb.find_query_match(search_term)
        if match:
            vid = match[DJDB.Attr.vID]
            # insert to db if not in db (Depreciated, safety catch)
            if not self.djdb.find_song_match(vid):
                error_log(f"(Unexpected behaviour) Query found but song not in DB: {search_term} -> {vid}")
                await self.notify(ctx, "Unexpected behaviour: see log", del_sec = None)
                self.yt_search_and_insert(vid, use_vID = True, newDJable = newDJable)
            vol = match[DJDB.Attr.SongVol]
        
        else: # no DB match entry  
            if DBonly: raise DJDBException(f"No item found for {search_term}")

            # get info by searching youtube API
            info = self.yt_search_and_insert(search_term, insert_after = False, newDJable = newDJable)
            vid = info.vID
            # add query to db
            self.djdb.add_query(search_term, info)
            vol = None
        
        return vid, vol
    
    def yt_search_and_insert(self, search_term, use_vID = False, insert_after = True, newDJable = True):
        '''
        [ Helper function for scp_search ]
        youtube search and insert to db
        return: searched song info
        '''
        
        info = yt_search(search_term, use_vID=use_vID)
        # no result from youtube api (by vid)
        if not info: 
            if use_vID: raise DJSongNotFoundException(f"No video found: {vid_to_url(search_term)}")
            else: raise DJSongNotFoundException(f"Nothing found in video form: {search_term}")

        if insert_after: 
            inserted = self.djdb.insert_song(info, newDJable = newDJable)
            info.inserted = inserted
        return info


    async def scp_compile(self, vid, vol, loud = False, stream = True, baseboost = False):
        '''
        scp step 2: compile youtube source
        compile YTDLSource (audio source object) from youtube url
        return: source object
        '''

        url = "https://youtube.com/watch?v=" + vid

        try:
            # search yt url
            data = await self.bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        except DownloadError as e: # youtube dl download error
            self.djdb.remove_song(vid)
            raise YTDLException(f"Unable to download {url}, removed ({str(e)})")

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        # options for baseboosted or normal
        if baseboost or need_baseboost(data.get('title')):
            ffmpeg_final_options = ffmpeg_options.copy()
            os = "options"
            ffmpeg_final_options[os] = ffmpeg_final_options[os] + " -af bass=g=50"
        else:
            ffmpeg_final_options = ffmpeg_options.copy()

        # Create source object
        if vol is None:
            vol = default_init_vol
        if loud:
            vol = vol * loud_vol_factor
        print(vol)
        source = YTDLSource(discord.FFmpegPCMAudio(filename, **ffmpeg_final_options), data=data, volume = vol)
        source.url = url
        source.vid = vid
        source.duration = self.djdb.find_duration(vid)

        # check valid song
        banned_reason = is_banned(source.title)
        if banned_reason:
            raise DJBannedException(f"{source.title} banned: {banned_reason}")
        else:
            return source

    async def scp_play(self, ctx, source, insert = False):
        '''
        scp step 3: play in voice client
        send source to playlist and play in vc
        '''
        vc = ctx.voice_client
        if vc is None:
            await self.join(ctx)
            vc = ctx.voice_client
        await self.vcControls[ctx.guild.id].add(vc, source, ctx.author, insert = insert)


# ------------------------------------ CONTROLS --------------------------------------- # 
    # COMMAND: nowplaying
    @commands.command(aliases = ['np', 'now'])
    async def nowplaying(self, ctx):
        '''Redisplay nowplaying board w/ controls'''
        await self.vcControls[ctx.guild.id].display_nowplaying()

    # COMMAND: queue
    @commands.command(aliases=['playlist'])
    async def queue(self, ctx):
        '''List current playlist queue'''
        await self.vcControls[ctx.guild.id].list(ctx)

    # COMMAND: skip
    @commands.command()
    async def skip(self, ctx):
        '''Skip the current song'''
        await self.vcControls[ctx.guild.id].skip(ctx.voice_client, ctx.author)

    # COMMAND: remove
    @commands.command()
    async def remove(self, ctx, *args):
        '''Remove a song from playlist'''
        k = " ".join(args)
        await self.vcControls[ctx.guild.id].remove_track(ctx.voice_client, k, ctx.author)

    # COMMAND: clear
    @commands.command()
    async def clear(self, ctx):
        '''Clear playlist'''
        await self.vcControls[ctx.guild.id].clear()

    # COMMAND: stop
    @commands.command()
    async def stop(self, ctx):
        '''Stop player'''
        await self.vcControls[ctx.guild.id].stop()

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



# -------------------------------------------------------------------------------------------- # 
# --------------------------------------- DB RELATED ----------------------------------------- # 
    # -------------------------------------------------------------------------------------------- # 
    
    # COMMAND: songinfo
    @commands.command(aliases=['info', 'si'])
    async def songinfo(self, ctx, *args):
        '''Get song info of a song (DB entry)'''
        try: 
            vid, vol = await self.process_song_input(ctx, args, DBonly = True)
            item = self.djdb.db_get(vid)
        except DJSongNotFoundException as e: 
            await self.notify(ctx, f"No record of {' '.join(args)}")
            return

        # only counting in this server
        DJcount = self.djdb.get_hist_count(vid, dj = True)
        embedInfo = Views.song_info_box(item, DJcount)
        await ctx.send(
            embed = embedInfo
        )

    
    # COMMAND: notDJable
    @commands.command()
    async def notDJable(self, ctx, *args):
        '''Turn a song off from DJ mode'''
        vid, vol = await self.process_song_input(ctx, args, DBonly = True)

        self.djdb.set_djable(vid, False)
        await self.notify(ctx, f"{vid_to_url(vid)} is no longer DJable")

    # COMMAND: DJable
    @commands.command()
    async def DJable(self, ctx, *args):
        '''Allow a song to play in DJ mode'''
        vid, vol = await self.process_song_input(ctx, args, DBonly = True)

        self.djdb.set_djable(vid, True)
        await self.notify(ctx, f"{vid_to_url(vid)} is now DJable")

    # COMMAND: removeFromDB
    @commands.command(aliases=['rmFromDB', 'rmDB'])
    async def removeFromDB(self, ctx, *args):
        '''Remove a song from database'''
        vid, vol = await self.process_song_input(ctx, args, DBonly = True)

        await self.del_btn_handler(ctx, [vid])

    
    # COMMAND: bind
    @commands.command()
    async def bind(self, ctx, *args):
        '''
        Bind a search query to a url / find what url is binded to a search query
        Usage: =bind [search term (can contain spaces)] [url (optional)]
        '''

        # adding query binding to a vID
        def add_binding(f_q, f_vid):
            # actual binding when url provided
            if not self.djdb.find_song_match(f_vid):
                info = self.yt_search_and_insert(f_vid, use_vID = True)
            else: # song exist
                info = f_vid

            self.djdb.add_query(f_q, info)

        out_message = None
        try:
            # case 1: url provided, delete current binding and bind [query terms] to the url

            # try add query with vid
            vid = yturl_to_vid(args[-1])
            q = " ".join(args[:-1])

            # delete all other query

            # db: add binding
            add_binding(q, vid)

            out_message = f"Added binding \n{q} -> {vid_to_url(vid)}"
        except: 
            # case 2: No url provided, find binded url for the [query terms]
            vid = None
            q = " ".join(args)

            # query binding if url not provided
            match = self.djdb.find_query_match(q)
            if match:
                vid = match[DJDB.Attr.vID]
                out_message = f"{q} is bind to {vid_to_url(vid)}"
            else: 
                out_message = f"{q} is not bind to anything"

        # final output message to client
        await self.notify(ctx, out_message, del_sec=None)
            

    # COMMAND: listdj
    # list all djable songs
    @commands.command()
    async def listdj(self, ctx, *args):
        '''List 10 djable songs'''
        songs = self.djdb.list_all_songs(dj = True, needed_attr = [DJDB.Attr.Title])
        await self.list(ctx, display_list = songs, title = "List 10 djable songs", none_message = "No song found")


    # COMMAND: listnotdj
    @commands.command()
    async def listnotdj(self, ctx, *args):
        '''List 10 not djable songs'''
        songs = self.djdb.list_all_songs(dj = False, needed_attr = [DJDB.Attr.Title])
        await self.list(ctx, display_list = songs, title = "List 10 not djable songs", none_message = "No song found")

    # COMMAND: search
    @commands.command()
    async def search(self, ctx, *args):
        '''List all matching title songs'''
        q = " ".join(args)
        songs = self.djdb.search(search_term = q)
        await self.list(ctx, songs = songs, title = f"Searching: {q}", none_message = "No song found")


    # list: for listing in discord channel (eg: list songs)
    async def list(self, ctx, songs, title = "", none_message = "Nothing found"):
        if songs:
            await self.notify(ctx, title, del_sec=None)
            for i, song in enumerate(songs):
                # create a song box embed
                embedSong = Views.song_box(song, title = f"{i+1}. {song.title}")
                await ctx.channel.send(
                    embed = embedSong
                )
        else: 
            await self.notify(ctx, none_message)


    # COMMAND: songvup
    @commands.command()
    async def songvup(self, ctx, vid, n = 2, *args):
        '''Permanently increase a song volume'''
        await self.songvMulti(ctx, vid, n)

    # COMMAND: songvdown
    @commands.command()
    async def songvdown(self, ctx, vid, n = 0.5, *args):
        '''Permanently reduce a song volume'''
        await self.songvMulti(ctx, vid, n)

    # COMMAND: songvset
    @commands.command()
    async def songvset(self, ctx, vid, n = 10, *args):
        '''Permanently set a song volume'''
        n = int(n)
        self.djdb.change_vol(vid, multiplier = None, setNewVol = n)
        await self.notify(ctx, f"Song Volume set to {n}")


    async def songvMulti(self, ctx, vid, n, noCtx = None):
        if noCtx:
            vc = noCtx["vc"]
            channel = noCtx["channel"]
        else: 
            vc = ctx.voice_client
            channel = ctx


        self.djdb.change_vol(vid, multiplier = n)
        await self.vset(vc, channel, volume = n, slient = True)
        await self.notify(channel, f"Song Volume multiplied by {n}")
        return f"Song Volume multiplied by {n}"


    # COMMAND: tag
    # tag "link" "tag"
    @commands.command()
    async def tag(self, ctx, *args):
        pass


# ------------------------------------------------------------------------------------------------- # 
# ------------------------------------- HISTORY / STATS --------------------------------------- # 
    # ------------------------------------------------------------------------------------------------- # 

    # COMMAND: djcountall
    @commands.command(aliases = ['djca', 'djcall'])
    async def djcountall(self, ctx, *args):
        '''Count how many times a song have been DJed (show rank if song not given) on all channels'''
        await self.djcount(ctx, *args, all_server = True)

    # COMMAND: djcount
    @commands.command(aliases = ['djc'])
    async def djcount(self, ctx, *args, all_server = False):
        '''Count how many times a song have been DJed (show rank if song not given) on this channel'''
        await self.count(ctx, *args, dj = True, all_server = all_server)

    # COMMAND: countall
    @commands.command(aliases = ['ca', 'call'])
    async def countall(self, ctx, *args):
        '''Count how many times a song played (by anyone inc. DJ) (show rank if song not given) on all channels'''
        await self.count(ctx, *args, all_server = True)

    # COMMAND: count
    @commands.command(aliases = ['c'])
    async def count(self, ctx, *args, all_server = False, 
        dj = False, top = 20):

        '''Count how many times a song played (by anyone inc. DJ) (show rank if song not given) on this channel'''

        if not all_server: guild_id = ctx.guild.id
        else: guild_id = None

        async with ctx.typing():
            try: 
                vID, vol = await self.process_song_input(ctx, args, DBonly = True)
            except DJSongNotFoundException as e: 
                vID = None

            if vID:
                # specific song count

                # will not fail by no vID, checked at the top of this function
                times = self.djdb.get_hist_count(vID, serverID = guild_id, dj = dj)
                title = self.djdb.db_get(vID, [DJDB.Attr.Title])[DJDB.Attr.Title]

                head_m = f"DJ played **{title}**" if dj else f"**{title}** played"
                m = f"{head_m} : __**{times}**__ time{'s' if times > 1 else ''}{'' if all_server else ' on this channel'} \n{vid_to_url(vID)}"
            else:
                # find most played song
                rank = self.djdb.get_hist_rank(serverID = guild_id, dj = dj)
                head_m = "DJed" if dj else "played"
                m = f"Most {head_m} song{'' if all_server else ' on this channel'}: (top {top})\n"
                for (vID, title, times) in rank[:top]:
                    m += f"__**{times}**__: {title}\n"

            await ctx.send(m)



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
if __name__ == "__main__":
    # set ffmpeg error log file
    os.environ['FFREPORT'] = f'file={ffmpeg_error_log}:level=16'

    # for voice client to work: you need opus and ffmpeg
    # NOT needed for windows environment
    # discord.opus.load_opus(opus_dir)

    # initialise ytdl from youtube_dl library
    ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

    intents = discord.Intents.default()
    intents.members = True
    client = ComponentsBot(command_prefix="=", case_insensitive=True, 
                    description='DJ', intents=intents)

    client.add_cog(DJ(client))
    client.run(TOKEN)