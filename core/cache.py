import functools
from os.path import isfile
from os import stat
import time
from .filemanager import FileManager


class Cache:
    def __init__(self, file, *args, maxOld=30, **kvargs):
        self.file = file
        self.data = {}
        self.func = None
        self.maxOld = maxOld
        self.slf = None
        if maxOld is not None:
            self.maxOld = time.time() - (maxOld * 86400)

    def get_file_name(self, *args, **kvargs):
        return self.file.format(*args, **kvargs)

    def read(self, file, *args, **kvargs):
        return FileManager.get().load(file)

    def save(self, file, data, *args, **kvargs):
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



