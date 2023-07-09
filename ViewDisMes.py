# individual discord message
import discord
import ServersHub
from typing import Optional

class PlayBox(discord.ui.View):
    def __init__(self, *, vID = None, timeout: Optional[float] = 1800):
        super().__init__(timeout=timeout)
        self.Hub = ServersHub.ServersHub
        self.count = 0
        self.vID = vID
        
    async def on_timeout(self):
        super().on_timeout()
        
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
        