from datetime import datetime, date, timedelta
from .filemanager import CNF, FileManager
import re
from munch import Munch
from .web import Web
from .util import json_serial, parse_mes, parse_dia, ttext, to_num, json_hook, dict_style
from os.path import isdir, join, isfile, expanduser
from .hm import HM, GesperIH, GesperIHCache
import json
from .retribuciones import Retribuciones
from functools import cached_property
import logging
from .cache import TupleCache
import bs4
from typing import Union, Dict, List, Any
from .types.festivo import Festivo
from .types.expediente import Expediente
from .types.vacaciones import Vacaciones


re_sp = re.compile(r"\s+")
re_pr = re.compile(r"\([^\(\)]+\)")

fix_url = (
    (re.compile(r"^(https?://[^/]*\.?)mapama\.es"), r"\1mapa.es"),
    (re.compile(r"^(https?://[^/]+):443/"), r"\1/"),
    (re.compile(r"/default\.aspx"), ""),
)
FCH_FIN = date(2022, 5, 29)

logger = logging.getLogger(__name__)


def _find_mes(*tds: bs4.Tag):
    for td in tds:
        spl = td.get_text().strip().lower().split()
        if len(spl) == 3 and spl[1] == "de":
            year = spl[-1]
            if year.isdigit():
                year = int(year)
                mes = parse_mes(spl[0][:3])
                return year, mes


def tr_clave_valor(soup: bs4.Tag, id: str, *args, **keys):
    ok_key = tuple(args) + tuple(keys.keys())
    for tr in soup.select("#" + id + " tr"):
        tds = ttext(tr.findAll("td"))
        if len(tds) < 2:
            continue
        clave, valor = tds
        if None in (clave, valor):
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


def parse_festivo(nombre: str):
    nombre = nombre.capitalize()
    if nombre == "Lunes siguiente a todos los santos":
        return "Todos los santos"
    if nombre == "Lunes siguiente al dia de la comunidad de madrid":
        return "Día de la Comunidad de Madrid"
    if nombre in ("Lunes siguiente al dia de la constitución española", "Fiesta nacional constitucion"):
        return "Día de la Constitución"
    if nombre in ("Nuestra señora de la almudena", 'Fiesta almudena'):
        return "La Almudena"
    if nombre == "Fiesta nacional de españa":
        return "Fiesta nacional"
    if nombre == "Fiesta del trabajo":
        return "Día del trabajo"
    if nombre == "Natividad del señor":
        return "Navidad"
    if nombre in ('Fiesta nacional inmaculada', ):
        return "La Inmaculada"
    if nombre.startswith("Fiesta nacional "):
        nombre = nombre[16:].capitalize()
    return nombre


class Gesper(Web):

    def __init__(self, *args, **kargv):
        super().__init__(*args, **kargv)
        for url in ("https://intranet.mapa.es/", "https://intranet.mapa.es/app/gesper/",
                    "https://intranet.mapa.es/app/gesper/Default.aspx"):
            self.get(url)
        self.submit("#Form1", TxtDNI=CNF.gesper.user, TxtClave=CNF.gesper.pssw)

    def get_expediente(self):
        def _find_a(tr: bs4.Tag):
            for a in tr.select("a[href]"):
                if a.attrs["href"].startswith("http"):
                    return a

        self.get("https://intranet.mapa.es/app/GESPER/Expediente/Consulta.aspx")
        exps: List[Expediente] = []
        for tr in reversed(self.soup.select("#TablaDocumentos tr")):
            a = _find_a(tr)
            tds = ttext(tr.findAll("td"))
            if a is None or len(tds) != 4:
                continue
            url: str = a.attrs["href"]
            tipo: str = tds[0]
            fecha: str = tds[1]
            desc: str = tds[2]
            desc = desc.capitalize()
            desc = desc.replace("/", " - ")
            desc = desc.replace("\\", " - ")
            dia, mes, year = map(int, fecha.split("-"))
            fecha = date(year, mes, dia)
            name = "{:%Y.%m.%d} - {} - {}.pdf".format(fecha, tipo, desc)
            name = re_sp.sub(" ", name)
            exp = Expediente(
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
        return tuple(exps)

    def get_vacaciones(self, year: Union[int, None] = None):
        vac: List[Vacaciones] = []
        cyr = datetime.today().year
        if year is None:
            for v in self.get_vacaciones(-1):
                if v.total > v.usados:
                    vac.append(v)
            year = cyr
        if year < 0:
            year = cyr + year
        self.get("https://intranet.mapa.es/app/GESPER/Permisos/Lapso.aspx")
        r = self.s.post(
            "https://intranet.mapa.es/app/GESPER/JSon/Permiso.ashx",
            data={"accion": "enjoy", "anio": year},
            verify=self.verify
        )
        data: Dict = r.json()
        disf = data.get("Disfrute")
        if not isinstance(disf, list) or len(disf) != 1:
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
            vac.append(Vacaciones(
                key=key,
                total=t,
                usados=u,
                year=year
            ))
        return tuple(vac)

    @TupleCache(
        "data/gesper/lapso.json",
        maxOld=None,
        json_default=json_serial,
        json_hook=json_hook,
        builder=lambda x: x,
    )
    def get_lapso(self):
        self.get("https://intranet.mapa.es/app/GESPER/Permisos/Lapso.aspx")
        var_permisos = 'var _permisos = '
        for txt in ttext(self.soup.select("script")):
            if txt is None or var_permisos not in txt:
                continue
            txt = txt.split(var_permisos)[1]
            txt = re.split(r";\s*//", txt)[0]
            js: List[Dict] = json.loads(txt)
            for i, j in enumerate(js):
                if j.get("_anio"):
                    j["_anio"] = int(j["_anio"])
                _literalLicencia: str = j["_literalLicencia"]
                j["txt"] = _literalLicencia.capitalize()
                j["date"] = datetime.strptime(
                    j["_fechaInicio"], '%d/%m/%Y').date()
                if j["_dias"] > 1:
                    j["date_fin"] = datetime.strptime(
                        j["_fechaFin"], '%d/%m/%Y').date()
                else:
                    hi: str = j.get("_horaInicio")
                    hf: str = j.get("_horaFin")
                    if hi and hf:
                        j["_horaInicio"] = HM(hi)
                        j["_horaFin"] = HM(hf)
                        j["_duraccion_hm"] = j["_horaFin"] - j["_horaInicio"]
                for k, v in list(j.items()):
                    if v is None or (isinstance(v, str) and v.strip() == ""):
                        del j[k]
                js[i] = j
            js = sorted(js, key=lambda x: x["date"])
            return tuple(js)

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

        kv: Dict[str, Any] = {}
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

    @cached_property
    def fecha_inicio(self):
        return self.get_puesto()['inicio']

    @GesperIHCache(file="data/gesper/informe_{:%Y-%m-%d}_{:%Y-%m-%d}.json", json_default=json_serial, maxOld=None)
    def _get_informe(self, ini: date, fin: date):
        logger.debug("Gesper._get_informe(%s, %s)", ini, fin)
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
            if not isfile(expanduser(absn)):
                i_url = "https://intranet.mapa.es/app/GESPER/ControlHorario/VerInforme.ashx?action=report&inicio=" + s_ini + "&fin=" + s_fin
                r = self.s.get(i_url)
                FileManager.get().dump(absn, r.content)
            jornadas = 0
            laborables = 0
            vacaciones = HM("00:00")
            festivos = HM("00:00")
            fiestas_patronales = 0
            for page in FileManager.get().load(absn, as_list=True, physical=True):
                n_fechas = len(re.findall(r"\b\d\d/\d\d/\d\d\d\d\b", page))
                jornadas = jornadas + n_fechas - 3
                laborables = laborables + n_fechas - 3
                i: str
                for i in re.findall(r"([\d:\.]+)\s+((?:VAC|FESTIVO|PCI|PAP|FP|VFP|L2|BAJA)\b\S*)", page):
                    h = HM(i[0])
                    t = tuple(a.strip() for a in i[1].strip().lower().split(","))
                    if "festivo" in t:
                        jornadas = jornadas - 1
                        laborables = laborables - 1
                        festivos = festivos + h
                    elif "vac" in t or "pap" in t or "vfp" in t:
                        jornadas = jornadas - 1
                        vacaciones = vacaciones + h
                    elif "fp" in t:
                        fiestas_patronales = fiestas_patronales + 1
            page = re.sub("Página\s*\d+\s*de\s*\d+", "", page)

            m = re.search(
                r"^\s*(-?[\d:\.,]+)\s+(-?[\d:\.,]+)\s+(-?[\d:\.,]+)\s+(-?[\d:\.,]+)\s+(-?[\d:\.,]+)\s+(-?[\d,\.,]+)\s*$",
                page, re.MULTILINE)

            if m is not None and len(m.groups()) == 6:
                # Fix: Error en el informe 2021 y 2022
                if ini <= date(2022, 5, 17) and fin >= date(2022, 5, 20):
                    fiestas_patronales = 4
                if ini <= date(2021, 5, 10) and fin >= date(2021, 5, 14):
                    fiestas_patronales = 5
                try:
                    porcentaje = to_num(m.groups()[-1])
                    trabajadas, incidencias, total, teoricas, saldo = (HM(i) for i in m.groups()[:-1])
                except ValueError:
                    break
                rst.append(GesperIH(
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

    def get_informe(self, ini: Union[date, None] = None, fin: date = FCH_FIN):  # fin=date(2022, 6, 5)):
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
    r = f.get_informe()
    print(json.dumps(r, indent=2, default=json_serial))
