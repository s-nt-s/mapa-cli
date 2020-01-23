import os
import re

import bs4
from jinja2 import Environment, FileSystemLoader
from glob import iglob
from os.path import relpath

re_br = re.compile(r"<br/>(\s*</)")


def toTag(html, *args):
    if len(args) > 0:
        html = html.format(*args)
    tag = bs4.BeautifulSoup(html, 'html.parser')
    return tag


class Jnj2():

    def __init__(self, origen, destino, pre=None, post=None):
        self.j2_env = Environment(
            loader=FileSystemLoader(origen), trim_blocks=True)
        self.destino = destino
        self.pre = pre
        self.post = post
        self.lastArgs = None
        self.javascript = sorted(relpath(i,self.destino) for i in iglob(self.destino+"/**/*.js", recursive=True))
        self.css = sorted(relpath(i,self.destino) for i in iglob(self.destino+"/**/*.css", recursive=True))


    def save(self, template, destino=None, parse=None, **kwargs):
        self.lastArgs = kwargs
        if destino is None:
            destino = template
        out = self.j2_env.get_template(template)
        html = out.render(javascript=self.javascript, css=self.css, **kwargs)
        if self.pre:
            html = self.pre(html, **kwargs)
            html = str(html)
        if parse:
            html = parse(html, **kwargs)
            html = str(html)
        if self.post:
            html = self.post(html, **kwargs)
            html = str(html)

        if self.javascript or self.css:
            soup = bs4.BeautifulSoup(html, 'lxml')
            remo = []
            for j in self.javascript:
                items = soup.select("script[src='"+j+"']")
                if len(items)>1:
                    remo.extend(items)
            for c in self.css:
                items = soup.select("link[href='"+c+"']")
                if len(items)>1:
                    remo.extend(items)
            for r in remo:
                if r.attrs.get("data-autoinsert"):
                    r.extract()
            html = str(soup)

        destino = self.destino + destino
        directorio = os.path.dirname(destino)

        if not os.path.exists(directorio):
            os.makedirs(directorio)

        with open(destino, "wb") as fh:
            fh.write(bytes(html, 'UTF-8'))
        return html
