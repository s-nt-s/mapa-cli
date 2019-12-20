#!/usr/bin/env python3

import json
import re

import bs4
from unidecode import unidecode
import requests

from core.common import create_script, read_js
from core.j2 import Jnj2, toTag
from bunch import Bunch
import os


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
    TXT={}
    for form in soup.findAll("form"):
        names = set()
        for fls in form.findAll("fieldset"):
            id_fls = fls.attrs.get("id")
            for i in fls.findAll(["input", "select"]):
                tp = i.attrs.get("type")
                if tp in ("submit", ):
                    continue
                id = i.attrs["id"]
                if not i.attrs.get("name"):
                    i.attrs["name"] = id
                if tp not in ("radio", "checkbox"):
                    i.attrs["required"] = "required"
                if tp == "checkbox" and not i.attrs.get("checked") and id_fls != "fDetalle":
                    i.attrs["checked"] = "checked"
                if tp == "radio":
                    name = i.attrs["name"]
                    if name not in names and not i.attrs.get("checked"):
                        i.attrs["checked"] = "checked"
                    names.add(name)
                if tp == "number" and i.attrs.get("min") is None:
                    i.attrs["min"] = 2006
                if i.attrs.get("title") is None:
                    lb = get_label(soup, id)
                    if i.name=="select" and i.attrs.get("multiple"):
                        lb = (lb or "")+". Manten pulsada la tecla control para seleccionar varias opciones"
                        lb.rstrip(". ")
                    if lb:
                        i.attrs["title"] = lb
                else:
                    lb = get_label(soup, id, tag=True)
                    if lb and not lb.attrs.get("title") and lb.get_text().strip()!=i.attrs.get("title"):
                        lb.attrs["title"] = i.attrs.get("title")
                name = i.attrs.get("name")
                if name and name.endswith("[]") and tp in ("radio", "checkbox"):
                    value, lb = i.attrs.get("value"), get_label(soup, id)
                    if None not in (value, lb) and "" not in (value, lb):
                        name = name[:-2]
                        obj = TXT.get(name, {})
                        obj[value]=lb
                        TXT[name]=obj
    att="data-defval"
    for i in soup.select("input[type=submit]"):
        v = i.attrs.get("value")
        if v and att not in i.attrs:
            i.attrs[att]=v

    zonas={}
    for op in soup.find("select", attrs={"name":"zona[]"}).findAll("option"):
        txt = op.get_text().strip()
        if txt:
            zonas[op.attrs["value"]]=txt

    entrenamiento={}
    for op in soup.find("select", attrs={"id":"tEntrenamiento"}).findAll("option"):
        txt = op.get_text().strip().rstrip(".")
        if txt:
            entrenamiento[op.attrs["value"]]=txt

    TXT["zonas"]=zonas
    TXT["entrenamiento"]=entrenamiento
    create_script("out/rec/txt.js", indent=2, TXT=TXT)
    return soup

def sort_prov(p):
    n = p.nombre.lower()
    n.replace("ñ", "--------")
    n = unidecode(n)
    n.replace("--------", "ñ")
    return (n, p.ID)

os.makedirs("out/geo", exist_ok=True)
os.makedirs("out/rec", exist_ok=True)

provincias=read_js("data/provincias.json") or []
if os.environ.get("JS_PROVINCIAS"):
    r = requests.get(os.environ["JS_PROVINCIAS"])
    provincias = r.json()

for t in ("provincias", "municipios"):
    url = os.environ.get("GEO_"+t.upper())
    r = requests.get(url)
    geojson = r.json()
    param={"geo"+t:geojson}
    create_script(out, indent=None, **param)
    
provincias = [Bunch(**i) for i in provincias]
provincias = sorted(provincias, key=sort_prov)

jHtml = Jnj2("templates/", "out/", post=parse)
jHtml.save("index.html", provincias=provincias, API_ENDPOINT=os.environ.get("API_ENDPOINT", ""))
