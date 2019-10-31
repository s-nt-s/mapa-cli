import json
import re
import os

import bs4
import requests
import yaml
from bunch import Bunch

re_json1 = re.compile(r"^\[\s*{")
re_json2 = re.compile(r" *}\s*\]$")
re_json3 = re.compile(r"}\s*,\s*{")
re_json4 = re.compile(r"\[\s*([^,\s]+)\s*,\s*([^,\s]+)\s*\]")
re_json5 = re.compile(r"\[\s*([^,\s]+)\s*\]")
re_json6 = re.compile(r"^  ", re.MULTILINE)


def obj_to_js(data):
    txt = json.dumps(data, indent=2)
    txt = re_json1.sub("[{", txt)
    txt = re_json2.sub("}]", txt)
    txt = re_json3.sub("},{", txt)
    txt = re_json4.sub(r"[\1, \2]", txt)
    txt = re_json5.sub(r"[\1]", txt)
    txt = re_json6.sub("", txt)
    return txt


def save_js(file, data):
    txt = obj_to_js(data)
    with open(file, "w") as f:
        f.write(txt)


def create_script(file, indent=2, **kargv):
    separators=(',', ':') if indent is None else None
    with open(file, "w") as f:
        for i, (k, v) in enumerate(kargv.items()):
            if i>0:
                f.write("\n")
            f.write("var "+k+"=")
            json.dump(v, f, indent=indent, separators=separators)
            f.write(";")

def read_js(fl):
    if os.path.isfile(fl):
        with open(fl, "r") as f:
            return json.load(f)