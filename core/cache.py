import functools
from os import stat
import time
from .filemanager import FileManager
from munch import Munch
import logging

logger = logging.getLogger(__name__)
FM = FileManager.get()


class Cache:
    def __init__(self, file: str, *args, maxOld=30, json_default=None, json_hook=None, keep_if_none=False, **kwargs):
        self.file = file
        self.data = {}
        self.func = None
        self._maxOld = maxOld
        self.slf = None
        self.json_default = json_default
        self.json_hook = json_hook
        self.keep_if_none = keep_if_none

    @property
    def maxOld(self):
        if self._maxOld is not None:
            return time.time() - (self._maxOld * 86400)

    def get_file_name(self, *args, **kwargs):
        return self.file.format(*args, **kwargs)

    def read(self, file: str, *args, **kwargs):
        logger.debug("LOAD "+file)
        if self.json_hook is not None:
            return FM.load(file, object_hook=self.json_hook)
        return FM.load(file)

    def save(self, file: str, data, *args, **kwargs):
        logger.debug("SAVE "+file)
        if self.json_default is not None:
            return FM.dump(file, data, default=self.json_default)
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
        functools.update_wrapper(self, func)
        self.func = func
        return lambda *args, **kwargs: self.callCache(*args, **kwargs)


class MunchCache(Cache):
    def read(self, *args, **kwargs):
        d = super().read(*args, **kwargs)
        if isinstance(d, dict) or (isinstance(d, list) and len(d)>0 and isinstance(d[0], dict)):
            return Munch.fromDict(d)
        return d
