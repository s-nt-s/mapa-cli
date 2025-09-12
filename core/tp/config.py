from typing import NamedTuple, Tuple, Union, Optional
from datetime import date


class HostPort(NamedTuple):
    host: str
    port: int

    def __str__(self):
        return f"{self.host}:{self.port}"

class UserPass(NamedTuple):
    user: str
    pssw: str


class Xmpp(NamedTuple):
    me: str
    user: str
    pssw: str
    LOG: str
    address: Union[Tuple[str, int], None] = None
    proxy: str = None


class Tunnel(NamedTuple):
    ssh_alias: str
    remote: Tuple[HostPort, ...]
    ssh_config: str = "~/.ssh/config"


class FakeNomina(NamedTuple):
    neto: float
    year: int
    mes: int
    bruto: float = None
    irpf: float = None


class SMTP(NamedTuple):
    host: str
    port: int
    user: str
    pasw: str
    default_to: str


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
    firefox: str = None
    festivos: Tuple[date] = tuple()
    tmp_nominas: Tuple[FakeNomina, ...] = tuple()
    smtp: SMTP = None
    tunnel: Tunnel = None
