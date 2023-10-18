#!/usr/bin/env python3
import argparse
import re
import sys
from io import StringIO
from typing import Tuple
from os.path import abspath, dirname
from os import chdir
from core.filemanager import FileManager
from unidecode import unidecode


chdir(dirname(abspath(__file__)))

# from core.api import Api
from core.printer import Printer

parser = argparse.ArgumentParser(
    description='Comando para los servicios de intranet.mapa.es')
group = parser.add_mutually_exclusive_group()
group.add_argument('--horas', action='store_true',
                   help="Muestra el control horario para la semana en curso")
group.add_argument('--mes', action='store_true', help="Muestra el control horario para el mes en curso")
group.add_argument('--vacaciones', action='store_true',
                   help="Muestra los días de vacaciones que te quedan")
group.add_argument('--lapso', action='store_true',
                   help="Muestra permisos registrados en lapso")
group.add_argument('--festivos', action='store_true',
                   help="Muestra los festivos hasta enero del año que viene")
group.add_argument('--menu', action='store_true',
                   help="Muestra el menú de la sede definida en config.yml")
group.add_argument('--nominas', action='store_true',
                   help="Descarga las nóminas en el directorio definido en config.yml y muestra las cantidades netas")
group.add_argument('--bruto', action='store_true',
                   help="Lo mismo que --nominas pero mostrando las cantidades en bruto")
group.add_argument('--expediente', action='store_true',
                   help="Descarga el expediente personal en el directorio definido en config.yml")
group.add_argument('--puesto', action='store_true',
                   help="Muestra información sobre el puesto ocupado")
group.add_argument('--novedades', action='store_true',
                   help="Muestra las novedades de intranet.mapa.es (con antigüedad máxima de 30 días)")
group.add_argument('--ofertas', action='store_true',
                   help="Muestra ofertas para los empleados de MAPA")
# group.add_argument('--servicios', action='store_true', help="Servicios prestados")
group.add_argument('--contactos', action='store_true', help="Contactos de interés")
group.add_argument('--busca', nargs="+", type=str, help="Busca en el directorio de personal")

ARG_OPTIONS: Tuple[str] = tuple(re.findall(r"--([a-z]+)", parser.format_help()))


def myunidecode(s: str):
    fake_ene = "~$%&@"
    s = s.replace("ñ", fake_ene)
    s = unidecode(s)
    s = s.replace(fake_ene, "ñ")
    return s


def main(arg, *args, **kwargs):
    prt = Printer()
    if arg.horas:
        prt.horas_semana(*args, **kwargs)
    if arg.mes:
        prt.horas_mes(*args, **kwargs)
    if arg.nominas:
        prt.nominas(*args, sueldo='neto', **kwargs)
    if arg.bruto:
        prt.nominas(*args, sueldo='bruto', **kwargs)
    if arg.festivos:
        prt.festivos(*args, **kwargs)
    if arg.expediente:
        prt.expediente(*args, **kwargs)
    if arg.vacaciones:
        prt.vacaciones(*args, **kwargs)
    if arg.menu:
        prt.menu(*args, **kwargs)
    if arg.lapso:
        prt.lapso(*args, **kwargs)
    if arg.puesto:
        prt.puesto(*args, **kwargs)
    if arg.novedades:
        prt.novedades(*args, **kwargs)
    if arg.ofertas:
        prt.ofertas(*args, **kwargs)
    # if arg.servicios:
    #    api.servicios(*args, **kwargs)
    if arg.contactos:
        prt.contactos(*args, **kwargs)
    if arg.busca:
        prt.busca(*arg.busca, **kwargs)


def parse_cmd(cmd: str, **kwargs):
    cmd = myunidecode(cmd)
    if cmd in ("nominas!", "bruto!"):
        # FileManager.get().remove("data/nominas/todas.json")
        cmd = cmd[:-1]
    if cmd in ("menu!", 'menus'):
        kwargs['show_all'] = True
        cmd = cmd[:-1]
    if cmd not in ARG_OPTIONS:
        opts = set(a for a in ARG_OPTIONS if a.startswith(cmd) and a != 'help')
        if len(opts) == 1:
            cmd = opts.pop()
    return cmd, kwargs


def str_main(text, *args, **kwargs):
    text, kwargs = parse_cmd(text, **kwargs)
    if text not in ARG_OPTIONS:
        return
    if text in ("busca", "nomina") and len(args) == 0:
        return
    if text == "help":
        return parser.format_help()
    try:
        arg = parser.parse_args(("--" + text,) + args)
    except SystemExit:
        return
    old_stdout = sys.stdout
    result = StringIO()
    sys.stdout = result
    main(arg, *args, **kwargs)
    sys.stdout = old_stdout
    result_string = result.getvalue()
    result_string = result_string.rstrip()
    return result_string


if __name__ == "__main__":
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    arg = None
    kwargs = {}
    if len(sys.argv) > 1:
        prm = sys.argv[1]
        prm, kwargs = parse_cmd(prm)
        if prm in ARG_OPTIONS:
            arg = parser.parse_args(["--" + prm] + sys.argv[2:])

    arg = arg or parser.parse_args()
    main(arg, **kwargs)
