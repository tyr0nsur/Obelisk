# Almacén privado de la suite

`services/SuiteStore.{h,cpp}` es una biblioteca C++ privada para datos locales. No forma parte de `libobelisk`, de la tabla C ABI ni del adaptador UE. No existe integración de permisos, wallets o economía con jugadores en vivo. El llamador aporta un sujeto externo cuya autoridad debe establecer por separado.

## Apertura y aislamiento

```cpp
using namespace Obelisk::Services;
SuiteStoreStatus status;
auto store = SuiteStore::Open("/ruta/privada/existente", "instancia-A", status);
```

El root debe existir, ser absoluto y tener modo 0700, con propietario del UID actual o root. Los ancestros reales pueden tener 0755 (p.ej. `/servidor`); deben pertenecer al UID actual/root y no permitir escritura de grupo/otros, salvo directorios sticky de esa autoridad como `/tmp`. Esto impide sustitución del root por otro UID a través de un padre modificable. Cada componente se abre con `openat`/`O_NOFOLLOW`; se rechazan `.`/`..` y symlinks. El ID de instancia es un token ASCII de 1..64 bytes con letras, números, `_` y `-`. Se crea su directorio en modo 0700 y `suite.sqlite3` en 0600. Directorios de instancia existentes y archivos DB/WAL/SHM/journal existentes deben conservar esos permisos y propietarios; se rechazan symlinks y archivos con múltiples hardlinks. Se revalida la identidad de inodes root/instancia/archivo después de abrir SQLite y antes de migrar. Las rutas son datos de un operador local confiable, no entradas de chat; ese operador debe conservarlas estables mientras haya conexiones abiertas. El propietario/root puede renombrar o alterar sus propios archivos, y no se promete aislamiento frente a esa autoridad.

Cada instancia tiene una base separada. SQLite abre en read/write, FULLMUTEX, cache privado y NOFOLLOW; el objeto añade un mutex que serializa operaciones completas de esa conexión. Otro objeto puede abrir la misma base y usar otra conexión. El propietario debe drenar sus propios llamadores antes de destruir el objeto; destruir un objeto C++ concurrentemente con sus métodos no está permitido.

Se usa WAL y `synchronous=FULL`, para un filesystem local y procesos del mismo host. WAL no es una base distribuida/compartida mediante NFS. La dependencia actual de build del laboratorio usa headers aislados y `libsqlite3.so.0` del host; no se instalaron paquetes desde este componente. [SQLite WAL](https://www.sqlite.org/wal.html), [apertura y NOFOLLOW](https://www2.sqlite.org/c3ref/open.html).

## Sujetos y ACL

`SuiteSubject{Namespace, OpaqueId}` identifica una clave de almacenamiento. Namespace es ASCII de 1..64 bytes: letras, números, `_`, `-`, `.` y `:`. OpaqueId tiene 1..256 bytes UTF-8 válido, sin NUL. Se conserva exactamente como `TEXT` con comparación BINARY: sin convertir números, normalizar Unicode, plegar mayúsculas ni interpretar nombres de storefront. No hay aliases automáticos entre namespaces.

Una cadena nativa observada de ARK no adquiere autenticación, unicidad, sesión o autoridad porque se almacene aquí. `CheckPermission` evalúa únicamente la ACL configurada para la clave externa recibida. No verifica que el llamador sea el jugador, que siga conectado o que sea administrador ARK.

API disponible:

- `CreateRole(role)` crea un rol de forma idempotente.
- `PutPermission(role, pattern, effect)` añade/reemplaza una regla allow/deny; requiere rol existente.
- `RemovePermission(role, pattern)` elimina esa regla.
- `PutMembership(subject, role, optional expiresUtcSeconds)` añade/reemplaza membresía, con expiry absoluto o sin expiry; requiere rol existente.
- `RemoveMembership(subject, role)` elimina membresía.
- `CheckPermission(subject, action, nowUtcSeconds)` evalúa una consulta sobre la instantánea de un SELECT.

Roles usan tokens ASCII de 1..64 bytes. Acciones/patrones tienen un máximo de 128 bytes y ocho segmentos ASCII no vacíos separados por puntos; cada segmento acepta letras, números, `_` y `-`. Sólo se admite un wildcard terminal de subárbol, como `history.*`. Coincide con `history.read` y descendientes, sin coincidir con `history` ni `historyExtra.read`. No se admite `*` global, glob intermedio o expresiones regulares. Las comparaciones distinguen mayúsculas.

Una membresía con `expires <= now` no está activa. Cualquier deny coincidente de un rol activo prevalece sobre todos los allows, incluso un deny amplio frente a un allow exacto. Ausencia de regla devuelve `Status::Ok` con `Allowed=false`; `ExplicitDeny` distingue denegación expresa de falta de allow. Error de input/almacenamiento nunca produce allow. No hay herencia de roles, nombres obtenidos de UE ni source de autoridad implícito.

## Wallets enteros e idempotencia

Los saldos y amounts son `int64_t` en unidades enteras; no se utilizan floats ni conversiones de moneda. Saldo mínimo cero. Amount debe ser positivo. `Balance` devuelve cero/`Exists=false` para un wallet aún inexistente. Crédito crea su wallet; una operación fallida no crea wallets parciales. Débito/transfer sin fondos devuelve `InsufficientFunds`; incremento fuera de INT64_MAX devuelve `Overflow`.

`Credit(subject, amount, operationId)`, `Debit(...)` y `Transfer(source, destination, amount, operationId)` usan un único `BEGIN IMMEDIATE` con prepared statements. La transferencia modifica origen, destino y journal dentro de la misma transacción. Se rechaza transferencia a la misma clave exacta. Un fallo durante el segundo write o el registro de la operación revierte todos los writes de esa operación. Un rollback por insuficiencia, overflow, busy o error no consume operationId.

OperationId es UTF-8 válido de 1..128 bytes, sin NUL, único para toda la base de esa instancia. El payload compara tipo de operación, namespace/ID de origen, namespace/ID de destino y amount. Un ID ya confirmado con payload idéntico devuelve `Status::Ok`, `Replayed=true` y los balances originales de esa operación, aunque los balances actuales hayan cambiado. Payload diferente devuelve `PayloadConflict` y no modifica saldos. Para consultar el saldo actual se usa `Balance` por separado.

`SuiteOperationResult::Balance` es el saldo resultante del sujeto para Credit/Debit y del origen para Transfer; `DestinationBalance` sólo describe el destino de Transfer. Son resultados válidos únicamente con `Status::Ok`. No existen pagos reales, wallet del jugador, saldo de tribu ni API de chat que ejecute estas operaciones.

Dos conexiones serializan sus writes mediante SQLite. El busy timeout es 2000 ms; `Busy` permite que el llamador reintente la misma operación sin duplicar una confirmada. No es una garantía de duración máxima ante un filesystem bloqueado. El componente revierte una transacción no confirmada al salir de su scope, incluyendo COMMIT fallido. [Transacciones SQLite y BEGIN IMMEDIATE](https://www3.sqlite.org/lang_transaction.html).

El journal de operaciones confirmadas se conserva completo: podarlo sin un contrato adicional permitiría reutilizar IDs viejos y rompería la idempotencia. Backups deben capturar un snapshot consistente de SQLite, incluyendo el estado WAL; copiar sólo el archivo principal mientras hay conexiones activas no basta.

## Schema y fallos

Schema version 1 usa `PRAGMA user_version` y un `application_id` privado. Una base nueva vacía (version 0/application 0) migra a v1 en una transacción. Una segunda apertura reconsulta la versión tras adquirir el write lock, para no migrar dos veces. Se rechazan versiones futuras, application IDs ajenos y bases v0 con objetos preexistentes; no se adopta ni sobrescribe una base de otra aplicación. Se verifican tablas/columnas esperadas al abrir. La biblioteca no ofrece downgrade ni migration de una versión futura.

`SuiteStoreStatus` distingue `Ok`, `InvalidArgument`, `InvalidPath`, `NotFound`, `InsufficientFunds`, `Overflow`, `PayloadConflict`, `Busy`, `UnsupportedSchema` y `StorageError`. Métodos públicos `noexcept` convierten excepciones internas en error. No se imprimen ni registran IDs, claves, consultas o secretos. Los parámetros SQL de negocio siempre se enlazan mediante prepared statements; SQL de schema/pragma es constante.

El archivo y directorio privados protegen frente a otros UIDs, no frente al propietario/root que puede alterar su propia base. Las comprobaciones de saldo/tipo y transacciones protegen la operación normal; este almacén no es un ledger criptográfico ni una fuente externa de autenticación.

## Verificación

`tests/core/SuiteStoreTests.cpp` usa bases SQLite reales temporales. Comprueba roles, deny sobre allow, wildcard acotado, expiry y namespaces; UTF-8 y texto con comillas/inyección como datos; reopen y journal idempotente; conflicto de payload; INT64_MAX y sobregiro; rollback después del primer wallet write y después de ambos writes mediante triggers de fallo; busy y retry; dos conexiones haciendo créditos y transferencias concurrentes; IDs duplicados y payloads en conflicto; rechazo de schema futuro/ajeno; separación por instancia y rutas privadas sin symlinks/hardlinks.

Estas pruebas son del almacén offline. No acreditan permisos, autenticación, economía ni otros efectos con jugadores reales. El root coordina CMake, compilación y ejecución; este cambio no instala paquetes, modifica ABI, carga plugins ni toca el servidor.
