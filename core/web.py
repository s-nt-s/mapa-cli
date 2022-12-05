import re
import os
import time
from urllib.parse import urljoin, urlsplit, parse_qsl

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (ElementNotInteractableException,
                                        TimeoutException,
                                        WebDriverException,
                                        StaleElementReferenceException,
                                        ElementNotVisibleException)
from selenium.webdriver.chrome.options import Options as CMoptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.firefox.options import Options as FFoptions
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import Select, WebDriverWait

re_sp = re.compile(r"\s+")
re_emb = re.compile(r"^image/[^;]+;base64,.*", re.IGNORECASE)
is_s5h = os.environ.get('http_proxy', "").startswith("socks5h://")
if is_s5h:
    proxy_ip, proxy_port = os.environ['http_proxy'].split("//", 1)[-1].split(":")
    proxy_port = int(proxy_port)
    if not os.environ.get('https_proxy'):
        os.environ['https_proxy'] = os.environ['http_proxy']

default_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0',
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Expires": "Thu, 01 Jan 1970 00:00:00 GMT",
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}


def get_query(url):
    q = urlsplit(url)
    q = parse_qsl(q.query)
    q = dict(q)
    return q


def retry(times, exceptions, sleep=0, skip_in_error=False):
    # https://stackoverflow.com/a/64030200/5204002
    """
    Retry Decorator
    Retries the wrapped function/method `times` times if the exceptions listed
    in ``exceptions`` are thrown
    :param times: The number of times to repeat the wrapped function/method
    :type times: Int
    :param exceptions: Lists of exceptions that trigger a retry attempt
    :type exceptions: Tuple of Exceptions
    """

    def decorator(func):
        def newfn(*args, **kwargs):
            attempt = 0
            last_exc = None
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    attempt += 1
                    time.sleep(sleep)
            if skip_in_error or isinstance(last_exc, SkipRetryException):
                return None
            return func(*args, **kwargs)

        return newfn

    return decorator


class RetryException(Exception):
    pass


class SkipRetryException(Exception):
    pass


def iterhref(soup):
    """Recorre los atriburos href o src de los tags"""
    for n in soup.findAll(["img", "form", "a", "iframe", "frame", "link", "script"]):
        attr = "href" if n.name in ("a", "link") else "src"
        if n.name == "form":
            attr = "action"
        val = n.attrs.get(attr)
        if val is None or re_emb.search(val):
            continue
        if not (val.startswith("#") or val.startswith("javascript:")):
            val = val.replace(":443/", "/")
            val = val.replace("/default.aspx", "")
            yield n, attr, val


def buildSoup(root, source, parser="lxml"):
    soup = BeautifulSoup(source, parser)
    for n, attr, val in iterhref(soup):
        val = urljoin(root, val)
        n.attrs[attr] = val
    return soup


class Web:
    def __init__(self, refer=None, verify=True):
        self.s = requests.Session()
        self.s.headers = default_headers
        self.response = None
        self.soup = None
        self.form = None
        self.refer = refer
        self.verify = verify

    def _get(self, url, allow_redirects=True, auth=None, **kvargs):
        if kvargs:
            return self.s.post(url, data=kvargs, allow_redirects=allow_redirects, verify=self.verify, auth=auth)
        return self.s.get(url, allow_redirects=allow_redirects, verify=self.verify, auth=auth)

    def get(self, url, auth=None, parser="lxml", **kvargs):
        if self.refer:
            self.s.headers.update({'referer': self.refer})
        self.response = self._get(url, auth=auth, **kvargs)
        self.refer = self.response.url
        self.soup = buildSoup(url, self.response.content, parser=parser)
        return self.soup

    def prepare_submit(self, slc, silent_in_fail=False, **kvargs):
        data = {}
        self.form = self.soup.select_one(slc)
        if silent_in_fail and self.form is None:
            return None, None
        for i in self.form.select("input[name]"):
            name = i.attrs["name"]
            data[name] = i.attrs.get("value")
        for i in self.form.select("select[name]"):
            name = i.attrs["name"]
            slc = i.select_one("option[selected]")
            slc = slc.attrs.get("value") if slc else None
            data[name] = slc
        data = {**data, **kvargs}
        action = self.form.attrs.get("action")
        action = action.rstrip() if action else None
        if action is None:
            action = self.response.url
        return action, data

    def submit(self, slc, silent_in_fail=False, **kvargs):
        action, data = self.prepare_submit(
            slc, silent_in_fail=silent_in_fail, **kvargs)
        if silent_in_fail and not action:
            return None
        return self.get(action, **data)

    def val(self, slc):
        n = self.soup.select_one(slc)
        if n is None:
            return None
        v = n.attrs.get("value", n.get_text())
        v = v.strip()
        return v if v else None

    @property
    def url(self):
        if self.response is None:
            return None
        return self.response.url

    def json(self, url, **kvargs):
        r = self._get(url, **kvargs)
        return r.json()

    def resolve(self, url, **kvargs):
        if self.refer:
            self.s.headers.update({'referer': self.refer})
        r = self._get(url, allow_redirects=False, **kvargs)
        if r.status_code in (302, 301):
            return r.headers['location']


FF_DEFAULT_PROFILE = {
    "browser.tabs.drawInTitlebar": True,
    "browser.uidensity": 1,
    "dom.webdriver.enabled": False,
    'network.proxy.type': 1,
}
if is_s5h:
    FF_DEFAULT_PROFILE['network.proxy.socks'] = proxy_ip
    FF_DEFAULT_PROFILE['network.proxy.socks_port'] = proxy_port
    FF_DEFAULT_PROFILE['network.proxy.socks_remote_dns'] = True


class Driver:
    def __init__(self, visible=None, wait=5, useragent=None, browser=None):
        self._driver = None
        self.visible = visible or (os.environ.get("DRIVER_VISIBLE") == "1")
        self._wait = wait
        self.useragent = useragent
        self.browser = browser

    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def _create_firefox(self):
        options = FFoptions()
        options.headless = not self.visible
        profile = webdriver.FirefoxProfile()
        if self.useragent:
            profile.set_preference("general.useragent.override", self.useragent)
        for k, v in FF_DEFAULT_PROFILE.items():
            profile.set_preference(k, v)
            profile.DEFAULT_PREFERENCES['frozen'][k] = v
        profile.update_preferences()
        driver = webdriver.Firefox(
            options=options, firefox_profile=profile)
        driver.maximize_window()
        driver.implicitly_wait(5)
        return driver

    def _create_chrome(self):
        options = CMoptions()
        if not self.visible:
            options.add_argument('headless')
        if self.useragent:
            options.add_argument('user-agent=' + self.useragent)
        options.add_argument("start-maximized")
        options.add_argument("--disable-extensions")
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument("--lang=es-ES")
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)

        if is_s5h:
            prox = Proxy()
            prox.proxy_type = ProxyType.MANUAL
            prox.socks_proxy = "{}:{}".format(proxy_ip, proxy_port)
            prox.socksVersion = 5
            capabilities = webdriver.DesiredCapabilities.CHROME
            prox.add_to_capabilities(capabilities)
            driver = webdriver.Chrome(options=options, desired_capabilities=capabilities)
        else:
            driver = webdriver.Chrome(options=options)
        driver.maximize_window()
        driver.implicitly_wait(5)
        return driver

    def get_dirver(self):
        if self._driver is None:
            crt = getattr(self, "_create_" + str(self.browser), None)
            if crt is None:
                raise Exception("Not implemented yet: %s" % self.browser)
            self._driver = crt()
        return self._driver

    @property
    def driver(self):
        return self.get_dirver()

    def close(self, *windows):
        if self._driver:
            sz = len(self._driver.window_handles)
            if len(windows) in (0, sz):
                self._driver.quit()
                self._driver = None
                return
            for w in reversed(windows):
                self._driver.switch_to.window(w)
                self._driver.close()
            self._driver.switch_to.window(self._driver.window_handles[0])

    @retry(times=3, exceptions=WebDriverException, sleep=3)
    def close_others(self, current=None):
        if self._driver:
            if current is None:
                current = self._driver.current_window_handle
            elif isinstance(current, int):
                current = self._driver.window_handles[current]
            windows = [w for w in self._driver.window_handles if w != current]
            if windows:
                self.close(*windows)

    def switch(self, window):
        if isinstance(window, int):
            window = self._driver.window_handles[window]
        self._driver.switch_to.window(window)

    def reintentar(self, intentos, sleep=1):
        if intentos > 50:
            return False, sleep
        if intentos % 3 == 0:
            sleep = int(sleep / 3)
            self.close()
        else:
            sleep = sleep * 2
        if intentos > 20:
            time.sleep(10)
        time.sleep(2 * (int(intentos / 10) + 1))
        return True, sleep

    def get(self, url):
        self.driver.get(url)

    def get_soup(self):
        if self._driver is None:
            return None
        return buildSoup(self._driver.current_url, self._driver.page_source)

    @property
    def current_url(self):
        if self._driver is None:
            return None
        return self._driver.current_url

    @property
    def source(self):
        if self._driver is None:
            return None
        return self._driver.page_source

    def wait(self, id, seconds=None, presence=False):
        if isinstance(id, (int, float)):
            time.sleep(id)
            return
        my_by = By.ID
        if seconds is None:
            seconds = self._wait
        if id.startswith("//"):
            my_by = By.XPATH
        if id.startswith("."):
            # id = id[1:]
            my_by = By.CSS_SELECTOR
        wait = WebDriverWait(self._driver, seconds)
        if presence:
            wait.until(ec.presence_of_element_located((my_by, id)))
        else:
            wait.until(ec.visibility_of_element_located((my_by, id)))
        if my_by == By.CLASS_NAME:
            return self._driver.find_element_by_class_name(id)
        if my_by == By.CSS_SELECTOR:
            return self._driver.find_element_by_css_selector(id)
        if my_by == By.XPATH:
            return self._driver.find_element_by_xpath(id)
        return self._driver.find_element_by_id(id)

    def safe_wait(self, *ids, **kvarg):
        for id in ids:
            if not isinstance(id, str):
                return id
            try:
                return self.wait(id, **kvarg)
            except TimeoutException:
                pass
        return None

    def val(self, n, val=None, **kwargs):
        if n is None or self._driver is None:
            return None
        if isinstance(n, str):
            n = self.wait(n, **kwargs)
        if val is not None:
            if n.tag_name == "select":
                Select(n).select_by_visible_text(val)
            else:
                n.clear()
                n.send_keys(val)
        return n.text

    def click(self, n, **kvarg):
        if n is None or self._driver is None:
            return None
        if isinstance(n, str):
            n = self.wait(n, **kvarg)
        if n.is_displayed():
            n.click()
        else:
            n.send_keys(Keys.RETURN)
        return True

    def safe_click(self, *ids, after=None, force_return=False, **kvarg):
        if len(ids) == 1 and not isinstance(ids[0], str):
            n = ids[0]
        else:
            n = self.safe_wait(*ids, **kvarg)
        if n is None:
            return -1
        try:
            if n.is_displayed() and not force_return:
                n.click()
            else:
                n.send_keys(Keys.RETURN)
        except (ElementNotInteractableException, StaleElementReferenceException, ElementNotVisibleException,
                WebDriverException):
            return 0
        if after is not None:
            time.sleep(after)
        return 1

    def pass_cookies(self, session=None):
        if self._driver is None:
            return session
        if session is None:
            session = requests.Session()
        for cookie in self._driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'])
        return session

    def to_web(self):
        w = Web()
        self.pass_cookies(w.s)
        return w
