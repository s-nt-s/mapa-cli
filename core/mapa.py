from datetime import datetime, date, timedelta
from typing import List, Tuple, Set, Union
from .filemanager import CNF
import bs4
import re
from .util import html_to_md, mk_re, strptime
from .web import Web
from .util import json_serial, ttext, nextone, get_text
from requests.auth import HTTPBasicAuth
from .user import User
from . import tp


re_sp = re.compile(r"\s+")

fix_url = (
    (re.compile(r"^(https?://[^/]*\.?)mapama\.es"), r"\1mapa.es"),
    (re.compile(r"^(https?://[^/]+):443/"), r"\1/"),
    (re.compile(r"/default\.aspx"), ""),
)

re_txt = {
    mk_re(k): v for k, v in {
        "Instituto Nacional de Administraciones Públicas": "INAP",
        "Administración General del Estado": "AGE",
        "Ministerio de Agricultura, Pesca y Alimentación": "MAPA",
        "Organización de las Naciones Unidas": "ONU",
        "Administraciones Públicas": "AAPP"
    }.items()
}


def clean_text(t: Union[str, bs4.Tag, None]) -> str:
    if t is None:
        return None
    if isinstance(t, bs4.Tag):
        for r_txt, txt in re_txt.items():
            n: bs4.Tag
            for n in t.findAll(text=r_txt):
                n.replace_with(r_txt.sub(txt, n.string))
        return t
    for r_txt, txt in re_txt.items():
        t = r_txt.sub(txt, t)
    return t


class Mapa(Web):
    def get_menu(self):
        """
        Obtiene el menú de la sede definida en config.yml
        """
        menus: List[tp.Menu] = []
        self.get("https://intranet.mapa.es/servicios-internos/cafeteria/menu/default.aspx")
        for div in self.soup.select("div.panel-heading"):
            h3 = div.get_text().strip()
            if CNF.sede not in h3:
                continue
            div = div.find_parent("div")
            fecha = div.select_one("span.fecha-menu")
            fecha = get_text(fecha)
            if fecha:
                fecha = fecha.split()[-1].split("/")
                fecha = reversed(tuple(map(int, fecha)))
                fecha = date(*fecha)
            elif len(menus) > 0 and menus[-1].fecha is not None:
                fecha = menus[-1].fecha + timedelta(days=1)
            # if dt < date.today():
            #    continue
            mhtml = div.select_one("div.menu")
            precios: List[str] = [p.replace(",", ".") for p, _ in re.findall(r"(\d+([.,]\d+))\s*€", str(mhtml))]
            menu = dict(
                fecha=fecha,
                precio=max(map(float, precios)),
                primeros=set(),
                segundos=set()
            )
            field = None
            for li in mhtml.select("li"):
                txt = nextone(map(get_text, li.contents))
                if txt is None:
                    continue
                if txt in ("Primeros platos", "Primer plato"):
                    field = "primeros"
                    continue
                if txt in ("Segundos platos", "Segundo plato"):
                    field = "segundos"
                    continue
                if txt in ("Pan, bebida y postre", ):
                    field = None
                    continue
                if field is not None:
                    menu[field].add(txt)

            for li in mhtml.select("li"):
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
            for li in mhtml.select("li"):
                lis = li.select("li")
                if len(lis) == 1:
                    li.replaceWith(lis[0])

            mmrk = html_to_md(mhtml, unwrap=('p', 'span'))
            mmrk = re.sub(r"^[ \t]*\* (Menú .+?)$", r"\n\1\n", mmrk, flags=re.MULTILINE)
            mmrk = re.sub(r"^[ \t]+\*\s*", r"* ", mmrk, flags=re.MULTILINE)
            mmrk = re.sub(r"^[ \t]+\+\s*", r"  + ", mmrk, flags=re.MULTILINE)
            mmrk = re.sub(r"\n\s*\n\s*\n+", r"\n\n", mmrk)

            menu['carta'] = mmrk.strip()
            for field in ("primeros", "segundos"):
                menu[field] = tuple(sorted(menu[field]))
            menus.append(tp.Menu(**menu))
        return tuple(menus)

    def get_novedades(self):
        def get_url_and_html(url:str, node: bs4.Tag) -> str:
            flag = False
            for n in node.select("span.novedad-lista-documentos"):
                flag = True
                n.extract()
            urls = set()
            a: bs4.Tag
            for a in node.select("a"):
                txt = a.get_text().strip().lower()
                s_txt = txt.split()
                urls.add(a.attrs["href"])
                if "ver" in s_txt or "enlace" in txt or re.match(r"^(para )?más información.*", txt):
                    a.string = a.attrs["href"]
                    a.name = "span"
            if len(urls) == 1:
                if flag:
                    n: bs4.Tag
                    for n in node.select(".lista-documentos"):
                        n.extract()
                a: bs4.Tag
                for a in node.findAll(["span", "a"]):
                    txt = a.get_text().strip()
                    for r, ntxt in fix_url:
                        txt = r.sub(ntxt, txt)
                    if txt in urls:
                        a.extract()
                url = urls.pop()
            while True:
                last = node.select(":scope > *")
                if len(last) == 0:
                    last = None
                    break
                last: bs4.Tag = last[-1]
                if get_text(last) is None and len(last.select(":scope > *")) == 0:
                    last.extract()
                    continue
                break
            if last is not None:
                txt = get_text(last)
                if txt is None or re.match(r"^(para |Puedes consultar )?más información.*", txt,
                                           flags=re.IGNORECASE):
                    last.extract()
            if url:
                a: bs4.Tag = node.find("a", attrs={"href": url})
                if a and len(a.get_text().strip()) < 3:
                    a.unwrap()
            n: bs4.Tag
            for n in node.findAll(["p", "div"]):
                if len(n.get_text().strip()) > 0:
                    continue
                chls = [i for i in n.select(":scope *") if i.name not in ("br", )]
                if len(chls) == 0:
                    n.extract()
            node = clean_text(node)
            return url, str(node)

        items: List[tp.Novedad] = []
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
            url = tt.find("a").attrs["href"]

            self.get(url)
            node = self.soup.select_one("div.novedad-descripcion")
            url, html = get_url_and_html(url, node)

            item = tp.Novedad(
                fecha=dt,
                titulo=clean_text(titu),
                url=url,
                descripcion=get_text(li.select_one("div.novedad-descripcion")),
                tipo="N",
                html=html
            )
            if item.descripcion:
                item = tp.merge(item, descripcion=re.sub(
                    r"\s*(Más información|Ver declaración)\s*\.?$", "", item.descripcion))
            items.append(item)

        self.get("https://intranet.mapa.es/comunicaciones-internas/tablon-de-anuncios/default.aspx")
        for li in self.soup.select("li.anuncio"):
            dt = li.select_one("span.fechacontenido")
            dt.extract()
            dt = get_text(dt)
            dt = re.sub(r"^\D+|\D+$", "", dt)
            dt = strptime(dt, "%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S")
            for div in li.select("div"):
                if len(div.select("div")) == 0:
                    div.name = "p"
            li.name = "div"
            h2 = li.select_one("h2")
            h2.extract()
            url, html = get_url_and_html(None, li)
            descripcion = html_to_md(html, links=True, unwrap=('span', 'strong', "b"))
            descripcion = re.sub(r"[ \t]+", " ", descripcion)
            descripcion = re.sub(r" *\[", " [", descripcion)
            descripcion = re.sub(r" \* ", r"\n* ", descripcion)
            descripcion = re.sub(r"\n\s*\n+", r"\n", descripcion)
            descripcion = re.sub(r"^[ \t]*\.[ \t]*$", r"", descripcion, flags=re.MULTILINE)
            # descripcion = re.sub(r"^ *", r"> ", descripcion, flags=re.MULTILINE)
            descripcion = descripcion.strip()

            item = tp.Novedad(
                fecha=dt,
                titulo=clean_text(get_text(h2)),
                url=url,
                descripcion=descripcion,
                tipo="A",
                html=html
            )
            items.append(item)

        return sorted(items, key=lambda x: (x.fecha, x.titulo))

    def get_ofertas(self):
        links: Set[Tuple[str, str]] = set()
        self.get("https://intranet.mapa.es/empleado-publico/ofertas-comerciales-para-los-empleados")
        for a in self.soup.select("ul.fotos-polaroid a[href]"):
            links.add((a.attrs["title"].strip(), a.attrs["href"]))
        r: List[tp.TreeUrl] = []
        for tipo, url in sorted(links):
            url = url.replace(":443/", "/")
            self.get(url)
            children: List[tp.TreeUrl] = []
            for o in self.soup.select("div.oferta-detalle"):
                tt = get_text(o.select_one("h3"))
                if tt.upper() == tt:
                    tt = tt.capitalize()
                if "." in tt and len(tt.split()) == 1:
                    tt = tt.lower()
                c_url = o.select_one("a.ico-website")
                if c_url:
                    c_url = c_url.attrs["href"]
                    c_url = c_url.rstrip(".")
                children.append(tp.TreeUrl(
                    txt=tt,
                    url=c_url
                ))
            r.append(tp.TreeUrl(txt=tipo, url=url, children=children))
        return tuple(r)

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
                td1 = ttext(table.select("tr > *:nth-of-type(1)"))
                td2 = ttext(table.select("tr > *:nth-of-type(2)"))
                for tds in (td1, td2):
                    if len(tds) <= 1:
                        continue
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
                tlf: List[str] = fnd_tlf.findall(txt)
                tlf = [i.strip().replace(" ", "") for i in tlf]
                if tlf:
                    kv["C.A.U."]["Teléfono"] = tlf

        self.get("https://intranet.mapa.es/app/Intranet_Form_Web/Web/Directory/DirectorySearch.aspx")
        ctr = self.soup.select_one("#telefonos-centralita")
        if ctr:
            tlf: List[str] = fnd_tlf.findall(get_text(ctr))
            kv["Centralita"] = [i.strip().replace(" ", "") for i in tlf]

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
        nodos: List[bs4.Tag] = []
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
