import re
from math import modf
from typing import NamedTuple, Union


class HM(NamedTuple):
    minutos: int

    @classmethod
    def build(cls, hm: Union[str, int, float, "HM"]):
        if hm is None:
            return None
        if isinstance(hm, cls):
            return hm
        if isinstance(hm, (int, float)):
            return HM(minutos=hm)
        if not isinstance(hm, str):
            raise TypeError(hm)
        m = re.match(r"^(\-|\+)?(\d+):(\d+)(:\d+)?$", hm)
        if m is None:
            raise ValueError(hm)
        signo = m.groups()[0] != '-'
        h, m, s = map(lambda x: int(x.strip(":")) if x else 0, m.groups()[1:])
        m = (h * 60) + m
        if s > 0:
            m = m + (s / 60)
        if signo is False:
            m = -m
        return HM(minutos=m)

    @staticmethod
    def intervalo(*args: "HM") -> "HM":
        args = sorted(args)
        intervalo = args[-1] - args[0]
        for i in range(1, len(args) - 1, 2):
            intervalo = intervalo - (args[i + 1] - args[i])
        return intervalo

    def _to_json(self):
        return str(self)

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

    def mul(self, ot: "HM"):
        minutos = self.minutos * ot
        return HM(minutos)

    def div(self, ot: "HM"):
        minutos = int(self.minutos / ot)
        return HM(minutos)

