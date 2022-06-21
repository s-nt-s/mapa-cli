from .web import Driver
from .filemanager import CNF
from urllib.parse import urlparse
import time
import re

NEED_AUTENTICA = (
    'trama.administracionelectronica.gob.es',
    'www.funciona.es'
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

    def autentica_login(self):
        if self._in_autentica:
            return
        time.sleep(2)
        if self.get_soup().select_one("#username") is None:
            self.click("//a")
        self.val("username", CNF.autentica.user)
        self.val("password", CNF.autentica.pssw)
        self.click("submitAutentica")
        time.sleep(2)
        if self.get_soup().select_one("div.botonera #grabar"):
            self.click("grabar")
            time.sleep(2)
            self.click("modal-btn-si")
            time.sleep(2)
        error = self.get_soup().find("p", text=re_autentica_error)
        if error:
            raise AutenticaWeakPassword(error.get_text().strip())
        self._in_autentica = True

    def get(self, url, *args, **kwargs):
        super().get(url, *args, **kwargs)
        dom = urlparse(url).netloc.lower()
        if dom in NEED_AUTENTICA:
            self.autentica_login()

