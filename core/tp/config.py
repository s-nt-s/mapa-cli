from typing import NamedTuple, Tuple, Union


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
    proxy: str
    nominas: str
    expediente: str
    retribuciones: str
    informe_horas: str
    xmpp: Xmpp
    sede: str
    tmp_nominas: Tuple[FakeNomina, ...] = tuple()