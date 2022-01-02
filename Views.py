import discord
from discord_components import Button, ButtonStyle, component
from helper import *
from enum import Enum
import random
import time

class ViewUpdateType(Enum):
    REPOST = 1
    EDIT = 2
    DURATION = 3

class Views():

    # -------------------------------- VIEWS ---------------------------------- # 

    def __init__(self, mChannel, vc, vcControl, guild_id) -> None:
        self.mChannel = mChannel # message channel
        self.nowPlaying = None
        self.dj = None # dj type: string?
        self.vc = vc # voice client (NOT voice channel)
        self.vcControl = vcControl
        self.djbot_component_manager = self.vcControl.djObj.bot.components_manager
        self.guild_id = guild_id

        # active display messages
        self.playbox = None
        self.playing_source = None
        self.listbox = None
        self.queue_items = [] # all queue messages


    # Static function
    def decompose_btn_id(id):
        '''Get guild_id, action, (params) from button ID'''
        tokens = id.split("_")
        return tokens[0], tokens[1], tokens[2:]

    # button identifier
    def BIgen(self, action, *args):
        '''
        Unique button identifier generation
        label: [guild_id]_[action]_[identifier(s)]
        '''
        full_args = [action] + list(args)
        linked_stringed_args = "_".join( list( [str(a) for a in full_args] ) )
        return f"{self.guild_id}_{linked_stringed_args}"


    # -------------------------------- QUEUE VIEW ---------------------------------- # 

    async def send_queue_message(self, vc, source):
        vid = source.vid
        self.queue_message = await self.mChannel.send(
            "Queued: " + source.title,
            components=[[
                self.remove_button(vc, vid, label = "Remove"),
                self.switch_djable_button(vc, vid, queue = True)
            ]]
        )
        return self.queue_message

    # -------------------------------- NOWPLAYING VIEW ---------------------------------- # 
    def get_playing_string(self, source, start_time, player = ""):
        player_string = f"**{player}**" 
        current_duration = readable_duration(time.time() - start_time)
        full_duration = readable_duration(source.duration) if source.duration > 0 else "Unknown"
        self.playing_string = f"{player_string} Now Playing: {source.title} \n{current_duration}/{full_duration} - {source.url}"
        return self.playing_string

    def update_duration(self, original_str):
        if self.start_time is not None:
            current_duration = time.time() - self.start_time
            lines = original_str.split("\n")
            duration_url = lines[1].split(" - ")
            current_full_duration = duration_url[0].split("/")
            return f"{lines[0]}\n{readable_duration(current_duration)}/{current_full_duration[1]} - {' - '.join(duration_url[1:])}"
        else:
            error_log(f"Cannot update duration without start time, return original: {original_str}")
            return original_str


    # send message on text channel with action buttons
    async def show_playing(self, is_dj_source, source, player = "", start_time = None, extended = False):
        if start_time: self.start_time = start_time

        self.playbox = await self.mChannel.send(
            self.get_playing_string(source, self.start_time, player = player),
            components = self.playbox_components(extended = extended)
        )

    # update play box info
    async def update_playing(self, update: ViewUpdateType, extended = False):
        assert self.playbox is not None, "Cannot update without playbox"
        
        if update == ViewUpdateType.REPOST:
            # repost
            m = await self.mChannel.send(
                self.playbox.content,
                components = self.playbox.components
            )
            await self.playbox.delete()
            self.playbox = m
        elif update == ViewUpdateType.EDIT:
            # edit
            await self.playbox.edit(
                components = self.playbox_components(extended = extended)
            )
        elif update == ViewUpdateType.DURATION:
            # edit duration
            await self.playbox.edit(
                self.update_duration(self.playbox.content),
            )

        else: raise Exception(f"Unknown udpate type: {update}")

    def playbox_components(self, extended = False):
        vc, vid = self.vc, self.vcControl.nowPlaying.vid
        btns = [
            self.switch_djable_button(vc, vid),
            self.remove_button(vc, vid),
            self.switch_dj_button(), 
            self.leave_button(),
            self.song_info_button(vc, vid),
        ]
        song_info_btns = [   
            # song perm vol up
            self.song_vol_up_button(vid),
            self.song_vol_down_button(vid),
            # extra song settings
            self.del_from_db_button(vc, vid),
            # replace
        ]
        if extended:
            return [ btns, song_info_btns ]
        else:
            return [ btns ]

    # --------------------------------- AFTER/SKIP VIEW ---------------------------------- #
    # replace old playing message with ended message (allow encore)
    # transforms into immutable PERMANANT message 
    async def end_playing(self, source, skip_author = None):
        head = f"Skipped by {skip_author}" if skip_author else "Ended"
        await self.playbox.edit(
            f"{head}: {source.title}",
            components = [[
                self.encore_button(self.vc, source.vid),
                # self.del_from_db_button(self.vc, source.vid),
                self.make_undjable_button(self.vc, source.vid)
            ]]
        )
        self.playbox = None


    # -------------------------------- PLAYLIST VIEW ---------------------------------- # 

    # send message on text channel with action buttons
    async def show_list(self):
        if self.listbox: await self.remove_list()
        m = f"Up Next ({len(self.vcControl.playlist)}): \n"

        for i, (s, _) in enumerate(self.vcControl.playlist):
            m += f"{s.title} \n"

        self.listbox = await self.mChannel.send(
            m, 
            components = self.listbox_components()
        )    

    # update list box info
    async def update_list(self):
        print(self.listbox)
        # only update when list is active
        if self.listbox:
            # edit ONLY (no need repost)
            await self.listbox.edit(
                components = self.listbox_components()
            )
    
    def listbox_components(self):
        return [ self.switch_dj_button() ]

    async def remove_list(self):
        await self.listbox.delete()
        self.listbox = None



    # ------------------------------ BUTTONS ----------------------------- # 
    def switch_dj_button(self):
        return self.djbot_component_manager.add_callback(
            (   
                Button(style=ButtonStyle.green, label="DJ: On", id=self.BIgen("djoff"))
                if self.vcControl.dj else
                Button(style=ButtonStyle.red, label="DJ: Off", id=self.BIgen("djon")) 
            ),
            self.switch_dj_callback
        )

    # handle in DJ.py
    def encore_button(self, vc, vid):
        return Button(style=ButtonStyle.blue, label="Encore", id=self.BIgen("encore", vid))

    def remove_button(self, vc, vid, label = "Skip"):
        return self.djbot_component_manager.add_callback(
            Button(style=ButtonStyle.red, label=label, id=self.BIgen(label, vid)), 
            lambda i: self.remove_callback(i, vc, vid)
        )

    def song_info_button(self, vc, vid):
        return self.djbot_component_manager.add_callback(
            Button(style=ButtonStyle.gray, label="Song Settings", id=self.BIgen("songinfo", vid)), 
            self.song_info_callback
        )

    def switch_djable_button(self, vc, vid, queue = False):
        return self.djbot_component_manager.add_callback(
            (   Button(style=ButtonStyle.green, label="Now: DJable", id=self.BIgen("switchdjable", vid))
                if self.vcControl.djObj.djdb.find_djable(vid) else
                Button(style=ButtonStyle.red, label="Now: Not DJable", id=self.BIgen("switchdjable", vid)) 
            ),
            lambda i: self.switch_djable_callback(i, vc, vid, queue = queue),
        )

    # handle in DJ.py (no longer using)
    def del_from_db_button(self, vc, vid):
        return Button(style=ButtonStyle.red, label="Del from DB", id=self.BIgen("del", vid))

    # handle in DJ.py
    def make_undjable_button(self, vc, vid):
        return Button(style=ButtonStyle.red, label="Make not DJable", id=self.BIgen("notdjable", vid))

    def leave_button(self):
        return self.djbot_component_manager.add_callback(
            Button(style=ButtonStyle.gray, label="Leave", id=self.BIgen("leave")), 
            lambda i: self.leave_callback()
        )

    def reDJ_button(self):
        return Button(style=ButtonStyle.blue, label="DJ again", id=self.BIgen("reDJ"))

    def song_vol_up_button(self, vid):
        return self.djbot_component_manager.add_callback(
            Button(style=ButtonStyle.gray, label="Song volume up", id=self.BIgen("pvup", vid)), 
            lambda i: self.song_vol_up_callback(vid)
        )
    def song_vol_down_button(self, vid):
        return self.djbot_component_manager.add_callback(
            Button(style=ButtonStyle.gray, label="Song volume down", id=self.BIgen("pvdown", vid)), 
            lambda i: self.song_vol_down_callback(vid)
        )

    # --------------------- BUTTONS CALLBACK -------------------- # 
    async def switch_dj_callback(self, interaction):
        await self.vcControl.set_dj_type(None if self.vcControl.dj else True)


    async def remove_callback(self, interaction, vc, vid):
        await self.vcControl.remove_track(vc, vid, interaction.author, vid=True)
    
    async def song_info_callback(self, interaction):
        await interaction.edit_origin(
            components = self.playbox_components(extended = True)
        )

    async def leave_callback(self):
        await self.mChannel.send(
            f"Goodbye!",
            # handle in DJ.py
            components = [ self.reDJ_button() ]
        )
        await self.vcControl.disconnectVC()

    async def switch_djable_callback(self, interaction, vc, vid, queue = False):
        self.vcControl.djObj.djdb.switch_djable(vid)
        if not queue: 
            # playbox
            await self.update_playing(ViewUpdateType.EDIT, extended = False)
        else: 
            # queue message
            await interaction.edit_origin(
                components = [[
                    self.remove_button(vc, vid, label="Remove"),
                    self.switch_djable_button(vc, vid, queue)
                ]]
            )

    async def song_vol_up_callback(self, vid):
        m = await self.vcControl.djObj.songvMulti(None, vid, 2, {
            "vc": self.vc,
            "channel": self.mChannel
        })
    
    async def song_vol_down_callback(self, vid):
        m = await self.vcControl.djObj.songvMulti(None, vid, 0.5, {
            "vc": self.vc,
            "channel": self.mChannel
        })