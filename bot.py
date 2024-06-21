#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import sys

import slixmpp
import time
from textwrap import dedent

from cli import str_main
from core.filemanager import CNF, FileManager
from core.timeout import timeout
from core.autdriver import AutenticaException
from datetime import date, timedelta

parser = argparse.ArgumentParser(
    description='Arranca un bot xmpp para interactuar con mapa-cli')
parser.add_argument('--amistoso', action='store_true', help=dedent('''
    Autoaceptar peticiones de amistad.
    Usa este parámetro solo la primera vez, para que el bot accepte tu petición de amistad.
    Cuando el bot ya sea tu amigo, omite este parámetro para evitar que responda a otra gente.
    '''.strip()))
parser.add_argument(
    '--send', help="Manda por chat el resultado del comando pasado como argumento")

logging.basicConfig(level=CNF.xmpp.get('LOG', logging.INFO), format='%(levelname)-8s %(message)s')
logger = logging.getLogger(__name__)


class ConnectionLost(Exception):
    pass


class BaseBot(slixmpp.ClientXMPP):
    def __init__(self):
        super().__init__(CNF.xmpp.user, CNF.xmpp.pssw)

    def run(self, loop=True):
        while True:
            self.connect(('443.suchat.org', 443), force_starttls=False, disable_starttls=True, use_ssl=True)
            #self.connect()
            logger.info("Bot started.")
            self.process()
            if not loop:
                return
            time.sleep(5)

    def connection_lost(self, *args, **kargv):
        super().connection_lost(*args, **kargv)
        self.disconnect()


class ApiBot(BaseBot):

    def __init__(self, amistoso=False):
        super().__init__()
        self.auto_reconnect = True
        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0004') # Data Forms
        self.register_plugin('xep_0060') # PubSub
        self.register_plugin('xep_0199') # XMPP Ping
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)
        if amistoso:
            self.auto_authorize = True
            self.auto_subscribe = True

    def start(self, event):
        self.send_presence()
        self.get_roster()

    def message(self, msg):
        if msg['type'] in ('chat', 'normal') and msg['from'].bare == CNF.xmpp.me:
            text = msg['body'].strip().lower()
            rlp = self.command(text)
            if rlp:
                logger.debug(text)
                msg.reply("```\n"+rlp+"\n```").send()
                logger.debug(rlp)

    def command(self, text):
        if not text:
            return None
        if text == "ping":
            return "pong"
        try:
            return str_main(*text.split())
        except AutenticaException as e:
            return str(e)


class SendBot(BaseBot):
    def __init__(self, msg, *args, **karg):
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
