from typing import Dict
import re

__all__ = ['MessageParser']

letter = r'a-zA-Z'
digit = r'0-9'
LD = letter + digit
hyphen = r'\x2d'
LDH = LD + hyphen
special = r'\x5b-\x60\x7b-\x7d'  # []\`_^{|}
nocrlfspcl = r'\x01-\x09\x0b-\x0c\x0e-\x1f\x21-\x39\x3b-\xff'
nowhite = rf'{nocrlfspcl}\x3a'

name = rf'[{LD}](?:[{LDH}]*[{LD}])*'
host = rf'{name}(?:\.{name})*'
nick = rf'[{letter}][{LD}{special}{hyphen}]{{,8}}'
user = rf'[{nowhite}]+'
prefix = rf'{host}|\:{nick}\!\~{{,1}}{user}\@{host}'

command = rf'[{letter}]+|[{digit}]{{3}}'
middle = rf'[{nocrlfspcl}]{{1}}[{nocrlfspcl}\x3a]*'
trailing = rf'[{nocrlfspcl}\x20\x3a]*'
params = (
    rf'(?: {middle}){{,14}}(?: :{trailing}){{,1}}'
    rf'|(?: {middle}){{14}}(?: :{{,1}}{trailing})'
)
msg = (
    rf'^(?:(?P<prefix>\:{prefix}) ){{0,1}}'
    rf'(?P<command>{command}){{1}}(?P<params>{params}{{,1}})'
)


class PartialMessageError(Exception):
    ...


class MessageParser:
    def __init__(self, encoding: str):
        self.re = re.compile(msg.encode(encoding))
        self.encoding = encoding

    def __call__(self, msg: bytes) -> Dict[str, bytes]:
        if msg[-2:] != b'\r\n':
            raise PartialMessageError

        if match := self.re.match(msg):
            return match.groupdict()
        else:
            raise ValueError
