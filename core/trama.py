from datetime import datetime, date, timedelta
from munch import Munch

from .autdriver import AutDriver
from .util import json_serial, tmap, get_text, get_times
from .hm import HM
from .cache import Cache
from .gesper import Gesper
from .filemanager import FileManager
from .gesper import FCH_FIN as gesper_FCH_FIN
from os.path import isfile
import re
import time

re_sp = re.compile(r"\s+")
JS_DIAS = "data/trama/cal/{:%Y-%m-%d}.json"
RT_URL = "https://trama.administracionelectronica.gob.es/portal/"
FCH_INI = date(2022, 5, 29)


class Trama:

    @Cache(file="data/autentica/trama.calendario.pickle", maxOld=(1 / 48))
    def _get_cal_session(self):
        with AutDriver(browser='firefox') as ff:
            ff.get(RT_URL)
            ff.click("//a[text()='Calendario']")
            return ff.to_web()

    @Cache(file="data/autentica/trama.incedencias.pickle", maxOld=(1 / 48))
    def _get_inc_session(self):
        with AutDriver(browser='firefox') as ff:
            ff.get(RT_URL)
            ff.click("//div[@id='appMenu']//a[text()='Incidencias']")
            time.sleep(2)
            ff.click("//div[@id='mainWindow']//a[text()='Enviadas']")
            return ff.to_web()

    def _get_dias(self, ini, fin):
        dias = []
        w = self._get_cal_session()
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
                tds = tmap(get_text, tr.findAll("td"))
                fec, mar, obs, ttt, tto, sld = tds
                fec = fec[:-1].split("(", 1)[-1]
                fec = tmap(int, reversed(fec.split("/")))
                fec = date(*fec)
                mar = tmap(HM, re.findall(r"\d+:\d+:\d+", mar))
                # if sld == "00:00:00" or len(mar) == 0:
                #    continue
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

    def get_dias(self, ini, fin):
        dias = []
        fln_dias = JS_DIAS.format(ini)
        if isfile(fln_dias):
            for d in FileManager.get().load(fln_dias):
                for k, v in list(d.items()):
                    if isinstance(v, str) and ":" in v:
                        d[k] = HM(v)
                d = Munch.fromDict(d)
                if d.ini >= ini and d.fin <= fin:
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

    def get_calendario(self, ini, fin):
        """
        Devuelve el control horario entre dos fechas
        """
        today = date.today()
        r = Munch(
            total=HM(0),
            teorico=HM(0),
            saldo=HM(0),
            jornadas=0,
            fichado=0,
            sal_ahora=Munch(
                ahora=HM(time.strftime("%H:%M")),
                total=None,
                saldo=None,
            ),
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
        if r.index is None:
            r.sal_ahora = None
        else:
            hoy = r.dias[r.index]
            if len(hoy.marcajes) % 2 == 0:
                r.sal_ahora = None
            else:
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
        ini = date.today()
        if ini.weekday() > 0:
            ini = ini - timedelta(days=ini.weekday())
        fin = ini + timedelta(days=6)
        return self.get_calendario(ini, fin)

    def get_informe(self, ini=FCH_INI, fin=None):
        hoy = date.today()
        if ini is None:
            raise ValueError("ini is mandatory")
        if fin is None or fin >= hoy:
            fin = hoy - timedelta(days=1)
        if ini >= hoy:
            return None
        if fin >= hoy:
            fin = hoy - timedelta(days=1)
        if ini > fin:
            return None
        r = Munch(
            total=HM(0),
            teorico=HM(0),
            saldo=HM(0),
            laborables=0,
        )
        if ini <= gesper_FCH_FIN:
            inf = Gesper().get_informe(ini, gesper_FCH_FIN)
            r.total += inf.total
            r.teorico += inf.teoricas
            r.saldo += inf.saldo
            r.laborables += inf.laborables
            ini = gesper_FCH_FIN + timedelta(days=1)
            if ini >= fin:
                return r
        for i in self.get_dias(ini, fin):
            r.total += i.total
            r.teorico += i.teorico
            r.saldo += i.saldo
            r.laborables += int(i.teorico.minutos > 0)
        #r.per_day = r.teorico.div(r.laborables)
        return r

    def get_vacaciones(self, year=None):
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

        w = self._get_cal_session()
        w.get("https://trama.administracionelectronica.gob.es/calendario/calendario.html")
        yrs = set()
        while True:
            yr = None
            for tr in w.soup.select("div.resumenMarcajes tbody tr"):
                tds = tmap(get_text, tr.select("td"))
                yr = int(tds[0])
                yrs.add(yr)
                vc = tmap(int, re.findall(r"\d+", tds[1]))
                pe = tmap(int, re.findall(r"\d+", tds[2]))
                _add(Munch(
                    key="permiso",
                    total=pe[1],
                    usados=pe[0],
                    year=yr
                ))
                _add(Munch(
                    key="vacaciones",
                    total=vc[1],
                    usados=vc[0],
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

    def get_incidencias(self, ini, fin, estado=3):
        w = self._get_inc_session()
        w.get("https://trama.administracionelectronica.gob.es/incidencias/bandejaEnviadas.html")
        mx = w.soup.select("#maximoElementosPagina option")[-1]
        mx = mx.attrs["value"]
        action, data = w.prepare_submit("#formularioPrincipal")
        data["maximoElementosPagina"] = mx
        if estado is not None:
            data["idEstadoIncidencia"] = str(estado)
        w.get(action, **data)
        r = []
        to_date = lambda x: date(*map(int, reversed(x.split("/"))))
        to_hm = lambda x: HM(x) if x is not None else None
        head = tmap(get_text, w.soup.select("#listaTablaMaestra thead tr th"))
        for tr in w.soup.select("#listaTablaMaestra tbody tr"):
            tds = tmap(get_text, tr.findAll("td"))
            tds = {k: v for k, v in zip(head, tds)}
            r.append(Munch(
                id=int(tds['Proceso']),
                tipo=tds['Tipo Solicitud'],
                solicitud=to_date(tds['Fecha solicitud']),
                validador=tds['Validador'],
                autorizador=tds['Autorizador'],
                incidencias=tds['Incidencias'],
                estado=tds['Estado'],
                tarea=to_date(tds['Fecha tarea']),
            ))
        for i in list(r):
            data['accion'] = 'REDIRIGIR_SOLICITUDES'
            data['idProceso'] = str(i.id)
            w.get(action, **data)
            tb = w.soup.select_one("#tablaIncidencias")
            if tb is None:
                continue
            i.incidencias = []
            tb.select_one("thead").extract()
            for tr in tb.select("tr"):
                tds = tmap(get_text, tr.findAll("td"))
                tipo, fecha, inicio, fin, observaciones, mensaje = tds
                i.incidencias.append(Munch(
                    tipo=tipo,
                    fecha=to_date(fecha),
                    inicio=to_hm(inicio),
                    fin=to_hm(fin),
                    observaciones=observaciones,
                    mensaje=mensaje
                ))
        return r


if __name__ == "__main__":
    a = Trama()
    #r = a.get_informe(gesper_FCH_FIN+timedelta(days=1), date.today())
    r = a.get_informe(date(2019, 2, 7), date.today())
    import json

    print(json.dumps(r, indent=2, default=json_serial))
