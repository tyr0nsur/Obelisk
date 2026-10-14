# Inspección de una migración ASE ArkApi → ObeliskNative

`scripts/obelisk_migrate.py` inspecciona **copias locales del operador** de
Permissions y ArkShop. Produce un informe propio; todavía no importa cuentas,
permisos, balances ni objetos. `inspect` y `dry-run` tienen las mismas operaciones
de lectura. Cambia la etiqueta del informe para facilitar una revisión previa.

El reconocimiento de un formato no demuestra compatibilidad de DLL, equivalencia
de producto, autenticación ni entrega de objetos en ARK. Las funciones nativas
y la suite propuesta tienen su propia aceptación: [catálogo funcional](research/ARKAPI_PLUGIN_SUITE_PARITY.md).

## Uso con copias offline

Requiere Python 3.11 o posterior y un módulo `sqlite3` con `Connection.deserialize`.
Para JSON no abre ninguna base de datos. Para SQLite lee el archivo con permisos
de lectura y deserializa esos bytes en memoria privada. SQLite recibe únicamente
`:memory:`; no abre el archivo original ni crea diarios junto a él. La conexión
deshabilita extensiones, activa `query_only` y `trusted_schema=OFF`, y admite sólo
consultas y la introspección necesaria. [Deserialización de Python](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.deserialize),
[controles SQLite](https://www.sqlite.org/pragma.html#pragma_query_only).

Proporciona una copia consistente realizada con el procedimiento de backup del
operador. Se rechazan archivos con `-wal`, `-shm` o `-journal` adyacentes, incluidos
enlaces rotos, y entradas que atraviesan symlinks. El SHA256 se compara antes y
después de una inspección completada. Esa comparación detecta cambios; no puede
certificar que una copia previa de una base viva sea consistente. La herramienta
no detiene servicios, no hace checkpoints y no prepara ese backup. Los archivos
WAL forman parte del estado de una base que los usa. [WAL de SQLite](https://www.sqlite.org/wal.html).

Desde la raíz del proyecto, ajustando las rutas a esas copias:

```bash
python3 scripts/obelisk_migrate.py inspect \
  --permissions-config /tmp/obelisk-legacy-copies/permissions.json \
  --shop-config /tmp/obelisk-legacy-copies/arkshop.json

python3 scripts/obelisk_migrate.py dry-run \
  --permissions-db /tmp/obelisk-legacy-copies/permissions.sqlite \
  --shop-db /tmp/obelisk-legacy-copies/arkshop.sqlite \
  --identity-namespace steam
```

No se contacta MySQL, Discord, un servidor ARK ni una API de cuentas. Las
credenciales de configuración se reconocen para identificar el formato y se
redactan en la salida habitual. No existe una opción `--apply` o `--import`.

## Informe y salida privada

El esquema original es `obelisk.native-migration-inspection.v1`. Contiene
`sources` con referencias ordinales, hashes, tamaños y estado; `issues` con
códigos y ubicaciones; y `unmapped_fields` para los campos que requieren revisión.
Todas las filas candidatas llevan `activation_allowed=false`. Los indicadores
`live_apply_available`, `automatic_admin_import` y `authoritative_identity`
permanecen en `false`.

| Estado | Código de salida | Significado |
| --- | --- | --- |
| `supported` | 0 | Formato inspeccionado sin un bloqueo identificado; no autoriza su aplicación. |
| `mapping_required` | 2 | La representación se reconoce pero necesita decisiones explícitas de identidad, permisos, persistencia o entrega. |
| `blocked` | 3 | Datos ambiguos, inválidos, desconocidos, inaccesibles o fuera del ámbito. |

El estado global es el más restrictivo de los estados de las fuentes. Un fichero
de mensajes conocido puede dar `supported`; una base de cuentas da al menos
`mapping_required` aunque declare `steam` y todos sus valores sean válidos.

Por defecto se redactan rutas de entrada, configuraciones completas, filas,
identificadores de cuenta y los nombres/valores de campos desconocidos. Quedan
conteos, totales enteros agregados y códigos de diagnóstico. Los errores no
imprimen SQL, credenciales, argumentos desconocidos ni excepciones de la fuente.

Para revisar contenido sensible, hay que pedirlo expresamente en un archivo
nuevo. La salida estándar sigue mostrando sólo el resultado de la escritura:

```bash
python3 scripts/obelisk_migrate.py dry-run \
  --shop-db /tmp/obelisk-legacy-copies/arkshop.sqlite \
  --identity-namespace steam \
  --include-sensitive --output ./migration-private/report.json
```

El archivo se crea con modo `0600`; su directorio debe ser propiedad del usuario
actual y tener modo `0700`. Los directorios nuevos de esa ruta se crean con
`0700`. Se rechazan symlinks, directorios existentes con otro modo y archivos
existentes; no se cambian permisos ni se sobrescriben entradas existentes.
`--output` sin `--include-sensitive` guarda un informe redactado con los mismos
permisos. No se debe versionar el informe sensible.

## Ámbito de los formatos

La referencia primaria está fijada al commit
`66faba2e46b5c5f4597fd72b6ac6eda838708569` de `ArkServerApi/ASE-Plugins`.
El parser y el informe son implementación propia a partir de hechos de esquema;
no contienen funciones copiadas de los plugins. Los archivos referenciados
pertenecen al repositorio cuyo [LICENSE.TXT](https://github.com/ArkServerApi/ASE-Plugins/blob/66faba2e46b5c5f4597fd72b6ac6eda838708569/LICENSE.TXT)
declara MIT. Esto no extiende esa licencia a productos independientes del
catálogo, paquetes comerciales, DLL o contenido adquirido por el operador.

| Entrada | Subconjunto inspeccionado |
| --- | --- |
| Configuración Permissions | Selección SQLite/MySQL y campos de conexión, ruta y sincronización. Reconoce también nombres de selección/tablas de formatos anteriores; no consulta tablas remotas. |
| Configuración ArkShop | Selector MySQL, configuración general, mensajes conocidos y catálogos de kits, compras y ventas. Textos, blueprints y requisitos se conservan para revisión. |
| SQLite Permissions | Tablas ordinarias `Players` y `Groups`, más `Tribes` si existe. Comprueba columnas, sujetos, referencias de grupos y estructura de membresías temporales. |
| SQLite ArkShop | Tabla ordinaria `Players`, sujetos, saldos, gasto acumulado y créditos de kits con forma `{nombre: {Amount: entero}}`. |

Referencias: [configuración Permissions](https://github.com/ArkServerApi/ASE-Plugins/blob/66faba2e46b5c5f4597fd72b6ac6eda838708569/Permissions/Configs/config.json),
[configuración ArkShop](https://github.com/ArkServerApi/ASE-Plugins/blob/66faba2e46b5c5f4597fd72b6ac6eda838708569/ArkShop/Configs/config.json),
[esquema SQLite Permissions](https://github.com/ArkServerApi/ASE-Plugins/blob/66faba2e46b5c5f4597fd72b6ac6eda838708569/Permissions/Permissions/Private/Database/SqlLiteDB.h),
[esquema SQLite ArkShop](https://github.com/ArkServerApi/ASE-Plugins/blob/66faba2e46b5c5f4597fd72b6ac6eda838708569/ArkShop/ArkShop/Private/Database/SqlLiteDB.h),
[representación de créditos de kits](https://github.com/ArkServerApi/ASE-Plugins/blob/66faba2e46b5c5f4597fd72b6ac6eda838708569/ArkShop/ArkShop/Private/Kits.cpp).

Campos desconocidos son bloqueos, incluidos los anidados. La copia privada
conserva los valores JSON originales; para tablas conocidas con columnas extra,
conserva también esas columnas en las filas copiadas. Un esquema sin las columnas
necesarias conserva sus nombres como diagnóstico, y sus valores permanecen en
la fuente intacta. Vistas, tablas virtuales, columnas generadas y otros objetos
SQLite desconocidos no se interpretan como tablas del producto. Los overrides
`GachaResources` se conservan bloqueados hasta desarrollar su contrato propio.

Se limitan las configuraciones a 2 MiB, las imágenes SQLite a 128 MiB, los objetos
de esquema a 100 y las filas a 10.000 por tabla. Cada JSON de créditos de kits
tiene un límite de 64 KiB y 1.000 entradas. Las consultas y el procesamiento de
filas tienen un presupuesto de dos segundos y las consultas tienen además un
límite de operaciones. Excederlos produce `blocked`; no se omiten filas para
declarar una migración completa.

## Identidad, permisos y dinero

`--identity-namespace steam` es una declaración explícita del origen legado,
no una comprobación del dueño de la cuenta. El nombre de columna esperado es
`SteamId`; una columna `EOSID` diferente no se renombra ni se infiere por la
longitud. Un número de 19 dígitos observado por el adaptador nativo tampoco
demuestra Steam, Epic ni una correspondencia con ese registro. Sin una declaración
explícita, las filas conservan el namespace sin resolver. No hay importación
automática de cuentas ni enlace con la identidad que observa `/whoami`.

Antes de aplicar datos en una fase posterior habrá que verificar proveedor y
cuenta con evidencia adecuada, fijar una clave de cluster y resolver conflictos.
Duplicados de un sujeto en la misma base son bloqueos incluso si sus saldos
coinciden. Grupos desconocidos, nombres duplicados sin distinguir mayúsculas y
formatos temporales desconocidos son bloqueos. Las membresías temporales
reconocidas conservan su representación y necesitan revisar expiración y reloj.

`Admins`, permisos comodín y nombres de permisos legados requieren revisión
expresa; no conceden administración nativa. Comandos incluidos en kits quedan
`blocked`, aunque no pidan `ExecuteAsAdmin`: el inspector no ejecuta comandos ni
transfiere esa capacidad. Los IDs de tribu necesitan namespace y membresía
verificados antes de asociarlos a una tribu nativa.

Precios, saldos, gasto acumulado y cantidades reconocidas deben ser enteros
exactos no negativos entre `0` y `2^63-1`. Se rechazan negativos, fracciones,
floats, booleanos, textos numéricos de dinero y overflow. Un entero por encima
de `2^53` conserva su valor; no pasa por `float`. Un decimal rechazado se conserva
en el informe privado como `decimal_exact`, sin convertirlo en saldo aceptado.
Los totales agregados usan enteros Python exactos y no son un balance importable.

La próxima fase necesitará un ledger propio con claves idempotentes, reglas de
privilegios y evidencia de entrega. Este informe no efectúa un crédito, no
restaura un personaje y no demuestra entrega de inventario/dinos. Las decisiones
de persistencia y aceptación Epic/Steam están en el catálogo funcional.

## Verificación de la herramienta

```bash
python3 scripts/test_obelisk_migrate.py
```

Las pruebas usan configuraciones y bases sintéticas temporales. Cubren lectura
en memoria y fuente intacta, esquemas maliciosos, conflictos de identidad,
unknown fields, enteros exactos y dinero inválido, redacción de salida, archivo
privado, symlinks y rechazo de ejecución administrativa. No son evidencia de
autenticación, migración aplicada o funcionamiento de una tienda dentro de ARK.
