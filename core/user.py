from munch import Munch
import re

re_sp = re.compile(r"\s+")
ORDINAL = ['primer', 'segund', 'tercer', 'cuart', 'quint', 'sext', 'septim', 'octav', 'noven', 'decim']

def parse_user(k, v):
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
    if len(w)==2 and w[1] == "planta":
        w=w[0][:-1].replace("é", "e")
        if w in ORDINAL:
            return str(ORDINAL.index(w)+1)+"ª planta"
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
    w=[i for i in args if i]
    return sep.join(w) if w else None

class User(Munch):
    def __init__(self, *args, **karg):
        c = karg.get("centro")
        u = karg.get("unidad")
        if c and u and u in c:
            karg["unidad"]=None
        karg = {k: parse_user(k, v) for k, v in karg.items()}
        super().__init__(*args, **karg)

    def isEmpty(self):
        for k in ("unidad", "unidad", "puesto", "despacho", "planta", "ubicacion", "telefono", "telefonoext", "correo"):
            if self[k]:
                return False
        return True

    def __str__(self):
        fl = lambda *args: tuple(a for a in args if a is not None)
        lines = [" ".join(fl(self.nombre, self.apellido1, self.apellido2))]
        if self.puesto:
            lines.append(self.puesto)
        lines.append(" > ".join(fl(self.centro, self.unidad)))
        lines.append(" - ".join(fl(self.despacho, self.planta, self.ubicacion)))
        lines.append(" - ".join(fl(self.telefono, self.telefonoext, self.correo)))
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
            dire=join_str(join_str(u.despacho, u.planta), u.ubicacion, sep=",")
            **dict(self)
        )
        lines=[]
        for l in vcard.strip().split("\n"):
            l = l.strip()
            l = l.replace("None;", ";")
            l = l.replace(" None", "")
            if l and not l.endswith(":") and "None" not in l:
                lines.append(l)
        vcard = "\n".join(lines)
        return vcard
