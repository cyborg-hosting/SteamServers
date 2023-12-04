import sqlite3
from typing import List, NamedTuple, Type
import aiosqlite
from discord.ext import commands
import discord
from discord import app_commands



def verify(t: Type[NamedTuple]) -> Type[NamedTuple]:
    t.__init__ = t._verifier_
    return t

class Host(NamedTuple):
    address: str
    port: int
    def __str__(self) -> str:
        return self.address + ":" + str(self.port)
    @classmethod
    def create(cls, address: str, port: int):
        if not (0 <= port <= 65535):
            raise ValueError("Invalid port number")
        return Host(address, port)
    @classmethod
    def fromHost(cls, host: str):
        address, port = host.split(':', maxsplit=1)
        try:
            return cls.create(address, int(port))
        except ValueError:
            raise ValueError("Malformed host")


class Server(NamedTuple):
    name: str
    host: Host | None

SQL_CREATE_TABLE=r"""
BEGIN;
CREATE TABLE IF NOT EXISTS server (
    guild_id INTEGER NOT NULL, 
    name TEXT NOT NULL CHECK (LENGTH(name) <= 100),
    address TEXT NOT NULL,
    port INTEGER NOT NULL CHECK (port >= 0 AND port <= 65535),
    PRIMARY KEY (guild_id, name)
);
COMMIT;
"""

class Database:
    def __init__(self, options):
        self.options = options
    
    async def create_table(self):
        async with aiosqlite.connect(**self.options) as connection:
            await connection.executescript(SQL_CREATE_TABLE)

    async def server_name_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        async with aiosqlite.connect(**self.options) as connection:
            async with connection.execute(r"SELECT name FROM server WHERE guild_id = ? AND name LIKE ? || '%';", (interaction.guild_id, current)) as cursor:
                return [ app_commands.Choice(name=row[0], value=row[0]) async for row in cursor ]
        
    async def server_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[Host]]:
        async with aiosqlite.connect(**self.options) as connection:
            async with connection.execute(r"SELECT name, address, port FROM server WHERE guild_id = ? AND name LIKE ? || '%';", (interaction.guild_id, current)) as cursor:
                return [ app_commands.Choice(name=row[0], value=str(Host(row[1], row[2]))) async for row in cursor ]
    
    async def select_servers(self, guild_id: int) -> List[Server]:
        async with aiosqlite.connect(**self.options) as connection:
            async with connection.execute(r"SELECT name, address, port FROM server WHERE guild_id = ?;", (guild_id, )) as cursor:
                return [ Server(row[0], Host(row[1], row[2])) async for row in cursor ]

    async def select_server(self, guild_id: int, name: str) -> Host | None:
        async with aiosqlite.connect(**self.options) as connection:
            async with connection.execute(r"SELECT name, address, port FROM server WHERE guild_id = ? AND name = ?;", (guild_id, name)) as cursor:
                if row := await cursor.fetchone():
                    return Host(row[0], row[1])
                else:
                    return None
    
    async def insert_server(self, guild_id: int, server: Server) -> bool:
        async with aiosqlite.connect(**self.options) as connection:
            try:
                connection.execute(r"INSERT INTO server (guild_id, name, address, port) VALUES (?, ?, ?, ?);", (guild_id, server.name, server.host.address, server.host.port))
                return True
            except sqlite3.IntegrityError:
                return False

    async def delete_server(self, guild_id: int, name: str) -> bool:
        async with aiosqlite.connect(**self.options) as connection:
            with connection.execute(r"DELETE FROM server WHERE guild_id = ? AND name = ?", (guild_id, name)) as cursor:
                if cursor.rowcount:
                    return True
                else:
                    return False
    

class AutoCompleteCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database):
        self.bot = bot
        self.db = db

    async def server_name_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        return await self.db.server_name_autocomplete(self, interaction, current)
    
    @app_commands.command(name="create_server")
    @app_commands.describe(
            address="Address(IP) of the server. For example, example.com or 198.51.100.242",
            port="Port of the server. For example, 27015",
            name="The name to give the server. For example, Awesome RP",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def create_server(self, interaction: discord.Interaction, address: str, port: int, name: str) -> None:
        """
        Create a new saved server.
        """
        if not 1 <= len(name) <= 100:
            await interaction.response.send_message("Name must be between 1 and 100 characters!", ephemeral=True)
            return
        await interaction.response.defer()
        
        try:
            if await self.db.insert_server(guild_id=interaction.guild_id, server=Server(name, Host(address, port))):
                await interaction.followup.send(content="Created!")
            else:
                await interaction.followup.send(content="Either this server name or server address is already being used!")
        except ValueError as e:
            await interaction.followup.send(content=f"Error: {e}")

    @app_commands.command(name="servers")
    async def servers(self, interaction: discord.Interaction) -> None:
        """
        Lists saved servers 
        """
        await interaction.response.defer(ephemeral=True)

        if results := await self.db.select_servers(interaction.guild_id):
            embed = discord.Embed(title="Server list")
            for server in results:
                embed.add_field(name=server.name, value=server.host.address+":"+str(server.host.port))
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(content="No servers added! Add one with `/create_server`")

    @app_commands.command(name="delete_server")
    @app_commands.autocomplete(name=server_name_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def delete_server(self, interaction: discord.Interaction, name: str) -> None:
        """
        Deletes a saved server.
        """
        await interaction.response.defer()

        if await self.db.delete_server(interaction.guild_id, name):
            await interaction.followup.send(content=f"Server `{name}` deleted")
        else:
            await interaction.followup.send(content="Server not found!")
