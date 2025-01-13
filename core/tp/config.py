from typing import NamedTuple, Tuple, Union
from datetime import date


class UserPass(NamedTuple):
    user: str
    pssw: str


class Xmpp(NamedTuple):
    me: str
    user: str
    pssw: str
    LOG: str
    address: Union[Tuple[str, int], None] = None


class FakeNomina(NamedTuple):
    neto: float
    year: int
    mes: int
    bruto: float = None
    irpf: float = None


class Config(NamedTuple):
    vpn: bool
    mapa: UserPass
    gesper: UserPass
    autentica: UserPass
    nominas: str
    expediente: str
    retribuciones: str
    informe_horas: str
    xmpp: Xmpp
    sede: str
    proxy: str = None
    festivos: Tuple[date] = tuple()
    tmp_nominas: Tuple[FakeNomina, ...] = tuple()
