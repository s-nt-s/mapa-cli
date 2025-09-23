#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import time
from datetime import date, timedelta
from textwrap import dedent

import slixmpp
from slixmpp.stanza import Message
from slixmpp.plugins.xep_0363 import XEP_0363

from cli import str_main
from core.autdriver import AutenticaException
from core.filemanager import CNF, FileManager
from core.timeout import timeout
from os import listdir
from os.path import isfile, join, expanduser, commonpath, relpath, basename
from asyncio import create_task
from mimetypes import guess_type
from core.trama import ICS_FESTIVOS, ICS_CUADRANTE
from pathlib import Path

parser = argparse.ArgumentParser(
    description='Arranca un bot xmpp para interactuar con mapa-cli')
parser.add_argument('--amistoso', action='store_true', help=dedent('''
    Autoaceptar peticiones de amistad.
    Usa este parámetro solo la primera vez, para que el bot accepte tu petición de amistad.
    Cuando el bot ya sea tu amigo, omite este parámetro para evitar que responda a otra gente.
    '''.strip()))
parser.add_argument(
    '--send', help="Manda por chat el resultado del comando pasado como argumento")

logging.basicConfig(level=CNF.xmpp.LOG, format='%(levelname)-8s %(message)s')
logger = logging.getLogger(__name__)

def full_ls():
    files: set[str] = set()
    for d in map(expanduser, (CNF.nominas, CNF.expediente, CNF.retribuciones, CNF.informe_horas)):
        for f in listdir(d):
            f = join(d, f)
            if isfile(f):
                files.add(f)
    return tuple(sorted(files))

def get_root_and_rel(files: tuple[str, ...]):
    root = commonpath(files)
    files = [relpath(f, root) for f in files]
    return root, tuple(files)


class ConnectionLost(Exception):
    pass


class BaseBot(slixmpp.ClientXMPP):
    def __init__(self):
        super().__init__(CNF.xmpp.user, CNF.xmpp.pssw)
        self.use_ipv6 = False

    def __run(self, loop: bool, host: str, port: int):
        while True:
            if host and port:
                logger.info(f"Connecting {CNF.xmpp.user} via {host}:{port}")
                self.connect(address=(host, port))
            else:
                logger.info(f"Connecting {CNF.xmpp.user}")
                self.connect()
            logger.info("Bot started.")
            self.process()
            if not loop:
                return
            time.sleep(5)
   
    def run(self, loop=True):
        self.__run(loop, None, None)

    def connection_lost(self, *args, **kwargs):
        super().connection_lost(*args, **kwargs)
        self.disconnect()


class ApiBot(BaseBot):

    def __init__(self, amistoso=False):
        super().__init__()
        self.auto_reconnect = True
        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0004') # Data Forms
        self.register_plugin('xep_0060') # PubSub
        self.register_plugin('xep_0199') # XMPP Ping
        self.register_plugin('xep_0363') # HTTP File Upload
        self.register_plugin('xep_0066') # Out of Band Data (OOB)

        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)
        if amistoso:
            self.auto_authorize = True
            self.auto_subscribe = True

    def start(self, event):
        self.send_presence()
        self.get_roster()

    def message(self, msg: Message):
        if msg['type'] in ('chat', 'normal') and msg['from'].bare == CNF.xmpp.me:
            text = msg['body'].strip().lower()
            files = full_ls()
            rlp = self.command(msg, text)
            if rlp:
                logger.debug(text)
                msg.reply("```\n"+rlp+"\n```").send()
                logger.debug(rlp)
            new_files = set(full_ls()).difference(files)
            if new_files:
                create_task(self.send_file(msg, *sorted(new_files)))
            elif text == "festivos":
                create_task(self.send_file(msg, FileManager.get().resolve_path(ICS_FESTIVOS)))
            elif text == "cuadrante":
                create_task(self.send_file(msg, FileManager.get().resolve_path(ICS_CUADRANTE)))

    def command(self, msg: Message, text: str):
        if not text:
            return None
        if text == "ping":
            return "pong"
        try:
            reply = str_main(*text.split())
            if isinstance(reply, str) and reply:
                return reply
        except AutenticaException as e:
            return str(e)
        root, files = get_root_and_rel(full_ls())
        if text == "ls":
            return "\n".join(files)
        ok_files = []
        for f in files:
            if text in f:
                ok_files.append(f)
        if len(ok_files) == 0:
            return
        if len(ok_files)==1:
            create_task(self.send_file(msg, join(root, ok_files[0])))
            return
        return "\n".join(ok_files)

    async def send_file(self, msg: Message, *files: str):
        plg: XEP_0363 = self['xep_0363']
        for file in files:
            if isinstance(file, Path):
                file = str(file)
            if not isfile(file):
                continue
            content_type, _ = guess_type(file)
            if content_type is None:
                content_type = 'application/octet-stream'
            url = await plg.upload_file(
                filename=file,
                content_type=content_type
            )
            reply = msg.reply(url)
            reply['oob']['url'] = url
            reply['oob']['desc'] = basename(file)
            reply.send()
    

class SendBot(BaseBot):
    def __init__(self, msg, *args, **kwargs):
        super().__init__()
        self.msg = msg
        self.add_event_handler("session_start", self.start)

    def start(self, event):
        self.send_presence()
        self.get_roster()
        self.send_message(mto=CNF.xmpp.me,
                          mbody="```\n"+self.msg+"\n```",
                          mtype='chat')
        self.disconnect()

    def run(self):
        with timeout(seconds=10):
            try:
                super().run(loop=False)
            except TimeoutError:
                pass


if __name__ == '__main__':
    arg = parser.parse_args()
    if arg.send:
        msg = None
        f = "msg/%s.txt" % arg.send
        old = FileManager.get().load(f)
        if arg.send == "novedades":
            msg = str_main(arg.send, desde=5)
        elif arg.send == "nominas" and old:
            today = date.today()
            if today.day < 20:
                today = today - timedelta(days=(today.day+1))
            ym = today.strftime("%Y.%m-")
            if ym in old:
                sys.exit()
        if msg is None and arg.send:
            msg = str_main(arg.send)
        if msg:
            if old is None or old != msg:
                bot = SendBot(msg)
                bot.run()
            FileManager.get().dump(f, msg)
        sys.exit()
    xmpp = ApiBot(amistoso=arg.amistoso)
    xmpp.run()
