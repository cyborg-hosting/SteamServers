from os import getenv

import discord
from discord.ext import commands

from querybot import AdministrationCog, BasicCog, Database, QueryCog

cogs = [ AdministrationCog, BasicCog, QueryCog ]

TOKEN = getenv("DISCORD_TOKEN")

class QueryBot(commands.Bot):
    async def setup_hook(self) -> None:
        db = Database(database="querybot.sqlite3")
        await db.create_table()

        for cog in cogs:
            await self.add_cog(cog(self, db))

intents=discord.Intents.none()
intents.message_content = True

bot = QueryBot(
    command_prefix="s!",
    intents=intents,
)

@bot.event
async def on_ready():
    await bot.tree.sync()

bot.run(TOKEN)
