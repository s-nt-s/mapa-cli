import re
import time
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
import sys
from urllib import parse

re_sp = re.compile(r"\s+")
re_emb = re.compile(r"^image/[^;]+;base64,.*", re.IGNORECASE)

def get_query(url):
    q = parse.urlsplit(url)
    q = parse.parse_qsl(q.query)
    q = dict(q)
    return q

def iterhref(soup):
    """Recorre los atriburos href o src de los tags"""
    for n in soup.findAll(["img", "form", "a", "iframe", "frame", "link", "script"]):
        attr = "href" if n.name in ("a", "link") else "src"
        if n.name == "form":
            attr = "action"
        val = n.attrs.get(attr)
        if val is None or re_emb.search(val):
            continue
        if not(val.startswith("#") or val.startswith("javascript:")):
            yield n, attr, val

def buildSoup(root, source, parser="lxml"):
    soup = BeautifulSoup(source, parser)
    for n, attr, val in iterhref(soup):
        val = urljoin(root, val)
        val = val.replace(":443/", "/")
        val = val.replace("/default.aspx", "")
        n.attrs[attr] = val
    return soup


default_profile = {
    "browser.tabs.drawInTitlebar": True,
    "browser.uidensity": 1,
}


class FF:
    def __init__(self, visible=False, wait=60):
        self._driver = None
        self.visible = visible
        self._wait = wait

    @property
    def driver(self):
        if self._driver is None:
            options = Options()
            options.headless = not self.visible
            profile = webdriver.FirefoxProfile()
            for k, v in default_profile.items():
                profile.set_preference(k, v)
                profile.DEFAULT_PREFERENCES['frozen'][k] = v
            profile.update_preferences()
            self._driver = webdriver.Firefox(
                options=options, firefox_profile=profile)
            self._driver.maximize_window()
            self._driver.implicitly_wait(5)
        return self._driver

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    def reintentar(self, intentos, sleep=1):
        if intentos > 50:
            return False, sleep
        if intentos % 3 == 0:
            sleep = int(sleep / 3)
            self.close()
        else:
            sleep = sleep*2
        if intentos > 20:
            time.sleep(10)
        time.sleep(2 * (int(intentos/10)+1))
        return True, sleep

    def get(self, url):
        self._soup = None
        self.driver.get(url)

    def get_soup(self):
        if self._driver is None:
            return None
        return buildSoup(self._driver.current_url, self._driver.page_source)

    @property
    def source(self):
        if self._driver is None:
            return None
        return self._driver.page_source

    def wait(self, id, seconds=None):
        if isinstance(id, (int, float)):
            time.sleep(id)
            return
        my_by = By.ID
        seconds = seconds or self._wait
        if id.startswith("//"):
            my_by = By.XPATH
        wait = WebDriverWait(self._driver, seconds)
        wait.until(ec.visibility_of_element_located((my_by, id)))
        if id.startswith("//"):
            return self._driver.find_element_by_xpath(id)
        return self._driver.find_element_by_id(id)

    def val(self, id, val=None):
        if self._driver is None:
            return None
        n = self.wait(id)
        if val is not None:
            n.clear()
            n.send_keys(val)
        return n.text

    def click(self, id):
        if self._driver is None:
            return None
        n = self.wait(id)
        n.click()

    def get_session(self):
        if self._driver is None:
            return None
        s = requests.Session()
        for cookie in self._driver.get_cookies():
            s.cookies.set(cookie['name'], cookie['value'])
        h = self._driver.requests[-1]
        s.headers = h.headers
        return s

    def pass_cookies(self, session=None):
        if session is None:
            session = requests.Session()
        for cookie in self._driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'])
        return session


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit()
    url = sys.argv[1]
    ff = FF()
    ff.get(url)
    print(ff.source)
