from munch import Munch
from math import modf
from datetime import date
from .cache import Cache
import re


class HM:

    def __init__(self, hm):
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

    def __sub__(self, ot):
        return HM(self.minutos - ot.minutos)

    def __add__(self, ot):
        return HM(self.minutos + ot.minutos)

    def __div__(self, ot):
        m1 = min(self.minutos, ot.minutos)
        m2 = max(self.minutos, ot.minutos)
        minutos = int(m2 / m1)
        return HM(minutos)

    def __lt__(self, ot):
        return self.minutos < ot.minutos

    def __le__(self, ot):
        return self.minutos <= ot.minutos

    def __eq__(self, ot):
        return self.minutos == ot.minutos

    def __ne__(self, ot):
        return self.minutos != ot.minutos

    def __gt__(self, ot):
        return self.minutos > ot.minutos

    def __ge__(self, ot):
        return self.minutos >= ot.minutos

    def mul(self, ot):
        minutos = self.minutos * ot
        return HM(minutos)

    def div(self, ot):
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
    def read(self, *args, **kvargs):
        d = super().read(*args, **kvargs)
        if d is None:
            return None
        for k, v in list(d.items()):
            if isinstance(v, str):
                if re.match(r"[\-+]?\d+:\d+(:\d+)?", v):
                    d[k] = HM(v)
                elif re.match(r"\d+-\d+-\d+", v):
                    d[k] = date(*map(int, v.split("-")))
        d = GesperIH(d)
        return d
