from munch import Munch
from math import modf, ceil, floor
from datetime import date
from .cache import Cache
import re
from typing import Union, Dict


class HM:

    def __init__(self, hm: Union[str, int, float]):
        if isinstance(hm, str):
            signo = True
            if hm[0] in ('-', '+'):
                signo = hm[0] == '+'
                hm = hm[1:]
            h, m, s = "0 0 0".split()
            shm = hm.split(":")
            if len(shm) == 2:
                h, m = shm
            elif len(shm) == 3:
                h, m, s = shm
            else:
                raise ValueError(hm)
            h = int(h.replace(".", ""))
            m = int(m.replace(".", ""))
            s = int(s.replace(".", ""))
            m = (h * 60) + m
            if s > 0:
                m = m + (s / 60)
            if signo is False:
                m = -m
            self.minutos = m
        elif isinstance(hm, (int, float)):
            self.minutos = hm
        else:
            raise TypeError(hm)
        
    def trunc(self):
        if self.minutos < 0:
            return HM(ceil(self.minutos))
        return HM(floor(self.minutos))

    @classmethod
    def intervalo(cls, *args):
        args = sorted(args)
        intervalo = args[-1] - args[0]
        for i in range(1, len(args) - 1, 2):
            intervalo = intervalo - (args[i + 1] - args[i])
        return intervalo

    def __str__(self):
        sg, hm = modf(abs(self.minutos))
        h = int(hm / 60)
        m = hm - (h * 60)
        s = round(sg * (100 / 60))
        hm = "%02d:%02d" % (h, m)
        if self.minutos < 0:
            return "-" + hm
        return hm

    def __sub__(self, ot: "HM"):
        return HM(self.minutos - ot.minutos)

    def __add__(self, ot: "HM"):
        return HM(self.minutos + ot.minutos)

    def __div__(self, ot: "HM"):
        m1 = min(self.minutos, ot.minutos)
        m2 = max(self.minutos, ot.minutos)
        minutos = int(m2 / m1)
        return HM(minutos)

    def __lt__(self, ot: "HM"):
        return self.minutos < ot.minutos

    def __le__(self, ot: "HM"):
        return self.minutos <= ot.minutos

    def __eq__(self, ot: "HM"):
        return self.minutos == ot.minutos

    def __ne__(self, ot: "HM"):
        return self.minutos != ot.minutos

    def __gt__(self, ot: "HM"):
        return self.minutos > ot.minutos

    def __ge__(self, ot: "HM"):
        return self.minutos >= ot.minutos

    def __hash__(self):
        return self.minutos

    def mul(self, ot: "HM"):
        minutos = self.minutos * ot
        return HM(minutos)

    def div(self, ot: "HM"):
        minutos = int(self.minutos / ot)
        return HM(minutos)


class GesperIH(Munch):
    def __init__(self, *args, **karg):
        super().__init__(*args, **karg)

    @property
    def computables(self):
        return self.teoricas - self.festivos - self.vacaciones - self.fiestas_patronales

    @property
    def sin_vacaciones(self):
        return self.teoricas - self.festivos - self.fiestas_patronales


class GesperIHCache(Cache):
    def read(self, *args, **kwargs):
        d = super().read(*args, **kwargs)
        if not isinstance(d, dict):
            return None
        for k, v in list(d.items()):
            if isinstance(v, str):
                if re.match(r"[\-+]?\d+:\d+(:\d+)?", v):
                    d[k] = HM(v)
                elif re.match(r"\d+-\d+-\d+", v):
                    d[k] = date(*map(int, v.split("-")))
        d = GesperIH(d)
        return d


def mk_parse(v: Union[str, list, dict]):
    if isinstance(v, dict):
        for k, x in list(v.items()):
            if isinstance(x, (str, list)):
                v[k] = mk_parse(x)
        return v
    if isinstance(v, list):
        return [mk_parse(i) for i in v]
    if re.match(r"[\-+]?\d+:\d+(:\d+)?", v):
        return HM(v)
    if re.match(r"\d+-\d+-\d+", v):
        return date(*map(int, v.split("-")))
    return v


class HMmunch(Munch):
    def _parse(self):
        mk_parse(self)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parse()


class HMCache(Cache):
    def read(self, *args, **kwargs):
        d = super().read(*args, **kwargs)
        if d is None:
            return None
        d = mk_parse(d)
        return Munch.fromDict(d)
