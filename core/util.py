import re
from markdownify import markdownify
from typing import NamedTuple
from datetime import date, datetime
from .hm import HM

DAYNAME = ('Lunes', 'Martes', 'Miércoles',
           'Jueves', 'Viernes', 'Sábado', 'Domingo')
MONTHNAME = ('Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre')
heads = ("h1", "h2", "h3", "h4", "h5", "h6")
block = heads + ("p", "div", "table", "article", "figure")
inline = ("span", "strong", "b", "del", "i", "em")
tag_concat = ('u', 'ul', 'ol', 'i', 'em', 'strong', 'b')
tag_round = ('u', 'i', 'em', 'span', 'strong', 'a', 'b')
tag_trim = ('li', 'th', 'td', 'div', 'caption', 'h(1-6)')
tag_right = ('p',)

re_url = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
re_mail = re.compile(r"^([a-záéíóú0-9_\-\.]+)@([a-záéíóú0-9_\-\.]+)\.([a-záéíóú]{2,5})$", re.IGNORECASE)
re_sp = re.compile(r"\s+")


def get_times(ini, fin, delta):
    while ini < fin:
        end = ini + delta
        yield ini, min(fin, end)
        ini = ini + delta

def get_months(ini: date, count: int):
    cur = ini.replace(day=1)
    for _ in range(count):
        m = cur.month + 1
        y = cur.year + int(m / 12)
        m = m % 12
        if m == 0:
            m = 12
        cur = cur.replace(year=y, month=m)
        yield cur

def get_text(node, default=None):
    if node is None:
        return default
    txt = re_sp.sub(" ", node.get_text()).strip()
    if len(txt) == 0:
        return default
    return txt


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


def html_to_md(node, links=False, unwrap=None):
    if unwrap is None:
        unwrap = tuple()
    for hr in node.select("hr"):
        # hr.replace_with(bs4.BeautifulSoup("<br/>", "html.parser"))
        hr.extract()
    for i in node.select(":scope > span"):
        i.name = "p"
    for p in node.findAll("p", text=re.compile(r"^\s*$")):
        ch = [i.name for i in p.select(":scope > *") if i.name not in ("br",)]
        if len(ch) == 0:
            p.extract()
    for n in node.select(":scope *"):
        if len(n.get_text().strip()) == 0:
            n.extract()
    if links:
        for n in node.select(":scope a[href]"):
            if len(n.select(":scope *")) > 0:
                continue
            href = n.attrs["href"]
            txt = n.get_text().strip()
            if ("mailto:" + txt) == href or re_mail.match(txt):
                n.unwrap()
                continue
            if href in txt or re_url.match(txt):
                n.string = href
                n.unwrap()
                continue
    for n in node.select(":scope *"):
        href = n.attrs.get("href")
        n.attrs.clear()
        if href:
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
    md = md.lstrip("\n")
    return md


def tmap(f, a):
    return tuple(map(f, a))


def json_serial(obj):
    if isinstance(obj, date):
        return obj.strftime("%Y-%m-%d")
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d %H:%M")
    if isinstance(obj, HM):
        return str(obj)
    if isinstance(obj, NamedTuple):
        return obj._asdict()


def json_hook(d):
    for (k, v) in d.items():
        if isinstance(v, str):
            if re.match(r"^[\-+]?\d+:\d+(:\d+)?$", v):
                d[k] = HM(v)
            elif re.match(r"^\d+-\d+-\d+$", v):
                d[k] = date(*map(int, v.split("-")))
            elif re.match(r"^\d+-\d+-\d+ \d+:\d+$", v):
                d[k] = datetime.strptime(v, "%Y-%m-%d %H:%M")
            elif re.match(r"^\d+-\d+-\d+ \d+:\d+\d+$", v):
                d[k] = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
    return d


def parse_mes(m):
    if m is None:
        return None
    m = m.strip().lower()[:3]
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


def to_num(s, safe=False):
    if s is None:
        return None
    if safe is True:
        try:
            return to_num(s)
        except ValueError:
            return s
    if isinstance(s, str):
        s = s.replace("€", "")
        s = s.replace(".", "")
        s = s.replace(",", ".")
        s = float(s)
    if int(s) == s:
        s = int(s)
    return s


def to_strint(f):
    if f is None:
        return None
    f = round(f)
    f = '{:,}'.format(f).replace(",", ".")
    return f


def notnull(*args, sep=None):
    arr = []
    for a in args:
        if isinstance(a, str):
            a = a.strip()
        if a not in (None, ""):
            arr.append(a)
    if sep:
        return sep.join(arr)
    return tuple(arr)


def mk_re(s, flags=re.IGNORECASE):
    words = s.strip().split()
    re_wd = [re.escape(w) for w in words]
    re_s = r"\s+".join(re_wd)
    return re.compile(re_s, flags=flags)


def nextone(iterator):
    for i in iterator:
        if i is not None:
            return i
    return None


def strptime(dt: str, *args: str):
    if len(args) == 0:
        raise ValueError("strptime() takes 2 positional or more arguments but 1 was given")
    for i, a in enumerate(args):
        try:
            return datetime.strptime(dt, a)
        except ValueError:
            if i == len(args) - 1:
                raise