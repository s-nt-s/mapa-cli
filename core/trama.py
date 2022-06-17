from datetime import date, timedelta
from munch import Munch

from .autdriver import AutDriver
from .util import json_serial, tmap, get_text
from .hm import HM
from .cache import Cache
import re

re_sp = re.compile(r"\s+")


def get_times(ini, fin, delta):
    while ini < fin:
        end = ini + delta
        yield ini, min(fin, end)
        ini = ini + delta


class Trama:

    @Cache(file="data/autentica/trama.calendario.pickle", maxOld=1)
    def _get_cal_session(self):
        with AutDriver(browser='firefox') as ff:
            ff.get("https://trama.administracionelectronica.gob.es/portal/")
            ff.click("//a[text()='Calendario']")
            return ff.to_web()


    def get_calendario(self, ini, fin):
        """
        Devuelve el control horario entre dos fechas
        """
        r = []
        w = self._get_cal_session()
        for a, z in get_times(ini, fin, timedelta(days=59)):
            w.get("https://trama.administracionelectronica.gob.es/calendario/marcajesRango.html",
                  fechaInicio=a.strftime("%d/%m/%Y"),
                  fechaFin=z.strftime("%d/%m/%Y"),
                  )
            for tr in w.soup.select("tr"):
                cls = tr.attrs.get("class")
                if isinstance(cls, list) and len(cls) > 0:
                    cls = cls[0]
                if cls not in ("even", "odd"):
                    continue
                tds = tmap(get_text, tr.findAll("td"))
                fec, mar, obs, ttt, tto, sld = tds
                fec = fec[:-1].split("(", 1)[-1]
                fec = tmap(int, reversed(fec.split("/")))
                fec = date(*fec)
                mar = tmap(HM, re.findall(r"\d+:\d+:\d+", mar))
                if sld == "00:00:00" or len(mar) == 0:
                    continue
                r.append(Munch(
                    fecha=fec,
                    marcajes=mar,
                    obs=obs,
                    total=HM(ttt),
                    teorico=HM(tto),
                    saldo=sld
                ))
        return r


if __name__ == "__main__":
    today = date.today()
    a = Trama()
    r = a.get_calendario(today - timedelta(days=today.weekday()), today)
    import json
    print(json.dumps(r, indent=2, default=json_serial))
