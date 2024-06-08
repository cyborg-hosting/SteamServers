import asyncio
import re
from socket import AF_INET
from typing import NamedTuple

import aiodns

IP_REGEX = re.compile(r"^(?P<IP>(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))$")
HOSTNAME_REGEX = re.compile(r"^(?P<HOSTNAME>(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9]))$")
PORT_REGEX = re.compile(r"^(?P<PORT>([0-9]|[1-9][0-9]{1,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5]))$")

IP_PORT_REGEX = re.compile(r"^(?P<IP>(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])):(?P<PORT>([0-9]|[1-9][0-9]{1,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5]))$")
HOSTNAME_PORT_REGEX = re.compile(r":(?P<PORT>([0-9]|[1-9][0-9]{1,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5]))$")

class Host:
    def __init__(self, hostname: str | bytes, port: int):
        if not isinstance(port, int):
            raise TypeError(f"Invalid port number: The value {port} is not valid. It should have type of int.")
        elif not (0 <= port <= 65535):
            raise ValueError(f"Invalid port number: The value {port} is not valid. It should be between 0 and 65535.")
        
        if isinstance(hostname, bytes):
            if len(hostname) != 4:
                raise ValueError(f"Invalid IP address: The value {hostname} is not valid. It should have length of 4 bytes.")
        elif isinstance(hostname, str):
            pass
        else:
            raise TypeError(f"Invalid hostname: The value {hostname} is not valid. It should have type of either str or bytes.")

        self.hostname = hostname
        self.port = port
    
    async def resolve(self):
        try:
            resolver = aiodns.DNSResolver(loop=asyncio.get_running_loop())
            await resolver.gethostbyname(self.hostname, AF_INET)
        except aiodns.error.DNSError:
            raise ValueError(f"Invalid hostname: The value {self.hostname} is not valid.")

    @staticmethod
    def parse(hostname: str, port: str):
        if not HOSTNAME_REGEX.match(hostname) or not IP_REGEX.match(hostname):
            raise ValueError
        port = int(port)
        return Host(hostname, port)

    @staticmethod
    def parse_socket_address(socket_address: str):
        if result := IP_PORT_REGEX.search(socket_address):
            ip, port = result.group('IP'), int(result.group('PORT'))
            return Host(ip, port)
        elif result := HOSTNAME_PORT_REGEX.search(socket_address):
            hostname, port = result.group('HOSTNAME'), int(result.group('PORT'))
            return Host(hostname, port)
        else:
            raise ValueError
    
    def __str__(self):
        return f"{self.hostname}:{self.port}"
    
    def __repr__(self):
        return f"Host({repr(self.hostname)}, {repr(self.port)})"

class Server(NamedTuple):
    name: str
    host: Host