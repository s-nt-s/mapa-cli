import tabula
from io import StringIO
import json
import re
from .common import to_num
import os

re_cellnb = re.compile(r'\s([\d\.,]+)\s')

def parseTb(table):
    if table is None:
        return []
    s = StringIO()
    sep = '\t'
    table.to_csv(s, index=False, header=False, sep=sep)
    s=s.getvalue()
    s=s.strip()
    rows = []
    for r in s.split("\n"):
        r = re_cellnb.sub(lambda m: sep+m.group()+sep, r)
        r = r.strip()
        row = []
        for c in re.split(r"\s*\t\s*", r):
            c=to_num(c, safe=True)
            row.append(c)
        rows.append(row)
    return rows

def retribucion_to_json(file, overwrite=False):
    if file is None or not os.path.isfile(file):
        return
    jfile = file.rsplit(".", 1)[0]+".json"
    if not overwrite and os.path.isfile(jfile):
        with open(jfile, "r") as f:
            data = json.load(f)
            data = {int(k):v for k,v in data.items()}
            return data

    tableC = None
    tableS = None
    for t in tabula.read_pdf(file, pages=1, multiple_tables=True):
        if 'COMPLEMENTO DE DESTINO' in t.columns:
            tableC = t
        elif 'A2' in t.columns and 'A2' in t.columns and 'C1' in t.columns:
            tableS= t


    data={}
    grupos = ("A1", "A2", "B", "C1", "C2", "E")
    for g in grupos:
        data[g]={}
    for row in parseTb(tableS):
        if not(len(row)>2 and isinstance(row[0], str) and isinstance(row[1], (int, float))):
            continue
        txt = row[0].replace(" ", '')
        sld = [r for i, r in enumerate(row[1:]) if i%2==0]
        tri = [r for i, r in enumerate(row[1:]) if i%2==1]
        key = None
        if txt.startswith("ANUAL"):
            key = "base"
        elif txt.startswith("PAGAEXTRAJUNIO"):
            key = "junio"
        elif txt.startswith("PAGAEXTRADICIEMBRE"):
            key = "diciembre"
        if key is None:
            continue
        for i, g in enumerate(grupos):
            data[g][key]={
                "sueldo": sld[i],
                "trienio": tri[i]
            }

    data["niveles"]={}
    for row in parseTb(tableC):
        if row[0] is None or not isinstance(row[0], int):
            continue
        row = [r for i, r in enumerate(row) if i%2==0]
        row = iter(row)
        nivel = next(row)
        compd = next(row)
        data["niveles"][nivel]=compd
    with open(jfile, "w") as f:
        json.dump(data, f, indent=2)
    return data


if __name__ == '__main__':
    import sys
    data = retribucion_to_json(sys.argv[1], overwrite=True)
    #print(json.dumps(data, indent=2))
