from typing import Dict, Callable, TypeVar, Set, Tuple, List, NamedTuple, Type, get_type_hints, get_origin, get_args
from functools import cache
import re
from datetime import date, datetime

TP = TypeVar('TP', bound=NamedTuple)


def is_namedtuple(tp):
    if not isinstance(tp, type):
        return False
    return issubclass(tp, NamedTuple)


def __build_date(x) -> date:
    if x is None:
        return None
    if isinstance(x, date):
        return x
    if not isinstance(x, str):
        raise ValueError(x)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", x):
        raise ValueError(x)
    return date(*map(int, x.split("-")))


def __build_datetime(x) -> datetime:
    if x is None:
        return None
    if isinstance(x, datetime):
        return x
    if not isinstance(x, str):
        raise ValueError(x)
    if not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", x):
        raise ValueError(x)
    return datetime(*map(int, re.split(r"\D", x)))

@cache
def __get_types(cls: Type):
    if not isinstance(cls, type):
        return {}
    tps: Dict[str, Type] = {}
    for k, tk in get_type_hints(cls).items():
        if isinstance(tk, type):
            tps[k] = tk
    return tps


@cache
def __get_builder(cls: Type):
    if not isinstance(cls, type):
        return None

    __build = getattr(cls, "build", None)
    if callable(__build):
        return __build

    if cls == date:
        return __build_date

    if cls == datetime:
        return __build_datetime

    if issubclass(cls, NamedTuple):
        return builder(cls.__class__)

    origin = get_origin(cls)
    args = get_args(cls)
    if len(args) == 0:
        return None

    if origin == Dict:
        if len(args) != 2:
            return None
        btk, btv = map(__get_builder, args)
        if not callable(btk) and not callable(btv):
            return None
        if not callable(btk):
            return lambda x: {k: btv(v) for k, v in x.items()}
        if not callable(btv):
            return lambda x: {btk(k): v for k, v in x.items()}
        return lambda x: {btk(k): btv(v) for k, v in x.items()}

    if origin not in (Set, Tuple, List):
        return lambda x: x
    ebuild = __get_builder(args[0])
    if not callable(ebuild):
        return None
    return lambda x: origin.__class__(map(ebuild, x))


def __get_obj(*args, **kwargs):
    if len(args) == 0:
        return kwargs
    if len(args) > 1:
        raise ValueError('Only one positional argument is allowed')
    if kwargs:
        raise ValueError('Positional argument is not allowed with keyword arguments')
    if not isinstance(args[0], dict):
        raise ValueError('Positional argument must be a dictionary')
    return args[0]


def build(cls: Type[TP], *args, **kwargs) -> TP:
    if not issubclass(cls, NamedTuple):
        raise ValueError('Type must be a NamedTuple')
    __build = getattr(cls, "build", None)
    if callable(__build):
        return __build
    tps = __get_types(cls)
    obj = {}
    for k, v in __get_obj(*args, **kwargs).items():
        if k in cls._fields:
            bld = __get_builder(tps.get(k))
            obj[k] = bld(v) if v is not None and callable(bld) else v
    return cls(**obj)

