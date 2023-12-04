import discord
from discord import app_commands
from discord.ext import commands


class BasicCog(commands.Cog):
    @app_commands.command(name="ping")
    async def ping(self, interaction: discord.Interaction) -> None:
        """
        Pings the bot
        """
        await interaction.response.send_message("Pong!", ephemeral=True)
