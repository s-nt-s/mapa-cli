from typing import NamedTuple


class Expediente(NamedTuple):
    expediente: str
    fecha: str
    tipo: str
    estado: str
    url: str = None

    def merge(self, **kwarg):
        return Expediente(**{**self._asdict(), **kwarg})

    def get(self, field):
        return self._asdict().get(field)

    @classmethod
    def build(cls, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if k in cls._fields}
        return cls(**kwargs)
