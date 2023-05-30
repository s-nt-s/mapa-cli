from datetime import datetime, date, timedelta
from .filemanager import CNF
import re
from .util import html_to_md, mk_re
from munch import Munch
from .web import Web
from .util import json_serial, tmap, parse_mes, parse_dia, get_text
from requests.auth import HTTPBasicAuth
from .user import User

re_sp = re.compile(r"\s+")

fix_url = (
    (re.compile(r"^(https?://[^/]*\.?)mapama\.es"), r"\1mapa.es"),
    (re.compile(r"^(https?://[^/]+):443/"), r"\1/"),
    (re.compile(r"/default\.aspx"), ""),
)

re_txt = {
    mk_re(k):v for k, v in {
        "Instituto Nacional de Administraciones Públicas": "INAP",
        "Administración General del Estado": "AGE",
        "Ministerio de Agricultura, Pesca y Alimentación": "MAPA",
        "Organización de las Naciones Unidas": "ONU",
        "Administraciones Públicas": "AAPP"
    }.items()
}

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

class Mapa(Web):
    def get_menu(self):
        """
        Obtiene el menú de la sede definida en config.yml
        """
        menus = []
        self.get("https://intranet.mapa.es/servicios-internos/cafeteria/menu/default.aspx")
        for div in self.soup.select("div.panel-heading"):
            h3 = div.get_text().strip()
            if CNF.sede not in h3:
                continue
            div = div.find_parent("div")
            fecha = div.select_one("span.fecha-menu")
            fecha = get_text(fecha)
            if fecha:
                fecha = reversed(tuple(int(i) for i in fecha.split()[-1].split("/")))
                fecha = date(*fecha)
            elif len(menus)>0 and menus[-1].fecha is not None:
                fecha = menus[-1].fecha + timedelta(days=1)
            # if dt < date.today():
            #    continue
            menu = div.select_one("div.menu")
            precios = [p for p, _ in re.findall(r"(\d+([.,]\d+))\s*€", str(menu))]
            flag = False
            for li in menu.findAll("li"):
                txt = get_text(li)
                if txt is None:
                    continue
                txt = txt.lower()
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
            menus.append(Munch(
                fecha=fecha,
                menu=menu.strip()
            ))
        return menus

    def get_novedades(self):
        items = []
        self.get("https://intranet.mapa.es/comunicaciones-internas/novedades/default.aspx")
        for li in self.soup.select("ul.listado-novedades li"):
            tt = li.find("h3")
            dt = get_text(li.select_one("span.novedad-fecha"))
            dt = datetime.strptime(dt, "%d/%m/%Y %H:%M:%S")
            titu = tt.get_text().strip()
            titu = re.sub(r"\s*[\–\-]\s*", " - ", titu)
            titu = re.sub(r"^(MAPA - MITERD|MITERD - MAPA)", "MAPA-MITERD", titu)
            titu = re.sub(r"^(MAPA - MITECO|MITECO - MAPA)", "MAPA-MITECO", titu)
            cod = titu.split(" - ", 1)
            if len(cod) > 1 and cod[0] in ("MITECO", "MITERD"):
                continue
            elif cod[0] in ("MAPA", "MAPA-MITERD", 'MAPA-MITECO'):
                titu = cod[1]
            if titu == titu.upper():
                titu = titu.capitalize()
            item = Munch(
                node=None,
                fecha=dt,
                titulo=titu,
                url=tt.find("a").attrs["href"],
                descripcion=get_text(li.select_one("div.novedad-descripcion")),
                tipo="N"
            )
            if item.descripcion:
                item.descripcion = re.sub(
                    r"\s*(Más información|Ver declaración)\s*\.?$", "", item.descripcion)
            items.append(item)

        self.get("https://intranet.mapa.es/comunicaciones-internas/tablon-de-anuncios/default.aspx")
        for li in self.soup.select("li.anuncio"):
            dt = li.select_one("span.fechacontenido")
            dt.extract()
            dt = get_text(dt)
            dt = datetime.strptime(dt, "%d/%m/%Y %H:%M:%S")
            for div in li.select("div"):
                if len(div.select("div")) == 0:
                    div.name = "p"
            li.name = "div"
            h2 = li.select_one("h2")
            h2.extract()

            item = Munch(
                node=li,
                fecha=dt,
                titulo=get_text(h2),
                url=None,
                descripcion=None,
                tipo="A"
            )
            items.append(item)

        for item in items:
            if item.node is None and item.url and item.tipo == "N":
                self.get(item.url)
                item.node = self.soup.select_one("div.novedad-descripcion")
            for r_txt, txt in re_txt.items():
                if item.titulo:
                    item.titulo = r_txt.sub(txt, item.titulo)

        for item in items:
            if item.node is None:
                continue
            flag = False
            for n in item.node.select("span.novedad-lista-documentos"):
                flag = True
                n.extract()
            urls = set()
            for a in item.node.select("a"):
                txt = a.get_text().strip().lower()
                s_txt = txt.split()
                urls.add(a.attrs["href"])
                if "ver" in s_txt or "enlace" in txt or re.match(r"^(para )?más información.*", txt):
                    a.string = a.attrs["href"]
                    a.name = "span"
            if len(urls) == 1:
                if flag:
                    for n in item.node.select(".lista-documentos"):
                        n.extract()
                for a in item.node.findAll(["span", "a"]):
                    txt = a.get_text().strip()
                    for r, ntxt in fix_url:
                        txt = r.sub(ntxt, txt)
                    if txt in urls:
                        a.extract()
                item.url = urls.pop()
            while True:
                last = item.node.select(":scope > *")
                if len(last) == 0:
                    last = None
                    break
                last = last[-1]
                if get_text(last) is None and len(last.select(":scope > *")) == 0:
                    last.extract()
                    continue
                break
            if last is not None:
                txt = get_text(last)
                if txt is None or re.match(r"^(para |Puedes consultar )?más información.*", txt,
                                           flags=re.IGNORECASE):
                    last.extract()
            if item.url:
                a = item.node.find("a", attrs={"href": item.url})
                if a and len(a.get_text().strip()) < 3:
                    a.unwrap()
            for n in item.node.findAll(["p", "div"]):
                if len(n.get_text().strip()) > 0:
                    continue
                chls = [i for i in n.select(":scope *") if i.name not in ("br", )]
                if len(chls) == 0:
                    n.extract()

            for n in item.node.findAll(text=r_txt):
                n.replace_with(r_txt.sub(txt, n.string))

            item.html = str(item.node)
            item.descripcion = html_to_md(item.node, links=True, unwrap=('span', 'strong', "b"))
            item.descripcion = re.sub(r"[ \t]+", " ", item.descripcion)
            item.descripcion = re.sub(r" *\[", " [", item.descripcion)
            item.descripcion = re.sub(r" \* ", r"\n* ", item.descripcion)
            item.descripcion = re.sub(r"\n\s*\n+", r"\n", item.descripcion)
            item.descripcion = re.sub(r"^[ \t]*\.[ \t]*$", r"", item.descripcion, flags=re.MULTILINE)
            item.descripcion = item.descripcion.strip()
            # item.descripcion = re.sub(r"^ *", r"> ", item.descripcion, flags=re.MULTILINE)

        for item in items:
            del item['node']

        items = sorted(items, key=lambda x: (x.fecha, x.titulo))
        return items

    def get_ofertas(self):
        links = set()
        self.get("https://intranet.mapa.es/empleado-publico/ofertas-comerciales-para-los-empleados")
        for a in self.soup.select("ul.fotos-polaroid a[href]"):
            links.add((a.attrs["title"].strip(), a.attrs["href"]))
        r = []
        for tipo, url in sorted(links):
            url = url.replace(":443/", "/")
            r.append(Munch(
                tipo=tipo,
                url=url,
                ofertas=[]
            ))
            self.get(url)
            for o in self.soup.select("div.oferta-detalle"):
                tt = get_text(o.select_one("h3"))
                if tt.upper() == tt:
                    tt = tt.capitalize()
                if "." in tt and len(tt.split()) == 1:
                    tt = tt.lower()
                url = o.select_one("a.ico-website")
                if url:
                    url = url.attrs["href"]
                    url = url.rstrip(".")
                r[-1].ofertas.append(Munch(
                    titulo=tt,
                    url=url
                ))
        return r

    def get_contactos(self):
        kv = {
            "Médico": None,
            "D.U.E.": None,
            "Centralita": None,
            "C.A.U.": {},
        }
        self.get("https://intranet.mapa.es/servicios-internos/servicio-medico/")
        for table in self.soup.select("table"):
            cap = get_text(table)
            if CNF.sede in cap:
                td1 = tmap(get_text, table.select("tr > *:nth-of-type(1)"))
                td2 = tmap(get_text, table.select("tr > *:nth-of-type(2)"))
                for tds in (td1, td2):
                    if len(tds) > 1:
                        v = tds[0]
                        t = [i for i in tds if i.startswith("Tfno:")]
                        if len(t) > 0:
                            t = t[0].split()[-1]
                            if v not in kv:
                                v = v.title()
                            if v in kv:
                                kv[v] = t

        fnd_tlf = re.compile(r"(\d[\d ]+\d)")
        self.get("https://intranet.mapa.es/servicios-internos/atencion-usuarios/default.aspx")
        for div in self.soup.select("div"):
            if div.select_one("div"):
                continue
            txt = (get_text(div) or "").strip(" .")
            if "Formulario" in txt:
                kv["C.A.U."]["Formulario"] = div.find("a").attrs["href"].split("://", 1)[-1]
            elif "Correo" in txt:
                kv["C.A.U."]["Correo"] = txt.split()[-1]
            elif "Teléfono" in txt:
                tlf = [i.strip().replace(" ", "") for i in fnd_tlf.findall(txt)]
                if tlf:
                    kv["C.A.U."]["Teléfono"] = tlf

        self.get("https://intranet.mapa.es/app/Intranet_Form_Web/Web/Directory/DirectorySearch.aspx")
        ctr = self.soup.select_one("#telefonos-centralita")
        if ctr:
            kv["Centralita"] = [i.strip().replace(" ", "") for i in fnd_tlf.findall(get_text(ctr))]

        user = CNF.mapa.user.split("@")[0]
        url = "https://servicio.mapama.gob.es/cucm-uds/user/"
        url = url + user + "/speedDials"
        self.get(url, auth=HTTPBasicAuth(user, CNF.mapa.pssw), parser="xml")

        for s in self.soup.select("speedDial"):
            n = get_text(s.find("number"))
            l = get_text(s.find("label"))
            if len(n) == 10 and n.startswith("0"):
                n = n[1:]
            if len(n) == 5:
                user = self.get_users(n, searchMethod=1)
                if len(user) == 1:
                    user = user[0]
                    if user.telefono and user.telefonoext and user.telefonoext == n:
                        n = user.telefono + ", " + user.telefonoext
                    if user.correo:
                        n = n + " (" + user.correo + ")"
            kv[l] = n

        for k, v in list(kv.items()):
            if v is None:
                del kv[k]

        return kv

    def get_users(self, *args, searchMethod=None):
        if len(args) == 0:
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
                searchMethod = (1,)
            else:
                searchMethod = (3, 4)
        elif isinstance(searchMethod, int):
            searchMethod = (searchMethod,)
        self.get("https://intranet.mapa.es//app/Intranet_Form_Web/Web/Directory/DirectorySearch.aspx")
        nodos = []
        users = set()
        keys = set()
        url = "https://intranet.mapa.es//app/Intranet_Form_Web/Web/Directory/DirectoryWebService.asmx/ResultadoBusquedaList?count=1&contextKey=3&prefixText=" + args
        for sm in searchMethod:
            self.get(url + "&searchMethod=" + str(sm), parser="xml")
            keys = keys.union(
                k.name.lower() for k in self.soup.select("UserDirectoryInfo > *") if k.name.lower() != "id")
            nodos.extend(self.soup.select("UserDirectoryInfo"))
        keys = sorted(keys)
        for n in nodos:
            u = {k: None for k in keys}
            for i in n.select(":scope > *"):
                k = i.name.lower()
                if k == "id":
                    continue
                u[k] = i.get_text().strip()
            u = frozenset(u.items())
            users.add(u)
        users = sorted((User(**{k: v for k, v in u}) for u in users),
                       key=lambda u: (u.nombre, u.apellido1, u.apellido2))
        return users


if __name__ == "__main__":
    f = Mapa()
    r = f.get_contactos()
    import json

    print(json.dumps(r, indent=2, default=json_serial))
