#!/usr/bin/env python3

import os
import re

import bs4
import requests
from bunch import Bunch
from unidecode import unidecode
import argparse
from datetime import datetime

from core.common import create_script, read_js
from core.j2 import Jnj2, toTag

parser = argparse.ArgumentParser(description='Crea la página web')
parser.add_argument('--local', action='store_true', help='No descarga los json si ya estan en local')
args = parser.parse_args()

def get_label(soup, id, tag=False):
    lb = soup.find("label", attrs={"for": id})
    if lb:
        if tag:
            return lb
        txt = lb.get_text().strip().rstrip(": ")
        if txt:
            return txt


def parse(html, *args, **kargv):
    html = re.sub(r"<br/>(\s*</)", r"\1", html).strip()
    soup = bs4.BeautifulSoup(html, 'lxml')

    # Eliminar elementos
    for n in soup.select("*[data-delete]"):
        d = n.attrs["data-delete"]
        for i in n.select(d):
            i.extract()

    # Añadir prefijos a los ids
    for wrapper in soup.select("*[data-idprefix]"):
        prefix = wrapper.attrs["data-idprefix"]
        for item in wrapper.select(":scope *[id]"):
            id = item.attrs["id"]
            if item.name in ("input", "select") and not item.attrs.get("name"):
                item.attrs["name"] = id
            ni = prefix+id
            for label in wrapper.select(":scope *[for='"+id+"']"):
                label.attrs["for"]=ni
            item.attrs["id"]=ni

    # Añadir prefijos a los nombres
    for wrapper in soup.select("*[data-nameprefix]"):
        prefix = wrapper.attrs["data-nameprefix"]
        for item in wrapper.select(":scope *[name]"):
            name = item.attrs["name"]
            name = prefix+name
            item.attrs["name"]=name

    for form in soup.findAll("form"):
        names = set()
        for fls in form.findAll("fieldset"):
            id_fls = fls.attrs.get("id")
            for i in fls.findAll(["input", "select"]):
                tp = i.attrs.get("type")
                if tp in ("submit", ):
                    continue
                id = i.attrs.get("id")
                # ID && !name ---> name = ID
                if id and not i.attrs.get("name"):
                    i.attrs["name"] = id
                # Todo obligatorio menos radio y checkbox
                if tp not in ("radio", "checkbox") and "opcional" not in i.attrs.get("class", ""):
                    i.attrs["required"] = "required"
                # Todo checkeado menos fDetalle
                if tp == "checkbox" and not i.attrs.get("checked") and id_fls != "fDetalle":
                    i.attrs["checked"] = "checked"
                # Checkear primer radio de cada grupo
                if tp == "radio":
                    name = i.attrs["name"]
                    if name not in names and not i.attrs.get("checked"):
                        i.attrs["checked"] = "checked"
                    names.add(name)
                if i.name == "select" and "fullsize" in i.attrs.get("class", "") and "size" not in i.attrs:
                    i.attrs["size"] = len(i.select(":scope *"))

                if not id:
                    continue

                # label && !title ---> title = label
                if i.attrs.get("title") is None:
                    lb = get_label(soup, id)
                    if i.name == "select" and i.attrs.get("multiple"):
                        lb = (
                            lb or "")+". Manten pulsada la tecla control para seleccionar varias opciones"
                        lb = lb.rstrip(". ")
                    if lb:
                        i.attrs["title"] = lb
                else:
                    # !label.title && label.text != input.title ---> lb.title = input.title
                    lb = get_label(soup, id, tag=True)
                    if lb and not lb.attrs.get("title") and lb.get_text().strip() != i.attrs.get("title"):
                        lb.attrs["title"] = i.attrs.get("title")

    for i in soup.select(".opcional select, .opcional input"):
        if "required" in i.attrs:
            del i.attrs["required"]

    # Guardar value inicial
    att = "data-defval"
    for i in soup.select("input[type=submit]"):
        v = i.attrs.get("value")
        if v and att not in i.attrs:
            i.attrs[att] = v

    TXT = {}
    # Guardar texto de grupos radio/checkbox
    for tp in ("radio", "checkbox"):
        for i in soup.select("input[type='"+tp+"']"):
            name = i.attrs.get("name")
            id = i.attrs.get("id")
            if id and name and name.endswith("[]"):
                value, lb = i.attrs.get("value"), get_label(soup, id)
                if None not in (value, lb) and "" not in (value, lb):
                    name = name[:-2]
                    obj = TXT.get(name, {})
                    obj[value] = lb
                    TXT[name] = obj

    # Guardar textos de los selects
    for i in soup.select("select[data-txt]"):
        s_txt={}
        for o in i.select("option[value]"):
            txt = o.get_text().strip().rstrip(".")
            if txt:
                s_txt[o.attrs["value"]] = txt
        TXT[i.attrs["data-txt"]] = s_txt

    for i in soup.select("span[data-txt]"):
        txt = i.get_text().strip()
        key = i.attrs["data-txt"]
        key = key.strip().split(None, 1)
        if len(key)==1:
            TXT[key[0]]=txt
        else:
            obj = TXT.get(key[0], {})
            obj[key[1]]=txt
            TXT[key[0]] = obj

    for k, v in list(TXT.items()):
        if len(set(v.values()))==1:
            del TXT[k]

    #create_script("out/rec/txt.js", indent=2, TXT=TXT)
    create_script("out/rec/js/00-constantes/txt.js", indent=2, TXT=TXT)

    for n in soup.select("*[data-extract]"):
        n.extract()

    return soup


def sort_prov(p):
    n = p.nombre.lower()
    n.replace("ñ", "--------")
    n = unidecode(n)
    n.replace("--------", "ñ")
    return (n, p.ID)


os.makedirs("out/geo", exist_ok=True)
os.makedirs("out/rec", exist_ok=True)

provincias = read_js("data/provincias.json") or []
if os.environ.get("JS_PROVINCIAS") and not(provincias and args.local):
    r = requests.get(os.environ["JS_PROVINCIAS"])
    provincias = r.json()

provincias = [p for p in provincias if int(p["ID"])<53]

for t in ("provincias", "municipios"):
    fl = "out/geo/"+t+".js"
    if args.local and os.path.isfile(fl):
        continue
    geojson = read_js("data/get/"+t+".json")
    if geojson is None:
        url = os.environ.get("GEO_"+t.upper())
        r = requests.get(url)
        geojson = r.json()
    if t == "provincias":
        geojson['features']=[f for f in geojson['features'] if int(f["properties"]["i"])<53]
    param = {"geo"+t: geojson}
    create_script(fl, indent=None, **param)

provincias = [Bunch(**i) for i in provincias]
provincias = sorted(provincias, key=sort_prov)
jHtml = Jnj2("templates/", "out/", post=parse)
jHtml.save("index.html", provincias=provincias,
           API_ENDPOINT=os.environ.get("API_ENDPOINT", ""), now=datetime.now())
