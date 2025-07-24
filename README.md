# Instalación

```console
$ sudo apt-get install build-essential libpoppler-cpp-dev pkg-config python-dev python3-dev
$ sudo -H pip3 install -r requirements.txt
$ cp config.example.yml config.yml
$ chmod 600 config.yml
```

Editar contenido de `config.yml` para añadir las credenciales.

Opcionalmente, si se quiere usar la linea de comandos cómodamente:

```console
$ sudo ln -s $(realpath cli.py) /usr/local/bin/mapa-cli
```

# Uso

## Linea de comandos

```console
$ python3 cli.py --help
usage: cli.py [-h]
              [--horas | --mes | --año | --vacaciones | --lapso | --festivos | --menu | --nominas | --bruto | --irpf | --expediente | --puesto | --novedades | --ofertas | --cuadrante | --contactos | --busca BUSCA [BUSCA ...]]

Comando para los servicios de intranet.mapa.es

optional arguments:
  -h, --help            show this help message and exit
  --horas               Muestra el control horario para la semana en curso
  --mes                 Muestra el control horario para el mes en curso
  --año                 Muestra el control horario para el año en curso
  --vacaciones          Muestra los días de vacaciones que te quedan
  --lapso               Muestra permisos registrados en lapso
  --festivos            Muestra los festivos hasta enero del año que viene
  --menu                Muestra el menú de la sede definida en config.yml
  --nominas             Descarga las nóminas en el directorio definido en config.yml y muestra las cantidades netas
  --bruto               Lo mismo que --nominas pero mostrando las cantidades en bruto
  --irpf                Muestra la evolución del irpf
  --expediente          Descarga el expediente personal en el directorio definido en config.yml
  --puesto              Muestra información sobre el puesto ocupado
  --novedades           Muestra las novedades de intranet.mapa.es (con antigüedad máxima de 30 días)
  --ofertas             Muestra ofertas para los empleados de MAPA
  --cuadrante           Muestra el cuadrante de personal
  --contactos           Contactos de interés
  --busca BUSCA [BUSCA ...]
                        Busca en el directorio de personal
```

## Bot

Con `bot.py` se puede levantar un bot xmpp que responde a los comandos por chat:

![horas](/rec/01-horas.png)

![vacaciones](/rec/02-vacaciones.png)

![festivos](/rec/03-festivos.png)

![menu](/rec/04-menu.png)

Las palabras a las que responde el bot son los `parámetros largos` de le
línea de comandos (pero sin `--`).

Recuerda arrancar la primera vez al bot como amistoso (`./bot.py --amistoso`)
para que acepte tu petición de amistad y poder comunicarte con él.
Luego rearrancalo en modo normal (`./bot.py`) para que nadie más pueda usarlo.

Adicionalmente se puede usar el bot para mandar notificaciones programadas.
Por ejemplo, si en nuestro `cron` ponemos:

```
45 11 25-31 * * test $(date +\%u) -lt 7 && /path-to-bot/bot.py --send nominas
```

Obtendremos un mensaje con nuestra nómina en cuanto este disponible. ¿Como funciona?

* `45 11 20-31 * * test $(date +\%u) -lt 7` se encarga de ejecutar el comando
cada lunes, martes, miércoles, jueves o viernes a las 11:45 a partir del día 25 de cada mes
* El bot consulta las nominas y las compara con el resultado de la última ejecución, y si son distintas
(normalmente, porque se ha añadido una nueva) entonces enviá el mensaje

Otros ejemplos:

```
# Recordar que el mensaje solo se enviara si su contenido
# es distinto al que se envió por última vez, por lo tanto
# no hay peligro de spam

# Enviar novedades cada día (entresemana) a las 10:15
15 10 * * 1-5 /path-to-bot/bot.py --send novedades
# Enviar cada 28 de mes, a las 9:15, las ofertas
15 09 28 * * /path-to-bot/bot.py --send ofertas
```
