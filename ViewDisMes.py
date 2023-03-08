# individual discord message
import discord
import ServersHub
from typing import Optional

class PlayBox(discord.ui.View):
    def __init__(self, *, vID = None, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)
        self.Hub = ServersHub.ServersHub
        self.count = 0
        self.vID = vID
        
    def setVID(self, vID):
        if vID != self.vID:
            self.vID = vID
    
    @discord.ui.button(label='SKIP', style=discord.ButtonStyle.blurple)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button, ):
        print("SKIP CLICKED")
        # print(interaction.channel)
        self.Hub.getControl(interaction.guild_id).skip()
        
    @discord.ui.button(label='Not DJable SKIP', style=discord.ButtonStyle.danger)
    async def nskip(self, interaction: discord.Interaction, button: discord.ui.Button, ):
        print("NSKIP CLICKED")
        # print(interaction.channel)
        self.Hub.getControl(interaction.guild_id).djable(self.vID, False)
        self.Hub.getControl(interaction.guild_id).skip()
        
    @discord.ui.button(label='LEAVE', style=discord.ButtonStyle.grey)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button, ):
        print("LEAVE CLICKED")
        self.Hub.getControl(interaction.guild_id).leave()
        
        
    # def patch_note_box(gif):
    #     # execute git log and store it in log
    #     os.system(f'git log -10 --pretty=format:"%ad%x09%s" --date=short > {patch_note_log}')
    #     # extract log 
    #     notes = parse_patch_note_log()
    #     color = rand_color()
    #     embed = discord.Embed(title = "Patch Note", color=color)
    #     for date, commit in notes.items():
    #         embed.add_field(name = date, value = commit, inline=False)
    #     embed.set_image(url = gif)
    #     embed.set_footer(text = "............................................................................................................................................................................................................................................................................................................................................")
    #     return embed