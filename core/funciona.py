import re

from munch import Munch
from os.path import isfile, join, expanduser, basename

from .web import Driver, get_query, buildSoup
from .autdriver import AutDriver
from .filemanager import CNF, FileManager

re_sp = re.compile(r"\s+")


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
        except KeyError:
            pass
    return q


def get_text(node):
    if node is None:
        return None
    txt = re_sp.sub(" ", node.get_text()).strip()
    if len(txt) == 0:
        return None
    return txt


def to_num(s, safe=False):
    if s is None:
        return None
    if safe is True:
        try:
            return to_num(s)
        except ValueError:
            return s
    if isinstance(s, str):
        s = s.replace("€", "")
        s = s.replace(".", "")
        s = s.replace(",", ".")
        s = float(s)
    if int(s) == s:
        s = int(s)
    return s


def get_int_match(txt, *regx):
    for r in regx:
        c = re.search(r, txt, flags=re.MULTILINE | re.IGNORECASE)
        if c:
            return to_num(c.group(1))


class Funciona:
    def get_nominas(self):
        """
        Devuelve las información de las nominas
        Es necesario configurar un directorio de descargas en config.yml
        """
        w = None
        r = []
        with AutDriver(browser='firefox', visible=True) as ff:
            ff.get("https://www.funciona.es/servinomina/action/Retribuciones.do")
            soup = ff.get_soup()
            a = soup.select_one(".mod_ultimas_nominas a[href]")
            if not a:
                return []
            # https://www.funciona.es/servinomina/action/DetalleNomina.do?habil=ARF&clasnm=02&tipo=NOMINA%20ORDINARIA%20DEL%20MES&mesano=01/02/2020&dirnedaes=194&cdcierre=29004&cddup=0&type=1&cdcalculo=28965&mes=Febrero&anio=2020
            href = a.attrs["href"]
            q = query_nom(href)
            if q.get("file") is None:
                return []
            for a in soup.select("a[href]"):
                href = a.attrs["href"]
                if "/servinomina/action/ListadoNominas.do?anio=" not in href:
                    continue
                ff.get(href)
                ff.wait("//div[contains(@class,'mod_nominas_anteriores')]")
                for a in ff.get_soup().select(".mod_ultimas_nominas a[href]"):
                    href = a.attrs["href"]
                    q = query_nom(href)
                    if q.get("file") is None:
                        continue
                    nom = Munch(
                        file=join(CNF.nominas, q["file"]),
                        url=href,
                        error=False,
                        mes=q['mes'],
                        year=q['year']
                    )
                    r.append(nom)
            w = ff.to_web()
        for nom in r:
            file = str(nom.file)
            if file.startswith("~"):
                file = expanduser(file)
            if isfile(file):
                continue
            rq = w.s.get(nom.url)
            if "text/html" in rq.headers["content-type"]:
                error = get_text(w.soup.select_one("div.box-bbr"))
                if error is None:
                    error = "No es un pdf"
                nom.error = error
                continue
            FileManager.get().dump(nom.file, rq.content)

        r = sorted(r, key=lambda x: basename(x.file))
        for index, nom in enumerate(r):
            txt = FileManager.get().load(nom.file)
            nom.bruto = get_int_match(txt, r"TRANSFERENCIA DEL LIQUIDO A PERCIBIR:\s+([\d\.,]+)")
            nom.neto = get_int_match(txt, r"R\s*E\s*T\s*R\s*I\s*B\s*U\s*C\s*I\s*O\s*N\s*E\s*S\s*\.+\s*([\d\.,]+)",
                                     r"^ +([\d\.,]+) *$")
            nom.index = index

        return r


if __name__ == "__main__":
    f = Funciona()
    r = f.get_nominas()
    import json

    print(json.dumps(r, indent=2))
