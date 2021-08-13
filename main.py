import select
import socket
import threading
import time
import yaml
# from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from message_parser import MessageParser


with open('settings.yaml', 'r') as settings_file:
    CONF = yaml.safe_load(settings_file)

CONF['server'] = (CONF['server'], CONF.pop('port'))


KST = timezone(timedelta(hours=9))


@dataclass
class IRCUser:
    nickname: str
    username: str
    # hostname: str
    mode: int
    realname: str

    def __hash__(self):
        return hash(self.nickname)


@dataclass
class IRCChannel:
    name: str
    users: List[IRCUser]

    def __hash__(self):
        return hash(self.name)


@dataclass
class IRCStatus:
    nickname: str
    username: str
    mode: int
    realname: str
    channels: List[IRCChannel]
    connected_at: Optional[datetime]

    def __post_init__(self):
        self.me = IRCUser(
            self.nickname, self.username, self.mode, self.realname,
        )


class MessageHandler:
    def __init__(self, client: 'IRCClient'):
        self.client = client
        self.parser = MessageParser(client.encoding)

    def __call__(self, msg: bytes):
        parsed = self.parser(msg)
        command = parsed['command'].lower()
        if command == b'ping':
            return self.__getattribute__('msg_ping')(parsed)
        if command == b'004':
            self.client.registered = True
        return self._msg(parsed)

    def msg_ping(self, parsed: dict[str, bytes]):
        self.client.socket.send(b'PONG' + parsed['params'] + b'\r\n')
        return True

    def _msg(self, parsed: dict[str, bytes]):
        print(*(v for v in parsed.values() if v))
        return True


class IRCClient:
    def __init__(
        self, server: Tuple[str, int], encoding: str, password: str,
        nickname: str, username: str, mode: int, realname: str,
        timeout: int,
    ):
        self.server = server
        self.encoding = encoding
        self.password = password
        self.status = IRCStatus(
            nickname, username, mode, realname, [], None
        )
        self.timeout = timeout
        self.registered = False

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.handler = MessageHandler(self)
        self.thread = threading.Thread(target=self.listen, daemon=True)

    def listen(self):
        while True:
            READ, _, __ = select.select([self.socket], [], [])
            if READ:
                data = READ[0].recv(4096)
                if not data:
                    continue
                messages = [line for line in data.split(b'\r\n') if line]
                for msg in messages:
                    self.handler(msg)

    def connect(self):
        self.socket.connect(self.server)
        self.thread.start()
        self.send(
            f'NICK {self.status.nickname}\r\n'
            f'USER {self.status.username} * 0 :{self.status.realname}'
        )

        timeout_counter = 0
        while not self.registered and timeout_counter < self.timeout:
            time.sleep(1)
            timeout_counter += 1

    def send(self, msg):
        return self.socket.send(f'{msg}\r\n'.encode(self.encoding))

    def recv(self, size=512, *args):
        return self.socket.recv(size, *args)


irc = IRCClient(**CONF)

if __name__ == '__main__':
    irc.connect()
    while True:
        INPUT = input('IRC > ')
        if not INPUT:
            continue
        irc.send(INPUT)
