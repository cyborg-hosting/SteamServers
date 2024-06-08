import logging
from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from querybot.database import Database
from querybot.host import Host, Server

logger = logging.getLogger(__name__)

class AdministrationCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database):
        self.bot = bot
        self.db = db

    async def server_name_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        guild_id = interaction.guild_id
        return [ app_commands.Choice(name=server.name, value=server.name) async for server in self.db.server_autocomplete(guild_id=guild_id, current=current) ]
    
    @app_commands.command(name="create_server")
    @app_commands.describe(
            hostname="Hostname of the server. For example, example.com or 198.51.100.242",
            port="Port of the server. For example, 27015",
            name="The name to give the server. For example, Awesome RP",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def create_server(self, interaction: discord.Interaction, name: str, hostname: str, port: int) -> None:
        """
        Create a new saved server.
        """
        if not 1 <= len(name) <= 100:
            await interaction.response.send_message("Name must be between 1 and 100 characters!", ephemeral=True)
            return
        await interaction.response.defer()

        try:
            try:
                host = Host.parse(hostname, port)
                server = Server(name, host)
            except ValueError:
                await interaction.followup.send(content="You submitted malformed host")
                return

            guild_id = interaction.guild_id

            if await self.db.insert_server(guild_id=guild_id, server=server):
                await interaction.followup.send(content="Created!")
            else:
                await interaction.followup.send(content="Either this server name or server address is already being used!")
        except Exception as e:
            await interaction.followup.send("Unknown error! Check the command, and contact support if this continues.")
            logger.exception("UNKNOWN ERROR")


    @app_commands.command(name="servers")
    async def servers(self, interaction: discord.Interaction) -> None:
        """
        Lists saved servers 
        """
        await interaction.response.defer(ephemeral=True)

        try:
            guild_id = interaction.guild_id
            if results := await self.db.select_servers(guild_id=guild_id):
                embed = discord.Embed(title="Server list")
                for server in results:
                    name = server.name
                    host = str(server.host)
                    embed.add_field(name=name, value=host)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(content="No servers added! Add one with `/create_server`")
        except Exception as e:
            await interaction.followup.send("Unknown error! Check the command, and contact support if this continues.")
            logger.exception("UNKNOWN ERROR")

    @app_commands.command(name="delete_server")
    @app_commands.autocomplete(name=server_name_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def delete_server(self, interaction: discord.Interaction, name: str) -> None:
        """
        Deletes a saved server.
        """
        await interaction.response.defer()

        try:
            guild_id = interaction.guild_id
            if await self.db.delete_server(guild_id=guild_id, name=name):
                await interaction.followup.send(content=f"Server `{name}` deleted")
            else:
                await interaction.followup.send(content="Server not found!")
        except Exception as e:
            await interaction.followup.send("Unknown error! Check the command, and contact support if this continues.")
            logger.exception("UNKNOWN ERROR")