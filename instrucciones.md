# Integración piloto residuos

Para la integración del piloto de residuos, se procederá de la siguiente manera:

## Alta de contenedores

El primer paso es dar de alta los contenedores de residuos en la plataforma. Para este piloto se consideran en principio dos contenedores, que se corresponden con las filas 3 y sucesivas de este CSV:

- [waste_containers.csv](config/csv/waste_containers.csv)

Para dar de alta los contenedores, es necesario **[Descargar ese CSV desde aquí](https://raw.githubusercontent.com/warpcomdev/residuos/master/config/csv/waste_containers.csv) y rellenar las siguientes columnas**:

- entityID: Esto es informativo, para identificar el contenedor en la plataforma. Se puede usar CONTAINER-001, CONTAINER-002, etc.
- deviceID: Este es el ID del sensor instalado en el container. Debe coincidir con el ID que se use en el tópic MQTT. Ver sección **Envío de datos**.
- protocol: Copiar el valor *IoTA-JSON*
- f:fillingLevel: Esto es una fórmula para calcular el nivel de llenado del contenedor (de 0.00: vacío a 1.00: lleno), en función de la información que manda el sensor (distancia, en centímetros). Para el piloto proponemos usar una fórmula sencilla, considerando por ejemplo que el contenedor tiene 1,50 metros de altura interior: *${(150-@fillingLevel)/150}*
- t:temperature: Dejar en blanco, esta información se enviará por MQTT.
- areaServed: Nombre del área a la que da servicio el contenedor.
- weight: Peso del contenedor en kilos.
- category: Categoría de contenedor. Valores soportados: *fixed*, *underground*, *ground*, *portable*, *other*.
- dateLastEmptying: Fecha del último vaciado del contenedor. De momento, copiar la fecha *1900-01-01T00:00:00*.
- description: Descripción del contenedor.
- isleId: ID del bloque o isleta al que pertenece el contenedor.
- location: Coordenadas del contenedor, en formato geo:json (por ejemplo: *{"type":"Point","coordinates":[-3.637209535,40.538009667]}*)
- methaneConcentration: Este valor lo soporta la vertical pero no el sensor, así que se puede dejar a 0.
- refWasteContainerModel: Referencia a algún modelo de contenedor definido en el fichero [waste_container_models.csv](config/csv/waste_container_models.csv). Para este piloto se define un sólo modelo, *MODEL-001*.
- serialNumber: Número de serie del contenedor.
- status: Estado del contenedor, dejar con el valor *ok*.
- storedWasteKind: Tipo de residuos. Valores soportados: *organic*, *inorganic*, *glass*, *oil*, *plastic*, *metal*, *paper*, *batteries*, *electronics*, *hazardous*, *other*
- storedWasteOrigin: Origen de los residuos. Valores soportados: *household*, *municipal*, *industrial*, *construction*, *hostelry*, *agriculture*, *other*

Como es simplemente un piloto, si hay datos desconocidos (por ejemplo *isleId*), se puede plantear rellenarlos con valores inventados.

## Envío de datos

Una vez se haya rellenado el CSV y creado las entidades, se pueden empezar a enviar datos por MQTT.

Cada dispositivo debe tener un ID único, que se habrá indicado en la columna **deviceID** del CSV anterior. Los datos que se envíen al broker MQTT deben tener el siguiente formato:

- topic: /**apiKey**/**deviceID**/attrs
- payload: {"f":*XX*, "t":*YY*}
  - *XX* es la distancia medida por el sensor de llenado, en centrímetros.
  - "YY" es la temperatura medida por el sensor de temperatura, en grados.

El valor de **apiKey**, así como la dirección IP del broker MQTT, y las credenciales de acceso al broker (nombre de usuario y contraseña), se enviarán por correo.

## Fecha de último vaciado

La vertical de residuos en la plataforma utiliza un campo *dateLastEmptying* con la fecha de último vaciado del contenedor, para sacar métricas.

El sensor utilizado en este piloto es capaz de enviar mensajes cuando se producen determinados eventos, como superar una cierta temperatura o umbral de llenado. Uno de estos eventos es "TILT", cuando se supera un umbral de inclinación.

No estamos seguros de si se puede relacionar un evento "TILT" con un vaciado del contenedor. Esto es necesario comentarlo con el proveedor.
