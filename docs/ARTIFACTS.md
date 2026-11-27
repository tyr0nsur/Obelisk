# Artifacts experimentales de ObeliskNative

`scripts/obelisk_artifacts.py` empaqueta un build existente, firma su manifiesto,
verifica todos sus bytes y prepara una versión aislada. No compila el runtime,
no cambia configuraciones, no arranca ARK, no publica en Internet y no activa una
versión instalada. Requiere Python 3.10 o posterior, Linux y OpenSSL con Ed25519.

La primera revisión admite únicamente `channel=experimental`,
`stability=experimental` y `runtime_ready=false`. Una firma válida demuestra que
la clave confiable autorizó esos bytes. No demuestra paridad de gameplay,
aceptación Steam/Epic ni estabilidad del servidor.

## Clave de publicación

El operador crea directorios privados fuera de Git, configura y conserva su
pareja de claves y distribuye la pública por un canal de confianza independiente.
Los directorios de salida, claves y staging deben existir con propietario actual
y modo `0700`. Los archivos de clave se crean con `0600`; no se sobrescriben.

```bash
python3 scripts/obelisk_artifacts.py keygen \
  --private-key /ruta/privada/keys/artifacts-ed25519.pem \
  --public-key /ruta/privada/keys/artifacts-ed25519.pub.pem
```

La clave privada nunca entra en el paquete, manifiesto, índice ni mensajes del
comando. `build` exige que pertenezca al usuario actual y tenga modo `0600`.
`verify` exige `--trusted-key`; no acepta una clave incrustada en un manifiesto
como autoridad. La rotación necesita entregar la nueva confianza explícitamente.

## Construcción desde el build actual

```bash
python3 scripts/obelisk_artifacts.py build \
  --build-dir build \
  --source-root . \
  --version 0.1.0-beta.1 \
  --channel experimental \
  --output-dir /ruta/privada/artifacts \
  --signing-key /ruta/privada/keys/artifacts-ed25519.pem
```

La lista de contenido es cerrada:

- `runtime/libobelisk.so` y `runtime/libsubhook.so`. La dependencia subhook es
  dinámica y debe acompañar al runtime; éste ya usa `$ORIGIN` en su RUNPATH.
- Seis bibliotecas bajo `plugins/<id>/<id>.so`: oPing, oEssentials, oShopKits,
  oAdvancedChat, oWorldTools y oHomes.
- Cuatro headers públicos bajo `sdk/include/obelisk/` y los tres archivos CMake
  del SDK bajo `sdk/lib/cmake/Obelisk/`.
- Los avisos existentes de Obelisk, fmt, spdlog y subhook bajo `licenses/`.
  De subhook sólo se extrae el aviso del comentario inicial del header.

No se recorren directorios para incluir archivos arbitrarios. El ejecutable y los
assets de ARK, partidas, perfiles, configuraciones, secretos, claves y código
interno quedan fuera. El operador instala el juego por separado, por ejemplo con
SteamCMD. El paquete tampoco incluye el panel FlowArk, una tienda o un servicio
de licencias: esta primera revisión empaqueta runtime, seis módulos y SDK.

El build se lee sin ejecutar sus bibliotecas. Se comprueba ELF compartido x86_64
y se preservan los bytes originales. El script no resuelve ni instala dependencias
del sistema como `libcrypto.so.3`, `libstdc++` o libc; un destino nuevo requiere
verificar esos requisitos antes de una futura activación. No se elimina el
RUNPATH de desarrollo ni se presenta este artifact como paquete de producción.

El tar usa orden de archivos, propietario y tiempo fijos; gzip omite nombre y
usa `mtime=0`. A igualdad de entradas, versión y clave produce los mismos bytes
y el mismo ID. No incorpora fecha de construcción para conservar esa propiedad.

## Esquemas y salida para el panel ObeliskNative

El manifiesto es JSON canónico ASCII, claves ordenadas, separadores compactos y
sin salto de línea final. `schema_version=1` contiene:

```json
{
  "schema_version": 1,
  "version": "0.1.0-beta.1",
  "channel": "experimental",
  "stability": "experimental",
  "platform": "linux-x86_64",
  "game": "ase",
  "game_build": "21241282",
  "game_executable_sha256": "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
  "api_bytes": 312,
  "runtime_ready": false,
  "components": ["oAdvancedChat", "oEssentials", "oHomes", "oPing", "oShopKits", "oWorldTools"],
  "archive_sha256": "<64 hex minúsculas>",
  "archive_size": 123,
  "files": [{"path": "<ruta permitida>", "size": 123, "sha256": "<64 hex minúsculas>"}]
}
```

El ejemplo abrevia la lista de archivos; el verificador requiere la lista exacta
y completa. La firma separada es Ed25519 binaria de 64 bytes sobre el manifiesto,
mediante `openssl pkeyutl -rawin`. El manifiesto vincula el digest y tamaño del
archivo comprimido y de cada archivo interno. Su SHA256 completo es el ID.

`build` escribe `obelisknative-<version>-experimental-linux-x86_64-<id>.tar.gz`,
el manifiesto con sufijo `.manifest.json` y la firma `.manifest.sig`. Los archivos
son de sólo lectura. Una repetición sólo acepta bytes idénticos. Cambiar de
clave para el mismo manifiesto requiere gestionar una nueva publicación; el
script no reemplaza una firma existente silenciosamente.

`index.json` tiene `schema_version=1` y `artifacts: []`. Cada entrada contiene
`id`, `version`, `channel`, `stability`, `platform`, `game`, `game_build`,
`api_bytes`, `runtime_ready`, `components`, `archive_sha256`, `archive_size`,
`archive_name`, `manifest_name` y `signature_name`. Los nombres sólo son
basenames; el índice no contiene rutas absolutas ni claves. Se actualiza con
bloqueo de publicación y rename atómico.
Si el rename del índice se completó pero falló su fsync, el comando comunica el
fallo y conserva los archivos a los que el índice ya apunta. Una repetición
revalida esos bytes; no borra una publicación de resultado incierto.

El índice sirve para descubrimiento y presentación, no como raíz de confianza.
El panel ObeliskNative puede mostrar «disponible para verificación». Antes de usar cualquier
archivo debe verificarse manifiesto, firma externa y contenido. No convertir
`runtime_ready=false` en una insignia de aceptación ni firmar de nuevo valores
de readiness a partir de la presencia del paquete.

## Verificación y staging sin activación

```bash
python3 scripts/obelisk_artifacts.py verify \
  --archive /ruta/artifact.tar.gz \
  --manifest /ruta/artifact.manifest.json \
  --signature /ruta/artifact.manifest.sig \
  --trusted-key /ruta/confiable/artifacts-ed25519.pub.pem

python3 scripts/obelisk_artifacts.py stage \
  --archive /ruta/artifact.tar.gz \
  --manifest /ruta/artifact.manifest.json \
  --signature /ruta/artifact.manifest.sig \
  --trusted-key /ruta/confiable/artifacts-ed25519.pub.pem \
  --stage-root /ruta/privada/staging
```

El verificador rechaza JSON ambiguo o no canónico, clave incorrecta, hashes
alterados, rutas no permitidas, traversal, duplicados, ausencias, links,
directorios o archivos especiales en tar, extensiones PAX/GNU y contenido después
del final de tar. Los límites son 64 archivos, 128 MiB por archivo, 512 MiB total,
256 MiB comprimidos y 128 KiB de manifiesto. Los archivos de entrada deben ser
regulares sin hardlinks, y ninguna ruta puede atravesar un symlink.
Los directorios sensibles y las claves rechazan ancestros de propietario no
confiable o escribibles por grupo/otros; se permite el ancestro temporal sticky
propiedad de root usado por los tests.

`stage` verifica antes de escribir. Prepara `versions/<id>/` con archivos
`0400` y directorios `0500`, incluyendo `manifest.json` y `manifest.sig`.
Usa directorio temporal, fsync y rename en el mismo filesystem. Ante un error
o interrupción de Python retira el staging parcial que creó. Una repetición vuelve a verificar bytes,
propietario, modos y contenido exacto del árbol existente; no confía únicamente
en su nombre. «Inmutable» significa publicación sin reemplazo y permisos de
sólo lectura; el propietario del sistema aún puede cambiar permisos, por lo que
es necesario revalidar al consumir el contenido.

No crea `current`, enlaces de activación ni escrituras en runtime/config del
servidor. La activación, respaldo de datos, compatibilidad con esquemas,
mantenimiento y rollback requieren otra operación revisada. Esta herramienta no
resuelve el SIGABRT histórico de apagado ni la aceptación de cada módulo.

## Pruebas

```bash
python3 scripts/test_obelisk_artifacts.py -v
```

Las pruebas generan claves OpenSSL reales y compilan una biblioteca ELF de
fixture con `cc`. Ejercitan firma y clave equivocadas, alteración de archivos,
tar malicioso aunque esté firmado por la clave de prueba, límites, rutas,
inmutabilidad, repetición, limpieza tras una escritura interrumpida y la CLI.
Los headers/configs de fixture prueban empaquetado, no el SDK del juego. La
construcción y el consumo del artifact del build real se registran aparte.
