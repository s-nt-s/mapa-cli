from typing import NamedTuple


class Festivo(NamedTuple):
    fecha: str
    dia: str
    tipo: str
    localidad: str
    provincia: str
    comunidad: str
    pais: str
    url: str = None

    def merge(self, **kwarg):
        return Festivo(**{**self._asdict(), **kwarg})

    def get(self, field):
        return self._asdict().get(field)

    @classmethod
    def build(cls, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if k in cls._fields}
        return cls(**kwargs)
