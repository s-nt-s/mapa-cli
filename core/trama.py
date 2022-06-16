import os
import re

from bunch import Bunch
from glob import glob
from datetime import date, timedelta
import selenium
import time

from .common import (DAYNAME, _str, dict_style, get_config, html_to_md,
                     js_print, parse_dia, parse_mes, print_response, js_print, read_pdf, to_num)
from .web import Driver, get_query, buildSoup
from .mapdriver import MapDriver

re_sp = re.compile(r"\s+")

def get_int_match(txt, *regx):
    for r in regx:
        c = re.search(r, txt, flags=re.MULTILINE | re.IGNORECASE)
        if c:
            return to_num(c.group(1))


def add_from_nomina_pdf(nominas, target):
    if nominas:
        m_year, m_mes = max((n.year, n.mes) for n in nominas)
        m_ym = m_year + (m_mes/100)
        files = tuple(n.name for n in nominas)
    else:
        m_ym = -1
        files = tuple()
    pdfs = glob(target+"/*XXXXXXX*.pdf")
    pdfs = pdfs + glob(target+"/*.*-*-*.pdf")
    for f in sorted(pdfs):
        n = os.path.basename(f)
        if n in files:
            continue
        y, m = n.split("-")[0].split(".")
        year, mes = int(y), int(m)
        ym = year + (mes/100)
        if ym<=m_ym:
            continue
        txt = "\n".join(read_pdf(f))
        neto = get_int_match(txt, r"TRANSFERENCIA DEL LIQUIDO A PERCIBIR:\s+([\d\.,]+)")
        bruto = get_int_match(txt, r"R\s*E\s*T\s*R\s*I\s*B\s*U\s*C\s*I\s*O\s*N\s*E\s*S\s*\.+\s*([\d\.,]+)", r"^ +([\d\.,]+) *$")
        if neto is None or bruto is None:
            continue
        nominas.append(Bunch(
            bruto=bruto,
            neto=neto,
            url=None,
            name=n,
            year=year,
            mes=mes,
            index=len(nominas)
        ))

def query_nom(href):
    q = get_query(href)
    q["file"] = None
    if "mesano" in q:
        mesano = q["mesano"].split("/")
        _, mes, year = (int(i) for i in mesano)
        q["mes"]=mes
        q["year"]=year
        try:
            q["file"] = "{year}.{mes:02d}-{cdcierre}-{cdcalculo}.pdf".format(**q)
        except KeyError:
            pass
    return q

def __dwn_trama(ff, cnf, ini, fin, target):
    ff.get("https://trama.administracionelectronica.gob.es/portal/")
    ff.click("//a[text()='Calendario']")
    ff.val("fechaInicio", ini.strftime("%d/%m/%Y"))
    ff.val("fechaFin", fin.strftime("%d/%m/%Y"))
    ff.click("//button[@value='ods']")
    time.sleep(5)
    ff.wait("//button[@value='ods']")
    s = ff.pass_cookies()
    r = s.get("https://trama.administracionelectronica.gob.es/calendario/descargaFicheros.html")
    name = ini.strftime("%Y-%m-%d") + "_" + fin.strftime("%Y-%m-%d") + ".ods"
    absn = os.path.join(target, name)
    with open(absn, "wb") as f:
        f.write(r.content)


def dwn_trama(cnf, ini, fin, target):
    with MapDriver(browser='firefox', visible=True) as ff:
        try:
            r = __dwn_trama(ff, cnf, ini, fin, target)
        except selenium.common.exceptions.TimeoutException:
            raise
            return False
    return r

if __name__ == "__main__":
    today = date.today()
    cnf = get_config()
    dwn_trama(cnf, today - timedelta(days=60), today - timedelta(days=1), target=cnf.informe_horas)
