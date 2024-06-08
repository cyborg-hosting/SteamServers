import logging
import socket
from typing import List

import a2s
import discord
from discord import app_commands
from discord.ext import commands

from querybot.database import Database
from querybot.host import Host

logger = logging.getLogger(__name__)

class QueryCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database):
        self.bot = bot
        self.db = db
    
    async def server_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        guild_id = interaction.guild_id
        return [ app_commands.Choice(name=server.name, value=str(server.host)) async for server in self.db.server_autocomplete(guild_id=guild_id, current=current) ]

    @app_commands.command(name="query")
    @app_commands.autocomplete(query=server_autocomplete)
    @app_commands.describe(
        query="The IP:Port to query. For example, 144.12.123.51:27017"
    )
    async def query(self, interaction: discord.Interaction, query: str):
        """
        Queries a server
        """
        await interaction.response.defer()

        try:
            guild_id = interaction.guild_id

            if ':' in query:
                try:
                    host = Host.parse_socket_address(query)
                except ValueError:
                    await interaction.followup.send(f"You entered malformed input: {query}")
                    return
            else:
                host = await self.db.select_server(guild_id=guild_id, name=query)
                if not host:
                    await interaction.followup.send(f"There is no server with given query: {query}")
                    return
            
            try:
                await host.resolve()
            except ValueError:
                await interaction.followup.send(f"Failed to resolve DNS on given host: {host}")
                return
            
            try:
                info = await a2s.ainfo((host.hostname, host.port))
            except socket.timeout:
                await interaction.followup.send("The server did not respond to the query in a timely fashion.")
                return
            except socket.gaierror:
                await interaction.followup.send(f"Failed to resolve DNS on given host: {host}")
                return
            
            embed = discord.Embed(title=info.server_name)
            embed.set_author(name="Server Information")
            embed.add_field(name="Host", value=str(host))
            embed.add_field(name="Map", value=info.map_name)
            embed.add_field(name="Players", value=f'{info.player_count}/{info.max_players}')
            embed.add_field(name="Game", value=info.game or "Unknown")
            embed.set_footer(text=("VAC Secured" if info.vac_enabled else "Insecure") + (" + Password Protected" if info.password_protected else ""))
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send("Unknown error! Check the command, and contact support if this continues.")
            logger.exception("UNKNOWN ERROR")

    @app_commands.command(name="query_players")
    @app_commands.autocomplete(query=server_autocomplete)
    @app_commands.describe(
            query="The IP:Port to query. For example, 144.12.123.51:27017"
    )
    async def query_players(self, interaction: discord.Interaction, query: str):
        """
        Queries a server and returns the players
        """
        await interaction.response.defer()

        try:
            guild_id = interaction.guild_id

            if ':' in query:
                try:
                    host = Host.parse_socket_address(query)
                except ValueError:
                    await interaction.followup.send(f"You entered malformed input: {query}")
                    return
            else:
                host = await self.db.select_server(guild_id=guild_id, name=query)
                if not host:
                    await interaction.followup.send(f"There is no server with given query: {query}")
                    return
            
            try:
                await host.resolve()
            except ValueError:
                await interaction.followup.send(f"Failed to resolve DNS on given host: {host}")
                return
            
            try:
                info = await a2s.aplayers((host.hostname, host.port))
            except socket.timeout:
                await interaction.followup.send("The server did not respond to the query in a timely fashion.")
                return
            except socket.gaierror:
                await interaction.followup.send(f"Failed to resolve DNS on given host: {host}")
                return

            if not info or len(info) == 0:
                await interaction.followup.send("Server is empty!")
                return
            
            table = ""
            for player in info:
                hour, minute, name = int(player.duration) // 3600, (int(player.duration) % 3600) // 60, player.name
                table += f"{hour:02}:{minute:02} | {name}\n"
            await interaction.followup.send("```r\n"+str(table)+"```")
        except Exception as e:
            await interaction.followup.send("Unknown error! Check the command, and contact support if this continues.")
            logger.exception("UNKNOWN ERROR")
