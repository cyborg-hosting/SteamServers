import socket
from typing import List
from discord.ext import commands
import discord
from discord import app_commands
from querybot import database
from .database import Host
import a2s


class QueryCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: database.Database):
        self.bot = bot
        self.db = db
    
    async def server_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[Host]]:
        return await self.db.server_autocomplete(interaction, current)
        
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

        host = await self.db.select_server(interaction.guild_id, query)
        if not host:
            host = Host.fromHost(query)

        try:
            info: a2s.SourceInfo = await a2s.ainfo(host)

            embed = discord.Embed(title=info.server_name)
            embed.set_author(name="Server Informnation")
            embed.add_field(name="Host", value=str(host))
            embed.add_field(name="Map", value=info.map_name)
            embed.add_field(name="Players", value=f'{info.player_count}/{info.max_players}')
            embed.add_field(name="Game", value=info.game or "Unknown")
            embed.set_footer(text=("VAC Secured" if info.vac_enabled else "Insecure") + (" + Password Protected" if info.password_protected else ""))

            await interaction.followup.send(embed=embed)
        except socket.timeout:
            interaction.followup.send("Server timeout! Check the IP:Port")
        except socket.gaierror:
            interaction.followup.send("Resolution error! Check the IP:Port")
        except Exception:
            interaction.followup.send("Unknown error! Check the command, and contact support if this continues.")


        

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

        host = await self.db.select_server(interaction.guild_id, query)
        if not host:
            host = Host.fromHost(query)
        
        try:
            info: a2s.SourceInfo = await a2s.aplayers(host)

            if not info or len(info) == 0:
                await interaction.followup.send("Server is empty!")
                return

            table = ""
            for player in info:
                table += "%02d:%02d" % (player.duration // 3600, (player.duration % 3600) // 60) + " | " + player.name + "\n"
            await interaction.followup.send("```r\n"+str(table)+"```")
        except socket.timeout:
            await interaction.followup.send("Server timeout! Check the IP:Port")
        except socket.gaierror:
            await interaction.followup.send("Resolution error! Check the IP:Port")
        except Exception:
            await interaction.followup.send("Unknown error! Check the command, and contact support if this continues.")


