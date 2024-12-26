import re
from .util import notnull
from typing import Union, Dict, Any
from dataclasses import dataclass, asdict, fields

re_sp = re.compile(r"\s+")
ORDINAL = ['primer', 'segund', 'tercer', 'cuart', 'quint', 'sext', 'septim', 'octav', 'noven', 'decim']


def parse_user(k: str, v: Union[str, None]):
    if v is None:
        return None
    v = re_sp.sub(" ", v).strip()
    if v == "":
        return None
    if k == "despacho" and " " not in v:
        return v
    if k in ("nombre", "apellido1", "apellido2"):
        return v.title()
    if k == "correo":
        return v.lower()
    w = v.lower().split()
    if len(w) == 2 and w[1] == "planta":
        w = w[0][:-1].replace("é", "e")
        if w in ORDINAL:
            return str(ORDINAL.index(w) + 1) + "ª planta"
    if "(FEGA)" in v:
        return "FEGA"
    if "(ENESA)" in v:
        return "ENESA"
    if k == "puesto":
        v = v.split(" / ", 1)[-1]
    v = v.capitalize()
    v = re.sub(r"^(D\.\s*g\.|Dirección general)", "DG", v)
    v = re.sub(r"^(S\.\s*g\.|Subdirección general)", "SG", v)
    v = v.replace("madrid", "Madrid")
    return v


def join_str(*args, sep=" "):
    w = [i for i in args if i]
    return sep.join(w) if w else None


@dataclass(frozen=True)
class User:
    nombre: str
    apellido1: str
    apellido2: str
    centro: str
    unidad: str
    puesto: str
    despacho: str
    planta: str
    ubicacion: str
    telefono: str
    telefonoext: str
    correo: str

    @classmethod
    def build(cls, obj: Dict[str, Any]):
        fls = tuple(f.name for f in fields(cls))
        data = {}
        for k, v in obj.items():
            if k in fls:
                data[k]=v
        for k, v in obj.items():
            if k.endswith("limpio"):
                k = k[:-6]
                if k in fls and data.get(k) is None:
                    data[k]=v

        return User(**data)

    def __post_init__(self):
        if self.centro and self.unidad and self.unidad in self.centro:
            object.__setattr__(self, 'unidad', None)
        for k, v in asdict(self).items():
            object.__setattr__(self, k, parse_user(k, v))

    def isEmpty(self):
        if self.unidad is not None:
            return False
        if self.puesto is not None:
            return False
        if self.despacho is not None:
            return False
        if self.planta is not None:
            return False
        if self.ubicacion is not None:
            return False
        if self.telefono is not None:
            return False
        if self.telefonoext is not None:
            return False
        if self.correo is not None:
            return False
        return True

    def __str__(self):
        lines = [notnull(self.nombre, self.apellido1, self.apellido2, sep=" ")]
        if self.puesto:
            lines.append(self.puesto)
        lines.append(notnull(self.centro, self.unidad, sep=" > "))
        lines.append(notnull(self.despacho, self.planta, self.ubicacion, sep=" - "))
        lines.append(notnull(self.telefono, self.telefonoext, self.correo, sep=" - "))
        return "\n".join(l for l in lines if l)

    @property
    def centro_unidad(self):
        if self.centro is None and self.unidad is None:
            return ("", "")
        if None in (self.centro, self.unidad):
            return (self.centro or self.unidad, "")
        return (self.centro, self.unidad)

    @property
    def apellidos(self):
        return join_str(self.apellido1, self.apellido2)

    @property
    def vcard(self):
        if self.isEmpty():
            return None
        vcard = '''
        BEGIN:VCARD
        VERSION:4.0
        N:{apellidos};{nombre};;;
        FN:{nombre} {apellidos}
        ORG:{centro_unidad}
        TITLE:{puesto}
        TEL;TYPE=work,voice;VALUE=uri:tel:{telefono}
        TEL;TYPE=home,voice;VALUE=uri:tel:{telefonoext}
        ADR;TYPE=WORK;PREF=1;LABEL="{dire}":;;;;;;
        EMAIL:{correo}
        END:VCARD
        '''.format(
            apellidos=self.apellidos,
            centro_unidad=join_str(self.centro, self.unidad, sep=" > "),
            dire=join_str(join_str(self.despacho, self.planta), self.ubicacion, sep=","),
            **dict(self)
        )
        lines = []
        for l in vcard.strip().split("\n"):
            l = l.strip()
            l = l.replace("None;", ";")
            l = l.replace(" None", "")
            if l and not l.endswith(":") and "None" not in l:
                lines.append(l)
        vcard = "\n".join(lines)
        return vcard
