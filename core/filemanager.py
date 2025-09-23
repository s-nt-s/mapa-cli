import json
import logging
import pickle
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from os import W_OK, access, makedirs
from os.path import dirname, realpath
from pathlib import Path
from tempfile import gettempdir
from typing import Union
from core.tunnel import SSHTunnel

import pdftotext
import yaml

from . import tp as tp

logger = logging.getLogger(__name__)


class CustomEncoder(json.JSONEncoder):

    def default(self, o):
        new_obj = CustomEncoder.parse(o)
        if new_obj is None:
            return super().default(o)
        return new_obj

    @classmethod
    def __has_func(cls, o, func):
        return callable(getattr(o, func, None))

    @classmethod
    def parse(cls, o):
        if cls.__has_func(o, "_to_json"):
            return o._to_json()
        if isinstance(o, (datetime, date)):
            return o.__str__()
        if isinstance(o, tuple) and hasattr(o, '_fields'):
            return o._asdict()
        if is_dataclass(o):
            return asdict(o)

    @classmethod
    def prepare(cls, o):
        new_obj = cls.parse(o)
        if new_obj is not None:
            o = new_obj
        if isinstance(o, dict):
            return {k: cls.prepare(v) for k, v in o.items()}
        if isinstance(o, set):
            try:
                o = tuple(sorted(o))
            except TypeError:
                pass
        if isinstance(o, (list, tuple)):
            return list(map(cls.prepare, o))
        return o

    def encode(self, o):
        return super().encode(CustomEncoder.prepare(o))


class FileManager:
    """
    Da funcionalidad de lectura (load) y escritura (dump) de ficheros
    sin importar el entorno de ejecución.
    Para ello transforma las rutas según necesario para poder escribir
    en directorios donde si haya permiso de escritura.
    """
    FM = None

    @staticmethod
    def get():
        """
        Devuelve una unica instancia de FileManager, con la configuracion por defecto
        """
        if FileManager.FM is None:
            FileManager.FM = FileManager()
        return FileManager.FM

    def __init__(self, root: Union[str, None] = None, scope: str = 'py.filemanager'):
        """
        Parameters
        ----------
        root: str | Path
            por defecto es la raiz del proyecto, es decir, el directorio ../.. al de este fichero
            se usa para interpretar que las rutas relativas son relativas a este directorio root
        scope: str
            nombre de subcarpeta a usar en tmp
        """
        if root is None:
            root = Path(dirname(realpath(__file__))).parent
        elif isinstance(root, str):
            root = Path(root)

        self.root: Path = root
        self.temp: Path = Path(gettempdir()) / scope

        for label, path in {
            "raiz": self.root,
            "temp": self.temp,
        }.items():
            wr = self.is_writeable(path)
            logger.info("Directorio %s %s [%s]",
                        label, path, "W_OK" if wr else "W_KO")

    @property
    def temp_root(self) -> Path:
        """
        Ruta donde se guardaran los ficheros que no se puedan crear en root
        """
        return self.temp / 'root'

    def is_writeable(self, path: Union[Path, str]) -> bool:
        """
        Determina si se podra escribir un fichero en la ruta pasada por parametro
        """
        if isinstance(path, str):
            path = Path(path)
        while not (path.exists() or path.parent == path):
            path = path.parent
        return access(path, W_OK)

    def _resolve_path(self, file: Union[Path, str], wr: bool = False) -> Path:
        """
        Si es una ruta absoluta se devuelve tal cual
        Si es una ruta relativa y se requiere escribir en ella:
            * se devuelve bajo la ruta root si se puede escribir en ella
            * y si no se devuelve sobre la ruta temp
        Si es una ruta relativa y no se requiere escribir en ella:
            * se devuelve bajo la temp si el fichero existe
            * y si no se devuelve sobre la ruta root

        Parameters
        ----------
        file: str | Path
            Ruta a resolver
        wr: bool
            Indica si la ruta va a ser utilizada para escribir en ella o no
        """

        if isinstance(file, str):
            file = Path(file)

        if str(file).startswith("~"):
            file = file.expanduser()

        if file.is_absolute():
            return file

        temp_file = self.temp_root.joinpath(file)
        root_file = self.root.joinpath(file)
        if wr:
            if self.is_writeable(root_file):
                return root_file
            return temp_file

        if temp_file.exists():
            # Devolvemos el temporal porque
            # si el fichero temporal existe es que anteriormente se escribio en él,
            # si se escribio en el temporal es porque en el raiz no se pudo
            # por lo tanto el temporal es más actual que el que esta en el raiz
            return temp_file

        return root_file

    def resolve_path(self, file: Union[Path, str], wr=False, **kwargs) -> Path:
        """
        Ver documentación _resolve_path
        """
        path = self._resolve_path(file, **kwargs)
        if file != path and not (self.root.joinpath(file) == path):
            logger.info("[%s] %s -> %s", "RW"[int(wr)], file, path)
        return path

    def normalize_ext(self, ext: str) -> str:
        """
        Normaliza extensiones para identificar el tipo de fichero en base a la extensión
        """
        ext = ext.lstrip(".")
        ext = ext.lower()
        return {
            "js": "txt",
            "yml": "yaml",
            "sql": "txt",
            "ics": "txt"
        }.get(ext, ext)

    def exist(self, file: Union[Path, str]):
        return self.resolve_path(file).exists()

    def remove(self, file: Union[Path, str]):
        file = self.resolve_path(file)
        if file.exists():
            file.unlink()

    def load(self, file: Union[Path, str], *args, **kwargs):
        """
        Lee un fichero en funcion de su extension
        Para que haya soporte para esa extension ha de existir una funcion load_extension
        """
        file = self.resolve_path(file)

        ext = self.normalize_ext(file.suffix)

        load_fl = getattr(self, "_load_" + ext, None)
        if load_fl is None:
            raise Exception(
                "No existe metodo para leer ficheros {} [{}]".format(ext, file.name))

        return load_fl(file, *args, **kwargs)

    def dump(self, file: Union[Path, str], obj, *args, **kwargs):
        """
        Guarda un fichero en función de su extension
        Para que haya soporte para esa extension ha de existir una función dump_extension
        """
        file = self.resolve_path(file, wr=True)
        makedirs(file.parent, exist_ok=True)

        if len(args) == 0 and len(kwargs) == 0 and isinstance(obj, bytes):
            with open(file, "wb") as fl:
                fl.write(obj)
            return

        ext = self.normalize_ext(file.suffix)
        dump_fl = getattr(self, "_dump_" + ext, None)
        if dump_fl is None:
            raise Exception(f"No existe método para guardar ficheros {ext} [{file.name}]")

        dump_fl(file, obj, *args, **kwargs)

    def _load_json(self, file: Path, *args, **kwargs):
        with open(file, "r") as f:
            return json.load(f, *args, **kwargs)

    def _dump_json(self, file: Path, obj, *args, indent=2, **kwargs):
        obj = CustomEncoder.prepare(obj)
        with open(file, "w") as f:
            json.dump(obj, f, *args, indent=indent, cls=CustomEncoder, **kwargs)

    def _dump_csv(self, file: Path, obj, *args, **kwargs):
        obj.to_csv(file, *args, **kwargs)

    def _load_yaml(self, file: Path, *args, Loader=yaml.FullLoader, **kwargs):
        with open(file, "r") as f:
            data = list(yaml.load_all(f, *args, Loader=Loader, **kwargs))
            if len(data) == 1:
                data = data[0]
            return data

    def _load_txt(self, file: Path, *args, **kwargs):
        with open(file, "r") as f:
            txt = f.read()
            if args or kwargs:
                txt = txt.format(*args, **kwargs)
            return txt

    def _dump_txt(self, file: Path, txt, *args, **kwargs):
        if args or kwargs:
            txt = txt.format(*args, **kwargs)
        with open(file, "w") as f:
            f.write(txt)

    def _load_pdf(self, file: Path, *args, as_list=False, **kwargs):
        with open(file, 'rb') as fl:
            pdf = pdftotext.PDF(fl, **kwargs)
            if as_list:
                return list(pdf)
            return "\n".join(pdf)

    def _load_pickle(self, file: Path, *args, **kwargs):
        with open(file, "rb") as f:
            return pickle.load(f)

    def _dump_pickle(self, file: Path, obj, *args, **kwargs):
        with open(file, "wb") as f:
            pickle.dump(obj, f)


CNF = tp.builder(tp.Config)(FileManager.get().load("config.yml"))
if CNF.firefox:
    CNF = CNF._replace(firefox=str(FileManager.get().resolve_path(CNF.firefox)))
if CNF.tunnel and CNF.tunnel.remote:
    SSHTunnel.init(
        *CNF.tunnel.remote,
        ssh_alias=CNF.tunnel.ssh_alias,
        ssh_config=CNF.tunnel.ssh_config,
        ssh_private_key_password=CNF.tunnel.ssh_private_key_password
    )

# Mejoras dinámicas en la documentación
FileManager.resolve_path.__doc__ = FileManager._resolve_path.__doc__
for mth in dir(FileManager):
    slp = mth.split("_", 1)
    if len(slp) == 2 and slp[0] in ("load", "dump"):
        key, ext = slp
        mth = getattr(FileManager, mth)
        if mth.__doc__ is None:
            if key == "load":
                mth.__doc__ = "Lee "
            else:
                mth.__doc__ = "Guarda "
            mth.__doc__ = mth.__doc__ + "un fichero de tipo " + ext

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    f = FileManager()
