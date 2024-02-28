import tabula
from io import StringIO
import json
import re
from .util import to_num, json_serial, tmap
from .web import Web
from .filemanager import CNF, FileManager
from os.path import join, isfile
from munch import Munch
import urllib3
from .cache import Cache
from datetime import date
from functools import lru_cache

urllib3.disable_warnings()

re_cellnb = re.compile(r'\s([\d\.,]+)\s')


class RtCache(Cache):
    def read(self, file, *args, **kvargs):
        d = super().read(file, *args, **kvargs)
        if d is None or len(d) == 0:
            return None
        if d["niveles"]:
            d["niveles"] = {int(k): v for k, v in d["niveles"].items()}
        d = Munch.fromDict(d)
        return d


def parseTb(table):
    if table is None:
        return []
    s = StringIO()
    sep = '\t'
    table.to_csv(s, index=False, header=False, sep=sep)
    s = s.getvalue()
    s = s.strip()
    rows = []
    for r in s.split("\n"):
        r = re_cellnb.sub(lambda m: sep + m.group() + sep, r)
        r = r.strip()
        row = []
        for c in re.split(r"\s*\t\s*", r):
            c = to_num(c, safe=True)
            if isinstance(c, str):
                slp = tmap(lambda x: to_num(x, safe=True), re.split(r"\s+", c))
                if not any([x for x in slp if isinstance(x, str)]):
                    row.extend(slp)
                    continue
            row.append(c)
        rows.append(row)
    return rows


class Retribuciones:

    @lru_cache(maxsize=None)
    def get_docs(self):
        w = Web(verify=False)
        retribucion = {}
        w.get(
            "https://www.sepg.pap.hacienda.gob.es/sitios/sepg/es-ES/CostesPersonal/EstadisticasInformes/Paginas/RetribucionesPersonalFuncionario.aspx")
        for a in w.soup.select("a[href]"):
            txt = a.get_text().strip()
            if txt.startswith("Retribuciones del personal funcionario"):
                yr = [int(i) for i in txt.split() if i.isdigit()]
                if yr and yr[0] > 2000:
                    url = a.attrs["href"]
                    yr = int(yr[0])
                    if yr not in retribucion:
                        retribucion[yr] = url
        return retribucion

    def get(self):
        year = date.today().year
        data = self._get(year)
        if data:
            return data
        rts = self.get_docs()
        if len(rts) == 0:
            return {}
        return self._get(max(rts.keys()))

    @RtCache(file="data/retribuciones/{}.json", maxOld=30)
    def _get(self, year):
        rts = self.get_docs()
        if len(rts) == 0 or year not in rts:
            return {}
        link = rts[year]
        absn = join(CNF.retribuciones, str(year) + ".pdf")
        if not isfile(absn):
            r = Web().s.get(link, verify=False)
            FileManager.get().dump(absn, r.content)

        tableC = None
        tableS = None
        for t in tabula.read_pdf(absn, pages=1, multiple_tables=True):
            if 'COMPLEMENTO DE DESTINO' in t.columns:
                tableC = t
            elif 'A2' in t.columns and 'A2' in t.columns and 'C1' in t.columns:
                tableS = t

        data = Munch(
            year=year,
            fuente=link
        )
        grupos = ("A1", "A2", "B", "C1", "C2", "E")
        for g in grupos:
            data[g] = Munch()

        tableS = parseTb(tableS)
        tableC = parseTb(tableC)
        for index, row in enumerate(tableS):
            if not tableC and row[0] == 'COMPLEMENTO DE DESTINO':
                tableC = tableS[index:]
                break
            if not (len(row) > 2 and isinstance(row[0], str) and isinstance(row[1], (int, float))):
                continue
            txt = row[0].replace(" ", '')
            sld = [r for i, r in enumerate(row[1:]) if i % 2 == 0]
            tri = [r for i, r in enumerate(row[1:]) if i % 2 == 1]
            key = None
            if txt.startswith("ANUAL"):
                key = "base"
            elif txt.startswith("PAGAEXTRAJUNIO"):
                key = "junio"
            elif txt.startswith("PAGAEXTRADICIEMBRE"):
                key = "diciembre"
            if key is None:
                continue
            for i, g in enumerate(grupos):
                data[g][key] = Munch(
                    sueldo=sld[i],
                    trienio=tri[i]
                )

        data.niveles = {}
        for row in tableC:
            if row[0] is None or not isinstance(row[0], int):
                continue
            row = [r for i, r in enumerate(row) if i % 2 == 0]
            row = iter(row)
            nivel = next(row)
            compd = next(row)
            data.niveles[nivel] = compd

        return data

    def get_sueldo(self, grupo, nivel, especifico, trienios):
        rt = self.get()
        rg = rt.get(grupo)

        sl = Munch(
            fuente=rt.fuente,
            base=rg.base.sueldo,
            complemento=Munch(
                destino=rt.niveles.get(nivel),
                especifico=especifico
            ),
            extra=Munch(
                junio=rg.junio.sueldo,
                diciembre=rg.diciembre.sueldo
            ),
            trienios=Munch(
                base=0,
                extra=Munch(
                    junio=0,
                    diciembre=0
                )
            )
        )

        for grupo, num in (trienios or {}).items():
            sl.trienios.base = sl.trienios.base + rt[grupo].base.trienio
            sl.trienios.extra.junio = sl.trienios.extra.junio + rt[grupo].junio.trienio
            sl.trienios.extra.diciembre = sl.trienios.extra.diciembre + rt[grupo].diciembre.trienio

        return sl


if __name__ == '__main__':
    r = Retribuciones()
    r = r.get()

    print(json.dumps(r, indent=2, default=json_serial))
