import functools
from os import stat
import time
from .filemanager import FileManager
import logging

logger = logging.getLogger(__name__)
FM = FileManager.get()


class Cache:
    def __init__(self, file: str, *args, maxOld=30, json_hook=None, keep_if_none=False, **kwargs):
        self.file = file
        self.data = {}
        self.func = None
        self.slf = None
        self.json_hook = json_hook
        self.keep_if_none = keep_if_none
        self.__maxOld = maxOld

    @property
    def maxOld(self):
        if self.__maxOld is not None:
            return time.time() - (self.__maxOld * 86400)

    def get_file_name(self, *args, **kwargs):
        return self.file.format(*args, **kwargs)

    def read(self, file: str, *args, **kwargs):
        logger.debug("LOAD "+file)
        if self.json_hook is not None:
            return FM.load(file, object_hook=self.json_hook)
        return FM.load(file)

    def save(self, file: str, data, *args, **kwargs):
        logger.debug("SAVE "+file)
        return FM.dump(file, data)

    def tooOld(self, fl: str):
        if not FM.exist(fl):
            return True
        if self.maxOld is None:
            return False
        if stat(fl).st_mtime < self.maxOld:
            return True
        return False

    def callCache(self, slf, *args, **kwargs):
        self.slf = slf
        fl = self.get_file_name(*args, **kwargs)
        if fl is not None and not self.tooOld(fl):
            data = self.read(fl, *args, **kwargs)
            if data is not None:
                return data
        data = self.func(slf, *args, **kwargs)
        if self.keep_if_none and data is None and fl is not None:
            return self.read(fl, *args, **kwargs)
        if fl is not None:
            self.save(fl, data, *args, **kwargs)
        return data

    def __call__(self, func):
        def callCache(*args, **kwargs):
            return self.callCache(*args, **kwargs)
        functools.update_wrapper(callCache, func)
        self.func = func
        setattr(callCache, "__cache_obj__", self)
        return callCache


class TupleCache(Cache):
    def __init__(self, *args, builder=None, **kwargs):
        if not callable(builder):
            raise ValueError('builder is None')
        self.builder = builder
        super().__init__(*args, **kwargs)

    def read(self, file, *args, **kwargs):
        data = super().read(file, *args, **kwargs)
        if isinstance(data, dict):
            return self.builder(data)
        return tuple((self.builder(d) for d in data))

