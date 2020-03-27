# Configuración de vertical residuos

## Modelo

Se ha realizado una adaptación de los [modelos de residuos de FiWare](https://fiware-datamodels.readthedocs.io/en/latest/WasteManagement/doc/introduction/index.html), manteniendo sólo aquellos atributos que posteriormente se persisten a base de datos de la [vertical de residuos de Smart Cities](https://github.com/telefonicasc/dumps-vertical/blob/master/model/db/ddls.sql):

Se han detectado algunas inconsistencias entre los modelos:

* **wasteContainerModel**:
  - La vertical no usa el atributo `name`, definido por fiware como **mandatory**.
  - La vertical usa el atributo `volumeStored`, fiware define `cargoVolume`.

* **wasteContainer**:
  - La vertical usa los atributos `containerIsle` y `isleId`, fiware define `refWasteContainerIsle` y `isleId`. De cualquier modo, en la vertical no está implementado el modelo `containerIsle`.
  - La vertical usa los atributos `dateUpdated` y `dateNextActuation`. El modelo fiware, sin embargo, define `dateServiceStarted` / `dateLastCleaning`, y `nextActuationDeadline`.

Tras discutir estas diferencias con los desarrolladores de plataforma, acordamos seguir el modelo definido por los esquemas de la base de datos.

## Entidades

Las entidades a crear se han definido mediante ficheros CSV:

- [waste_container_models.csv](csv/waste_container_models.csv): Modelos de contenedores de residuos.
- [waste_containers.csv](csv/waste_containers.csv): Contenedores dados de alta.

La cabecera de cada fichero csv define los **atributos** de las diferentes entidades, además del **tipo** y **object_id** (opcional) de cada atributo, usando este formato: *object_id*:*atributo*<*tipo*>, por ejemplo: `t:temperature<Number>`.

Las entidades que tienen atributos con un *object_id* se crean en el IoT-Agent. Las entidades que no tienen ningún *object_id* ni ningún atributo calculados (atributos que utilizan la sintaxis *${ ... }*), se crean directamente en el context broker (se asume que no van a pasar por el IoT-Agent).

### Creación de entidades

Para crear estas entidades, es necesario establecer unas variables de entorno (directamente o en un fichero **.env**):

```bash
url_keystone=https://<direccion_servidor>:<puerto>
url_cb=https://<direccion_servidor>:<puerto>
url_iotagent=https://<direccion_servidor>:<puerto>
service=<servicio>
subservice=</subservicio>
username=<usuario>
password=<password>
protocol=IoTA-JSON
```

Con las variables establecidas, se puede utilizar el script *main.py* para crear las entidades en la API correspondiente:

```bash
python3 main.py -c csv/waste_container_models.csv
python3 main.py -c csv/waste_containers.csv
```

### Borrado de entidades

El script *main.py* no hace comprobaciones previas de que las entidades existan en el context broker o el IoT-Agent; en caso de que existieran, intentar crearlas otra vez resultaría en un error *409: Conflict*.

Para evitar este problema, el workarund actual consiste en borrar las entidades del context broker e IotAgent usando el flag *-d* del script, es decir:

```bash
python3 main.py -d -c csv/waste_containers.csv
python3 main.py -d -c csv/waste_container_models.csv
```

Borrar las entidades no tiene efectos sobre los datos retenidos en la base de datos, ni sobre las suscripciones, de manera que actualmente no se considera un problema.

## Datos

Los datos se pueden enviar mediante MQTT. Es necesario tener:

- La dirección IP y puerto del servidor MQTT.
- Usuario y password MQTT.
- Cadena de certificados del servidor MQTT.
- API key y Device ID del dispositivo a simular.

Las direcciones y credenciales deben obtenerse del proveedor. Para obtener la cadena de certificados, se han añadido unas instrucciones en la carpeta [certs](certs/README.md)

Ejemplo de envío de datos:

```
# Datos de conexión a MQTT
MQTT_IP=...
MQTT_PORT=...
MQTT_USER=...
MQTT_PASS=...

# apiKey y deviceID
APIKEY=...
DEVICEID=...

mosquitto_pub -d --cafile certs/smc.pem --insecure -h "$MQTT_IP" -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASS" -t "/$APIKEY/$DEVICEID/attrs" -m '{"t":16,"f":25}'
```
