from datetime import datetime, date, timedelta
from munch import Munch

from .autdriver import AutDriver
from .web import Web
from .util import json_serial, tmap, ttext, get_text, get_times, json_hook, get_months
from .hm import HM, HMCache, HMmunch
from .cache import Cache, MunchCache
from .gesper import Gesper
from .filemanager import FileManager
from .gesper import FCH_FIN as gesper_FCH_FIN
from os.path import isfile
import re
import time
import logging
from typing import Dict, List, Tuple, Union
import bs4

re_sp = re.compile(r"\s+")
JS_DIAS = "data/trama/cal/{:%Y-%m-%d}.json"
RT_URL = "https://trama.administracionelectronica.gob.es/portal/"
FCH_INI = date(2022, 5, 29)

logger = logging.getLogger(__name__)


def get_from_label(sp: bs4.Tag, lb):
    tb = sp.find("span", text=lb)
    if tb is None:
        return
    val = get_text(tb.find_parent("div").find("p"))
    if val is None:
        return
    if val.isdigit():
        val = int(val)
    return val


class Trama:

    @Cache(file="data/autentica/trama.calendario.pickle", maxOld=(1 / 48))
    def _get_cal_session(self):
        logger.debug("_get_cal_session()")
        with AutDriver(browser='firefox') as ff:
            ff.get(RT_URL)
            ff.click("//a[text()='Calendario']")
            return ff.to_web()

    @Cache(file="data/autentica/trama.cuadrante.pickle", maxOld=(1 / 48))
    def _get_cua_session(self):
        logger.debug("_get_cua_session()")
        with AutDriver(browser='firefox') as ff:
            ff.get(RT_URL)
            ff.click("//a[text()='Calendario']")
            ff.click("//a[@id='idCuadranteEmpleados']")
            return ff.to_web()

    @Cache(file="data/autentica/trama.incedencias.pickle", maxOld=(1 / 48))
    def _get_inc_session(self):
        logger.debug("_get_inc_session()")
        with AutDriver(browser='firefox') as ff:
            ff.get(RT_URL)
            ff.click("//div[@id='appMenu']//a[text()='Incidencias']")
            time.sleep(2)
            ff.click("//div[@id='mainWindow']//a[text()='Enviadas']")
            ff.val("idEstadoIncidencia", "Cualquier estado")
            ff.click("btnBuscar")
            # ff.wait("maximoElementosPagina")
            # ff.val("maximoElementosPagina", "100")
            return ff.to_web()

    @Cache(file="data/autentica/trama.vacaciones.pickle", maxOld=(1 / 48))
    def _get_vac_session(self):
        logger.debug("_get_vac_session()")
        with AutDriver(browser='firefox') as ff:
            ff.get(RT_URL)
            ff.click("//div[@id='appMenu']//a[text()='Permisos']")
            time.sleep(2)
            ff.click("//div[@id='mainWindow']//a[text()='Enviadas']")
            ff.val("idEstadoIncidencia", "Cualquier estado")
            ff.click("btnBuscar")
            # ff.wait("maximoElementosPagina")
            # ff.val("maximoElementosPagina", "100")
            return ff.to_web()

    def _get_dias(self, ini: date, fin: date):
        logger.debug("_get_dias(%s, %s)", ini, fin)
        dias = []
        w: Web = self._get_cal_session()
        for a, z in get_times(ini, fin, timedelta(days=59)):
            w.get("https://trama.administracionelectronica.gob.es/calendario/marcajesRango.html",
                  fechaInicio=a.strftime("%d/%m/%Y"),
                  fechaFin=z.strftime("%d/%m/%Y"),
                  )
            for tr in w.soup.select("tr"):
                cls = tr.attrs.get("class")
                if isinstance(cls, list):
                    cls = cls[0]
                if cls not in ("even", "odd"):
                    continue
                tds = ttext(tr.findAll("td"))
                prs = None
                fec, mar, obs, ttt, tto, sld = tds
                if "Permisos:" in mar:
                    prs = mar.split("Permisos:", 1)[-1].strip()
                fec = fec[:-1].split("(", 1)[-1]
                fec = tmap(int, reversed(fec.split("/")))
                fec = date(*fec)
                mar: Tuple[HM, ...] = tmap(HM, sorted(re.findall(r"\d+:\d+:\d+", mar)))
                if isinstance(prs, str):
                    obs = ((obs or "") + " "+prs).strip()

                i = Munch(
                    fecha=fec,
                    marcajes=mar,
                    obs=obs,
                    total=HM(ttt),
                    teorico=HM(tto),
                    saldo=HM(sld)
                )
                dias.append(i)
        return dias

    def get_dias(self, ini: date, fin: date):
        logger.debug("get_dias(%s, %s)", ini, fin)
        dias = []
        fln_dias = JS_DIAS.format(ini)
        if isfile(fln_dias):
            for d in FileManager.get().load(fln_dias):
                d = HMmunch.fromDict(d)
                d._parse()
                if ini <= d.fecha <= fin:
                    dias.append(d)
        if len(dias) == 0:
            dias = self._get_dias(ini, fin)
        elif len(dias) > 0:
            _ini = dias[0].fecha
            _fin = dias[-1].fecha
            pre, pst = [], []
            if ini < _ini:
                pre = self._get_dias(ini, _ini - timedelta(days=1))
            if fin > _fin:
                pst = self._get_dias(_fin + timedelta(days=1), fin)
            dias = pre + dias + pst
        today = date.today()
        dt_top = today - timedelta(days=59)
        sv_dias = [d for d in dias if d.fecha < dt_top]
        if len(sv_dias):
            FileManager.get().dump(fln_dias, sv_dias, default=json_serial)
        # dias = [d for d in dias if d.fecha >= ini]
        return dias

    def get_calendario(self, ini: date, fin: date):
        """
        Devuelve el control horario entre dos fechas
        """
        logger.debug("get_calendario(%s, %s)", ini, fin)
        today = date.today()
        r = Munch(
            total=HM(0),
            teorico=HM(0),
            saldo=HM(0),
            jornadas=0,
            fichado=0,
            sal_ahora=None,
            futuro=HM(0),
            index=None,
            dias=self.get_dias(ini, fin)
        )
        for index, i in enumerate(r.dias):
            r.total += i.total
            r.teorico += i.teorico
            r.saldo += i.saldo
            if i.fecha == today:
                r.index = index
            elif i.fecha > today:
                r.futuro += i.saldo
            if i.teorico.minutos > 0:
                r.jornadas += 1
            if len(i.marcajes) > 0:
                r.fichado += 1
                if i.total.minutos > 0:
                    mrc: List[HM] = sorted(set(m.trunc() for m in i.marcajes))
                    for x in reversed(tuple(range(1, len(mrc) - 1, 2))):
                        if mrc[x].minutos+1 == mrc[x+1].minutos:
                            del mrc[x+1]
                            del mrc[x]
                    i.marcajes = tuple(mrc)
        if r.index is None:
            return r
        hoy = r.dias[r.index]
        if len(hoy.marcajes) % 2 == 0:
            return r
        r.sal_ahora = Munch(
            ahora=HM(time.strftime("%H:%M")),
            total=None,
            saldo=None,
        )
        # Aún estamos en la oficina
        sld = r.sal_ahora.ahora - hoy.marcajes[-1]
        r.sal_ahora.hoy_total = hoy.total + sld
        r.sal_ahora.total = r.total + sld
        r.sal_ahora.saldo = r.saldo + sld
        # Hasta que salgamos no deberíamos contar este día
        r.fichado = r.fichado - 1
        if hoy.total.minutos > 0:
            # Si hay algo ya computado (por ejemplo, tenemos 3 fichajes)
            # lo restamos del total porque aún no sabemos cuanto se va
            # a terminar imputando al día actual
            r.total = r.total - hoy.total
            r.saldo = r.saldo - hoy.total
        return r

    def get_semana(self):
        logger.debug("get_semana()")
        ini = date.today()
        if ini.weekday() > 0:
            ini = ini - timedelta(days=ini.weekday())
        fin = ini + timedelta(days=6)
        return self.get_calendario(ini, fin)

    @HMCache(file="data/trama/informe_{:%Y-%m-%d}_{:%Y-%m-%d}.json", json_default=json_serial, maxOld=(1 / 24))
    def _get_informe(self, ini: date, fin: date):
        logger.debug("Trama._get_informe(%s, %s)", ini, fin)
        r = Munch(
            ini=ini,
            fin=fin,
            total=HM(0),
            teorico=HM(0),
            saldo=HM(0),
            laborables=0,
            vacaciones=HM(0)
        )
        if ini <= gesper_FCH_FIN:
            inf = Gesper().get_informe(ini, gesper_FCH_FIN)
            if inf:
                r.total += inf.total
                r.teorico += (inf.teoricas - inf.festivos - inf.fiestas_patronales)
                r.saldo += inf.saldo
                r.laborables += inf.laborables
                r.vacaciones += inf.vacaciones
            ini = gesper_FCH_FIN + timedelta(days=1)
            if ini >= fin:
                return r
        for i in self.get_dias(ini, fin):
            r.total += i.total
            r.teorico += i.teorico
            r.saldo += i.saldo
            r.laborables += int(i.teorico.minutos > 0)
            # r.vacaciones += inf.vacaciones
        return r

    def get_informe(self, ini: Union[None, date] = None, fin: Union[None, date] = None):
        # Por defecto da el informe desde el inicio
        # hasta el último día del último mes completo
        hoy = date.today()
        if ini is None:
            ini = Gesper().fecha_inicio
        if fin is None or fin >= hoy:
            fin = date.today()
            if (fin + timedelta(days=1)).day != 1:
                fin = fin.replace(day=1) - timedelta(days=1)
        if ini >= hoy:
            return None
        if fin >= hoy:
            fin = hoy - timedelta(days=1)
        if ini > fin:
            return None
        return self._get_informe(ini, fin)

    def get_vacaciones(self, year: Union[int, None] = None):
        GESPER_BREAK = 2022
        vac = {}
        cyr = datetime.today().year
        if year is None:
            for v in self.get_vacaciones(-1):
                if v.total > v.usados:
                    vac[(v.year, v.key)] = v
            year = cyr
        if year < 0:
            year = cyr + year
        if year > cyr:
            return []
        if year < GESPER_BREAK:
            # hack gesper
            return Gesper().get_vacaciones(year)

        def _add(v):
            vac[(v.year, v.key)] = v

        w: Web = self._get_cal_session()
        w.get("https://trama.administracionelectronica.gob.es/calendario/calendario.html")
        yrs = set()
        while True:
            yr = None
            for tr in w.soup.select("div.resumenMarcajes tbody tr"):
                tds = ttext(tr.select("td"))
                yr = int(tds[0])
                yrs.add(yr)
                vc: Tuple[int, ...] = tmap(int, re.findall(r"\d+", tds[1]))
                pe: Tuple[int, ...] = tmap(int, re.findall(r"\d+", tds[2]))
                _add(Munch(
                    key="permiso",
                    total=pe[1],
                    usados=pe[0],
                    year=yr
                ))
                vgast, vtotal, vigast, vitotal = vc
                if yr > GESPER_BREAK:
                    vgastadas = int(vgast)
                    vtotal = vtotal - vitotal
                    vgast = min(vtotal, vgastadas - vigast)
                    vigast = vgastadas - vgast
                    _add(Munch(
                        key="sueltos",
                        total=vitotal,
                        usados=vigast,
                        year=yr
                    ))
                _add(Munch(
                    key="vacaciones",
                    total=vtotal,
                    usados=vgast,
                    year=yr
                ))
            if yrs and (year in range(min(yrs), max(yrs) + 1)):
                break
            if yr == GESPER_BREAK:
                # hack gesper
                break
            prv = w.soup.select_one("#retrocedeAnyo")
            if prv is None:
                break
            action, data = w.prepare_submit("#formularioPrincipal")
            data[prv.attrs["name"]] = prv.attrs["value"]
            w.get(action, **data)

        if year == GESPER_BREAK:
            # hack gesper
            for gv in Gesper().get_vacaciones(year):
                k = (gv.year, gv.key)
                if k not in vac:
                    vac[k] = gv
                else:
                    tv = vac[k]
                    tv.total = gv.total
                    tv.usados = gv.usados + tv.usados

        rst = []
        for v in vac.values():
            if v.year == year or (v.year == year - 1 and v.total > v.usados):
                rst.append(v)
        vac = sorted(rst, key=lambda v: (v.year, v.key))
        return vac

    @MunchCache("data/trama/incidencias_{estado}.json", maxOld=0, json_default=json_serial, json_hook=json_hook)
    def get_incidencias(self, estado=3):
        def to_date(x: str):
            return date(*map(int, reversed(x.split("/"))))

        def to_hm(x: Union[str, None]):
            if x is None:
                return None
            return HM(x)

        w: Web = self._get_inc_session()
        w.get("https://trama.administracionelectronica.gob.es/incidencias/bandejaEnviadas.html")
        mx = w.soup.select("#maximoElementosPagina option")[-1]
        mx = mx.attrs["value"]
        action, data = w.prepare_submit("#formularioPrincipal")
        data["maximoElementosPagina"] = mx
        if estado is not None:
            data["idEstadoIncidencia"] = str(estado)
        w.get(action, **data)
        r = []
        head = ttext(w.soup.select("#listaTablaMaestra thead tr th"))
        for tr in w.soup.select("#listaTablaMaestra tbody tr"):
            tds = ttext(tr.findAll("td"))
            tds = {k: v for k, v in zip(head, tds)}
            i = Munch(
                id=int(tds['Proceso']),
                tipo=tds['Tipo Solicitud'],
                solicitud=to_date(tds['Fecha solicitud']),
                validador=tds['Validador'],
                autorizador=tds['Autorizador'],
                incidencias=tds['Incidencias'],
                estado=tds['Estado'],
                tarea=to_date(tds['Fecha tarea']),
            )
            r.append(i)
            data['accion'] = 'REDIRIGIR_SOLICITUDES'
            data['idProceso'] = str(i.id)
            w.get(action, **data)
            tb = w.soup.select_one("#tablaIncidencias")
            if tb is None:
                continue
            i.incidencias = []
            tb.select_one("thead").extract()
            for tr in tb.select("tr"):
                tds = ttext(tr.findAll("td"))
                tipo, fecha, inicio, fin, observaciones, mensaje = tds
                i.incidencias.append(Munch(
                    tipo=tipo,
                    fecha=to_date(fecha),
                    inicio=to_hm(inicio),
                    fin=to_hm(fin),
                    observaciones=observaciones,
                    mensaje=mensaje
                ))
        w: Web = self._get_vac_session()
        w.get("https://trama.administracionelectronica.gob.es/Permisos/bandejaEnviadas.html")
        mx = w.soup.select("#maximoElementosPagina option")[-1]
        mx = mx.attrs["value"]
        action, data = w.prepare_submit("#formularioPrincipal")
        data["maximoElementosPagina"] = mx
        if estado is not None:
            data["idEstadoIncidencia"] = str(estado)
        w.get(action, **data)
        head = ttext(w.soup.select("#listaTablaMaestra thead tr th"))
        for tr in w.soup.select("#listaTablaMaestra tbody tr"):
            tds = ttext(tr.findAll("td"))
            if len(tds) != len(head):
                continue
            tds = {k: v for k, v in zip(head, tds)}
            fechas = tds['Fechas Solicitadas/Anuladas']
            fechas: Tuple[date, ...] = tmap(to_date, re.findall(r'\d\d/\d\d/\d\d\d\d', fechas))
            i = Munch(
                id=int(tds['Proceso']),
                tipo=tds['Tipo Solicitud'],
                solicitud=to_date(tds['Fecha solicitud']),
                validador=tds['Validador'],
                autorizador=tds['Autorizador'],
                permiso=tds['Tipo Permiso'],
                estado=tds['Estado'],
                tarea=to_date(tds['Fecha tarea']),
                fecha=fechas[0],
                fin=fechas[-1],
            )
            r.append(i)
            data['accion'] = 'REDIRIGIR_SOLICITUDES'
            data['idProceso'] = str(i.id)
            w.get(action, **data)
            dias = get_from_label(w.soup, "Días")
            year = get_from_label(w.soup, "Ejercicio")
            if dias is not None:
                i.dias = dias
            if year is not None:
                i.year = year
        return r

    def get_lapso(self, estado=3):
        lps = []
        for x in self.get_incidencias(estado=estado):
            if x.get('incidencias'):
                for i in x.incidencias:
                    lps.append(i)
                continue
            if x.get('fecha'):
                lps.append(x)
        lps = sorted(lps, key=lambda x: x.fecha)
        return lps

    def get_cuadrante(self, ini=None, months=6):
        def __check_cls(cls: Union[str, None, List[str]]):
            if cls is None:
                return False
            if isinstance(cls, str) and cls in ("FESTIVOANUAL", ""):
                return False
            if isinstance(cls, list) and ("FESTIVOANUAL" in cls or tuple(cls) == tuple()):
                return False
            return True

        if ini is None:
            ini = date.today()
        cuadrante: Dict[str, List[date]] = {}
        w: Web = self._get_cua_session()
        w.get("https://trama.administracionelectronica.gob.es/calendario/cuadranteEmpleados.html")
        action, data = w.prepare_submit("#formularioPrincipal", _mostrarVacacionesSolicitadas="on")
        for cur in get_months(ini, months):
            data["anio"] = str(cur.year)
            data["mes"] = str(cur.month-1)
            w.get(action, **data)
            for tr in w.soup.select("#cuadranteEmpleadosVisibilidadCuadrante tr"):
                tds = tr.findAll("td")
                if len(tds) < 28:
                    continue
                name = get_text(tds[0]).title()
                if name not in cuadrante:
                    cuadrante[name] = []
                for td in tds[1:]:
                    cls = td.attrs.get("class")
                    day = get_text(td)
                    if day is None or not day.isdigit() or not __check_cls(cls):
                        continue
                    cuadrante[name].append(cur.replace(day=int(day)))

        r = {k: tuple(v) for k, v in cuadrante.items() if v}
        return r

if __name__ == "__main__":
    a = Trama()
    r = a.get_cuadrante()
    # r = a.get_incidencias()
    import json

    print(json.dumps(r, indent=2, default=json_serial))
