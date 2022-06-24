#!/usr/bin/env python3
import argparse
import re
import sys
from io import StringIO

#from core.api import Api
from core.printer import Printer

parser = argparse.ArgumentParser(
    description='Comando para los servicios de intranet.mapa.es', add_help=False)
group = parser.add_mutually_exclusive_group()
group.add_argument('-h', '--horas', action='store_true',
                   help="Muestra el control horario para la semana en curso")
group.add_argument('-m', '--mes', action='store_true', help="Muestra el control horario para el mes en curso")
group.add_argument('-v', '--vacaciones', action='store_true',
                   help="Muestra los días de vacaciones que te quedan")
group.add_argument('-l', '--lapso', action='store_true',
                   help="Muestra permisos registrados en lapso")
group.add_argument('-f', '--festivos', action='store_true',
                   help="Muestra los festivos hasta enero del año que viene")
group.add_argument('--menu', action='store_true',
                   help="Muestra el menú de la sede definida en config.yml")
group.add_argument('-n', '--nominas', action='store_true',
                   help="Descarga las nóminas en el directorio definido en config.yml y muestra las cantidades netas")
group.add_argument('-b', '--bruto', action='store_true',
                   help="Lo mismo que --nominas pero mostrando las cantidades en bruto")
group.add_argument('-e', '--expediente', action='store_true',
                   help="Descarga el expediente personal en el directorio definido en config.yml")
group.add_argument('--puesto', action='store_true',
                   help="Muestra información sobre el puesto ocupado")
group.add_argument('--novedades', action='store_true',
                   help="Muestra las novedades de intranet.mapa.es (con antigüedad máxima de 30 días)")
group.add_argument('--ofertas', action='store_true',
                   help="Muestra ofertas para los empleados de MAPA")
#group.add_argument('--servicios', action='store_true', help="Servicios prestados")
group.add_argument('--contactos', action='store_true', help="Contactos de interés")
group.add_argument('--busca', nargs="+", type=str, help="Busca en el directorio de personal")

arg_options = re.findall(r"--([a-z]+)", parser.format_help())


def main(arg, *args, **kargv):
    prt = Printer()

    if arg.horas:
        prt.horas_semana(*args, **kargv)
    if arg.mes:
        prt.horas_mes(*args, **kargv)
    if arg.nominas:
        prt.nominas(*args, sueldo='neto', **kargv)
    if arg.bruto:
        prt.nominas(*args, sueldo='bruto', **kargv)
    if arg.festivos:
        prt.festivos(*args, **kargv)
    if arg.expediente:
        prt.expediente(*args, **kargv)
    if arg.vacaciones:
        prt.vacaciones(*args, **kargv)
    if arg.menu:
        prt.menu(*args, **kargv)
    if arg.lapso:
        prt.lapso(*args, **kargv)
    if arg.puesto:
        prt.puesto(*args, **kargv)
    if arg.novedades:
        prt.novedades(*args, **kargv)
    if arg.ofertas:
        prt.ofertas(*args, **kargv)
    #if arg.servicios:
    #    api.servicios(*args, **kargv)
    if arg.contactos:
        prt.contactos(*args, **kargv)
    if arg.busca:
        prt.busca(*arg.busca, **kargv)


def str_main(text, *args, **kargv):
    if text not in arg_options:
        return
    if text in ("busca", "nomina"):
        if len(args)==0:
            return
    try:
        arg = parser.parse_args(("--"+text,) + args)
    except SystemExit:
        return
    old_stdout = sys.stdout
    result = StringIO()
    sys.stdout = result
    main(arg, *args, **kargv)
    sys.stdout = old_stdout
    result_string = result.getvalue()
    return result_string.rstrip()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    arg = None
    if len(sys.argv) > 1:
        prm = sys.argv[1]
        if prm == "parametros":
            print(" ".join(arg_options()))
            sys.exit()
        if prm in arg_options:
            arg = parser.parse_args(["--"+prm] + sys.argv[2:])

    arg = arg or parser.parse_args()
    main(arg)
