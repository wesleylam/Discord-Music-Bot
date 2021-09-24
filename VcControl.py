from asyncio.queues import Queue
import discord
import asyncio
from discord_components import Button, ButtonStyle
from helper import help

class VcControl():
    def __init__(self, mChannel, djo) -> None:
        self.playlist = []
        self.mChannel = mChannel # message channel
        self.nowPlaying = None
        self.dj = None # dj type: string?
        self.djObj = djo
        self.playing_message = None
        self.queuing_message = []


    # ---------------------------- MESSAGING --------------------------- # 
    async def notify(self, message, del_sec = 10):
        m = await self.mChannel.send(message)

        # delete the message if needed
        if del_sec: 
            assert type(del_sec) == int
            await m.delete(delay = del_sec)

    # ---------------------------- CONTROLS --------------------------- # 
    async def add(self, vc: discord.VoiceClient = None, source = None):
        self.playlist.append(source)
        print(source.title, source.vid, source.url)
        if not vc.is_playing(): 
            await self.next(vc)
        else:
            m = await self.mChannel.send(
                "Queued: " + source.title,
                components=[[
                    self.remove_button(vc, source.vid, label = "Remove"),
                    self.switch_djable_button(vc, source.vid)
                ]]
            )
            self.queuing_message.append(m)

    async def next(self, vc: discord.VoiceClient):
        def after_handler(e):
            if e: 
                m = "Error occured in streaming"
                print(m + "\n" + e.message)
                raise Exception(m)
            print("song ended w/o error")

        # queue loop
        while len(self.playlist) > 0 or self.dj:
            # activate dj when no song in queue
            if self.dj and len(self.playlist) <= 0: 
                # query a random vid and compile source
                vid = self.djObj.djdb.find_rand_song()
                try: source = await self.djObj.compile_yt_source(vid)
                except Exception as e: self.mChannel.send(e.message)
                dj_source = True
                q_message = None
            else:
                source = self.playlist.pop(0)
                q_message = self.queuing_message.pop(0)
                dj_source = False

            self.nowPlaying = source
            vc.play(source, after = after_handler )
            
            # arrange buttons 
            vid = source.vid

            # delete old playing message and the corresponding queuing message
            if self.playing_message:
                await self.playing_message.delete()
                if q_message: await q_message.delete()

            # send message on text channel with action buttons
            dj_string = "DJ " if dj_source else ""
            m = await self.mChannel.send(
                f"{dj_string}Playing: {source.title} \n{source.url}",
                components=[self.get_play_buttons(vc, vid)]
            )
            self.playing_message = m
            # wait until the current track ends
            while vc.is_playing(): 
                await asyncio.sleep(1)

        await self.playing_message.delete()
        for m in self.queuing_message:
            await m.delete()
        return 
                

    # skip current song
    async def skip(self, vc: discord.VoiceClient):
        if not vc: raise Exception("I am not in any voice channel")

        if vc.is_playing(): 
            vc.stop()
 
    # remove song from playlist
    async def remove_track(self, vc, key, silent = False, exact = False, vid = False):
        if vid: exact = True
        def match(k, source):
            # url or title
            target = (source.vid if vid else source.title).lower()
            k = k.lower()
            if exact: return k == target
            else: return k in target

        if match(key, self.nowPlaying):
            await self.skip(vc)
            if not silent: await self.notify("Removed: " + self.nowPlaying.title)
            return self.nowPlaying.url

        for i, s in enumerate(self.playlist): 
            if match(key, s):
                del self.playlist[i]
                if not silent: await self.notify("Removed: " + s.title)
                return s.url

        if not silent: await self.notify("No matching result for: " + key)
        return None
 

    # display nowplaying 
    async def display_nowplaying(self, ctx = None, interaction = None, vc = None):
        assert not (ctx is None and interaction is None), "Nowplaying cannot run without ctx or interaction"
        message = f"Now playing: {self.nowPlaying.title} \n{self.nowPlaying.url}"
        if ctx and vc is None: vc = ctx.voice_client 
        vid = self.nowPlaying.vid
        components = [
            self.get_play_buttons(vc, vid),
            [
                self.switch_djable_button(vc, vid),
                self.del_from_db_button(vc, vid),
                # perm vol up
            ]
        ]
        if interaction: 
            # Song options from play
            await interaction.edit_origin(message, components=components)
        else:
            await ctx.send(message, components=components)

    # list playlist
    async def list(self, ctx):
        m = f"Up Next ({len(self.playlist)}): \n"

        for i, s in enumerate(self.playlist):
            m += f"{s.title} \n"

        await ctx.send(m, components = [self.switch_dj_button(ctx.voice_client, )])

    # clear playlist
    async def clear(self, silent = False):
        self.playlist = []
        if not silent: await self.mChannel.send("Playlist cleared")

    # stop and clear playlist
    async def stop(self, vc: discord.VoiceClient):
        if not vc: raise Exception("I am not in any voice channel")

        if vc.is_playing():
            self.dj = None
            await self.clear(silent = True)
            vc.stop()
           
    def insert(self, source):
        pass



    # ------------------------------ BUTTONS ----------------------------- # 
    def get_play_buttons(self, vc, vid):
        btns = [
            self.switch_dj_button(vc, vid), 
            self.encore_button(vc, vid),
            self.remove_button(vc, vid),
            self.song_info_button(vc, vid),
        ]
        return btns

    def switch_dj_button(self, vc, vid):
        return self.djObj.bot.components_manager.add_callback(
            (   Button(style=ButtonStyle.green, label="DJ on")
                if self.dj else
                Button(style=ButtonStyle.red, label="DJ off") 
            ),
            lambda i: self.switch_dj_callback(i, vc, vid)
        )

    def encore_button(self, vc, vid):
        return self.djObj.bot.components_manager.add_callback(
            Button(style=ButtonStyle.blue, label="Encore"), 
            lambda i: self.encore_callback(i, vc, vid)
        )

    def remove_button(self, vc, vid, label = "Skip"):
        return self.djObj.bot.components_manager.add_callback(
            Button(style=ButtonStyle.red, label=label), 
            lambda i: self.remove_callback(i, vc, vid)
        )

    def song_info_button(self, vc, vid):
        return self.djObj.bot.components_manager.add_callback(
            Button(style=ButtonStyle.gray, label="Song info"), 
            lambda i: self.song_info_callback(i, vc, vid)
        )

    def switch_djable_button(self, vc, vid):
        return self.djObj.bot.components_manager.add_callback(
            (   Button(style=ButtonStyle.green, label="DJable")
                if self.djObj.djdb.find_djable(vid) else
                Button(style=ButtonStyle.red, label="Not DJable") 
            ),
            lambda i: self.switch_djable_callback(i, vc, vid)
        )

    def del_from_db_button(self, vc, vid):
        return self.djObj.bot.components_manager.add_callback(
            Button(style=ButtonStyle.red, label="Del from DB"), 
            lambda i: self.db_del_entry_callback(i, vid)
        )

    # --------------------- BUTTONS CALLBACK -------------------- # 
    async def switch_dj_callback(self, interaction, vc, vid):
        self.dj = None if self.dj else True
        await interaction.edit_origin(
            components = [self.get_play_buttons(vc, vid)]
        )

    async def encore_callback(self, interaction, vc, vid):
        source = await self.djObj.compile_yt_source(vid)
        await self.add(vc, source)

    async def remove_callback(self, interaction, vc, vid):
        await self.remove_track(vc, vid, vid=True)
    

    async def song_info_callback(self, interaction, vc, vid):
        await self.display_nowplaying(interaction = interaction, vc = vc)

    # --- MORE --- # 
    async def switch_djable_callback(self, interaction, vc, vid):
        self.djObj.djdb.switch_djable(vid)
        await self.display_nowplaying(interaction = interaction, vc = vc)

    async def db_del_entry_callback(self, interaction, vid):
        self.djObj.djdb.remove_song(vid)
        await self.notify(f"Removed song from db ({vid})")
