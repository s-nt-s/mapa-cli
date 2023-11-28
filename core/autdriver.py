from .web import Driver
from bs4 import Tag
from .filemanager import CNF
from urllib.parse import urlparse
from selenium.common.exceptions import TimeoutException
import time
import re

NEED_AUTENTICA = (
    'trama.administracionelectronica.gob.es',
    'www.funciona.es'
)
NEED_INSIST = (
    'https://www.funciona.es/servinomina/action/ErrorAcceso.do',
)
IN_LOGIN = (
    'https://trama.administracionelectronica.gob.es/portal/loginTrama.html',
    'https://trama.administracionelectronica.gob.es/portal/loginUrlAutentica.html'
)


class AutenticaException(Exception):
    pass


class AutenticaWeakPassword(AutenticaException):
    pass


class AutenticaDown(AutenticaException):
    pass


def mk_re(text: str):
    re_text = []
    for word in text.strip().split():
        re_text.append(re.escape(word))
    return r"\s+".join(re_text)


re_autentica_error = re.compile(
    r"\s*("+mk_re("Sólo es posible acceder a esta aplicación con una contraseña fuerte")+r")\s*\.?\s*",
    re.IGNORECASE)

re_autentica_down = re.compile(
    r".*("+mk_re("Autentica no responde, puede que este caída")+r").*",
    re.IGNORECASE | re.DOTALL)


def is_error_box(n, reg_exp):
    if not isinstance(n, Tag):
        return False
    if n.name != "div":
        return False
    if not n.attrs.get("class"):
        return False
    if "error-box" not in n.attrs['class']:
        return False
    text = n.get_text().strip()
    if len(text) == 0:
        return False
    if reg_exp.match(text):
        return True
    return False


class AutDriver(Driver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._in_autentica = False

    @property
    def in_autentica(self):
        for lk in IN_LOGIN:
            if self.current_url.startswith(lk):
                self._in_autentica = False
                return False
        if self._in_autentica:
            return True
        return False

    @in_autentica.setter
    def in_autentica(self, b):
        self._in_autentica = b

    def autentica_login(self):
        if self.in_autentica:
            return
        time.sleep(2)
        self.__raise_if_find(AutenticaDown, lambda d: is_error_box(d, re_autentica_down))
        if self.get_soup().select_one("#username") is None:
            self.click("//a")
        try:
            self.val("username", CNF.autentica.user, seconds=5)
            self.val("password", CNF.autentica.pssw, seconds=5)
            self.click("submitAutentica", seconds=5)
        except TimeoutException:
            pass
        try:
            self.click("grabar", seconds=5)
            self.click("modal-btn-si", seconds=5)
        except TimeoutException:
            pass
        time.sleep(5)
        self.__raise_if_find(AutenticaWeakPassword, "p", text=re_autentica_error)
        self.in_autentica = True

    def __raise_if_find(self, exp, *args, **kwargs):
        error = self.get_soup().find(*args, **kwargs)
        if error:
            msg = re.sub(r"\s+", " ", error.get_text()).strip()
            raise exp(msg)

    def get(self, url, *args, **kwargs):
        super().get(url, *args, **kwargs)
        dom = urlparse(url).netloc.lower()
        if dom in NEED_AUTENTICA:
            while not self.in_autentica:
                self.autentica_login()
        if self.current_url in NEED_INSIST:
            super().get(url, *args, **kwargs)
