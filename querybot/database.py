import logging
from typing import AsyncGenerator, Iterable

import aiosqlite

from querybot.host import Host, Server

logger = logging.getLogger(__name__)

SQL_CREATE_TABLE = r"""
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

SQL_SELECT = r"SELECT name, address, port FROM server WHERE guild_id = ? AND name = ?;"
SQL_SELECT_ALL = r"SELECT name, address, port FROM server WHERE guild_id = ?;"
SQL_INSERT = r"INSERT INTO server ( guild_id, name, address, port ) VALUES ( ?, ?, ?, ? );"
SQL_DELETE = r"DELETE FROM server WHERE guild_id = ? AND name = ?;"
SQL_AUTOCOMPLETE = r"SELECT name, address, port FROM server WHERE guild_id = ? AND name LIKE ? || '%';"

class Database:
    def __init__(self, **options):
        self.__options = options
    
    async def create_table(self):
        async with aiosqlite.connect(**self.__options) as connection:
            await connection.executescript(SQL_CREATE_TABLE)

    async def select_server(self, guild_id: int, name: str) -> Server | None:
        try:
            async with aiosqlite.connect(**self.__options) as connection:
                connection.row_factory = aiosqlite.Row
                async with connection.execute(SQL_SELECT, (guild_id, name)) as cursor:
                    async for row in cursor:
                        return Server(row["name"], Host(row["address"], row["port"])) 
                    return None
        except aiosqlite.Error:
            logger.exception("database.select_server")
            return None
    async def select_servers(self, guild_id: int) -> Iterable[Server]:
        try:
            async with aiosqlite.connect(**self.__options) as connection:
                connection.row_factory = aiosqlite.Row
                async with connection.execute(SQL_SELECT_ALL, (guild_id,)) as cursor:
                    return [ Server(row["name"], Host(row["address"], row["port"])) async for row in cursor ]
        except aiosqlite.Error:
            logger.exception("database.select_servers")
            return []
    async def insert_server(self, guild_id: int, server: Server) -> bool:
        name, hostname, port = server.name, server.host.hostname, server.host.port
        try:
            async with aiosqlite.connect(**self.__options) as connection:
                await connection.execute(SQL_INSERT, (guild_id, name, hostname, port))
                await connection.commit()
                return True
        except aiosqlite.IntegrityError:
            return False
        except aiosqlite.Error:
            logger.exception("database.insert_server")
            return False
    async def delete_server(self, guild_id: int, name: str) -> bool:
        try:
            async with aiosqlite.connect(**self.__options) as connection:
                await connection.execute(SQL_DELETE, (guild_id, name))
                await connection.commit()
                return True
        except aiosqlite.Error:
            logger.exception("database.delete_server")
            return False
            
    async def server_autocomplete(self, guild_id: int | None, current: str) -> AsyncGenerator[Server, None]:
        try:
            async with aiosqlite.connect(**self.__options) as connection:
                connection.row_factory = aiosqlite.Row
                async with connection.execute(SQL_AUTOCOMPLETE, (guild_id, current)) as cursor:
                    async for row in cursor:
                        yield Server(row["name"], Host(row["address"], row["port"])) 
        except aiosqlite.Error:
            logger.exception("database.server_autocomplete")
            raise StopAsyncIteration
