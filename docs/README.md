# Requisitos

## Librerias

```console
$ pip3 install -r requirements.txt
```

## Variables de entorno

### Obligatorias

* `GEO_PROVINCIAS`: url s3 al geojson de las provincias
* `GEO_MUNICIPIOS`: url s3 al geojson de los municipios
* `JS_PROVINCIAS`: url s3 al json con el listado de provincias de España
* `API_ENDPOINT_XX`: enpoint raiz a los lambda de cada proyecto, sindo `XX` el identificador de proyecto (`P1`, `P2`, etc)

### Solo necesarias para CodeCommit

* `ROOT_OUT`: nombre con el que se renombrara la carpeta `out` antes de subirla a `s3`

# Creación de la web

```console
$ ./build.py
```

Genera en el directorio `out` la página web.
