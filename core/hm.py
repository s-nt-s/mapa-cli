from bunch import Bunch


class HM:

    def __init__(self, hm):
        if isinstance(hm, str):
            h, m = hm.split(":")
            self.h = int(h.replace(".", ""))
            self.m = int(m.replace(".", ""))
        else:
            self.h = int(hm / 60)
            self.m = hm - (self.h*60)

    @classmethod
    def intervalo(cls, *args):
        args = sorted(args)
        intervalo = args[-1] - args[0]
        return intervalo

    @classmethod
    def jornadas(cls):
        return (
            HM("07:30"),
            HM("06:30")
        )

    @property
    def minutos(self):
        return (self.h * 60) + self.m

    def __str__(self):
        return "%02d:%02d" % (self.h, self.m)

    def __sub__(self, ot):
        minutos = abs(self.minutos - ot.minutos)
        return HM(minutos)

    def __add__(self, ot):
        minutos = self.minutos + ot.minutos
        return HM(minutos)

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

    @property
    def jornada(self):
        minutos = self.minutos
        for j in HM.jornadas():
            j_m = j.minutos
            if minutos % j_m == 0:
                return int(minutos / j_m), j
        raise Exception("%s no corresponde a ninguna jornada" % self)

    @property
    def safe_jornada(self):
        try:
            _, jornada = self.jornada
            return jornada
        except:
            return None

    @property
    def spanish(self):
        m = self.minutos
        if m % 60 == 0:
            return "%sh" % int(m/60)
        if m > 59:
            return str(self)
        return "%sm" % m

    def enJornadas(self, jornada, maximo=5):
        if jornada is None:
            return self
        md = jornada.div(2)
        if self < (jornada+md):
            return self
        dias = round(self.minutos / jornada.minutos)
        dias = min(maximo, dias)
        if dias < 2:
            return self
        per_day = self.div(dias)
        return str(per_day)+" * "+str(dias)+" = "+str(self)


class IH(Bunch):
    def __init__(self, *args, **karg):
        super().__init__(*args, **karg)

    @property
    def computables(self):
        return self.teoricas - self.festivos - self.vacaciones - self.fiestas_patronales

    @property
    def sin_vacaciones(self):
        return self.teoricas - self.festivos - self.fiestas_patronales
