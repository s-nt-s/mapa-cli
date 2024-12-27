import json
import os
import re
from datetime import date, datetime
from typing import Any, Callable, Union

import bs4
from jinja2 import Environment, FileSystemLoader
from unidecode import unidecode

re_br = re.compile(r"<br/>(\s*</)")


def myconverter(o):
    if isinstance(o, (datetime, date)):
        return o.__str__()


def millar(value: Union[int, float, str, None, Any]):
    if value is None:
        return "----"
    if not isinstance(value, (int, float)):
        return value
    value = "{:,.0f}".format(value).replace(",", ".")
    return value


def decimal(value: Union[int, float, Any]):
    if not isinstance(value, (int, float)):
        return value
    if int(value) == value:
        return int(value)
    return str(value).replace(".", ",")


def mb(value: Union[int, float, Any]):
    if not isinstance(value, (int, float)):
        return value
    v = round(value)
    if v == 0:
        v = round(value*10)/10
    if v != 0:
        return str(v)+" MB"
    value = value * 1024
    v = round(v)
    if v != 0:
        return str(v)+" KB"
    value = value * 1024
    v = round(v)
    return str(v)+" B"


def toTag(html: str, *args):
    if len(args) > 0:
        html = html.format(*args)
    tag = bs4.BeautifulSoup(html, 'html.parser')
    return tag


def slug(s: str):
    s = "-".join(s.strip().lower().split())
    s = unidecode(s)
    return s


class Jnj2():

    def __init__(self, origen: str, destino: str, pre: Union[Callable, None] = None, post: Union[Callable, None] = None):
        self.j2_env = Environment(
            loader=FileSystemLoader(origen), trim_blocks=True)
        self.j2_env.filters['millar'] = millar
        self.j2_env.filters['decimal'] = decimal
        self.j2_env.filters['mb'] = mb
        self.j2_env.filters['slug'] = slug
        self.destino = destino
        self.pre = pre
        self.post = post
        self.lastArgs = None

    def save(self, template, destino: Union[str, None] = None, parse: Union[Callable, None] = None, **kwargs):
        self.lastArgs = kwargs
        if destino is None:
            destino = template
        out = self.j2_env.get_template(template)
        html = out.render(**kwargs)
        if self.pre:
            html = self.pre(html, **kwargs)
        if parse:
            html = parse(html, **kwargs)
        if self.post:
            html = self.post(html, **kwargs)

        destino = self.destino + destino
        directorio = os.path.dirname(destino)

        if not os.path.exists(directorio):
            os.makedirs(directorio)

        with open(destino, "wb") as fh:
            fh.write(bytes(html, 'UTF-8'))
        return html

    def create_script(self, destino: str, indent=2, replace=False, **kargv):
        destino = self.destino + destino
        if not replace and os.path.isfile(destino):
            return
        separators = (',', ':') if indent is None else None
        with open(destino, "w") as f:
            for i, (k, v) in enumerate(kargv.items()):
                if i > 0:
                    f.write(";\n")
                f.write("var "+k+" = ")
                json.dump(v, f, indent=indent,
                          separators=separators, default=myconverter)
                f.write(";")

    def exists(self, destino):
        destino = self.destino + destino
        return os.path.isfile(destino)
