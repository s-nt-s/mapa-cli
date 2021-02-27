import os
import re

from bunch import Bunch
from glob import glob
from datetime import date, timedelta
import selenium
import time

from .common import (DAYNAME, _str, dict_style, get_config, html_to_md,
                     js_print, parse_dia, parse_mes, print_response, js_print, read_pdf, to_num)
from .web import FF, get_query, buildSoup

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

def __dwn_funciona_nominas(ff, target, cnf, m_year, m_mes):
    ff.get("https://www.funciona.es/servinomina/action/Retribuciones.do")
    ff.val("username", cnf.autentica.user)
    ff.val("password", cnf.autentica.pssw)
    ff.click("submitAutentica")
    time.sleep(5)
    if ff.get_soup().find("p", text="Sólo es posible acceder a esta aplicación con una contraseña fuerte."):
        return False
    ff.wait("//div[contains(@class,'mod_nominas_anteriores')]")
    soup = ff.get_soup()
    a = soup.select_one(".mod_ultimas_nominas a[href]")
    if not a:
        return False
    #https://www.funciona.es/servinomina/action/DetalleNomina.do?habil=ARF&clasnm=02&tipo=NOMINA%20ORDINARIA%20DEL%20MES&mesano=01/02/2020&dirnedaes=194&cdcierre=29004&cddup=0&type=1&cdcalculo=28965&mes=Febrero&anio=2020
    href = a.attrs["href"]
    q = query_nom(href)
    if q.get("file") is None:
        return False
    flag = False
    for a in soup.select("a[href]"):
        href = a.attrs["href"]
        if "/servinomina/action/ListadoNominas.do?anio=" in href:
            ff.get(href)
            ff.wait("//div[contains(@class,'mod_nominas_anteriores')]")
            for a in ff.get_soup().select(".mod_ultimas_nominas a[href]"):
                href = a.attrs["href"]
                q = query_nom(href)
                if q.get("file") is None:
                    continue
                absn = os.path.join(target, q["file"])
                if os.path.isfile(absn):
                    continue
                s = ff.pass_cookies()
                r = s.get(href)
                if "text/html" in r.headers["content-type"]:
                    error = buildSoup(href, r.content)
                    error = error.select_one("div.box-bbr")
                    if error:
                        error = error.get_text()
                        error = re_sp.sub(" ", error)
                        error = error.strip()
                    if not error:
                        error = "No es un pdf"
                    print(q['file'], error)
                    continue
                flag = True
                with open(absn, "wb") as f:
                    f.write(r.content)
    return flag

def dwn_funciona_nominas(target, cnf, m_year, m_mes):
    today = date.today()
    if today.day<25:
        today = today - timedelta(days=(today.day+1))
    mes, year = today.month, today.year
    if (year<m_year or (year==m_year and mes<=m_mes)):
        return False
    ff = FF()
    try:
        r = __dwn_funciona_nominas(ff, target, cnf, m_year, m_mes)
    except selenium.common.exceptions.TimeoutException:
       return False
    finally:
        ff.close()
    return r
