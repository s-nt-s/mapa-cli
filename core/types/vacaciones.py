from typing import NamedTuple


class Vacaciones(NamedTuple):
    fecha: str
    dias: int
    tipo: str
    url: str = None

    def merge(self, **kwarg):
        return Vacaciones(**{**self._asdict(), **kwarg})

    def get(self, field):
        return self._asdict().get(field)

    @classmethod
    def build(cls, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if k in cls._fields}
        return cls(**kwargs)
