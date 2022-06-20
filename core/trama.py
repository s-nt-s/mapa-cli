from datetime import datetime, date, timedelta
from munch import Munch

from .autdriver import AutDriver
from .util import json_serial, tmap, get_text, get_times
from .hm import HM
from .cache import Cache
import re
import time

re_sp = re.compile(r"\s+")
today = date.today()
now = datetime.now()


class Trama:

    @Cache(file="data/autentica/trama.calendario.pickle", maxOld=(1/48))
    def _get_cal_session(self):
        with AutDriver(browser='firefox') as ff:
            ff.get("https://trama.administracionelectronica.gob.es/portal/")
            ff.click("//a[text()='Calendario']")
            return ff.to_web()

    def get_calendario(self, ini, fin):
        """
        Devuelve el control horario entre dos fechas
        """
        r = Munch(
            total=None,
            teorico=None,
            saldo=None,
            jornadas=0,
            fichado=0,
            sal_ahora=Munch(
                index=None,
                ahora=HM(time.strftime("%H:%M")),
                total=None,
                saldo=None,
            ),
            futuro=HM(0),
            dias=[]
        )
        w = self._get_cal_session()
        for a, z in get_times(ini, fin, timedelta(days=59)):
            w.get("https://trama.administracionelectronica.gob.es/calendario/marcajesRango.html",
                  fechaInicio=a.strftime("%d/%m/%Y"),
                  fechaFin=z.strftime("%d/%m/%Y"),
                  )
            for tr in w.soup.select("tr"):
                tds = tmap(get_text, tr.findAll("td"))
                if tr.select_one("td.total"):
                    r.total, r.teorico, r.saldo = map(HM, tds[-3:])
                    continue
                cls = tr.attrs.get("class")
                if isinstance(cls, list):
                    cls = cls[0]
                if cls not in ("even", "odd"):
                    continue
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
                if i.fecha == today:
                    r.sal_ahora.index = len(r.dias)
                elif i.fecha > today:
                    r.futuro = i.saldo + r.futuro
                if i.teorico.minutos > 0:
                    r.jornadas = r.jornadas + 1
                if len(i.marcajes) > 0:
                    r.fichado = r.fichado + 1
                r.dias.append(i)
        if r.sal_ahora.index is None:
            r.sal_ahora = None
        else:
            hoy = r.dias[r.sal_ahora.index]
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


if __name__ == "__main__":
    a = Trama()
    r = a.get_semana()
    import json

    print(json.dumps(r, indent=2, default=json_serial))
