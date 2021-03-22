import json
import os
import re
import socket
import textwrap

import bs4
import yaml
from bunch import Bunch
from markdownify import markdownify
import requests
from urllib import parse
import pdftotext

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__))
)
__location__ = os.path.join(__location__, "..")

DAYNAME = ['Lunes', 'Martes', 'Miércoles',
           'Jueves', 'Viernes', 'Sábado', 'Domingo']
heads = ["h1", "h2", "h3", "h4", "h5", "h6"]
block = heads + ["p", "div", "table", "article", "figure"]
inline = ["span", "strong", "b", "del", "i", "em"]
tag_concat = ['u', 'ul', 'ol', 'i', 'em', 'strong', 'b']
tag_round = ['u', 'i', 'em', 'span', 'strong', 'a', 'b']
tag_trim = ['li', 'th', 'td', 'div', 'caption', 'h[1-6]']
tag_right = ['p']


def get_html(soup):
    h = str(soup)
    r = re.compile("(\s*\.\s*)</a>", re.MULTILINE | re.DOTALL | re.UNICODE)
    h = r.sub("</a>\\1", h)
    for t in tag_concat:
        r = re.compile(
            "</" + t + ">(\s*)<" + t + ">", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\1", h)
    for t in tag_round:
        r = re.compile(
            "(<" + t + ">)(\s+)", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\2\\1", h)
        r = re.compile(
            "(<" + t + " [^>]+>)(\s+)", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\2\\1", h)
        r = re.compile(
            "(\s+)(</" + t + ">)", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\2\\1", h)
    for t in tag_trim:
        r = re.compile(
            "(<" + t + ">)\s+", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\1", h)
        r = re.compile(
            "\s+(</" + t + ">)", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\1", h)
    for t in tag_right:
        r = re.compile(
            "\s+(</" + t + ">)", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\1", h)
        r = re.compile(
            "(<" + t + ">) +", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\1", h)
    h = r.sub(r"\n\1\n", h)
    r = re.compile(r"\n\n+", re.MULTILINE | re.DOTALL | re.UNICODE)
    h = r.sub(r"\n", h)
    return h


def get_config(fl="config.yml"):
    f = os.path.join(__location__, fl)
    config = mkBunch(f)
    if config is None:
        raise Exception("No existe el fichero "+f)
    if "vpn" not in config:
        config.vpn = exist("intranet.mapama.es")
    return config


def read_file(fl):
    fl = os.path.join(__location__, fl)
    if os.path.isfile(fl):
        with open(fl, "r") as f:
            return f.read()


def write_file(fl, txt):
    fl = os.path.join(__location__, fl)
    with open(fl, "w") as f:
        f.write(txt)


def dict_style(n):
    style = [s.split(":")
             for s in n.attrs["style"].lower().split(";") if s]
    style = {k: v for k, v in style}
    return style


def exist(hostname):
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.error:
        return False


def mkBunchParse(obj):
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = mkBunchParse(v)
        return obj
    if isinstance(obj, dict):
        data = []
        # Si la clave es un año lo pasamos a entero
        flag = True
        for k in obj.keys():
            if not isinstance(k, str):
                return {k: mkBunchParse(v) for k, v in obj.items()}
            if not(k.isdigit() and len(k) == 4 and int(k[0]) in (1, 2)):
                flag = False
        if flag:
            return {int(k): mkBunchParse(v) for k, v in obj.items()}
        obj = Bunch(**{k: mkBunchParse(v) for k, v in obj.items()})
        return obj
    if isinstance(obj, str) and obj.startswith("~/"):
        obj = os.path.expanduser(obj)
    return obj


def mkBunch(file):
    if not os.path.isfile(file):
        return None
    ext = file.rsplit(".", 1)[-1]
    with open(file, "r") as f:
        if ext == "json":
            data = json.load(f)
        elif ext == "yml":
            data = list(yaml.load_all(f, Loader=yaml.FullLoader))
            if len(data) == 1:
                data = data[0]
    data = mkBunchParse(data)
    return data


def js_print(data):
    print(json.dumps(data, indent=4))


def _str(s, *args):
    if args:
        s = s.format(*args)
    s = textwrap.dedent(s)
    return s.strip()


def parse_mes(m):
    if m == "ene":
        return 1
    if m == "feb":
        return 2
    if m == "mar":
        return 3
    if m == "abr":
        return 4
    if m == "may":
        return 5
    if m == "jun":
        return 6
    if m == "jul":
        return 7
    if m == "ago":
        return 8
    if m == "sep":
        return 9
    if m == "oct":
        return 10
    if m == "nov":
        return 11
    if m == "dic":
        return 12
    return None


def parse_dia(d):
    d = d.weekday()
    return ["L", "M", "X", "J", "V", "S", "D"][d]


def html_to_md(node, links=False, unwrap=None):
    if unwrap is None:
        unwrap = tuple()
    for hr in node.select("hr"):
        #hr.replace_with(bs4.BeautifulSoup("<br/>", "html.parser"))
        hr.extract()
    for i in node.select(":scope > span"):
        i.name = "p"
    for p in node.select("p"):
        if not p.get_text().strip():
            ch = [i.name for i in p.select(
                ":scope > *") if i.name not in ("br",)]
            if not ch:
                p.extract()
    for n in node.select(":scope *"):
        if not n.get_text().strip():
            n.extract()
        else:
            href = None
            if links and n.name == "a":
                href = n.attrs.get("href")
            n.attrs.clear()
            if href and n.get_text() not in href:
                n.attrs["href"] = href
    if unwrap:
        for n in node.findAll(unwrap):
            n.unwrap()
    html = get_html(node)
    md = markdownify(html)
    md = md.rstrip()
    md = md.replace(r"\r", "")
    md = re.sub(r"[ \t\r]+$", "", md, flags=re.MULTILINE)
    md = re.sub(r"\n\n\n+", r"\n\n", md)
    return md


def print_response(*responses):
    for response in responses:
        print(response.request.method, response.request.url)
        print("request = ", end="")
        js_print(dict(response.request.headers))
        p = parse.urlsplit(response.request.url)
        if p.query:
            body = parse.parse_qs(p.query)
            body = {k:v[0] if len(v)==1 else v for k,v in body.items()}
            print("query = ", end="")
            js_print(body)
        if response.request.body:
            body = parse.parse_qs(response.request.body)
            body = {k:v[0] if len(v)==1 else v for k,v in body.items()}
            print("body = ", end="")
            js_print(body)
        print("response = ", end="")
        js_print(dict(response.headers))
        if response.cookies:
            print("cookies = ", end="")
            ck = requests.utils.dict_from_cookiejar(response.cookies)
            js_print(ck)
        print(">>>", response.status_code, end="")
        if response.url != response.request.url:
            print(" ", response.url)
        else:
            print("")


def read_pdf(*files):
    for file in files:
        with open(file, 'rb') as fl:
            pdf = pdftotext.PDF(fl)
            for page in pdf:
                yield page


def to_num(s):
    if isinstance(s, str):
        s = s.replace("€", "")
        s = s.replace(".", "")
        s = s.replace(",", ".")
        s = float(s)
    if int(s)==s:
        s=int(s)
    return s
