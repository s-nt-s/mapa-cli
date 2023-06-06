import re

from munch import Munch
from os.path import isfile, join, expanduser, basename

from .web import Driver, get_query, buildSoup
from .autdriver import AutDriver
from .filemanager import CNF, FileManager
from .util import get_text, to_num
from .cache import MunchCache
from glob import glob

re_sp = re.compile(r"\s+")
import requests

# Evitar error (Caused by SSLError(SSLError(1, '[SSL: DH_KEY_TOO_SMALL] dh key too small (_ssl.c:997)')))
# en www.funciona.es
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'
try:
    requests.packages.urllib3.contrib.pyopenssl.DEFAULT_SSL_CIPHER_LIST += 'HIGH:!DH:!aNULL'
except AttributeError:
    pass

def query_nom(href):
    q = get_query(href)
    q["file"] = None
    if "mesano" in q:
        mesano = q["mesano"].split("/")
        _, mes, year = (int(i) for i in mesano)
        q["mes"] = mes
        q["year"] = year
        try:
            q["file"] = "{year}.{mes:02d}-{cdcierre}-{cdcalculo}.pdf".format(**q)
        except KeyError as e:
            pass
    return q


def get_int_match(txt, *regx):
    for r in regx:
        c = re.search(r, txt, flags=re.MULTILINE | re.IGNORECASE)
        if c:
            return to_num(c.group(1))


class Funciona:

    @MunchCache(file="data/nominas/todas.json", maxOld=(1 / 24))
    def get_nominas(self):
        """
        Devuelve las información de las nominas
        Es necesario configurar un directorio de descargas en config.yml
        """

        done = set()
        w = None
        r = {}
        nom_json = "data/nominas/{}.json"
        for fl in sorted(glob(nom_json.format("*"))):
            for nom in (Munch.fromDict(FileManager.get().load(fl)) or []):
                r[basename(nom.file)]=nom
            done.add(fl.split("/")[-1].split(".")[0])
        with AutDriver(browser='firefox', visible=False) as ff:
            ff.get("https://www.funciona.es/servinomina/action/Retribuciones.do")
            soup = ff.get_soup()
            a = soup.select_one(".mod_ultimas_nominas a[href]")
            if not a:
                return None
            # https://www.funciona.es/servinomina/action/DetalleNomina.do?habil=ARF&clasnm=02&tipo=NOMINA%20ORDINARIA%20DEL%20MES&mesano=01/02/2020&dirnedaes=194&cdcierre=29004&cddup=0&type=1&cdcalculo=28965&mes=Febrero&anio=2020
            href = a.attrs["href"]
            q = query_nom(href)
            if q.get("file") is None:
                return None
            for ayr in soup.select("a[href]"):
                href = ayr.attrs["href"]
                if "/servinomina/action/ListadoNominas.do?anio=" not in href:
                    continue
                if str(get_query(href)['anio']) in done:
                    continue
                ff.get(href)
                ff.wait("//div[contains(@class,'mod_nominas_anteriores')]")
                for a in ff.get_soup().select(".mod_ultimas_nominas a[href]"):
                    href = a.attrs["href"]
                    q = query_nom(href)
                    if q.get("file") is None:
                        continue
                    href = href.replace(" ", "+")
                    nom = Munch(
                        file=join(CNF.nominas, q["file"]),
                        url=href,
                        error=False,
                        mes=q['mes'],
                        year=q['year']
                    )
                    r[basename(nom.file)] = nom
            w = ff.to_web()

        r = sorted(r.values(), key=lambda x: basename(x.file))
        for nom in r:
            if nom.get('neto') is not None:
                continue
            if not isfile(expanduser(nom.file)):
                rq = w.s.get(nom.url)
                if "text/html" in rq.headers["content-type"]:
                    error = get_text(w.soup.select_one("div.box-bbr"))
                    if error is None:
                        error = "No es un pdf"
                    nom.error = error
                FileManager.get().dump(nom.file, rq.content)
            if isfile(expanduser(nom.file)):
                txt = FileManager.get().load(nom.file, physical=True)
                txt = txt.split("IMPORTES EN NOMINA", 1)[-1]
                nom.neto = get_int_match(txt, r"TRANSFERENCIA DEL LIQUIDO A PERCIBIR:\s+([\d\.,]+)")
                nom.bruto = get_int_match(txt, r"R\s*E\s*T\s*R\s*I\s*B\s*U\s*C\s*I\s*O\s*N\s*E\s*S\s*\.+\s*([\d\.,]+)",
                                          r"^ +([\d\.,]+) *$")
                if nom.bruto < nom.neto:
                    aux = [b for b in map(to_num, re.findall(r"\b\d[\d\.\,]+\b", txt)) if nom.neto < b < (nom.neto*1.5)]
                    if aux:
                        nom.bruto=aux[0]
        yrs = sorted(set(i.year for i in r))
        myr = yrs[-1]
        if r[-1].mes < 3:
            myr = myr - 1
        for y in yrs:
            njs = nom_json.format(y)
            if y < myr and not isfile(njs):
                FileManager.get().dump(njs, [n for n in r if n.year == y])

        for index, nom in enumerate(r):
            nom.index = index
        return r


if __name__ == "__main__":
    f = Funciona()
    r = f.get_nominas()
    import json

    print(json.dumps(r, indent=2))
