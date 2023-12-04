import os
import discord
from discord.ext import commands

from querybot import BasicCog, QueryCog, AutoCompleteCog, Database

cogs = [ BasicCog, QueryCog, AutoCompleteCog ]

TOKEN = os.getenv("DISCORD_TOKEN")

CONNECT_OPTIONS = { "database": "querybot.sqlite3" }

class QueryBot(commands.Bot):
    async def setup_hook(self) -> None:
        db = Database(CONNECT_OPTIONS)
        await db.create_table()

        for cog in cogs:
            await self.add_cog(cog(self, db))

bot = QueryBot(
    command_prefix="s!",
    intents=discord.Intents.none(),
)

@bot.event
async def on_ready():
    await bot.tree.sync()

bot.run(TOKEN)
