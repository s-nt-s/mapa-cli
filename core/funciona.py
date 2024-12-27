import re

from os.path import isfile, join, expanduser, basename

from .web import get_query, Web
from .autdriver import AutDriver
from .filemanager import CNF, FileManager
from .util import get_text, to_num
from .cache import Cache
from glob import glob
import requests
from typing import NamedTuple, Dict, List, Union, Tuple

re_sp = re.compile(r"\s+")

# Evitar error
# (Caused by SSLError(SSLError(1, '[SSL: DH_KEY_TOO_SMALL] dh key too small (_ssl.c:997)')))
# en www.funciona.es
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'
try:
    requests.packages.urllib3.contrib.pyopenssl.DEFAULT_SSL_CIPHER_LIST += 'HIGH:!DH:!aNULL'
except AttributeError:
    pass


class NominaCache(Cache):
    def read(self, *args, **kwargs):
        d = super().read(*args, **kwargs)
        if isinstance(d, list):
            d = [Nomina.build(**n) for n in d]
        return tuple(d)

    def save(self, file, data: Union[List[NamedTuple], Tuple[NamedTuple]], *args, **kwargs):
        if isinstance(data, (list, tuple)):
            data = [d._asdict() for d in data]
        return super().save(file, data, *args, **kwargs)


class Nomina(NamedTuple):
    mes: int
    year: int
    file: str = None
    url: str = None
    error: bool = False
    bruto: float = None
    neto: float = None
    irpf: float = None

    def merge(self, **kwarg):
        return Nomina(**{**self._asdict(), **kwarg})

    def get(self, field):
        return self._asdict().get(field)

    @classmethod
    def build(cls, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if k in cls._fields}
        return cls(**kwargs)


def query_nom(href):
    q = get_query(href)
    q["file"] = None
    mesano = q.get("mesano")
    if isinstance(mesano, str):
        _, mes, year = map(int, mesano.split("/"))
        q["mes"] = mes
        q["year"] = year
        try:
            q["file"] = "{year}.{mes:02d}-{cdcierre}-{cdcalculo}.pdf".format(**q)
        except KeyError:
            pass
    return q


def get_int_match(txt, *regx, top=None):
    for r in regx:
        if isinstance(r, re.Pattern):
            c = r.search(txt)
        else:
            c = re.search(r, txt, flags=re.MULTILINE | re.IGNORECASE)
        if isinstance(c, re.Match):
            v = to_num(c.group(1))
            if v is None:
                continue
            if top is None or v<=top:
                return v


class FuncionException(Exception):
    pass


class Funciona:
    NOM_JSON = "data/nominas/{}.json"

    @NominaCache(file="data/nominas/todas.json", maxOld=(1 / 24))
    def get_nominas(self):
        """
        Devuelve las información de las nominas
        Es necesario configurar un directorio de descargas en config.yml
        """

        w: Web
        r: List[Nomina]
        w, r = self.__get_nominas()

        def _complete(nom: Nomina):
            if nom.neto:
                return nom
            if not isfile(expanduser(nom.file)):
                rq = w.s.get(nom.url)
                if "text/html" in rq.headers["content-type"]:
                    error = get_text(w.soup.select_one("div.box-bbr"))
                    if error is None:
                        error = "No es un pdf"
                    return nom.merge(error=error)
                FileManager.get().dump(nom.file, rq.content)
            if not isfile(expanduser(nom.file)):
                return nom
            txt: str = FileManager.get().load(nom.file, physical=True)
            txt = txt.split("IMPORTES EN NOMINA", 1)[-1]
            nom = nom.merge(
                neto=get_int_match(
                    txt,
                    r"TRANSFERENCIA DEL LIQUIDO A PERCIBIR:\s+(\d[\d\.,]+)"
                ),
                bruto=get_int_match(
                    txt,
                    r"R\s*E\s*T\s*R\s*I\s*B\s*U\s*C\s*I\s*O\s*N\s*E\s*S\s*\.+\s*(\d[\d\.,]+)",
                    r"^ +([\d\.,]+) *$"
                ),
                irpf=get_int_match(
                    txt,
                    re.compile(r"DATOS\s+DEL\s+I\.R\.P\.F\..*?RETENCION\n.*?(\d[\d\.]+)\n", flags=re.DOTALL),
                    r"BASE\s+SUJETA\s+A\s+RETENCION\s+DEL\s+IRPF.*?(\d[\d\.,]+)\s*$",
                    r"(\d[\d\.,]+)\n\s*4\.\s+BASE\s+SUJETA\s+A\s+RETENCION\s+DEL\s+IRPF",
                    r"I\.R\.P\.F\..*?([\d\.,]+)\s*$",
                    top=60
                )
            )
            if nom.bruto < nom.neto:
                aux = map(to_num, re.findall(r"\b\d[\d\.\,]+\b", txt))
                aux = [b for b in aux if nom.neto < b < (nom.neto*1.5)]
                if aux:
                    nom = nom.merge(bruto=aux[0])
            return nom

        r = list(map(_complete, r))

        yrs = sorted(set(i.year for i in r))
        myr = yrs[-1]
        if r[-1].mes < 3:
            myr = myr - 1
        for y in yrs:
            njs = Funciona.NOM_JSON.format(y)
            if y < myr and not isfile(njs):
                FileManager.get().dump(njs, [n._asdict() for n in r if n.year == y])

        return tuple(r)

    def __get_nominas(self):
        done = set()
        w: Web = None
        r: Dict[str, Nomina] = {}
        for fl in sorted(glob(Funciona.NOM_JSON.format("*"))):
            for nom in FileManager.get().load(fl):
                r[basename(nom['file'])] = Nomina.build(**nom)
            done.add(fl.split("/")[-1].split(".")[0])
        with AutDriver(browser='firefox', visible=False) as ff:
            ff.get("https://www.funciona.es/servinomina/action/Retribuciones.do")
            soup = ff.get_soup()
            # https://www.funciona.es/servinomina/action/DetalleNomina.do?habil=ARF&clasnm=02&tipo=NOMINA%20ORDINARIA%20DEL%20MES&mesano=01/02/2020&dirnedaes=194&cdcierre=29004&cddup=0&type=1&cdcalculo=28965&mes=Febrero&anio=2020
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
                    nom = Nomina(
                        file=join(CNF.nominas, q["file"]),
                        url=href,
                        error=False,
                        mes=q['mes'],
                        year=q['year']
                    )
                    r[basename(nom.file)] = nom
            w = ff.to_web()

        noms = sorted(r.values(), key=lambda x: basename(x.file))

        return w, noms


if __name__ == "__main__":
    f = Funciona()
    r = f.get_nominas()
    import json

    print(json.dumps(r, indent=2))
