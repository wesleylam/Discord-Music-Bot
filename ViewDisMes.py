# individual discord message
import discord
import ServersHub
from typing import Optional
from const import SongInfo
from const.helper import vid_to_url

class QueueSelect(discord.ui.Select):
    def __init__(self, options, hub, guild_id):
        super().__init__(placeholder="Select a song to remove...", min_values=1, max_values=1, options=options)
        self.hub: ServersHub.ServersHub = hub
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        index = int(self.values[0])
        title_to_remove = next((opt.label for opt in self.options if opt.value == self.values[0]), "Song")
        self.hub.getControl(self.guild_id).remove_at(index, interaction.user)
        await interaction.response.send_message(f"Removed: {title_to_remove}", ephemeral=True)

class QueueView(discord.ui.View):
    def __init__(self, hub, guild_id, queue_items):
        super().__init__()
        options = []
        for i, (source, songInfo, player) in enumerate(queue_items[:25]):
            label = songInfo.Title
            if len(label) > 100:
                label = label[:97] + "..."
            val = str(i)
            options.append(discord.SelectOption(label=label, value=val, description=f"Added by {player}"))

        if options:
            self.add_item(QueueSelect(options, hub, guild_id))

class SuggestionSelect(discord.ui.Select):
    def __init__(self, options, hub, guild_id):
        super().__init__(placeholder="Select a song to play...", min_values=1, max_values=1, options=options)
        self.hub = hub
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        vid = self.values[0]
        url = vid_to_url(vid)
        selected_label = next((opt.label for opt in self.options if opt.value == vid), "Song")
        
        await interaction.response.send_message(f"Queuing **{selected_label}**...", ephemeral=True)
        # Run play in executor to avoid blocking
        await self.hub.loop.run_in_executor(None, lambda: self.hub.getControl(self.guild_id).play(url, author=interaction.user))

class SuggestionView(discord.ui.View):
    def __init__(self, hub, guild_id, suggestions: list[SongInfo.SongInfo]):
        super().__init__()
        options = []
        for song in suggestions:
            label = song.Title[:95]
            val = song.vID
            # desc = song.ChannelID[:100] if song.ChannelID else None
            desc = song.Duration if song.Duration else None
            options.append(discord.SelectOption(label=label, value=val, description=desc))
        
        if options:
            self.add_item(SuggestionSelect(options, hub, guild_id))

class RandomSongSelect(discord.ui.Select):
    def __init__(self, options, hub, guild_id):
        super().__init__(placeholder="Select a random song to play...", min_values=1, max_values=1, options=options)
        self.hub = hub
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        vid = self.values[0]
        url = vid_to_url(vid)
        selected_label = next((opt.label for opt in self.options if opt.value == vid), "Song")
        
        await interaction.response.send_message(f"Queuing **{selected_label}**...", ephemeral=True)
        await self.hub.loop.run_in_executor(None, lambda: self.hub.getControl(self.guild_id).play(url, author=interaction.user))

class RandomSongView(discord.ui.View):
    def __init__(self, hub, guild_id, songs: list[SongInfo.SongInfo]):
        super().__init__()
        options = []
        for song in songs:
            label = song.Title[:95]
            val = song.vID
            desc = f"Duration: {song.Duration}" if song.Duration else None
            options.append(discord.SelectOption(label=label, value=val, description=desc))
        
        if options:
            self.add_item(RandomSongSelect(options, hub, guild_id))

class PlayBox(discord.ui.View):
    def __init__(self, *, songInfo: SongInfo.SongInfo = None, timeout: Optional[float] = 1800):
        super().__init__(timeout=timeout)
        self.Hub = ServersHub.ServersHub
        self.count = 0
        self.songInfo = songInfo
        self.vID = songInfo.vID if songInfo else None
        
    async def on_timeout(self):
        await super().on_timeout()
        
    def setVID(self, vID):
        if vID != self.vID:
            self.vID = vID
    
    @discord.ui.button(label='⏭️', style=discord.ButtonStyle.blurple)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button, ):
        print("SKIP CLICKED")
        # print(interaction.channel)
        self.Hub.getControl(interaction.guild_id).skip()
        
    @discord.ui.button(label='🗑️⏭️', style=discord.ButtonStyle.danger)
    async def nskip(self, interaction: discord.Interaction, button: discord.ui.Button, ):
        print("NSKIP CLICKED")
        # print(interaction.channel)
        self.Hub.getControl(interaction.guild_id).djable(self.vID, False)
        self.Hub.getControl(interaction.guild_id).skip()

    @discord.ui.button(label='💡', style=discord.ButtonStyle.blurple)
    async def suggest(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True, ephemeral=True)
        suggestions: list[SongInfo.SongInfo] = await self.Hub.getControl(interaction.guild_id).fetchSuggestions(self.songInfo)
        
        if not suggestions:
            await interaction.followup.send("No suggestions found (API might be restricted).", ephemeral=True)
        else:
            view = SuggestionView(self.Hub, interaction.guild_id, suggestions[:25])
            await interaction.followup.send("Suggestions based on current song:", view=view, ephemeral=True)

    @discord.ui.button(label='🎲', style=discord.ButtonStyle.blurple)
    async def random(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True, ephemeral=True)
        random_songs = await self.Hub.getControl(interaction.guild_id).fetchRandomSongs(n=15)
        
        if not random_songs:
            await interaction.followup.send("Could not find any random songs from the database.", ephemeral=True)
        else:
            view = RandomSongView(self.Hub, interaction.guild_id, random_songs[:25])
            await interaction.followup.send("Here are some random songs from the database:", view=view, ephemeral=True)

    @discord.ui.button(label='📜', style=discord.ButtonStyle.green)
    async def queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        print("QUEUE CLICKED")
        queue = self.Hub.getControl(interaction.guild_id).getQueue()
        if len(queue) == 0:
            await interaction.response.send_message("(No queued item)", ephemeral=True, delete_after=10)
        else:
            items = [songInfo.Title for source, songInfo, player in queue]
            displayStr = "Current queue:\n" + "\n".join(items[:15])
            if len(items) > 15:
                displayStr += f"\n... and {len(items)-15} more"
            view = QueueView(self.Hub, interaction.guild_id, queue)
            await interaction.response.send_message(displayStr, ephemeral=True, view=view, delete_after=30)
        
    @discord.ui.button(label='🛑', style=discord.ButtonStyle.grey)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button, ):
        print("LEAVE CLICKED")
        self.Hub.getControl(interaction.guild_id).leave()
