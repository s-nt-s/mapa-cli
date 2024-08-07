from typing import NamedTuple, TypeVar, Type, Callable
from .builder import build

TP = TypeVar('TP', bound=NamedTuple)


def builder(cls: Type[TP]) -> Callable[..., TP]:
    if not issubclass(cls, NamedTuple):
        raise ValueError('Type must be a NamedTuple')

    def __cls_build(*args, **kwargs) -> TP:
        return build(cls, *args, **kwargs)

    return __cls_build


def merge(tp: TP, **kwargs) -> TP:
    return tp.__class__(**{**tp._asdict(), **kwargs})


def get(tp: TP, field):
    dct = tp._asdict()
    if isinstance(dct, dict):
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

