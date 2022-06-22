import re
from .trama import Trama
from .funciona import Funciona
from datetime import datetime, timedelta
from .gesper import Gesper
from .mapa import Mapa
from .filemanager import CNF
from .hm import HM
from .util import to_strint, DAYNAME, parse_dia, notnull, tmap
from io import StringIO

re_rtrim = re.compile(r"^\s*\n")
dt_now = datetime.now()
re_sp = re.compile(r"\s+")

prnt_func = print
prnt_line = ""


def print(*args, **kvargs):
    # Previene imprimir dos lineas vacias seguidas
    global prnt_line
    io_line = StringIO()
    prnt_func(*args, file=io_line, flush=True, **kvargs)
    line = io_line.getvalue()
    line = line.strip()
    if tmap(len, (line, prnt_line)) == (0, 0):
        return
    prnt_line = line
    prnt_func(*args, **kvargs)


def print_dict(kv, prefix=""):
    max_campo = max(len(i[0]) for i in kv.items())
    line = "%-" + str(max_campo) + "s:"
    for k, v in kv.items():
        if v:
            print(prefix + (line % k), end="")
            if isinstance(v, (tuple, list, set)):
                v = ", ".join(str(i) for i in v)
            if isinstance(v, dict):
                print("")
                print_dict(v, prefix="  ")
            else:
                print(" " + str(v))


class Printer:
    def __init__(self):
        pass

    def horas_semana(self):
        t = Trama()
        cal = t.get_semana()

        quedan = cal.jornadas - cal.fichado
        idx_trabajando = None
        if cal.sal_ahora is not None and cal.index is not None:
            idx_trabajando = cal.index

        print("Semana:", cal.teorico.div(cal.jornadas), "*", cal.jornadas, "=", cal.teorico)
        print("")
        for index, dia in enumerate(cal.dias):
            hms = list(dia.marcajes)
            if not hms:
                continue
            print("%2d:" % dia.fecha.day, end=" ")
            if idx_trabajando == index:
                hms.append("--_--")
            str_hms = ["{} - {}".format(hms[i], (hms + ["--_--"])[i + 1]) for i in range(0, len(hms), 2)]
            str_hms = " + ".join(str_hms)
            if idx_trabajando == index:
                print("%s = %s" % (str_hms, cal.sal_ahora.hoy_total), "▲")
            else:
                print("%s = %s" % (str_hms, dia.total))
        print("")
        if cal.fichado > 1:
            print("Media:", cal.total.div(cal.fichado), "*", cal.fichado, "=", cal.total)
            if idx_trabajando is not None:
                print("Media:", cal.sal_ahora.total.div(cal.fichado + 1), "*", cal.fichado + 1, "=",
                      cal.sal_ahora.total)

        sld, dqn = cal.saldo, quedan
        if idx_trabajando is not None:
            sld, dqn = cal.sal_ahora.saldo, quedan - 1
        if (quedan - (int(idx_trabajando is not None))) > 0:
            sgn = sld.minutos > 0
            us_sld = HM(abs(sld.minutos))
            line = ["Falta:", us_sld.div(dqn), "*", dqn, "=", us_sld]
            if sgn > 0:
                line[0] = "Queda:"
            if idx_trabajando is not None:
                line.append("▲" if sgn else "▼")
            print(*line)

        print("")
        wf_sld = sld - cal.futuro
        sgn = wf_sld.minutos > 0
        if idx_trabajando is not None:
            print("Desfase:", wf_sld, "▲" if sgn else "▼")
        else:
            print("Desfase:", wf_sld)

        if cal.index is None or len(cal.dias) <= cal.index:
            return

        if idx_trabajando is not None:
            print("")
            if quedan == 0 and wf_sld.minutos > 0:
                print("¡¡SAL AHORA!!")
                return
            if wf_sld.minutos <= 0:
                print("Sal a las", cal.sal_ahora.ahora - wf_sld)
                return
        man = cal.dias[cal.index + 1]
        outhm = HM("14:30")
        if man.teorico < HM("07:30"):
            outhm = HM("14:00")
        if (wf_sld.minutos > 0 and cal.sal_ahora is None) or (cal.sal_ahora.ahora.minutos > outhm.minutos):
            print("")
            man = man.teorico - wf_sld
            if cal.sal_ahora:
                print("Sal ahora y mañana haz", man)
            else:
                print("Mañana haz", man)
            print(" 07:00 -", HM("07:00") + man)
            print("", outhm - man, "-", outhm)

    def nominas(self, sueldo='neto'):
        f = Funciona()
        nominas = f.get_nominas()
        n_ym = sorted(set((n.year, n.mes) for n in nominas))
        for index, n in enumerate(CNF.get("_nominas", [])):
            if (n.year, n.mes) not in n_ym:
                n.index = index
                nominas.append(n)
        nominas = sorted(nominas, key=lambda n: (n.year, n.mes, -n.index))
        years = sorted(set(n.year for n in nominas))
        for y in years:
            meses = set()
            euros = 0
            for n in nominas:
                if n.year != y:
                    continue
                euros = euros + n[sueldo]
                meses.add(n.mes)
            meses = len(meses)
            print("{year}: {meses:>2} x {euros:>5}€ = {total:>6}€".format(year=y, euros=to_strint(euros / meses),
                                                                          meses=meses, total=to_strint(euros)))
        print("")
        agg_nomias = {}
        for n in nominas:
            k = (n.year, n.mes)
            agg_nomias[k] = agg_nomias.get(k, 0) + n[sueldo]
        if sueldo == 'bruto':
            for n in nominas:
                print("{}-{:02d} __ {:>5}€".format(n.year, n.mes, to_strint(n[sueldo])))
        else:
            for ((y, mes), sld) in agg_nomias.items():
                print("{}-{:02d} __ {:>5}€".format(y, mes, to_strint(sld)))

        n_ym = sorted(set((n.year, n.mes) for n in nominas), reverse=True)
        if len(n_ym) < 4:
            return

        print_medias = [
            (" año     ", 12),
            (" semestre", 6)
        ]
        ln = len(n_ym) - 1
        if ln > 12 or (ln > 6 and ln < 12) or ln < 6:
            print_medias.insert(0, (" %s meses" % ln, ln))
            if ln < 10:
                print_medias[0][0] = " " + print_medias[0][0]

        sldhr = None
        print("")
        print("Media último/s:")
        for l, c in print_medias:
            if len(n_ym) <= c:
                continue
            sldhr = None
            cant = 0
            for y, m in n_ym[:c]:
                for nom in nominas:
                    if nom.year == y and nom.mes == m:
                        cant = cant + nom[sueldo]
            # ini = meses[c-1]
            # fin = meses[0]
            # ini = date(ini[0], ini[1], 1)
            # fin = date(fin[0], fin[1], monthrange(*fin)[1])
            # per_hour = self.informe_de_horas(ini, fin)
            # if per_hour:
            #    per_hour = cant / (per_hour.computables.minutos / 60)
            # if c == 12 and sueldo == 'bruto':
            #    sldhr = Munch(sueldo=cant, hora=per_hour)
            # per_hour = to_strint(per_hour)
            cant = to_strint(cant / c)
            print("{}: {:>6}€".format(l, cant))
        if sldhr and sueldo == 'bruto':
            print("")
            print("Sueldo anual: " + to_strint(sldhr.sueldo))
            if sldhr.hora:
                cotizar = 6.35
                print("Si trabajaras 8h/día con 22 días de vacaciones y cotizando {}%:".format(cotizar))
                print("Sueldo anual: " + to_strint((260 - 22) * 8 * sldhr.hora * (100 + cotizar) / 100))

    def festivos(self):
        g = Gesper()
        cYear = dt_now.year
        for f in g.get_festivos():
            if cYear != f.year:
                print("===", f.year, "===")
                cYear = f.year
            print("%s %2d.%02d %s" % (f.semana, f.dia, f.mes, f.nombre))

    def expediente(self):
        exps = Gesper().get_expediente()
        mx_tipo = max(len(e.tipo) for e in exps)
        frmt = "{fecha:%-d.%m} {tipo:" + str(mx_tipo) + "} {desc}"
        for inx, e in enumerate(exps):
            if inx == 0 or e.fecha.year != exps[inx - 1].fecha.year:
                print("===", e.fecha.year, "===")
            line = frmt.format(**dict(e))
            if e.fecha.day < 10:
                line = " " + line
            print(line)

    def vacaciones(self):
        vs = Gesper().get_vacaciones()
        years = sorted(set(v.year for v in vs))
        for y in years:
            if len(years) > 1:
                print("======== %s ========" % y)
            yvs = [v for v in vs if v.year == y]
            qdn = 0
            s_ln = max(len(v.key) for v in yvs)
            for v in yvs:
                q = v.total - v.usados
                qdn = qdn + q
                print(v.key.capitalize().ljust(s_ln, '.') +
                      " %2d - %2d = %2d" % (v.total, v.usados, q))
            print(" quedan".rjust(s_ln + 8, '.'), "= %2d" % qdn)

    def menu(self):
        menus = [m for m in Mapa().get_menu() if m.fecha >= dt_now.date()]
        if len(menus) == 0:
            print("Menú no publicado")
            return
        for i, m in enumerate(menus):
            if i > 0:
                print("")
            print("#", DAYNAME[m.fecha.weekday()], m.fecha.strftime("%Y-%m-%d"))
            print("")
            print(m.menu)

    def lapso(self):
        year = None
        for i in Gesper().get_lapso():
            if year is None or year != i["date"].year:
                year = i["date"].year
                print("===", year, "===")
            print("%s: %s" % (
                parse_dia(i["date"]), i["date"].strftime('%d/%m')), end=" ")
            if i["_dias"] > 1:
                print("(+%s)" % i["_dias"], end=" ")
            txt = re_sp.sub(" ", i["txt"]).strip()
            print(txt)

    def puesto(self):
        pst = Gesper().get_puesto()
        print("==", pst.denominacion, "==")
        kv = {
            "N.R.P.": pst.nrp,
            "Grupo": pst.grupo,
            "Nivel": pst.nivel,
            "Sueldo B.": "{:>6}€".format(to_strint(pst.sueldo.base + pst.sueldo.trienios.base)),
            "Extra Ju.": "{:>6}€".format(to_strint(pst.sueldo.extra.junio + pst.sueldo.trienios.extra.junio)),
            "Extra Di.": "{:>6}€".format(to_strint(pst.sueldo.extra.diciembre + pst.sueldo.trienios.extra.diciembre)),
            "Compl. E.": "{:>6}€".format(to_strint(pst.sueldo.complemento.especifico)),
            "Compl. D.": "{:>6}€".format(to_strint(pst.sueldo.complemento.destino)),
            "Trienios": " ".join(["{}x{}".format(v, k) for k, v in pst.trienios.items()]),
            "Teléfono": pst.contacto.telefono,
            "Correo": pst.contacto.correo,
            "Jornada": pst.jornada,
            "Dirección": pst.contacto.direccion,
            "Planta": pst.contacto.planta,
            "Despacho": pst.contacto.despacho,
        }

        max_campo = max(len(i[0]) for i in kv.items())
        line = "%-" + str(max_campo) + "s: %s"
        for i in kv.items():
            print(line % i)
        print(pst.sueldo.fuente)

    def novedades(self):
        desde = dt_now - timedelta(days=30)
        items = [n for n in Mapa().get_novedades() if n.fecha >= desde]

        if not items:
            print("No hay novedades")
            return

        items = sorted(items, key=lambda x: (x.fecha, x.titulo))
        last_date = None
        for index, i in enumerate(items):
            if index > 0:
                print("")
            if last_date is None or i.fecha.date() != last_date.date():
                print("===", i.fecha.strftime("%d/%m/%Y"), "===")
            print("[%s]" % i.tipo, i.titulo)
            if i.url:
                print(i.url)
            if i.descripcion:
                descripcion = re.sub(r"^ *", r"> ", i.descripcion, flags=re.MULTILINE)
                print(descripcion)
            last_date = i.fecha

    def ofertas(self):
        for index, i in enumerate(Mapa().get_ofertas()):
            if index > 0:
                print("")
            print("===", i.tipo, "===")
            print(i.url)
            print("")
            for o in i.ofertas:
                print("*", o.titulo)

    def contactos(self):
        kv = Mapa().get_contactos()
        print_dict(kv)

    def busca(self, *args):
        users = Mapa().get_users(*args)
        if len(users) == 0:
            print("No encontrado")
            return None

        cenun = tuple((u.centro or u.unidad) for u in users)
        if len(users) < 3 or len(set(cenun)) > (len(cenun) - 3):
            for u in users:
                print("")
                print(u)
            return users

        empt = []
        nocu = []
        ocou = []
        resto = []
        for u in users:
            if u.isEmpty():
                empt.append(u)
            elif not u.centro and not u.unidad:
                nocu.append(u)
            else:
                resto.append(u)

        cenun = sorted(set((u.centro or u.unidad) for u in resto))
        for ctun in cenun:
            print("")
            _resto = [u for u in resto if (u.centro or u.unidad) == ctun]
            unidad = set((u.unidad for u in _resto))
            if len(unidad) == 1:
                print("## " + ctun, unidad.pop(), sep=" > ")
                unidad = False
            else:
                print("## " + ctun)
                unidad = True
            for i, u in enumerate(_resto):
                print("")
                print(notnull(u.nombre, u.apellido1, u.apellido2, sep=" "))
                if unidad and ctun != u.unidad and u.unidad:
                    print(u.unidad)
                if u.puesto:
                    print(u.puesto)
                print(notnull(u.despacho, u.planta, u.ubicacion, sep=" - "))
                print(notnull(u.telefono, u.telefonoext, u.correo, sep=" - "))

        if nocu:
            print("")
            print("<<sin centro ni unidad>>")
        for u in nocu:
            print("")
            print(u)

        if empt:
            print("")
            print("Otros:")
        for u in empt:
            print("*", end=" ")
            print(notnull(u.nombre, u.apellido1, u.apellido2, sep=" "))

        return users


if __name__ == "__main__":
    p = Printer()
    p.horas_semana()
