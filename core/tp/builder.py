from typing import _GenericAlias, Dict, Callable, Union, Any, Set, Tuple, List, NamedTuple, Type, get_type_hints, get_origin, get_args
from functools import cache, cached_property
import re
from datetime import date, datetime
from .util import TP, isNamedTuple, getNamedTupleClass, getClass, isClassNamedTuple, isObjectNamedTuple
    

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
    cls = getClass(cls)
    if cls is None:
        return {}
    tps: Dict[str, Union[Type, _GenericAlias]] = {}
    for k, tk in get_type_hints(cls).items():
        if isinstance(tk, type):
            tps[k] = tk
        elif get_origin(tk) in (list, tuple, dict):
            tps[k] = tk
    return tps


def __get_type_or_alias(obj: Any):
    if isinstance(obj, (type, _GenericAlias)):
        return obj
    if get_origin(obj) in (list, tuple, dict):
        return obj
    cls = getClass(obj)
    if isinstance(cls, (type, _GenericAlias)):
        return cls
    if get_origin(cls) in (list, tuple, dict):
        return cls
    return None

@cache
def __get_builder(obj: Any):
    cls = __get_type_or_alias(obj)
    if cls is None:
        return

    __build = getattr(cls, "build", None)
    if callable(__build):
        return __build

    if cls == date:
        return __build_date

    if cls == datetime:
        return __build_datetime

    ntcls = getNamedTupleClass(cls)
    if ntcls is not None:
        return builder(ntcls)

    origin = get_origin(cls)
    args = get_args(cls)
    if len(args) == 0:
        return None

    if origin in (Dict, dict):
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

    if origin not in (Set, Tuple, List, set, tuple, list):
        return lambda x: x
    ebuild = __get_builder(args[0])
    if not callable(ebuild):
        return None
    ocls = origin if isinstance(origin, type) else origin.__class__
    mpbuid = lambda x: ocls(map(ebuild, x))
    return mpbuid


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
    cls = getNamedTupleClass(cls)
    if cls is None:
        raise ValueError(f'{cls} Type must be a NamedTuple')
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


def builder(cls: Type[TP]) -> Callable[..., TP]:
    cls = getNamedTupleClass(cls)
    if cls is None:
        raise ValueError(f'{cls} Type must be a NamedTuple')

    def __cls_build(*args, **kwargs) -> TP:
        return build(cls, *args, **kwargs)

    return __cls_build
