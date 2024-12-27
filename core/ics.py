import re
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime
from textwrap import dedent
from typing import Union

import pytz

from .filemanager import FileManager

UUID_NAMESPACE = uuid.UUID('00000000-0000-0000-0000-000000000000')

ICS_BEGIN = dedent(
    '''
    BEGIN:VCALENDAR
    PRODID:-//Eventos//python3.10//ES
    VERSION:2.0
    '''
).strip()

ICS_END = "END:VCALENDAR"

@dataclass(frozen=True)
class IcsEvent:
    dtstamp: str
    uid: str
    categories: str
    summary: str
    dtstart: str
    dtend: str
    description: str

    def __post_init__(self):
        for f, v in asdict(self).items():
            if f in ('dtstamp', 'dtstart', 'dtend'):
                object.__setattr__(self, f, self.parse_dt(f, v))
                continue
            f_parse = getattr(self, f'parse_{f}', None)
            if callable(f_parse):
                object.__setattr__(self, f, f_parse(v))

    def parse_dt(self, k: str, d: Union[datetime, str]):
        if isinstance(d, date):
            return d.strftime("%Y%m%d")
        if isinstance(d, str):
            if not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$"):
                return d
            tz = pytz.timezone('Europe/Madrid')
            dt = datetime.strptime(d, "%Y-%m-%d %H:%M")
            d = tz.localize(dt)
        if d is None:
            if k != 'dtstamp':
                return None
            d = datetime.now(tz=pytz.timezone('Europe/Madrid'))
        dutc = d.astimezone(pytz.utc)
        return dutc.strftime("%Y%m%dT%H%M%SZ")

    def parse_uid(self, s: str):
        try:
            _ = uuid.UUID(s)
            return s.upper()
        except ValueError:
            return str(uuid.uuid5(UUID_NAMESPACE, s)).upper()

    def parse_description(self, s: str):
        if s is None:
            return None
        s = s.strip()
        if len(s) == 0:
            return None
        return re.sub(r"\n", r"\\n", s)

    def __str__(self):
        lines = ["BEGIN:VEVENT", "STATUS:CONFIRMED"]
        for k, v in asdict(self).items():
            if v is not None:
                lines.append(f"{k.upper()}:{v}")
        lines.append("END:VEVENT")
        return "\n".join(lines)

    def __lt__(self, o: "IcsEvent"):
        return self.key_order < o.key_order

    @property
    def key_order(self):
        return (self.dtstart, self.dtend, self.uid)

    @staticmethod
    def dump(path, *events: "IcsEvent"):
        events = sorted(events)
        ics = ICS_BEGIN+"\n"+("\n".join(map(str, events)))+"\n"+ICS_END
        ics = re.sub(r"[\r\n]+", r"\r\n", ics)
        FileManager.get().dump(path, ics)

    def dumpme(self, path):
        IcsEvent.dump(path, self)