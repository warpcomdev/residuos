# Configuración de vertical residuos

## Modelos

Se ha realizado una adaptación de los [modelos de residuos de FiWare](https://fiware-datamodels.readthedocs.io/en/latest/WasteManagement/doc/introduction/index.html), manteniendo sólo aquellos atributos que posteriormente se persisten a base de datos de la [vertical de residuos de Smart Cities](https://github.com/telefonicasc/dumps-vertical/blob/master/model/db/ddls.sql):

Se han detectado algunas inconsistencias entre los modelos:

**wasteContainerModel**:

- La vertical no usa el atributo "name", definido por fiware como *mandatory*.
- La vertical usa el atributo "volumeStored", fiware define "cargoVolume".

**wasteContainer**:

- La vertical usa los atributos "containerIsle" y "isleId", fiware define "refWasteContainerIsle" y "isleId". De cualquier modo, en la vertical no está implementado el modelo containerIsle.
- La vertical usa los atributos "dateUpdated" y "dateNextActuation". El modelo fiware, sin embargo, define "dateServiceStarted", "dateLastCleaning", "nextActuationDeadline".
- La vertical usa el atributo "weight", el modelo fiware define "cargoWeight".
