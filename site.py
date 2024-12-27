#!/usr/bin/env python3

from datetime import datetime

from core.j2 import Jnj2
from core.mapa import Mapa

api = Mapa()
nov = api.get_novedades()
nov = sorted(nov, key=lambda x: (x.fecha, x.titulo), reverse=True)

j2 = Jnj2("template/", destino="_site/")
j2.save("index.html",
    novedades=nov,
    now=datetime.now()
)