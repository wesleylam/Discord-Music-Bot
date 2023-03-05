# individual discord message
import discord
import ServersHub
from typing import Optional

class PlayBox(discord.ui.View):
    def __init__(self, *, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)
        self.Hub = ServersHub.ServersHub
        self.count = 0
    
    @discord.ui.button(label='SKIP', style=discord.ButtonStyle.red)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button, ):
        await interaction.message.edit(view=self)
        
        print(interaction.guild_id)
        # print(interaction.channel)
        self.Hub.getControl(interaction.guild_id).skip()
        
    @discord.ui.button(label='Not DJable SKIP', style=discord.ButtonStyle.danger)
    async def nskip(self, interaction: discord.Interaction, button: discord.ui.Button, ):
        await interaction.message.edit(view=self)
        
        print(interaction.guild_id)
        # print(interaction.channel)
        self.Hub.getControl(interaction.guild_id).djable()
        self.Hub.getControl(interaction.guild_id).skip()
        
    @discord.ui.button(label='LEAVE', style=discord.ButtonStyle.grey)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button, ):
        await interaction.message.edit(view=self)
        
        print(interaction.guild_id)
        # print(interaction.channel)
        self.Hub.getControl(interaction.guild_id).leave()
        