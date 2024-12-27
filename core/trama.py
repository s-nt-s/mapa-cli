import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from functools import cached_property
from os.path import isfile
from typing import Dict, List, NamedTuple, Set, Tuple, Union

import bs4

from . import ics, tp
from .autdriver import AutDriver
from .cache import Cache, TupleCache
from .filemanager import FileManager
from .gesper import FCH_FIN as gesper_FCH_FIN
from .gesper import Gesper
from .util import get_months, get_text, get_times, tmap, ttext
from .web import Web

re_sp = re.compile(r"\s+")
JS_DIAS = "data/trama/cal/{:%Y-%m-%d}.json"
RT_URL = "https://trama.administracionelectronica.gob.es/portal/"
FCH_INI = date(2022, 5, 29)

logger = logging.getLogger(__name__)


class Festivo(date):
    @property
    def nombre(self):
        wd = self.weekday()
        dm = (self.month, self.day)
        if dm == (1, 1):
            return "Año nuevo"
        if dm == (1, 6):
            return "Epifanía"
        if self.month == 4:
            if wd == 3 and self.day == 17:
                return "Jueves santo"
            if wd == 4 and self.day == 18:
                return "Viernes santo"
        if dm == (5, 1):
            return "Día del trabajo"
        if dm == (5, 2):
            return "Comunidad de Madrid"
        if dm == (5, 15):
            return "San Isidro"
        if dm == (7, 25):
            return "Santiago Apóstol"
        if dm == (8, 15):
            return "Asunción de la virgen"
        if dm in ((11, 9), (11, 10)):
            return "Almudena"
        if self.month == 12:
            if self.day == 6:
                return "Constitución española"
            if self.day == 8:
                return "Inmaculada concepción"
            if self.day == 24:
                return "Noche buena"
            if self.day == 25:
                return "Navidad"
            if self.day == 31:
                return "Noche vieja"
        return ""


class Informe(NamedTuple):
    ini: date
    fin: date
    total: tp.HM = tp.HM(0)
    teorico: tp.HM = tp.HM(0)
    saldo: tp.HM = tp.HM(0)
    laborables: int = 0
    vacaciones: tp.HM = tp.HM(0)


@dataclass(frozen=True)
class Calendario:
    dias: Tuple[tp.Fichaje, ...]
    saldo: tp.HM = field(init=False, default=0)
    total: tp.HM = field(init=False, default=0)
    teorico: tp.HM = field(init=False, default=0)
    futuro: tp.HM = field(init=False, default=0)
    fichados: int = field(init=False, default=0)
    jornadas: int = field(init=False, default=0)

    def __post_init__(self):
        sumHM = lambda x: sum(x, start=tp.HM(0))
        for k in ("saldo", "total", "teorico"):
            object.__setattr__(self, k, sumHM((getattr(d, k) for d in self.dias)))
        today = date.today()
        object.__setattr__(self, "futuro", sumHM(d.saldo for d in self.dias if d.fecha > today))
        object.__setattr__(self, "fichados", sum(int(len(d.marcajes) > 0) for d in self.dias))
        object.__setattr__(self, "jornadas", sum(int(d.teorico.minutos > 0) for d in self.dias))
        if self.jornada_en_curso is not None:
            # Hasta que salgamos no deberíamos contar este día
            object.__setattr__(self, "fichados",  getattr(self, "fichados")-1)
            if self.jornada_en_curso.total.minutos > 0:
                # Si hay algo ya computado (por ejemplo, tenemos 3 fichajes)
                # lo restamos del total porque aún no sabemos cuanto se va
                # a terminar imputando al día actual
                for k in ("saldo", "total"):
                    object.__setattr__(self, k, getattr(self, k) - self.jornada_en_curso.total)

    @cached_property
    def hoy(self):
        today = date.today()
        for d in self.dias:
            if d.fecha == today:
                return d

    @cached_property
    def tomorrow(self):
        tomorrow = date.today() + timedelta(days=1)
        for d in self.dias:
            if d.fecha == tomorrow:
                return d

    @cached_property
    def jornada_en_curso(self):
        if self.hoy and len(self.hoy.marcajes) % 2 != 0:
            return self.hoy

    @cached_property
    def ahora(self):
        if self.jornada_en_curso is None:
            return None

        ahora = tp.HM.build(time.strftime("%H:%M"))

        # Aún estamos en la oficina
        sld = ahora - self.jornada_en_curso.marcajes[-1]

        return tp.SiFichoAhora(
            saldo=self.saldo + sld,
            total=self.total + sld,
            ahora=self.jornada_en_curso.total + sld
        )


def get_from_label(sp: bs4.Tag, lb):
    tb = sp.find("span", string=lb)
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
        dias: List[tp.Fichaje] = []
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
                mar: Tuple[tp.HM, ...] = tmap(tp.HM.build, sorted(re.findall(r"\d+:\d+:\d+", mar)))
                if isinstance(prs, str):
                    obs = ((obs or "") + " "+prs).strip()

                i = tp.Fichaje(
                    fecha=fec,
                    marcajes=mar,
                    obs=obs,
                    total=tp.HM.build(ttt),
                    teorico=tp.HM.build(tto),
                    saldo=tp.HM.build(sld)
                )
                dias.append(i)
        return dias

    def get_dias(self, ini: date, fin: date):
        logger.debug("get_dias(%s, %s)", ini, fin)
        dias: List[tp.Fichaje] = []
        fln_dias = JS_DIAS.format(ini)
        if isfile(fln_dias):
            for d in map(tp.builder(tp.Fichaje), FileManager.get().load(fln_dias)):
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
            FileManager.get().dump(fln_dias, sv_dias)
        # dias = [d for d in dias if d.fecha >= ini]
        return dias

    def get_calendario(self, ini: date, fin: date):
        """
        Devuelve el control horario entre dos fechas
        """
        logger.debug("get_calendario(%s, %s)", ini, fin)
        return Calendario(
            dias=self.get_dias(ini, fin)
        )

    def get_semana(self):
        logger.debug("get_semana()")
        ini = date.today()
        if ini.weekday() > 0:
            ini = ini - timedelta(days=ini.weekday())
        fin = ini + timedelta(days=6)
        return self.get_calendario(ini, fin)

    @TupleCache(
        "data/trama/informe_{:%Y-%m-%d}_{:%Y-%m-%d}.json",
        builder=tp.builder(Informe),
        maxOld=(1 / 24)
    )
    def _get_informe(self, ini: date, fin: date):
        logger.debug("Trama._get_informe(%s, %s)", ini, fin)
        r = Informe(
            ini=ini,
            fin=fin
        )
        if ini <= gesper_FCH_FIN:
            inf = Gesper().get_informe(ini, gesper_FCH_FIN)
            if inf:
                r = tp.merge(
                    r,
                    total=r.total + inf.total,
                    teorico=r.teorico+(inf.teoricas - inf.festivos -inf.fiestas_patronales),
                    saldo=r.saldo + inf.saldo,
                    laborables=r.laborables + inf.laborables,
                    vacaciones=r.vacaciones + inf.vacaciones
                )
            ini = gesper_FCH_FIN + timedelta(days=1)
            if ini >= fin:
                return r
        for i in self.get_dias(ini, fin):
            r = tp.merge(
                r,
                total=r.total + i.total,
                teorico=r.teorico+i.teorico,
                saldo=r.saldo + i.saldo,
                laborables=r.laborables + int(i.teorico.minutos > 0),
                #vacaciones = r.vacaciones + inf.vacaciones
            )
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
        vac: Dict[Tuple[int, int], tp.VacacionesResumen] = {}
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

        def _add(v: tp.VacacionesResumen):
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
                _add(tp.VacacionesResumen(
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
                    _add(tp.VacacionesResumen(
                        key="sueltos",
                        total=vitotal,
                        usados=vigast,
                        year=yr
                    ))
                _add(tp.VacacionesResumen(
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
                    vac[k] = tv._replace(
                        total=gv.total,
                        usados=gv.usados + tv.usados
                    )

        rst: List[tp.VacacionesResumen] = []
        for v in vac.values():
            if v.year == year or (v.year == year - 1 and v.total > v.usados):
                rst.append(v)
        arr = tuple(sorted(rst, key=lambda v: (v.year, v.key)))
        return arr

    @TupleCache(
        "data/trama/incidencias_{estado}.json",
        builder=tp.builder(tp.Incidencia),
        maxOld=(1 / 24)
    )
    def get_incidencias(self, estado=3):
        def to_date(x: str):
            return date(*map(int, reversed(x.split("/"))))

        w: Web = self._get_inc_session()
        w.get("https://trama.administracionelectronica.gob.es/incidencias/bandejaEnviadas.html")
        mx = w.soup.select("#maximoElementosPagina option")[-1]
        mx = mx.attrs["value"]
        action, data = w.prepare_submit("#formularioPrincipal")
        data["maximoElementosPagina"] = mx
        if estado is not None:
            data["idEstadoIncidencia"] = str(estado)
        w.get(action, **data)
        r: List[tp.Incidencia] = []
        head = ttext(w.soup.select("#listaTablaMaestra thead tr th"))
        for tr in w.soup.select("#listaTablaMaestra tbody tr"):
            tds = ttext(tr.findAll("td"))
            tds = {k: v for k, v in zip(head, tds)}
            i = tp.Incidencia(
                id=int(tds['Proceso']),
                tipo=tds['Tipo Solicitud'],
                solicitud=to_date(tds['Fecha solicitud']),
                validador=tds['Validador'],
                autorizador=tds['Autorizador'],
                incidencias=tuple(),#tds['Incidencias'],
                estado=tds['Estado'],
                tarea=to_date(tds['Fecha tarea']),
                permiso=None,
                fecha=None,
                fin=None,
                dias=None,
                year=None,
                inicio=None,
                observaciones=None,
                mensaje=None
            )
            data['accion'] = 'REDIRIGIR_SOLICITUDES'
            data['idProceso'] = str(i.id)
            w.get(action, **data)
            tb = w.soup.select_one("#tablaIncidencias")
            if tb is not None:
                incidencias = []
                tb.select_one("thead").extract()
                for tr in tb.select("tr"):
                    tds = ttext(tr.findAll("td"))
                    tipo, fecha, inicio, fin, observaciones, mensaje = tds
                    incidencias.append(tp.Incidencia(
                        tipo=tipo,
                        fecha=to_date(fecha),
                        inicio=tp.HM.build(inicio),
                        fin=tp.HM.build(fin),
                        observaciones=observaciones,
                        mensaje=mensaje,
                        id=None,
                        solicitud=None,
                        validador=None,
                        autorizador=None,
                        incidencias=tuple(),
                        permiso=None,
                        estado=None,
                        tarea=None,
                        dias=None,
                        year=None
                    ))
                i = i._replace(
                    incidencias=tuple(incidencias)
                )
            r.append(i)
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
            i = tp.Incidencia(
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
                incidencias=tuple(),
                dias=None,
                year=None,
                inicio=None,
                observaciones=None,
                mensaje=None
            )
            data['accion'] = 'REDIRIGIR_SOLICITUDES'
            data['idProceso'] = str(i.id)
            w.get(action, **data)
            dias = get_from_label(w.soup, "Días")
            year = get_from_label(w.soup, "Ejercicio")
            if dias is not None:
                i = i._replace(dias=dias)
            if year is not None:
                i = i._replace(year=year)
            r.append(i)
        return tuple(r)

    def get_lapso(self, estado=3):
        lps: List[tp.Incidencia] = []
        for x in self.get_incidencias(estado=estado):
            if x.incidencias:
                for i in x.incidencias:
                    lps.append(i)
                continue
            if x.fecha is not None:
                lps.append(x)
        lps = sorted(lps, key=lambda x: x.fecha)
        return tuple(lps)

    def get_cuadrante(self, ini=None, months=6):
        def __check_cls(cls: Union[str, None, List[str]]):
            if isinstance(cls, str):
                cls = cls.strip().split()
            if cls is None or len(cls)==0:
                return False
            if "FESTIVOANUAL" in cls:
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

    def get_festivos(self, max_iter=-1):
        r: Set[Festivo] = set()
        today=date.today()
        top = today.year + 2
        w: Web = self._get_cal_session()
        w.get("https://trama.administracionelectronica.gob.es/calendario/calendario.html")
        while True:
            size = len(r)
            for td in w.soup.select("td.FESTIVOANUAL"):
                day = get_text(td)
                if not isinstance(day, str) or not day.isdigit():
                    continue
                day = int(day)
                monday = td.find_parent("tr").attrs["class"][0]
                mday, mmonth, myear = tuple(map(int, (monday[:2], monday[2:4], monday[4:])))
                if day < mday:
                    mmonth = mmonth + 1
                if mmonth == 13:
                    mmonth = 1
                    myear = myear + 1
                dt = Festivo(myear, mmonth, day)
                if dt.weekday() not in (5, 6):
                    r.add(dt)
            if size == len(r) or max(r).year >= top:
                break
            action, data = w.prepare_submit("#formularioPrincipal")
            for b in w.soup.select("button[type='submit']"):
                name = b.attrs.get('name')
                if name in data.keys() and name != 'avanzaAnyo':
                    del data[name]
            b = w.soup.select_one("#avanzaAnyo")
            data[b.attrs["name"]] = b.attrs['value']
            w.get(action, **data)
        fest = tuple(sorted([f for f in r if f>=today and f.year<top]))
        events: List[ics.IcsEvent] = []
        for f in fest:
            events.append(ics.IcsEvent(
                uid="festivo_"+str(f),
                dtstamp=f,
                dtstart=f,
                dtend=f,
                categories="Festivo",
                summary=f.nombre,
                description=None
            ))
        ics.IcsEvent.dump("data/festivos.ics", *events)
        return fest

if __name__ == "__main__":
    a = Trama()
    #r = a.get_cuadrante()
    r = a.get_incidencias()
    import json

    print(json.dumps(r, indent=2))
