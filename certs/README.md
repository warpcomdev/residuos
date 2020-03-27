# Certificados MQTT

Este directorio contiene la cadena de certificados que utiliza el servidor MQTT. La cadena se ha construido de la siguiente forma:

## Obtención del certificado del propio servidor

```bash
MQTT_IP=...
MQTT_PORT=...
echo -n | openssl s_client -connect "$MQTT_IP:$MQTT_PORT" | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > mqtt.crt
```

## Obtención de los certificados intermedios

Para identificar quien es la CA que firma el certificado del servidor:

```bash
openssl x509 -in mqtt.crt -noout -text
```

Una vez localizada, descargar los certificados de las CAs intermedias y raiz. En este caso, es DigiCert:

```bash
wget "https://geotrust.tbs-certificats.com/GeoTrust_RSA_CA_2018.crt"
wget "https://www.tbs-certificats.com/issuerdata/DigiCertGlobalRootCA.crt"
```

## Creación de la cadena

Concatenamos los certificados desde el servidor a la raíz:

```bash
cat mqtt.crt GeoTrust_RSA_CA_2018.crt DigiCertGlobalRootCA.crt > smc.pem
```
