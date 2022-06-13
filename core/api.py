import json
import os
import re
import time
from calendar import monthrange
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlparse

import bs4
import requests
import urllib3
from bunch import Bunch
from glob import glob
import textwrap
from requests.auth import HTTPBasicAuth

from .common import (DAYNAME, _str, dict_style, get_config, html_to_md,
                     js_print, parse_dia, parse_mes, print_response, js_print, read_pdf, to_num)
from .retribuciones import retribucion_to_json
from .hm import HM, IH
from .user import User
from .web import FF
from .funciona import add_from_nomina_pdf, dwn_funciona_nominas

urllib3.disable_warnings()

default_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0',
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Expires": "Thu, 01 Jan 1970 00:00:00 GMT",
    'Accept': 'text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    "X-Requested-With": "XMLHttpRequest",
}

re_hm = re.compile(r"\d\d:\d\d")
re_sp = re.compile(r"\s+")
re_pr = re.compile(r"\([^\(\)]+\)")
re_url = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
fix_url = (
    (re.compile(r"^(https?://[^/]*\.?)mapama\.es"), r"\1mapa.es"),
    (re.compile(r"^(https?://[^/]+):443/"), r"\1/"),
    (re.compile(r"/default\.aspx"), ""),
)

def get_select_text(soup, *selects, index=0, extract=False):
    r = []
    for select in selects:
        n = soup.select(select)
        if len(n) > index:
            n = n[index]
            if extract:
                n.extract()
            v = n.get_text().strip()
            if v:
                r.append(v)
    if len(selects)==1:
        return r[0] if r else None
    return r

def to_strint(f):
    if f is None:
        return None
    f = round(f)
    f = '{:,}'.format(f).replace(",", ".")
    return f


def tr_clave_valor(soup, id, *args, **keys):
    ok_key = tuple(args) + tuple(keys.keys())
    for tr in soup.select("#"+id+" tr"):
        tds = [td.get_text().strip() for td in tr.findAll("td")]
        if len(tds) < 2:
            continue
        clave = tds[0]
        valor = tds[1]
        if not clave or not valor:
            continue
        if ok_key and clave not in ok_key:
            continue
        if keys and keys.get(clave) is not None:
            clave = keys[clave]
        if valor == valor.upper() and clave not in ("N.R.P.", ):
            valor = valor.capitalize()
        if clave == "Dirección":
            valor = valor.split(", madrid")[0]
            valor = valor.title()
            valor = valor.replace(" De ", " de ")
            valor = valor.replace(" La ", " la ")
        yield clave, valor

def print_dict(kv, _print, prefix=""):
    max_campo = max(len(i[0]) for i in kv.items())
    line = "%-"+str(max_campo)+"s:"
    for k, v in kv.items():
        if v:
            _print(prefix + (line % k), end="")
            if isinstance(v, (tuple, list, set)):
                v = ", ".join(str(i) for i in v)
            if isinstance(v, dict):
                _print("")
                print_dict(v, _print, prefix="  ")
            else:
                _print(" "+str(v))


def iterhref(soup, *args):
    if len(args)==0:
        args = ("img", "form", "a", "iframe", "frame", "link", "script")
    for n in soup.findAll(args):
        attr = "href" if n.name in ("a", "link") else "src"
        if n.name == "form":
            attr = "action"
        val = n.attrs.get(attr)
        if val and not (val.startswith("#") or val.startswith("javascript:")):
            yield n, attr, val


def buildSoup(response):
    soup = bs4.BeautifulSoup(response.content, "lxml")
    for n, attr, val in iterhref(soup):
        val = urljoin(response.url, val)
        for r, txt  in fix_url:
            val = r.sub(txt, val)
        n.attrs[attr] = val
    return soup


class Api:
    def __init__(self, refer=None, bot=None):
        self.cnf = get_config()
        self.s = requests.Session()
        self.s.headers = default_headers
        self.response = None
        self.soup = None
        self.form = None
        self.refer = refer
        self.debug = None
        self.debug_count = 0
        self.root_url = None
        self.silent = False
        self.verify = True
        self.bot = bot
        self._log_response =  []

    def print(self, *args, avoidEmpty=False, **kargv):
        if avoidEmpty:
            args = tuple(a for a in args if a)
        if avoidEmpty and len(args)==0:
            return
        if self.silent:
            if isinstance(self.silent, int) and not isinstance(self.silent, bool):
                self.silent = self.silent - 1
            return
        print(*args, **kargv)

    def log_response(self, response=None):
        response = response or self.response
        for r in response.history:
            self._log_response.append(r)
        self._log_response.append(response)

    def get(self, *urls, **kargv):
        for url in urls[:-1]:
            self.get(url)
        url = urls[-1].rstrip()
        if self.refer:
            self.s.headers.update({'referer': self.refer})
        if kargv and "DirectoryWebService.asmx" in url:
            dt = json.dumps(kargv, separators=(',', ':'))
            self.s.headers["Content-Type"]="application/json; charset=utf-8"
            self.response = self.s.post(url, data=dt, verify=self.verify)
            self.log_response()
            del self.s.headers["Content-Type"]
            return self.response
        if kargv:
            self.response = self.s.post(url, data=kargv, verify=self.verify)
        else:
            self.response = self.s.get(url, verify=self.verify)
        self.log_response()
        if "VerInforme.ashx" in url:
            return self.response
        self.refer = self.response.url
        self.soup = buildSoup(self.response)
        for n, attr, val in iterhref(self.soup, "script"):
            self.s.get(n.attrs[attr], verify=self.verify)

        if self.debug:
            fl = ""
            if os.path.isdir(self.debug):
                self.debug_count = self.debug_count + 1
                p = urlparse(url)
                fl = ("%02d-" % self.debug_count) + p.netloc +p.path
                if fl.endswith(".html"):
                    fl = fl[:-5]
                if p.query:
                    fl = fl+"_"+p.query
                if fl.endswith(".html"):
                    fl = fl[:-5]
                fl = "/" + fl.replace("/", "_") +".html"
            self.save(self.debug+fl)
        return self.soup

    def prepare_submit(self, slc, silent_in_fail=False, **kargv):
        data = {}
        slc = self.soup.select(slc)
        if silent_in_fail and len(slc)==0:
            return None, None
        self.form = slc[0]
        for i in self.form.select("input[name]"):
            name = i.attrs["name"]
            data[name] = i.attrs.get("value")
        for i in self.form.select("select[name]"):
            name = i.attrs["name"]
            slc = i.select("option[selected]")
            slc = slc[0].attrs.get("value") if len(slc) else None
            data[name] = slc
        data = {**data, **kargv}
        return self.form.attrs.get("action").rstrip(), data

    def submit(self, slc, silent_in_fail=False, **kargv):
        action, data = self.prepare_submit(slc, silent_in_fail=silent_in_fail, **kargv)
        if silent_in_fail and action is None:
            return
        self.get(action, **data)

    def save(self, fl):
        with open(fl, "w") as f:
            f.write(str(self.soup))

    def _id(self, id, cast=None):
        n = self.soup.find(attrs={"id": id})
        if cast is not None:
            return cast(n.get_text().strip())
        return n

    @property
    def dias(self):
        prev = 0
        year, mes = self._find_mes(*self.soup.select("#Tabla td"))
        for a in self.soup.select("#CalHorario td a"):
            dia = a.get_text().strip()
            if dia.isdigit():
                dia = int(dia)
                prev = dia
                href = a.attrs["href"]
                if href.startswith("javascript:__doPostBack('CalHorario','"):
                    id = href[38:].split("'")[0]
                    id = int(id)
                    td = a.find_parent("td")
                    style = dict_style(td)
                    _mes = a.attrs["title"].strip().split()[-1]
                    _mes = _mes.lower()[:3]
                    _mes = parse_mes(_mes)
                    dt = date(year, _mes, dia)
                    if mes != _mes:
                        if _mes == 12:
                            dt = dt.replace(year=year-1)
                        if _mes == 1:
                            dt = dt.replace(year=year+1)
                    yield dt, id, style.get("background-color"), td

    def needVpn(self):
        if not self.cnf.vpn:
            return False
        self.get("https://vpn.mapama.es",
                 "https://vpn.mapama.es/+CSCOE+/logon.html")
        self.submit("#unicorn_form", username=self.cnf.mapa.user,
                    password=self.cnf.mapa.pssw)
        return True

    def gesper(self, *args, **kargv):
        isVpn = False
        if self.needVpn():
            isVpn = True
            self.root_url = "https://vpn.mapama.es/+CSCO+1075676763663A2F2F766167656E6172672E7A6E636E7A6E2E7266++/app/GESPER/"
            self.get(
                "https://vpn.mapama.es/+CSCO+0075676763663A2F2F766167656E6172672E7A6E636E7A6E2E7266++/app/gesper/login.aspx")
        else:
            self.root_url = "https://intranet.mapa.es/app/GESPER/"
            self.get("https://intranet.mapa.es/", "https://intranet.mapa.es/app/gesper/",
                     "https://intranet.mapa.es/app/gesper/Default.aspx")
        self.submit("#Form1", TxtDNI=self.cnf.gesper.user,
                    TxtClave=self.cnf.gesper.pssw)
        for i, url in enumerate(args):
            if isVpn:
                url = url.replace("/VerInforme.ashx",
                                  "/-CSCO-3p--VerInforme.ashx")
            if kargv and i == len(args)-1:
                self.get(self.root_url+url, **kargv)
            else:
                self.get(self.root_url+url)

    def agenda(self, *args, **kargv):
        user = self.cnf.mapa.user.split("@")[0]
        url = "https://servicio.mapama.gob.es/cucm-uds/user/"
        if self.needVpn():
            url = "https://vpn.mapama.es/+CSCO+0475676763663A2F2F66726569767076622E7A6E636E7A6E2E74626F2E7266++/cucm-uds/user/"
        url = url + user+"/speedDials"
        self.response = self.s.get(url, auth=HTTPBasicAuth(user, self.cnf.mapa.pssw))
        self.log_response()
        self.soup = buildSoup(self.response)
        return self.soup

    def intranet(self, *args, **kargv):
        if self.needVpn():
            self.root_url = "https://vpn.mapama.es/+CSCO+1h75676763663A2F2F766167656E6172672E7A6E636E7A6E2E7266++/"
        else:
            self.root_url = "https://intranet.mapa.es/"
        self.get(self.root_url)
        for i, url in enumerate(args):
            if not url.startswith("http"):
                url = self.root_url + url
            if kargv and i == len(args)-1:
                self.get(url, **kargv)
            else:
                self.get(url)

    def semana_estadistica(self, jornada, *laburo):
        dias = len(laburo)
        if dias == 0:
            return None

        jZer = HM("07:00")
        jIni = HM("09:00")
        jFin = HM("14:30")
        jMin = jFin - jIni

        laburado = sum(laburo, HM("00:00"))
        per_day = laburado.div(dias)
        deberia = jornada.mul(dias)
        desfase = deberia - laburado
        signo = None
        manana = jornada
        if desfase.minutos:
            signo = (deberia < laburado)

        e = Bunch(
            dias=dias,
            per_day=per_day,
            laburado=laburado,
            desfase=desfase,
            signo=signo,
            desfase_str=None,
            manana=None
        )
        e.media_str = "Media: %s * %s = %s" % (e.per_day, e.dias, e.laburado)
        if signo is not None:
            e.desfase_str = "Desfase de %s%s" % (
                "+" if e.signo else "-", e.desfase.spanish)
            if signo:
                manana = manana - e.desfase
            else:
                manana = manana + e.desfase
        if manana >= jMin:
            _ini = jFin - manana
            if _ini < jZer:
                _ini = jZer
            e.manana = Bunch(
                op1=(jIni, jIni+manana),
                op2=(_ini, _ini+manana),
                op1_str=None,
                op2_str=None
            )
            e.manana.op1_str = "de %s a %s" % e.manana.op1
            if e.manana.op2 != e.manana.op1:
                e.manana.op2_str = "de %s a %s" % e.manana.op2

        return e

    def horas_semana(self):
        festi = {f.date.date():f for f in self.get_festivos(max_iter=1)}
        lapso = self.lapso_dias()
        today = date.today()
        self.gesper("ControlHorario/Fichajes.aspx")
        hecho = self._id("LblTotalCumplidas", cast=HM)
        total = self._id("LblTotalCumplir", cast=HM)
        falta = total - hecho if total > hecho else None
        self.print("Semana: "+str(total)+"\n")
        hoy = None
        laburo = []
        isTrabajando = False
        parcial_lapso = None
        parcial_lapso_hoy = HM("00:00")
        count_festivos = 0
        for fch, id, style, td in self.dias:
            if style != "lightgrey":
                continue
            fst = festi.get(fch)
            if fst:
                self.print("%2d: %s " % (fst.dia, fst.nombre))
                count_festivos = count_festivos + 1
                continue
            parcial_lapso = HM("00:00")
            txt = td.get_text().strip()
            hms = [HM(hm) for hm in re_hm.findall(txt)]
            if fch in lapso:
                self.print("%2d: %s " % (fch.day, lapso[fch].txt))
                parcial_lapso = lapso[fch].h_dur
            if len(hms) > 0:
                isHoy = (fch == today)
                ini = hms[0]
                if fch in lapso and len(hms) == 1 and not isHoy:
                    laburo.append(parcial_lapso)
                    continue
                if len(hms) > 1:
                    fin = hms[-1]
                    itr = HM.intervalo(*hms)
                    laburo.append(itr + parcial_lapso)
                else:
                    isTrabajando = isHoy
                    parcial_lapso_hoy = parcial_lapso
                    hoy = ini
                    fin = HM(time.strftime("%H:%M"))
                    itr = HM.intervalo(ini, fin)
                if isTrabajando:
                    self.print("%2d: %s - %s = %s" % (fch.day, ini,
                                                      fin, itr), "y subiendo")
                elif len(hms) == 1:
                    self.print("%2d: %s - --_-- = --:--" % (fch.day, ini))
                else:
                    str_hms = ["{} - {}".format(hms[i], (hms+["--_--"])[i+1]) for i in range(0, len(hms), 2)]
                    str_hms = " + ".join(str_hms)
                    self.print("%2d: %s = %s" % (fch.day, str_hms, itr))

        jornada = total.safe_jornada
        if jornada and count_festivos:
            falta = falta - jornada.mul(count_festivos)

        ahora = HM(datetime.now().strftime("%H:%M"))
        flag = True
        if jornada is not None:
            e1 = self.semana_estadistica(jornada, *laburo)
            e2 = self.semana_estadistica(jornada, HM.intervalo(
                hoy, ahora) + parcial_lapso_hoy, *laburo) if isTrabajando else None
            if (e1 or e2):
                flag = False
                self.print("")
            if e1 and not(e2 and e2.per_day >= jornada):
                self.print(e1.media_str)
            if e2:
                self.print(e2.media_str, "y subiendo")

        if falta is not None:
            if flag:
                self.print("")
            if isTrabajando:
                itr = HM.intervalo(hoy, ahora) + parcial_lapso_hoy
                f = falta - itr
                if (itr > falta):
                    self.print("Falta:", "-"+str(f), "¡Te has pasado!")
                else:
                    self.print("Falta:", f.enJornadas(
                        jornada, maximo=(4-today.weekday())), "y bajando")
            else:
                self.print("Falta:", falta.enJornadas(jornada))

        if jornada is None:
            return

        if e2 and e2.desfase_str:
            self.print("\n"+e2.desfase_str, "y subiendo")
        elif e1 and e1.desfase_str:
            self.print("\n"+e1.desfase_str)

        if not isTrabajando:
            if e1 and e1.manana and today.weekday() < 4:
                self.print("\nPróxima jornada:")
                self.print(" ", e1.manana.op1_str)
                if e1.manana.op2_str:
                    self.print(" ", e1.manana.op2_str)
            return

        jFin = HM("14:30")
        salida = hoy + jornada - parcial_lapso_hoy
        if (e1 and e1.desfase_str):
            if e1.signo:
                salida = salida - e1.desfase
            else:
                salida = salida + e1.desfase

        if salida == ahora:
            self.print("\n¡SAL AHORA!")
            return
        if salida > ahora and salida >= jFin:
            self.print("\nSal a las", str(salida))
            return

        if today.weekday() >= 4:
            if salida < ahora:
                self.print("\n¡SAL YA! Qué te has pasado")
            else:
                self.print("\nSal a las", str(salida))
            return

        if falta is None:
            return

        if salida < ahora:
            sbr = HM.intervalo(salida, ahora)
            if falta <= sbr:
                return
            manana = falta - sbr
            if manana > jornada:
                manana = jornada - sbr
            self.print("\nSal ahora y mañana haz %s" % (manana))
            if e2 and e2.manana:
                self.print(" ", e2.manana.op1_str)
                if e2.manana.op2_str:
                    self.print(" ", e2.manana.op2_str)
            return

        if salida > ahora and salida < jFin:
            sbr = HM.intervalo(salida, jFin)
            if falta <= sbr:
                self.print("\nSal a las", str(salida))
                return
            manana = falta - HM.intervalo(hoy, jFin)
            if manana > jornada:
                manana = jornada - sbr
            self.print("\nSal a las", str(salida)+", o")
            self.print("sal a las %s y mañana haz %s" % (jFin, manana))
            e3 = self.semana_estadistica(
                jornada, HM.intervalo(hoy, jFin), *laburo)
            if e3 and e3.manana:
                self.print(" ", e3.manana.op1_str)
                if e3.manana.op2_str:
                    self.print(" ", e3.manana.op2_str)

    @property
    def js_lapso(self):
        self.gesper("Permisos/Lapso.aspx")
        for js in self.soup.select("script"):
            js = js.get_text().strip()
            js = js.split("var _permisos = ")
            if len(js) > 1:
                js = js[1]
                js = re.split(r";\s*//", js)[0]
                js = json.loads(js)
                for i, j in enumerate(js):
                    j["txt"] = j["_literalLicencia"].capitalize()
                    j["date"] = datetime.strptime(
                        j["_fechaInicio"], '%d/%m/%Y').date()
                    if j["_dias"] > 1:
                        j["date_fin"] = datetime.strptime(
                            j["_fechaFin"], '%d/%m/%Y').date()
                    else:
                        hi = j.get("_horaInicio")
                        hf = j.get("_horaFin")
                        if hi and hf:
                            j["_horaInicio"] = HM(hi)
                            j["_horaFin"] = HM(hf)
                            j["_duraccion_hm"] = j["_horaFin"] - j["_horaInicio"]
                    for k, v in list(j.items()):
                        if v is None or (isinstance(v, str) and v.strip() == ""):
                            del j[k]
                    js[i] = j
                js = sorted(js, key=lambda x: x["date"])
                return js

    def lapso_dias(self):
        obj = {}
        for i in self.js_lapso:
            ini = i["date"]
            txt = re_sp.sub(" ", i["txt"]).strip()
            dat = Bunch(
                h_ini=None,
                h_fin=None,
                h_dur=None,
                txt=txt,
            )
            obj[ini] = dat
            fin = i.get("date_fin")
            if fin is not None:
                while fin > ini:
                    obj[fin] = dat
                    fin = fin - timedelta(days=1)
            elif i.get("_duraccion_hm"):
                obj[ini] = Bunch(
                    h_ini=i["_horaInicio"],
                    h_fin=i["_horaFin"],
                    h_dur=i["_duraccion_hm"],
                    txt="%s - %s = %s (%s)" % (i["_horaInicio"],
                                                  i["_horaFin"], i["_duraccion_hm"], txt)
                    )
        return obj

    def lapso(self):
        year = None
        for i in self.js_lapso:
            if year is None or year != i["date"].year:
                year = i["date"].year
                self.print("===", year, "===")
            self.print("%s: %s" % (
                parse_dia(i["date"]), i["date"].strftime('%d/%m')), end=" ")
            if i["_dias"] > 1:
                self.print("(+%s)" % i["_dias"], end=" ")
            txt = re_sp.sub(" ", i["txt"]).strip()
            self.print(txt)

    def horas_mes(self):
        lapso = self.lapso_dias()
        self.gesper("ControlHorario/Fichajes.aspx")
        semanas = []
        flag = False
        year, mes = self._find_mes(*self.soup.select("#Tabla td"))
        for fch, id, style, td in self.dias:
            if fch.month == mes:
                if len(semanas) == 0 or fch.weekday() == 0:
                    semanas.append(id)
        total = HM("00:00")
        dias = 0
        premiso = 0
        while semanas:
            id = semanas.pop(0)
            self.submit("#Form1", __EVENTARGUMENT=id,
                        __EVENTTARGET="CalHorario")
            for fch, id, style, td in self.dias:
                if fch.month != mes:
                    continue
                if style == "lightgrey":
                    txt = td.get_text().strip()
                    hms = [HM(hm) for hm in re_hm.findall(txt)]
                    if fch in lapso:
                        self.print("%s %2d: %s" %
                                   (parse_dia(fch), fch.day, lapso[fch].txt))
                        premiso = premiso + 1
                    if len(hms) > 0:
                        ini = hms[0]
                        if len(hms) > 1:
                            fin = hms[-1]
                            itr = HM.intervalo(*hms)
                            total = total + itr
                            dias = dias + 1
                        else:
                            hoy = ini
                            fin = "--:--"
                            itr = "--:--"
                        self.print("%s %2d: %s - %s = %s" %
                                   (parse_dia(fch), fch.day, ini, fin, itr))
        if dias > 1:
            per_day = total.div(dias)
            self.print("\nMedia: %s * %s = %s" % (per_day, dias, total))

    def get_nominas(self, target=None):
        target = target or self.cnf.nominas
        self.gesper("Nomina/Consulta.aspx")
        years = sorted([int(i.get_text().strip())
                        for i in self.soup.select("#ComAño option")])
        nominas = []
        while years:
            year = years.pop()
            y = self.soup.select("#ComAño option[selected]")[0]
            if year != int(y.get_text()):
                self.submit(
                    "#Form1", **{"ComAño": year, "__EVENTTARGET": "ComAño"})
            for tr in reversed(self.soup.select("#DgrNominas tr")):
                a = tr.find("a")
                if not a:
                    continue
                url = a.attrs["href"]
                tds = [td.get_text().strip() for td in tr.findAll("td")]
                rfs = tds[0].split(".")
                bruto = to_num(tds[1])
                neto = to_num(tds[-2])
                mes = rfs[-1].lower()
                rfs = rfs[0]
                mes = parse_mes(mes)
                name = "%s.%02d-%s.pdf" % (year, mes, rfs)
                nom = Bunch(
                    bruto=bruto,
                    neto=neto,
                    url=url,
                    name=name,
                    year=year,
                    mes=mes,
                    index=len(nominas)
                )
                nominas.append(nom)
                if target:
                    absn = os.path.join(target, nom.name)
                    if not os.path.isfile(absn):
                        r = self.s.get(nom.url, verify=self.verify)
                        with open(absn, "wb") as f:
                            f.write(r.content)
        if target:
            add_from_nomina_pdf(nominas, target)
            if nominas:
                m_year, m_mes = max((n.year, n.mes) for n in nominas)
            else:
                m_year, m_mes = -1, -1
            if dwn_funciona_nominas(target, self.cnf, m_year, m_mes):
                add_from_nomina_pdf(nominas, target)

        m_ym = set(n.year+ (n.mes/100) for n in nominas)
        for n in self.cnf.get("_nominas", []):
            for k in ("name", "url", "neto", "bruto"):
                if k not in n:
                    n[k]=None
            n = Bunch(**n)
            ym = n.year + (n.mes/100)
            if ym in m_ym:
                continue
            if not n.name:
                n.name = "%s.%02d-________.___" % (n.year, n.mes)
            n.index = len(nominas)
            nominas.append(n)

        return sorted(nominas, key=lambda n: (n.year, n.mes, -n.index))

    def nominas(self, target=None, enBruto=False, agrupar=None):
        if agrupar is None:
            agrupar = enBruto is False
        target = target or self.cnf.nominas
        if target and not os.path.isdir(target):
            self.print("No existe el directorio", target)
            target = None
        nominas = self.get_nominas(target)
        if agrupar:
            nms={}
            for n in nominas:
                key = (n.year, n.mes)
                if key in nms:
                   x = nms[key]
                   n.neto = n.neto + x.neto
                   n.bruto = n.bruto + x.bruto
                nms[key]=n
            nominas = nms.values()
        for n in nominas:
            n._mes = n.mes
            n.mes = int(n.mes)
        meses = sorted(set((n.year, n.mes) for n in nominas), reverse=True)
        nominas = (n for n in nominas if (n.year, n.mes) in meses and ((n.bruto and enBruto) or (n.neto and not enBruto)))
        nominas = sorted(nominas, key=lambda n: (n.year, n._mes, -n.index))
        for y in sorted(set(n.year for n in nominas)):
            y_nom = list(n for n in nominas if n.year == y)
            y_eur = sum(n.bruto if enBruto else n.neto for n in nominas if n.year == y)
            y_mes = len(set((n.year, n.mes) for n in y_nom))
            euros = to_strint(y_eur / y_mes)
            self.print("{year}: {meses:>2} x {euros:>5}€ = {total:>6}€".format(year=y, euros=euros, meses=y_mes, total=to_strint(y_eur)))

        self.print("")
        for n in nominas:
            euros = to_strint(n.bruto if enBruto else n.neto)
            self.print("{year}-{mes:02d} __ {euros:>5}€".format(euros=euros, **dict(n)))
            if not target and n.url:
                self.print(n.url)
        if len(meses) < 4:
            return

        print_medias = [
            (" año     ", 12),
            (" semestre", 6)
        ]
        ln = len(meses) - 1
        if ln > 12 or (ln > 6 and ln < 12) or ln < 6:
            print_medias.insert(0, (" %s meses" % ln, ln))
            if ln<10:
                print_medias[0][0] = " " + print_medias[0][0]
        sueldo = None
        self.print("")
        self.print("Media último/s:")
        for l, c in print_medias:
            if len(meses) > c:
                cant = 0
                for y, m in meses[:c]:
                    for nom in nominas:
                        if nom.year == y and nom.mes == m:
                            cant = cant + (nom.bruto if enBruto else nom.neto)
                ini = meses[c-1]
                fin = meses[0]
                ini = date(ini[0], ini[1], 1)
                fin = date(fin[0], fin[1], monthrange(*fin)[1])
                per_hour = self.informe_de_horas(ini, fin)
                if per_hour:
                    per_hour = cant / (per_hour.computables.minutos / 60)
                if c == 12 and enBruto:
                    sueldo = Bunch(bruto=cant, hora=per_hour)
                per_hour = to_strint(per_hour)
                cant = to_strint(cant / c)
                if per_hour:
                    self.print("%s: %s€ (%s€/h)" % (l, cant, per_hour))
                else:
                    self.print("%s: %s€" % (l, cant))
        if sueldo:
            self.print("")
            self.print("Sueldo anual: "+to_strint(sueldo.bruto))
            if sueldo.hora:
                cotizar = 6.35
                self.print("Si trabajaras 8h/día con 22 días de vacaciones y cotizando {}%:".format(cotizar))
                self.print("Sueldo anual: "+to_strint((260-22)*8*sueldo.hora*(100+cotizar)/100))


    def nomina(self, nomina, target=None):
        target = target or self.cnf.nominas
        if target and not os.path.isdir(target):
            self.print("No existe el directorio", target)
            return
        nms = sorted(glob(target+"/"+nomina+"*.pdf"))
        if len(nms)==0:
            self.print("Nomina no encontrada:", nomina)
            return
        self.silent=1
        for f in nms:
            p = next(read_pdf(f))
            grp = re.search(r"\bGRUPO\s+(\S+)", p, flags=re.IGNORECASE)
            nlv = re.search(r"\bNIVEL\s+P\.?\s*T\.?\s+(\S+)", p, flags=re.IGNORECASE)
            grp = grp.group(1) if grp else None
            nlv = nlv.group(1) if nlv else None
            imp = re.search(r"2\.?\s+IMPORTES\s+EN\s+NOMINA\s*?\n(.+)3.?\s+FORMA\s+DE\s+PAGO", p, flags=re.IGNORECASE|re.MULTILINE|re.DOTALL)
            imp = textwrap.dedent(imp.group(1)) if imp else None
            if not(grp and nlv and imp):
                continue
            self.print("")
            self.print("===", f.split("/")[-1], "===")
            col = imp.index("TOTAL")+4
            for i in imp.split("\n"):
                while len(i)>col and i[col]!=" ":
                    col = col + 1
            col1 = ""
            col2 = ""
            for i in imp.split("\n"):
                col1 = col1 + i[0:col].rstrip() + "\n"
                col2 = col2 + i[col:].rstrip() + "\n"
            col1 = textwrap.dedent(col1).rstrip()
            col2 = textwrap.dedent(col2).rstrip()
            col1 = re.sub(r"\n\n+", r"\n", col1)
            col2 = re.sub(r"\n+", r"\n", col2)
            col2 = re.sub(r" +DATOS DEL ", r"\nDATOS DEL ", col2)
            col1 = col1.replace(",00", "   ")
            col2 = col2.replace(",00", "   ")
            col1 = re.sub(r"\bCODIGO\b( +)CONCEPTO", r" CD CONCEPTO\1 ", col1)
            for a, b in (
                ("MENSUAL", "  MES  "),
                ("REINTEGROS", " REINTEGRO"),
                ("ATRASOS", " ATRASO"),
                ("i.r.p.f.", "IRPF"),
                ("R.G.S.S. general - CONTINGENCIAS COMUNES", "RGSS (cc)"),
                ("complemento de destino", "c.destino"),
                ("complemento especifico", "c.especifico"),
                ("paga extra sueldo", "extra"),
                ("paga extra c.destino", "extra c.dest."),
                ("paga adicional c.especifico", "extra c.espe."),
            ):
                col1 = col1.replace(a.upper(), b.upper()+(" "*(len(a)-len(b))))
            col1 = re.sub(r" ( +)(\(\d+\))",r" \2\1", col1)
            col1 = textwrap.dedent(col1).rstrip()
            irpf = re.search(r"DATOS\s+DEL\s+I\.?R\.?P\.?F\.?\s*?\n(.+)DATOS\s+DEL\s+", col2, flags=re.IGNORECASE|re.MULTILINE|re.DOTALL)
            irpf = irpf.group(1).strip().split()[-1] if irpf else None
            segs = re.search(r"^\s*091\s+R\.?G\.?S\.?S\.?\s+GENERAL.*?CONTINGENCIAS\s+COMUNES.*?(\d\d/\d+/\d\d)\s+[\d,\.]+\s+([\d,\.]+)", p, flags=re.IGNORECASE|re.MULTILINE)
            self.print("Grupo:", grp)
            self.print("Nivel:", nlv)
            self.print("%IRPF:", irpf)
            if segs:
                self.print("Nº SS:", segs.group(1))
                self.print("  %SS:", segs.group(2))

            lineas=[]
            noblank=set()
            head = None
            for ln in col1.split("\n"):
                lineas.append(ln)
                if ln.startswith("CD"):
                    head = len(lineas)-1
                    ln = ln.replace("ATRASO", "      ")
                    ln = ln.replace("REINTEGRO", "         ")
                elif ln.startswith("  "):
                    ln = "".join(l if l.isdigit() else " " for l in ln)
                else:
                    a, b = ln.split(None, 1)
                    if a.isdigit():
                        ln = ("%2s" % int(a)) + " " +b
                        lineas[len(lineas)-1] = ln
                for i, c in enumerate(ln):
                    if c!=" ":
                        noblank.add(i)
                        noblank.add(i-1)
            for k in ("ATRASO", "REINTEGRO"):
                flag = False
                a = lineas[head].index(k)
                rg = set(range(a, a+len(k)))
                for i in rg:
                    flag = flag or i in noblank
                if flag:
                    noblank = noblank.union(rg)
                    rg = sorted(rg)
                    noblank.add(rg[0]-1)
                    noblank.add(rg[-1]+1)
                else:
                    lineas[head] = lineas[head].replace(k, " "*len(k))

            noblank = sorted(i for i in noblank if i>=0)
            for c, ln in enumerate(lineas):
                ln = "".join(i for c, i in enumerate(ln) if c in noblank)
                lineas[c] = ln

            if tuple(lineas[head].split()) == ("CD", "CONCEPTO", "MES", "TOTAL"):
                for c, ln in enumerate(lineas):
                    w1 = ln.strip().split(None, 1)[0]
                    if w1 == "CD":
                        lineas[c]=""
                    elif w1.isdigit():
                        lineas[c]=re.sub(r" +\S+\s*$", "", ln)

            width = max(len(l) for l in lineas if l.strip() and l.strip().split()[0].isdigit())

            self.print()
            keys=["RETRIBUCIONES", "DEDUCCIONES", "LIQUIDO"]
            for ln in lineas:
                if not ln:
                    continue
                w1 = ln.strip().split(None, 1)[0]
                if w1.isdigit():
                    ln = ln.lower()
                    ln = ln.replace("irpf", "IRPF")
                    ln = ln.replace("rgss", "RGSS")
                elif ln.startswith(" "):
                    n = ln.rsplit(None, 1)[-1]
                    if "," not in n:
                        n = n+"   "
                    ln = keys.pop(0)+" "
                    ln = ln+("."*(width-len(ln)-len(n)-1))+" "+n
                self.print(ln)

    def expediente(self, target=None):
        files = []
        target = target or self.cnf.expediente
        if not os.path.isdir(target):
            self.print("No existe el directorio", target)
            target = None
        self.gesper("Expediente/Consulta.aspx")
        exps = []
        for tr in reversed(self.soup.select("#TablaDocumentos tr")):
            a = [a for a in tr.findAll("a") if a.attrs.get(
                "href").startswith("http")]
            tds = [td.get_text().strip() for td in tr.findAll("td")]
            if len(a) == 0 or len(tds) != 4:
                continue
            a = a[0]
            url = a.attrs["href"]
            tipo, fecha, desc, _ = tds
            desc = desc.capitalize()
            desc = desc.replace("/", " - ")
            desc = desc.replace("\\", " - ")
            dia, mes, year = map(int, fecha.split("-"))
            fecha = date(year, mes, dia)
            name = "{:%Y.%m.%d} - {} - {}.pdf".format(fecha, tipo, desc)
            name = re_sp.sub(" ", name)
            exps.append(Bunch(
                fecha=fecha,
                name=name,
                tipo=tipo,
                desc=desc,
                url=url,
                index=len(exps)
            ))
        exps = sorted(exps, key=lambda x:(x.fecha, x.index))
        mx_tipo = max(len(e.tipo) for e in exps)
        frmt = "{fecha:%-d.%m} {tipo:"+str(mx_tipo)+"} {desc}"
        for inx, e in enumerate(exps):
            if inx == 0 or e.fecha.year != exps[inx-1].fecha.year:
                self.print("===", e.fecha.year, "===")
            line = frmt.format(**dict(e))
            if e.fecha.day<10:
                line = " "+line
            self.print(line)
            if target:
                absn = os.path.join(target, e.name)
                files.append(absn)
                if not os.path.isfile(absn):
                    r = self.s.get(e.url, verify=self.verify)
                    with open(absn, "wb") as f:
                        f.write(r.content)
            else:
                self.print(e.url)
        return files

    def _find_mes(self, *tds):
        for td in tds:
            spl = td.get_text().strip().lower().split()
            if len(spl) == 3 and spl[1] == "de":
                year = spl[-1]
                if year.isdigit():
                    year = int(year)
                    mes = parse_mes(spl[0][:3])
                    return year, mes

    def get_festivos(self, max_iter=-1):
        today = datetime.today()
        self.gesper("CalendarioLaboral.aspx")
        while True:
            if max_iter == 0:
                break
            max_iter = max_iter -1
            table = self.soup.select("#CalFestivos")[0]
            nxt = table.findAll("a")[-1]
            tds = table.findAll("td")
            year, mes = self._find_mes(*tds)
            delta = (year - today.year)
            if delta > 1 or (delta == 1 and mes > 1):
                break
            if year > today.year or (year == today.year and mes >= today.month):
                for td in tds:
                    style = dict_style(td)
                    if style.get("background-color") == "pink" and style.get("font-style") != "italic":
                        br = td.find("br")
                        if br:
                            br.replaceWith(" ")
                            dia, nombre = td.get_text().strip().split(None, 1)
                            dia = int(dia)
                            dt = datetime(year, mes, dia)
                            if dt >= today and dt.weekday() not in (5, 6):
                                nombre = nombre.capitalize()
                                semana = parse_dia(dt)
                                if nombre == "Lunes siguiente a todos los santos":
                                    nombre = "'Todos los santos'"
                                elif nombre == "Lunes siguiente al dia de la comunidad de madrid":
                                    nombre = "Día de la Comunidad de Madrid"
                                elif nombre == "Lunes siguiente al dia de la constitución española":
                                    nombre = "'Día de la Constitucion'"
                                elif nombre == "Nuestra señora de la almudena":
                                    nombre = "La Almudena"
                                elif nombre == "Fiesta nacional de españa":
                                    nombre = "Fiesta nacional"
                                elif nombre == "Fiesta del trabajo":
                                    nombre = "Día del trabajo"
                                elif nombre == "Natividad del señor":
                                    nombre = "Navidad"
                                yield Bunch(
                                    date=dt,
                                    year=dt.year,
                                    semana=semana,
                                    dia=dia,
                                    mes=mes,
                                    nombre=nombre
                                )
            nxt = nxt.attrs["href"].split("'")[-2]
            self.submit("#Form1", __EVENTARGUMENT=nxt, __EVENTTARGET="CalFestivos")

    def festivos(self):
        today = datetime.today()
        cYear = today.year
        for f in self.get_festivos():
            if cYear != f.year:
                self.print("===", f.year, "===")
                cYear = f.year
            self.print("%s %2d.%02d %s" % (f.semana, f.dia, f.mes, f.nombre))

    def get_vacaciones(self, year=None):
        if year is None:
            year = datetime.today().year
        if year < 0:
             year = datetime.today().year + year
        self.gesper("Permisos/Lapso.aspx")
        r = self.s.post(self.root_url+"JSon/Permiso.ashx",
                        data={"accion": "enjoy", "anio": year}, verify=self.verify)
        data = r.json()
        disf = data.get("Disfrute")
        if disf is None or len(disf) != 1:
            js_print(data)
            return
        disf = disf[0]
        total = re_sp.sub(" ", disf["_textoCorresponde"]).strip()
        usados = re_sp.sub(" ", disf["_textoDisfrutados"]).strip()
        total = re_pr.sub("", total)
        usados = re_pr.sub("", usados)
        total = re.sub("<font color='red'>.*</font>", "", total).strip()
        re_vac = re.compile(r"(\d+).*?(permiso|vacaciones)")
        total = {k: int(v) for v, k in re_vac.findall(total)}
        usados = {k: int(v) for v, k in re_vac.findall(usados)}
        keys = set(list(total.keys()) + list(usados.keys()))
        vac = []
        for key in sorted(keys):
            t = total.get(key, 0)
            u = usados.get(key, 0)
            vac.append(Bunch(
                key=key,
                total=t,
                usuados=u,
                year=year
            ))
        return vac

    def print_vacaciones(self, vs, show_year=False):
        if show_year:
            self.print("======== %s ========" % vs[0].year)
        qdn = 0
        s_ln = max(len(v.key) for v in vs)
        for v in vs:
            q = v.total - v.usuados
            qdn = qdn + q
            self.print(v.key.capitalize().ljust(s_ln, '.') +
                       " %2d - %2d = %2d" % (v.total, v.usuados, q))
        self.print(" quedan".rjust(s_ln+8, '.'), "= %2d" % qdn)

    def vacaciones(self):
        vs = self.get_vacaciones(-1)
        qd = sum(v.total - v.usuados for v in (vs or []))
        qd = qd > 0
        if qd:
            self.print_vacaciones(vs, True)
        vs = self.get_vacaciones()
        if vs:
            self.print_vacaciones(vs, qd)

    def get_rpt(self):
        self.silent = True
        files = self.expediente()
        self.silent = False
        for page in read_pdf(*files):
            page = re.sub(r"\s+", " ", page)
            for k in (". DATOS ACTUALES DEL PUESTO DE TRABAJO", ". DATOS DEL PUESTO DE TRABAJO"):
                if k in page:
                    page = page.split(k, 1)[1]
                    for w in re.findall(r" [\|\d]+ ", page):
                        if "|" in w:
                            w = w.replace("|", "").strip()
                            if w.isdigit() and len(w) == 7:
                                return int(w)
        return None

    def get_retribuciones(self, target=None):
        retribucion = []
        self.verify = False
        target = target or self.cnf.retribuciones
        soup = self.get(
            "https://www.sepg.pap.hacienda.gob.es/sitios/sepg/es-ES/CostesPersonal/EstadisticasInformes/Paginas/RetribucionesPersonalFuncionario.aspx")
        for a in soup.select("a[href]"):
            txt = a.get_text().strip()
            if txt.startswith("Retribuciones del personal funcionario."):
                yr = [int(i) for i in txt.split() if i.isdigit()]
                if yr and yr[0] > 2000:
                    url = a.attrs["href"]
                    yr = yr[0]
                    name = "%s.pdf" % yr
                    retribucion.append(Bunch(
                        year=yr,
                        url=url,
                        name=name,
                        file=None,
                        data=None
                    ))
                    if target:
                        absn = os.path.join(target, name)
                        retribucion[-1].file=absn
                        if not os.path.isfile(absn):
                            r = self.s.get(url, verify=self.verify)
                            with open(absn, "wb") as f:
                                f.write(r.content)
        self.verify = True
        if not retribucion:
            return None
        r = sorted(retribucion, key=lambda r:(r.year, r.url)).pop()
        data = None
        try:
            data = retribucion_to_json(r.file)
        except:
            pass
        r.data = (data or {})
        return r

    def puesto(self):
        keys = {
            "Denominación": None,
            "N.R.P.": None,
            "Grupos Adscritos": "Grupo",
            "Nivel": None,
            "Sueldo B.": None,
            "Extra Ju.": None,
            "Extra Di.": None,
            "Complemento Específico": "Compl. E.",
            "Compl. D.": None,
            "Sueldo T.": None,
            "Trienios": None,
            "Teléfono": None,
            "Correo Electrónico": "Correo",
            "Jornada": None,
            "Dirección": None,
            "Planta": None,
            "Despacho": None,
        }
        orden = tuple((v or k) for k, v in keys.items())
        grupo = None
        kv = {}

        mi_grupo = None
        mi_nivel = None
        retri = self.get_retribuciones()
        rpt = self.get_rpt()
        self.gesper("Consulta/Puesto.aspx")
        for clave, valor in tr_clave_valor(self.soup, "TablaFuncionario", **keys):
            if clave == "Denominación":
                if rpt:
                    self.print(rpt, "-", valor)
                else:
                    self.print(valor)
                continue
            if clave == "Grupo":
                valor = valor.upper()
                mi_grupo = valor
            if clave == "Nivel":
                mi_nivel = int(valor)
            kv[clave] = valor

        self.gesper("Consulta/Personales.aspx")
        for clave, valor in tr_clave_valor(self.soup, "TablaPersonales", **keys):
            kv[clave] = valor

        self.gesper("Default.aspx")
        for clave, valor in tr_clave_valor(self.soup, "TablaPersonales", **keys):
            kv[clave] = valor

        self.gesper("Consulta/Profesionales.aspx")
        for clave, valor in tr_clave_valor(self.soup, "TablaFuncionario", "Grupo", Grado="Nivel"):
            if clave == "Grupo":
                mi_grupo = valor
            if clave == "Nivel" and mi_nivel is None:
                mi_nivel = int(valor)
            if clave in ("Grupo", "Nivel"):
                if clave not in kv:
                    kv[clave] = valor
                elif kv[clave] != valor:
                    kv[clave] = kv[clave] + " (%s)" % valor


        if retri and retri.data:
            rg = retri.data.get(mi_grupo)
            rn = retri.data["niveles"].get(mi_nivel)
            if rn:
                kv["Compl. D."] = rn
            if rg:
                kv["Sueldo B."] = rg.get("base", {}).get("sueldo")
                kv["Extra Ju."] = rg.get("junio", {}).get("sueldo")
                kv["Extra Di."] = rg.get("diciembre", {}).get("sueldo")

        trienios = {}
        self.gesper("Consulta/Trienios.aspx")
        for clave, valor in tr_clave_valor(self.soup, "TablaFuncionario"):
            if valor.isdigit() and valor != "0":
                grupo = clave.split()[-1]
                grupo = grupo.upper()
                trienios[grupo] = int(valor)
        if not trienios:
            pass
            #kv.append(("Trienios", "0"))
        elif len(trienios) == 1:
            ((k, v),) = trienios.items()
            kv["Trienios"] = "%s %s" % (v, k)
        else:
            total = sum(v for k, v in trienios.items())
            desglose = ", ".join("%s %s" % (v, k) for k, v in trienios.items())
            kv["Trienios"] = str(total)+" [%s]" % desglose
        euros = ["Compl. D.", "Base", "Compl. E.", "Sueldo B.", "Sueldo T.", "Sueldo", "Extra Ju.", "Extra Di."]
        canti = []
        for e in euros:
            if e in kv:
                v = kv[e]
                v = to_num(v)
                if v is None:
                    del kv[e]
                else:
                    kv[e] = v
                    canti.append(v)
        if len(canti)>4:
            total = sum(canti)
            kv["Sueldo T."] = total
            canti.append(total)
        for e in euros:
            line = max(len(str(round(i))) for i in canti)
            line = "%"+str(line+1)+"s €"
            if e in kv:
                kv[e] = line % to_strint(kv[e])

        max_campo = max(len(i[0]) for i in kv.items())
        line = "%-"+str(max_campo)+"s: %s"
        for i in sorted(kv.items(), key=lambda x: (orden.index(x[0]), x)):
            self.print(line % i)
        if retri:
            self.print(retri.url)

    def servicios(self):
        inicio = None
        self.gesper("/Consulta/Servicios.aspx")
        for td in self.soup.select("td"):
            td = td.get_text().strip()
            if re.match(r"\d\d/\d\d/\d\d\d", td):
                td = datetime.strptime(td, "%d/%m/%Y").date()
                if inicio is None or inicio > td:
                    inicio = td
        if not inicio:
            self.print("No se han encontrado servicios prestados")
            return
        self.print("Desde", inicio.strftime("%d/%m/%Y"), "has hecho:")
        inf = self.informe_de_horas(inicio, None)
        per_day = inf.computables.div(inf.jornadas)
        per_day = str(per_day).replace(":00", "h")
        computa = str(inf.computables).replace(":00", "h")
        self.print(computa, "=", per_day, "*", inf.jornadas, "jornadas")
        dias = inf.computables.minutos / (24*60)
        year = round(dias/36)/10
        igual = (" "*(len(computa)+1)) + "="
        self.print(igual, round(dias), "días o", year, "años")
        fin = date.today() - timedelta(days=1)
        horas = (fin - inicio).days * 24 * 60
        prc = (inf.computables.minutos / horas)*100
        self.print(igual, str(round(prc))+"% de tu tiempo")
        per_day = inf.computables.div((inf.fin-inf.ini).days)
        per_day = str(per_day).replace(":00", "h")
        self.print(igual, per_day, "al día")

    def contactos(self):
        kv={
            "Médico": None,
            "D.U.E.": None,
            "Centralita": None,
            "C.A.U.": {},
        }
        self.intranet("servicios-internos/servicio-medico/")
        for table in self.soup.select("table"):
            cap = table.find("caption").get_text().strip()
            if self.cnf.sede in cap:
                td1 = [i.get_text().strip() for i in table.select("tr > *:nth-of-type(1)")]
                td2 = [i.get_text().strip() for i in table.select("tr > *:nth-of-type(2)")]
                for tds in (td1, td2):
                    if len(tds)>1:
                        v = tds[0]
                        t = [i for i in tds if i.startswith("Tfno:")]
                        if len(t)>0:
                            t = t[0].split()[-1]
                            if v not in kv:
                                v = v.title()
                            if v in kv:
                                kv[v]=t

        fnd_tlf = re.compile(r"(\d[\d ]+\d)")
        self.intranet("servicios-internos/atencion-usuarios/default.aspx")
        for div in self.soup.select("div"):
            if div.select("div"):
                continue
            txt = div.get_text().strip().strip(" .")
            if "Formulario" in txt:
                kv["C.A.U."]["Formulario"] = div.find("a").attrs["href"].split("://", 1)[-1]
            elif "Correo" in txt:
                kv["C.A.U."]["Correo"] = txt.split()[-1]
            elif "Teléfono" in txt:
                tlf = [i.strip().replace(" ", "") for i in fnd_tlf.findall(txt)]
                if tlf:
                    kv["C.A.U."]["Teléfono"] = tlf

        self.intranet("app/Intranet_Form_Web/Web/Directory/DirectorySearch.aspx")
        ctr = self.soup.select_one("#telefonos-centralita")
        if ctr:
            kv["Centralita"] = [i.strip().replace(" ", "") for i in fnd_tlf.findall(ctr.get_text().strip())]

        self.agenda()
        for s in self.soup.select("speedDial"):
            n = s.find("number").get_text().strip()
            l = s.find("label").get_text().strip()
            if len(n)==10 and n.startswith("0"):
                n=n[1:]
            if len(n)==5:
                user = self.get_users(n, searchMethod=1)
                if len(user)==1:
                    user = user[0]
                    if user.telefono and user.telefonoext and user.telefonoext==n:
                        n = user.telefono+", "+user.telefonoext
                    if user.correo:
                        n = n + " ("+user.correo+")"
            kv[l]=n

        print_dict(kv, self.print)

    def menu(self):
        menus = []
        today = datetime.today()
        self.intranet("servicios-internos/cafeteria/menu/default.aspx")
        for div in self.soup.select("div.panel-heading"):
            h3 = div.get_text().strip()
            if self.cnf.sede not in h3:
                continue
            div = div.find_parent("div")
            fecha = div.select("span.fecha-menu")[0]
            fecha = fecha.get_text().strip()
            dt = reversed(tuple(int(i) for i in fecha.split("/")))
            dt = datetime(*dt).date()
            if dt < date.today():
                continue
                #self.print(DAYNAME[dt.weekday()], fecha)
                #self.print("")
            menu = div.select("div.menu")[0]
            precios = [p for p, _ in re.findall(r"(\d+([.,]\d+))\s*€", str(menu))]
            flag = False
            for li in menu.findAll("li"):
                txt = re_sp.sub(" ", li.get_text()).strip().lower()
                if txt.startswith("menú "):
                    (li.find("span") or li).append(" (%s€)" % precios.pop(0))
                    flag = False
                elif txt.startswith("pan, bebida y postre"):
                    flag = True
                if flag:
                    li.extract()
            for li in menu.findAll("li"):
                lis = li.findAll("li")
                if len(lis) == 1:
                    li.replaceWith(lis[0])
            menu = html_to_md(menu, unwrap=('p', 'span'))
            menu = re.sub(r"^[ \t]*\* (Menú .+?)$", r"\n\1\n", menu, flags=re.MULTILINE)
            menu = re.sub(r"^[ \t]+\*\s*", r"* ", menu, flags=re.MULTILINE)
            menu = re.sub(r"^[ \t]+\+\s*", r"  + ", menu, flags=re.MULTILINE)
            menu = re.sub(r"\n\s*\n\s*\n+", r"\n\n", menu)
            menus.append((dt, fecha, menu.strip()))
        if len(menus)==0:
            self.print("Menú no publicado")
            return
        for i, (dt, fecha, menu) in enumerate(menus):
            if i>0:
                self.print("")
            self.print("#", DAYNAME[dt.weekday()], fecha)
            self.print("")
            self.print(menu)

    def novedades(self, desde=None):
        if isinstance(desde, int):
            desde = datetime.now() - timedelta(days=desde)
        if desde is None:
            desde = datetime.now() - timedelta(days=30)

        items = []
        self.intranet("comunicaciones-internas/novedades/default.aspx")
        for li in self.soup.select("ul.listado-novedades li"):
            tt = li.find("h3")
            dt = get_select_text(li, "span.novedad-fecha")
            dt = datetime.strptime(dt, "%d/%m/%Y %H:%M:%S")
            titu = tt.get_text().strip()
            titu = re.sub(r"\s*[\–\-]\s*", " - ", titu)
            titu = re.sub(r"^(MAPA - MITERD|MITERD - MAPA)", "MAPA-MITERD", titu)
            cod = titu.split(" - ", 1)
            if len(cod) > 1 and cod[0] in ("MITECO", "MITERD"):
                continue
            elif cod[0] in ("MAPA", "MAPA-MITERD"):
                titu = cod[1]
            if titu == titu.upper():
                titu = titu.capitalize()
            item = Bunch(
                node=None,
                fecha=dt,
                titulo=titu,
                url=tt.find("a").attrs["href"],
                descripcion=get_select_text(li, "div.novedad-descripcion"),
                tipo="N"
            )
            if item.descripcion:
                item.descripcion = re.sub(
                    r"\s*(Más información|Ver declaración)\s*\.?$", "", item.descripcion)
            items.append(item)

        self.intranet(
            "comunicaciones-internas/tablon-de-anuncios/default.aspx")
        for li in self.soup.select("li.anuncio"):
            dt = get_select_text(li, "span.fechacontenido", extract=True)
            dt = datetime.strptime(dt, "%d/%m/%Y %H:%M:%S")
            for div in li.select("div"):
                if len(div.select("div")) == 0:
                    div.name = "p"
            li.name = "div"
            item = Bunch(
                node=li,
                fecha=dt,
                titulo=get_select_text(li, "h2", extract=True),
                url=None,
                descripcion=None,
                tipo="A"
            )
            items.append(item)

        if not items:
            self.print("No hay novedades")
            return

        items = sorted(items, key=lambda x: (x.fecha, x.titulo))
        flag = False
        last_date = None
        for i in items:
            if i.fecha < desde:
                continue
            if flag:
                self.print("")
            if last_date is None or i.fecha.date() != last_date.date():
                self.print("===", i.fecha.strftime("%d/%m/%Y"), "===")
            self.print("[%s]" % i.tipo, i.titulo)
            if not i.node and i.url and i.tipo == "N":
                self.intranet(i.url)
                d = self.soup.select("div.novedad-descripcion")
                i.node = d[0] if len(d) == 1 else None
            if i.node:
                flag = False
                for n in i.node.select("span.novedad-lista-documentos"):
                    flag = True
                    n.extract()
                urls = set()
                for a in i.node.select("a"):
                    txt = a.get_text().strip().lower()
                    s_txt = txt.split()
                    urls.add(a.attrs["href"])
                    if "ver" in s_txt or "enlace" in txt or re.match(r"^(para )?más información.*", txt):
                        a.string = a.attrs["href"]
                        a.name = "span"
                if len(urls) == 1:
                    if flag:
                        for n in i.node.select(".lista-documentos"):
                            n.extract()
                    for a in i.node.findAll(["span", "a"]):
                        txt = a.get_text().strip()
                        for r, ntxt  in fix_url:
                            txt = r.sub(ntxt, txt)
                        if txt in urls:
                            a.extract()
                    i.url = urls.pop()
                last = None
                while True:
                    last = i.node.select(":scope > *")
                    if len(last)==0:
                        last = None
                        break
                    last = last[-1]
                    if len(last.get_text().strip())==0 and len(last.select(":scope > *"))==0:
                        last.extract()
                        continue
                    break
                if last is not None:
                    if re.match(r"^(para |Puedes consultar )?más información.*", last.get_text().strip(), flags=re.IGNORECASE):
                        last.extract()
                if i.url:
                    a = i.node.find("a", attrs={"href":i.url})
                    if a and len(a.get_text().strip())<3:
                        a.unwrap()
                i.descripcion = html_to_md(
                    i.node, links=True, unwrap=('span', 'strong', "b"))
            if i.url:
                self.print(i.url)
            if i.descripcion:
                i.descripcion = re.sub(r"[ \t]+", " ", i.descripcion)
                i.descripcion = re.sub(r" *\[", " [", i.descripcion)
                i.descripcion = re.sub(r" \* ", r"\n* ", i.descripcion)
                i.descripcion = re.sub(r"\n\s*\n+", r"\n", i.descripcion)
                i.descripcion = re.sub(
                    r"^ *", r"> ", i.descripcion, flags=re.MULTILINE)
                self.print(i.descripcion)
            flag = True
            last_date = i.fecha

    def ofertas(self):
        links = set()
        self.intranet(
            "empleado-publico/ofertas-comerciales-para-los-empleados")
        for a in self.soup.select("ul.fotos-polaroid a[href]"):
            links.add((a.attrs["title"].strip(), a.attrs["href"]))
        for i, (t, l) in enumerate(sorted(links)):
            if i > 0:
                self.print("")
            self.print("===", t, "===")
            self.print(l.replace(":443/", "/"))
            self.print("")
            self.intranet(l)
            for o in self.soup.select("div.oferta-detalle"):
                tt = get_select_text(o, "h3")
                if tt.upper() == tt:
                    tt = tt.capitalize()
                if "." in tt and len(tt.split()) == 1:
                    tt = tt.lower()
                self.print("*", tt)
                url = None # o.select_one("a.ico-website")
                if url:
                    url = url.attrs["href"]
                    url = url.rstrip(".")
                    self.print(" ", url)

    def _informe_de_horas(self, ini, fin):
        self.gesper(
            "/ControlHorario/VerInforme.ashx?action=report&inicio="+ini+"&fin="+fin)
        return self.response.content

    def informe_de_horas(self, ini, fin, target=None):
        target = target or self.cnf.informe_horas
        if target and not os.path.isdir(target):
            return None
        hoy = date.today()
        if fin is None:
            fin = hoy - timedelta(days=1)
        if isinstance(ini, (date, datetime)):
            if ini >= hoy:
                return None
            ini = ini.strftime("%Y-%m-%d")
        if isinstance(fin, (date, datetime)):
            if fin >= hoy:
                return None
            fin = fin.strftime("%Y-%m-%d")
        if ini > fin:
            return None
        name = ini+"_"+fin+".pdf"
        absn = os.path.join(target, name)
        if not os.path.isfile(absn):
            r = self._informe_de_horas(ini, fin)
            with open(absn, "wb") as f:
                f.write(r)
        jornadas = 0
        laborables = 0
        vacaciones = HM("00:00")
        festivos = HM("00:00")
        fiestas_patronales = 0
        for page in read_pdf(absn):
            n_fechas = len(re.findall(r"\b\d\d/\d\d/\d\d\d\d\b", page))
            jornadas = jornadas + n_fechas - 3
            laborables = laborables + n_fechas - 3
            for i in re.findall(r"([\d:\.]+)\s+((?:VAC|FESTIVO|PCI|PAP|FP)\b\S*)", page):
                h = HM(i[0])
                t = tuple(a.strip() for a in i[1].strip().lower().split(","))
                if "festivo" in t:
                    jornadas = jornadas - 1
                    laborables = laborables - 1
                    festivos = festivos + h
                elif "vac" in t or "pap" in t:
                    jornadas = jornadas - 1
                    vacaciones = vacaciones + h
                elif "fp" in t:
                    fiestas_patronales = fiestas_patronales + 1
        m = re.search(
            r"^\s*(-?[\d:\.]+)\s+(-?[\d:\.]+)\s+(-?[\d:\.]+)\s+(-?[\d:\.]+)\s+(-?[\d:\.]+)\s+(-?[\d,\.]+)\s*$", page, re.MULTILINE)
        if m is None:
            return
        porcentaje = to_num(m.groups()[-1])
        trabajadas, incidencias, total, teoricas, saldo = (
            HM(i) for i in m.groups()[:-1])
        return IH(
            laborables=laborables,
            jornadas=jornadas,
            trabajadas=trabajadas,
            incidencias=incidencias,
            total=total,
            teoricas=teoricas,
            saldo=saldo,
            porcentaje=porcentaje,
            festivos=festivos,
            vacaciones=vacaciones,
            fiestas_patronales=HM("02:30").mul(fiestas_patronales),
            pdf=absn,
            ini=datetime.strptime(ini, "%Y-%m-%d").date(),
            fin=datetime.strptime(fin, "%Y-%m-%d").date()
        )


    def get_users(self, *args, searchMethod=None):
        if len(args)==0:
            return []
        args = "+".join(args)
        if "@" in args:
            mail = args.lower()
            apel = mail.split("@")[0][1:]
            users = []
            for u in self.get_users(apel, searchMethod=3):
                if u.correo and u.correo.lower() == mail:
                    users.append(u)
            return users
        if searchMethod is None:
            if args.isdigit():
                searchMethod=(1,)
            else:
                searchMethod=(3, 4)
        elif isinstance(searchMethod, int):
            searchMethod = (searchMethod, )
        self.intranet("app/Intranet_Form_Web/Web/Directory/DirectorySearch.aspx")
        nodos=[]
        users=set()
        keys=set()
        url = "app/Intranet_Form_Web/Web/Directory/DirectoryWebService.asmx/ResultadoBusquedaList?count=1&contextKey=3&prefixText="+args
        for sm in searchMethod:
            self.intranet(url+"&searchMethod="+str(sm))
            #print (self.response.url)
            keys = keys.union(k.name.lower() for k in self.soup.select("UserDirectoryInfo > *") if k.name.lower()!="id")
            nodos.extend(self.soup.select("UserDirectoryInfo"))
        keys = sorted(keys)
        for n in nodos:
            u = {k: None for k in keys}
            for i in n.select(":scope > *"):
                k = i.name.lower()
                if k == "id":
                    continue
                u[k]=i.get_text().strip()
            u = frozenset(u.items())
            users.add(u)
        users = sorted((User(**{k:v for k,v in u}) for u in users), key=lambda u: (u.nombre, u.apellido1, u.apellido2))
        if len(users)==1 and self.bot and not self.silent:
            pass
        return users

    def busca(self, *args):
        users = self.get_users(*args)
        if len(users)==0:
            self.print("No encontrado")
            return None

        self.silent = 1
        cenun = tuple((u.centro or u.unidad) for u in users)
        if len(users)<3 or len(set(cenun))>(len(cenun)-3):
            for u in users:
                self.print("")
                u.print(self.print)
            return users

        empt = []
        nocu = []
        ocou = []
        resto =[]
        for u in users:
            if u.isEmpty():
                empt.append(u)
            elif not u.centro and not u.unidad:
                nocu.append(u)
            else:
                resto.append(u)

        cenun = sorted(set((u.centro or u.unidad) for u in resto))
        for ctun in cenun:
            self.print("")
            _resto = [u for u in resto if (u.centro or u.unidad)==ctun]
            unidad = set((u.unidad for u in _resto))
            if len(unidad)==1:
                self.print("## "+ctun, unidad.pop(), sep=" > ", avoidEmpty=True)
                unidad = False
            else:
                self.print("## "+ctun)
                unidad = True
            for i, u in enumerate(_resto):
                self.print("")
                self.print(u.nombre, u.apellido1, u.apellido2, avoidEmpty=True)
                if unidad and ctun!=u.unidad:
                    self.print(u.unidad, avoidEmpty=True)
                self.print(u.puesto, avoidEmpty=True)
                self.print(u.despacho, u.planta, u.ubicacion, sep=" - ", avoidEmpty=True)
                self.print(u.telefono, u.telefonoext, u.correo, sep=" - ", avoidEmpty=True)

        if nocu:
            self.print("")
            self.print("<<sin centro ni unidad>>")
        for u in nocu:
            self.print("")
            u.print(self.print)

        if empt:
            self.print("")
            self.print("Otros:")
        for u in empt:
            self.print("*", end=" ")
            self.print(u.nombre, u.apellido1, u.apellido2, avoidEmpty=True)

        return users
