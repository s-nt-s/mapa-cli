from datetime import datetime, date, timedelta
from .filemanager import CNF, FileManager
import re
from munch import Munch
from .web import Web
from .util import json_serial, parse_mes, parse_dia, get_text, tmap, to_num, get_times
from os.path import isdir, join, isfile, expanduser
from .hm import HM, IH, IHCache
import json
from .retribuciones import Retribuciones
from functools import lru_cache

re_sp = re.compile(r"\s+")
re_pr = re.compile(r"\([^\(\)]+\)")

fix_url = (
    (re.compile(r"^(https?://[^/]*\.?)mapama\.es"), r"\1mapa.es"),
    (re.compile(r"^(https?://[^/]+):443/"), r"\1/"),
    (re.compile(r"/default\.aspx"), ""),
)


def _find_mes(*tds):
    for td in tds:
        spl = td.get_text().strip().lower().split()
        if len(spl) == 3 and spl[1] == "de":
            year = spl[-1]
            if year.isdigit():
                year = int(year)
                mes = parse_mes(spl[0][:3])
                return year, mes


def dict_style(n):
    style = [s.split(":")
             for s in n.attrs["style"].lower().split(";") if s]
    style = {k: v for k, v in style}
    return style


def tr_clave_valor(soup, id, *args, **keys):
    ok_key = tuple(args) + tuple(keys.keys())
    for tr in soup.select("#" + id + " tr"):
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
        if valor == valor.upper() and clave not in ("N.R.P.",):
            valor = valor.capitalize()
        if clave == "Dirección":
            valor = valor.split(", madrid")[0]
            valor = valor.title()
            valor = valor.replace(" De ", " de ")
            valor = valor.replace(" La ", " la ")
        yield clave, valor


class Gesper(Web):
    def __init__(self, *args, **kargv):
        super().__init__(*args, **kargv)
        for url in ("https://intranet.mapa.es/", "https://intranet.mapa.es/app/gesper/",
                    "https://intranet.mapa.es/app/gesper/Default.aspx"):
            self.get(url)
        self.submit("#Form1", TxtDNI=CNF.gesper.user, TxtClave=CNF.gesper.pssw)

    def get_festivos(self, max_iter=-1):
        r = []
        today = datetime.today()
        self.get("https://intranet.mapa.es/app/GESPER/CalendarioLaboral.aspx")
        while True:
            if max_iter == 0:
                break
            max_iter = max_iter - 1
            table = self.soup.select("#CalFestivos")[0]
            nxt = table.findAll("a")[-1]
            tds = table.findAll("td")
            year, mes = _find_mes(*tds)
            delta = (year - today.year)
            if delta > 1 or (delta == 1 and mes > 1):
                break
            if year > today.year or (year == today.year and mes >= today.month):
                for td in tds:
                    style = dict_style(td)
                    if not (style.get("background-color") == "pink" and style.get("font-style") != "italic"):
                        continue
                    br = td.find("br")
                    if br is None:
                        continue
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
                        r.append(Munch(
                            date=dt,
                            year=dt.year,
                            semana=semana,
                            dia=dia,
                            mes=mes,
                            nombre=nombre
                        ))
            nxt = nxt.attrs["href"].split("'")[-2]
            self.submit("#Form1", __EVENTARGUMENT=nxt, __EVENTTARGET="CalFestivos")
        return r

    def get_expediente(self):
        self.get("https://intranet.mapa.es/app/GESPER/Expediente/Consulta.aspx")
        exps = []
        for tr in reversed(self.soup.select("#TablaDocumentos tr")):
            a = [a for a in tr.select("a[href]") if a.attrs["href"].startswith("http")]
            tds = tmap(get_text, tr.findAll("td"))
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
            exp = Munch(
                fecha=fecha,
                name=name,
                tipo=tipo,
                desc=desc,
                url=url,
                file=None,
                index=len(exps)
            )
            exps.append(exp)
            if isdir(expanduser(CNF.expediente)):
                exp.file = join(CNF.expediente, exp.name)
                if not isfile(exp.file):
                    r = self.s.get(exp.url, verify=self.verify)
                    FileManager.get().dump(exp.file, r.content)

        exps = sorted(exps, key=lambda x: (x.fecha, x.index))
        return exps

    def get_vacaciones(self, year=None):
        vac = []
        cyr = datetime.today().year
        if year is None:
            for v in self.get_vacaciones(-1):
                if v.total > v.usados:
                    vac.append(v)
            year = cyr
        if year < 0:
            year = cyr + year
        self.get("https://intranet.mapa.es/app/GESPER/Permisos/Lapso.aspx")
        r = self.s.post("https://intranet.mapa.es/app/GESPER/JSon/Permiso.ashx",
                        data={"accion": "enjoy", "anio": year}, verify=self.verify)
        data = r.json()
        disf = data.get("Disfrute")
        if disf is None or len(disf) != 1:
            return []
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
        for key in sorted(keys):
            t = total.get(key, 0)
            u = usados.get(key, 0)
            vac.append(Munch(
                key=key,
                total=t,
                usados=u,
                year=year
            ))
        return vac

    def get_lapso(self):
        self.get("https://intranet.mapa.es/app/GESPER/Permisos/Lapso.aspx")
        var_permisos = 'var _permisos = '
        for js in map(get_text, self.soup.select("script")):
            if js is None or var_permisos not in js:
                continue
            js = js.split(var_permisos)[1]
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

    def get_puesto(self):
        keys = {
            "Denominación": "denominacion",
            "N.R.P.": "nrp",
            "Grupos Adscritos": "grupo",
            "Nivel": "nivel",
            "Sueldo B.": "sueldo.base",
            "Extra Ju.": "sueldo.extra.junio",
            "Extra Di.": "sueldo.extra.diciembre",
            "Complemento Específico": "sueldo.complemento.especifico",
            "Compl. D.": "sueldo.complement.destino",
            "Trienios": "sueldo.trienios",
            "Correo Electrónico": "contacto.correo",
            "Jornada": "jornada",
            "Teléfono": "contacto.telefono",
            "Dirección": "contacto.direccion",
            "Planta": "contacto.planta",
            "Despacho": "contacto.despacho",
        }

        kv = {}
        mi_grupo = None
        mi_nivel = None

        self.get("https://intranet.mapa.es/app/GESPER/Consulta/Puesto.aspx")
        for clave, valor in tr_clave_valor(self.soup, "TablaFuncionario", **keys):
            if clave == "grupo":
                valor = valor.upper()
                mi_grupo = valor
            if clave == "nivel":
                mi_nivel = int(valor)
            kv[clave] = valor

        self.get("https://intranet.mapa.es/app/GESPER/Consulta/Personales.aspx")
        for clave, valor in tr_clave_valor(self.soup, "TablaPersonales", **keys):
            kv[clave] = valor

        self.get("https://intranet.mapa.es/app/GESPER/Default.aspx")
        for clave, valor in tr_clave_valor(self.soup, "TablaPersonales", **keys):
            kv[clave] = valor

        self.get("https://intranet.mapa.es/app/GESPER/Consulta/Profesionales.aspx")
        for clave, valor in tr_clave_valor(self.soup, "TablaFuncionario", Grupo="grupo", Grado="nivel"):
            if clave not in ("grupo", "nivel"):
                continue
            if clave == "grupo":
                mi_grupo = valor
            if clave == "nivel" and mi_nivel is None:
                mi_nivel = int(valor)
            if clave not in kv:
                kv[clave] = valor
            elif kv[clave] != valor:
                kv[clave] = kv[clave] + " (%s)" % valor

        self.get("https://intranet.mapa.es/app/GESPER/Consulta/Trienios.aspx")
        for clave, valor in tr_clave_valor(self.soup, "TablaFuncionario"):
            if valor.isdigit() and valor != "0":
                valor = int(valor)
                grupo = clave.split()[-1]
                grupo = grupo.upper()
                kv["trienios." + grupo] = valor

        for k, v in list(kv.items()):
            if not (k.startswith("sueldo.") and isinstance(v, (str, float))):
                continue
            v = to_num(v)
            if v is None:
                del kv[k]
            else:
                kv[k] = v

        # kv = dict(sorted(kv.items(), key=lambda x: orden.index(x[0])))

        inicio = None
        self.get("https://intranet.mapa.es/app/GESPER/Consulta/Servicios.aspx")
        for td in self.soup.select("td"):
            td = td.get_text().strip()
            if re.match(r"\d\d/\d\d/\d\d\d", td):
                td = datetime.strptime(td, "%d/%m/%Y").date()
                if inicio is None or inicio > td:
                    inicio = td
        if inicio:
            kv["inicio"] = inicio

        for k, v in sorted(kv.items()):
            path = k.split(".")
            if len(path) == 1:
                continue
            obj = kv
            for w in path[:-1]:
                if w not in obj:
                    obj[w] = Munch()
                obj = obj[w]
            obj[path[-1]] = v
            del kv[k]

        kv = Munch.fromDict(kv)
        rt = Retribuciones().get_sueldo(mi_grupo, mi_nivel, kv.sueldo.complemento.especifico, kv.trienios)
        if rt:
            kv.sueldo = rt

        return kv

    @property
    @lru_cache(maxsize=None)
    def fecha_inicio(self):
        return self.get_puesto()['inicio']

    @IHCache(file="data/gesper/informe_{:%Y-%m-%d}_{:%Y-%m-%d}.json", json_default=json_serial)
    def _get_informe(self, ini, fin):
        _fin = date(fin.year, fin.month, fin.day)
        rst = []
        while ini <= _fin:
            fin = date(ini.year, 12, 31)
            if fin > _fin:
                fin = date(_fin.year, _fin.month, _fin.day)
            s_ini = ini.strftime("%Y-%m-%d")
            s_fin = fin.strftime("%Y-%m-%d")
            name = s_ini + "_" + s_fin + ".pdf"
            absn = join(CNF.informe_horas, name)
            if not isfile(absn):
                r = self.s.get(
                    "https://intranet.mapa.es/app/GESPER/ControlHorario/VerInforme.ashx?action=report&inicio=" + s_ini + "&fin=" + s_fin)
                FileManager.get().dump(absn, r.content)
            jornadas = 0
            laborables = 0
            vacaciones = HM("00:00")
            festivos = HM("00:00")
            fiestas_patronales = 0
            for page in FileManager.get().load(absn, as_list=True):
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
                r"^\s*(-?[\d:\.]+)\s+(-?[\d:\.]+)\s+(-?[\d:\.]+)\s+(-?[\d:\.]+)\s+(-?[\d:\.]+)\s+(-?[\d,\.]+)\s*$",
                page, re.MULTILINE)

            if m is None:
                continue
            porcentaje = to_num(m.groups()[-1])
            trabajadas, incidencias, total, teoricas, saldo = (HM(i) for i in m.groups()[:-1])
            rst.append(IH(
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
                ini=ini,
                fin=fin
            ))
            ini = ini.replace(year=ini.year + 1, month=1, day=1)
        if len(rst) == 0:
            return None
        r = rst[0]
        del r['porcentaje']
        del r['pdf']
        r.fin = rst[-1].fin
        for i in rst[1:]:
            for k in ('laborables', 'jornadas', 'trabajadas', 'incidencias', 'total', 'teoricas', 'saldo', 'festivos',
                      'vacaciones', 'fiestas_patronales'):
                r[k] = r[k] + i[k]
        return r

    def get_informe(self, ini=None, fin=date(2022, 5, 29)):#fin=date(2022, 6, 5)):
        hoy = date.today()
        if ini is None:
            ini = self.fecha_inicio
        if ini >= hoy:
            return None
        if fin >= hoy:
            fin = hoy - timedelta(days=1)
        if ini > fin:
            return None
        return self._get_informe(ini, fin)

if __name__ == "__main__":
    f = Gesper()
    r = f.get_vacaciones()
    print(json.dumps(r, indent=2, default=json_serial))
