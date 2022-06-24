from .web import Driver
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
)

class AutenticaWeakPassword(Exception):
    pass

def mk_re(text):
    re_text = []
    for word in text.strip().split():
        re_text.append(re.escape(word))
    return r"\s+".join(re_text)

re_autentica_error = re.compile(
    r"\s*("+mk_re("Sólo es posible acceder a esta aplicación con una contraseña fuerte")+r")\s*\.?\s*",
    re.IGNORECASE)


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
        error = self.get_soup().find("p", text=re_autentica_error)
        if error:
            raise AutenticaWeakPassword(error.get_text().strip())
        self.in_autentica = True

    def get(self, url, *args, **kwargs):
        super().get(url, *args, **kwargs)
        dom = urlparse(url).netloc.lower()
        if dom in NEED_AUTENTICA:
            while not self.in_autentica:
                self.autentica_login()
        if self.current_url in NEED_INSIST:
            super().get(url, *args, **kwargs)


