# Requisitos

## Librerias

```console
$ pip3 install -r requirements.txt
```

## Variables de entorno

* `GEO_PROVINCIAS`: url al geojson de las provincias
* `GEO_MUNICIPIOS`: url al geojson de los municipios
* `JS_PROVINCIAS`: url al json con el listado de provincias de España
* `API_ENDPOINT`: url a la que deben apuntar los `actions` de los formularios

# Creación de la web

```console
$ ./build.py
```

Genera en el directorio `out` la página web.
