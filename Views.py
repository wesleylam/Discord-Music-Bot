import discord
from discord_components import Button, ButtonStyle
from helper import help
from enum import Enum
import random

class ViewUpdateType(Enum):
    REPOST = 1
    EDIT = 2

class Views():
    def __init__(self, mChannel, vc, vcControl) -> None:
        self.mChannel = mChannel # message channel
        self.nowPlaying = None
        self.dj = None # dj type: string?
        self.vc = vc # voice client
        self.vcControl = vcControl
        self.djbot_component_manager = self.vcControl.djObj.bot.components_manager

        # active display messages
        self.playbox = None
        self.playing_source = None
        self.listbox = None


    # -------------------------------- NOWPLAYING VIEW ---------------------------------- # 

    # send message on text channel with action buttons
    async def show_playing(self, dj_source, source, extended = False):
        dj_string = "[DJ] " if dj_source else ""
        self.playbox = await self.mChannel.send(
            f"{dj_string}Now Playing: {source.title} \n{source.url}",
            components = self.playbox_components(extended = extended)
        )

    # update play box info
    async def update_playing(self, update: ViewUpdateType, extended = False):
        assert self.playbox is not None, "Cannot update without playbox"
        
        if update == ViewUpdateType.REPOST:
            # repost
            m = self.playbox.copy()
            await self.playbox.delete()
            await self.mChannel.send(m)
        elif update == ViewUpdateType.EDIT:
            # edit
            await self.playbox.edit(
                components = self.playbox_components(extended = extended)
            )
        else: raise Exception(f"Unknown udpate type: {update}")

    def playbox_components(self, extended = False):
        vc, vid = self.vc, self.vcControl.nowPlaying.vid
        btns = [
            self.encore_button(vc, vid),
            self.remove_button(vc, vid),
            self.switch_dj_button(), 
            self.leave_button(),
            self.song_info_button(vc, vid),
        ]
        song_info_btns = [   
            # extra song settings
            self.switch_djable_button(vc, vid),
            self.del_from_db_button(vc, vid),
            # perm vol up
        ]
        if extended:
            return [ btns, song_info_btns ]
        else:
            return [ btns ]

    # replace old playing message with ended message (allow encore)
    # transforms into immutable PERMANANT message 
    async def end_playing(self, source, skip_author = None):
        head = f"Skipped by {skip_author}" if skip_author else "Ended"
        await self.playbox.edit(
            f"{head}: {source.title}",
            components = [self.encore_button(self.vc, source.vid)]
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
                Button(style=ButtonStyle.green, label="DJ: On")
                if self.vcControl.dj else
                Button(style=ButtonStyle.red, label="DJ: Off") 
            ),
            self.switch_dj_callback
        )

    def encore_button(self, vc, vid):
        return Button(style=ButtonStyle.blue, label="Encore", id=f"encore_{vid}")

    def remove_button(self, vc, vid, label = "Skip"):
        return self.djbot_component_manager.add_callback(
            Button(style=ButtonStyle.red, label=label), 
            lambda i: self.remove_callback(i, vc, vid)
        )

    def song_info_button(self, vc, vid):
        return self.djbot_component_manager.add_callback(
            Button(style=ButtonStyle.gray, label="Song Settings"), 
            self.song_info_callback
        )

    def switch_djable_button(self, vc, vid, queue = False):
        return self.djbot_component_manager.add_callback(
            (   Button(style=ButtonStyle.green, label="Now: DJable", id = "djable", custom_id = "djable")
                if self.vcControl.djObj.djdb.find_djable(vid) else
                Button(style=ButtonStyle.red, label="Now: Not DJable", id = "djable", custom_id = "djable") 
            ),
            lambda i: self.switch_djable_callback(i, vc, vid, queue = queue),
        )

    def del_from_db_button(self, vc, vid):
        return self.djbot_component_manager.add_callback(
            Button(style=ButtonStyle.red, label="Del from DB"), 
            lambda i: self.db_del_entry_callback(i, vid)
        )

    def leave_button(self):
        return self.djbot_component_manager.add_callback(
            Button(style=ButtonStyle.gray, label="Leave"), 
            lambda i: self.leave_callback()
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
        await self.vcControl.disconnectVC()
        await self.mChannel.send(
            f"Goodbye!",
            components = [ Button(style=ButtonStyle.blue, label="DJ again", id=f"reDJ") ]
        )


    # --- MORE --- # 
    async def switch_djable_callback(self, interaction, vc, vid, queue = False):
        self.vcControl.djObj.djdb.switch_djable(vid)
        if not queue: 
            # playbox
            await self.update_playing(ViewUpdateType.EDIT, extended = True)
        else: 
            # queue message
            await interaction.edit_origin(
                components = [[
                    self.remove_button(vc, vid),
                    self.switch_djable_button(vc, vid, queue)
                ]]
            )

    async def db_del_entry_callback(self, interaction, vid):
        self.vcControl.djObj.djdb.remove_song(vid)
        await self.vcControl.djObj.notify(self.vcControl.mChannel, f"Removed song from db ({vid})")

