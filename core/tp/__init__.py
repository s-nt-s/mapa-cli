from typing import NamedTuple, Tuple
from datetime import date
from .builder import TP
from .builder import builder as bb_builder
from .hm import HM

builder = bb_builder


def merge(tp: TP, **kwargs) -> TP:
    return tp.__class__(**{**tp._asdict(), **kwargs})


def get(tp: TP, field):
    dct = tp._asdict()
    return dct.get(field)


class Expediente(NamedTuple):
    fecha: str
    name: str
    tipo: str
    desc: str
    url: str
    file: str
    index: int


class Festivo(NamedTuple):
    fecha: str
    dia: str
    tipo: str
    localidad: str
    provincia: str
    comunidad: str
    pais: str
    url: str = None


class Vacaciones(NamedTuple):
    fecha: str
    dias: int
    tipo: str
    url: str = None


class Extra(NamedTuple):
    junio: float
    diciembre: float


class Complemento(NamedTuple):
    especifico: float
    destino: float


class Sueldo(NamedTuple):
    base: float
    extra: Extra
    complemento: Complemento
    trienios: float


class Contacto(NamedTuple):
    correo: str
    telefono: str
    direccion: str
    planta: str
    despacho: str


class Puesto(NamedTuple):
    denominacion: str
    nrp: str
    grupo: str
    nivel: int
    sueldo: Sueldo
    contacto: Contacto
    inicio: date


class Menu(NamedTuple):
    fecha: date
    precio: float
    primeros: Tuple[str, ...]
    segundos: Tuple[str, ...]
    carta: str


class Novedad(NamedTuple):
    fecha: date
    titulo: str
    url: str
    descripcion: str
    tipo: str
    html: str


class TreeUrl(NamedTuple):
    txt: str
    url: str
    children: Tuple['TreeUrl', ...] = ()


class Fichaje(NamedTuple):
    fecha: date
    marcajes: Tuple[HM, ...]
    obs: str
    total: HM
    teorico: HM
    saldo: HM