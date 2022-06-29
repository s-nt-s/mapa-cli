import functools
from os.path import isfile
from os import stat
import time
from .filemanager import FileManager
from munch import Munch
import logging

logger = logging.getLogger(__name__)

class Cache:
    def __init__(self, file, *args, maxOld=30, json_default=None, **kvargs):
        self.file = file
        self.data = {}
        self.func = None
        self._maxOld = maxOld
        self.slf = None
        self.json_default = json_default

    @property
    def maxOld(self):
        if self._maxOld is not None:
            return time.time() - (self._maxOld * 86400)

    def get_file_name(self, *args, **kvargs):
        return self.file.format(*args, **kvargs)

    def read(self, file, *args, **kvargs):
        logger.debug("LOAD "+file)
        return FileManager.get().load(file)

    def save(self, file, data, *args, **kvargs):
        logger.debug("SAVE "+file)
        if self.json_default is not None:
            return FileManager.get().dump(file, data, default=self.json_default)
        return FileManager.get().dump(file, data)

    def tooOld(self, fl):
        if not isfile(fl):
            return True
        if self.maxOld is None:
            return False
        if stat(fl).st_mtime < self.maxOld:
            return True
        return False

    def callCache(self, slf, *args, **kvargs):
        self.slf = slf
        fl = self.get_file_name(*args, **kvargs)
        if fl is not None and not self.tooOld(fl):
            data = self.read(fl, *args, **kvargs)
            if data is not None:
                return data
        data = self.func(slf, *args, **kvargs)
        if fl is not None:
            self.save(fl, data, *args, **kvargs)
        return data

    def __call__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        return lambda *args, **kvargs: self.callCache(*args, **kvargs)

class MunchCache(Cache):
    def read(self, *args, **kvargs):
        d = super().read(*args, **kvargs)
        if isinstance(d, dict) or (isinstance(d, list) and len(d)>0 and isinstance(d[0], dict)):
            return Munch.fromDict(d)
        return d