#!/usr/bin/env python3

import os
import re

import bs4
import requests
from bunch import Bunch
from unidecode import unidecode
import argparse

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
    TXT = {}
    for form in soup.findAll("form"):
        names = set()
        for fls in form.findAll("fieldset"):
            id_fls = fls.attrs.get("id")
            for i in fls.findAll(["input", "select"]):
                tp = i.attrs.get("type")
                if tp in ("submit", ):
                    continue
                id = i.attrs["id"]
                # ID && !name ---> name = ID
                if not i.attrs.get("name"):
                    i.attrs["name"] = id
                # Todo obligatorio menos radio y checkbox
                if tp not in ("radio", "checkbox"):
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
                # label && !title ---> title = label
                if i.attrs.get("title") is None:
                    lb = get_label(soup, id)
                    if i.name == "select" and i.attrs.get("multiple"):
                        lb = (
                            lb or "")+". Manten pulsada la tecla control para seleccionar varias opciones"
                        lb.rstrip(". ")
                    if lb:
                        i.attrs["title"] = lb
                else:
                    # !label.title && label.text != input.title ---> lb.title = input.title
                    lb = get_label(soup, id, tag=True)
                    if lb and not lb.attrs.get("title") and lb.get_text().strip() != i.attrs.get("title"):
                        lb.attrs["title"] = i.attrs.get("title")

                # Añadir title a los inputs de habilitar/deshabilitar
                if tp == "checkbox" and id and "enable_" in id and i.attrs.get("title") is None:
                    ot = id.replace("enable_", "")
                    lb = fls.select(":scope label[for='"+ot+"']")
                    if len(lb)==1:
                        tt = lb[0].get_text().strip().rstrip(":")
                        i.attrs["title"]="Habilita "+tt

                if i.attrs.get("disabled"):
                    i.attrs["data-defdisabled"]="true"

                # Guardar texto de grupos radio/checkbox
                name = i.attrs.get("name")
                if name and name.endswith("[]") and tp in ("radio", "checkbox"):
                    value, lb = i.attrs.get("value"), get_label(soup, id)
                    if None not in (value, lb) and "" not in (value, lb):
                        name = name[:-2]
                        obj = TXT.get(name, {})
                        obj[value] = lb
                        TXT[name] = obj

    # Guardar value inicial
    att = "data-defval"
    for i in soup.select("input[type=submit]"):
        v = i.attrs.get("value")
        if v and att not in i.attrs:
            i.attrs[att] = v

    # Guardar texto de las zonas
    zonas = {}
    for op in soup.find("select", attrs={"name": "zona[]"}).findAll("option"):
        txt = op.get_text().strip()
        if txt:
            zonas[op.attrs["value"]] = txt

    # Guardar texto de tipos de entrenamiento
    entrenamiento = {}
    for op in soup.find("select", attrs={"id": "tEntrenamiento"}).findAll("option"):
        txt = op.get_text().strip().rstrip(".")
        if txt:
            entrenamiento[op.attrs["value"]] = txt

    TXT["zonas"] = zonas
    TXT["entrenamiento"] = entrenamiento
    create_script("out/rec/txt.js", indent=2, TXT=TXT)

    # Añadir prefijos a los ids
    for wrapper in soup.select("*[data-idprefix]"):
        prefix = wrapper.attrs["data-idprefix"]
        for item in wrapper.select(":scope *[id]"):
            id = item.attrs["id"]
            ni = prefix+id
            for label in wrapper.select(":scope *[for='"+id+"']"):
                label.attrs["for"]=ni
            item.attrs["id"]=ni

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

for t in ("provincias", "municipios"):
    fl = "out/geo/"+t+".js"
    if args.local and os.path.isfile(fl):
        continue
    url = os.environ.get("GEO_"+t.upper())
    r = requests.get(url)
    geojson = r.json()
    param = {"geo"+t: geojson}
    create_script(fl, indent=None, **param)

provincias = [Bunch(**i) for i in provincias]
provincias = sorted(provincias, key=sort_prov)
jHtml = Jnj2("templates/", "out/", post=parse)
jHtml.save("index.html", provincias=provincias,
           API_ENDPOINT=os.environ.get("API_ENDPOINT", ""))
