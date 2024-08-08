from typing import Union, Any, TypeVar, NamedTuple, Type
from inspect import isclass, isfunction, ismodule

TP = TypeVar('TP', bound=NamedTuple)


def getClass(obj: Any) -> Union[Type[Any], None]:
    if obj is None or isclass(obj):
        return obj
    cls = getattr(obj, '__class__', None)
    if isclass(obj):
        return cls
    return None


def isClassNamedTuple(cls: Type[Any]) -> bool:
    if not isclass(cls):
        return False
    return issubclass(cls, tuple) and hasattr(cls, '_fields')


def isObjectNamedTuple(obj: Any) -> bool:
    if isclass(obj) or isfunction(obj) or ismodule(obj):
        return False
    return isinstance(obj, tuple) and hasattr(obj, '_fields')


def isNamedTuple(o: Union[Any, Type[Any]]) -> bool:
    return isClassNamedTuple(o) or isObjectNamedTuple(o)


def getNamedTupleClass(o: Any) -> Union[Type[NamedTuple], None]:
    cls = getClass(o)
    if isClassNamedTuple(cls):
        return o
