# Decisiones privadas de permisos por comando

`services/SuiteCommandPermissions.{h,cpp}` conecta rutas de comandos con la ACL
SQLite de `SuiteStore`, exigiendo un principal de una autoridad explícita. Es una
biblioteca privada para integración y pruebas offline. El servidor y la SDK no
exponen todavía este servicio; no hay resolver autenticado de jugadores ni
comandos de juego que concedan roles o privilegios de administrador.

## Qué aporta

El operador configura una instancia, los pares exactos
`(AuthorityId, SubjectNamespace)` confiables y rutas
`(PluginId, Command) -> Action`. Por ejemplo, `oHomes` y `/home` pueden consultar
`homes.travel`; `oAdvancedChat` y `/tell`, `chat.whisper`. No hay herencia entre
plugins, comando por prefijo, wildcard de rutas ni parsing de argumentos. El
adaptador entrega el verbo canónico de la ruta que registró, como `/home`.

La fuente de autoridad es un objeto `SuiteCommandPrincipalAuthority` instalado
por el operador o un adaptador privado autenticado. Su resolver recibe el scope
actual y devuelve un principal con namespace/ID opacos, emisor, revisión y
generación, instante de emisión y caducidad. Debe verificar por sí mismo que el
principal está conectado y corresponde a esa invocación. Resolver dos veces no
autentica nada si el proveedor inventa esas garantías: el objeto y su
implementación forman parte de la autoridad confiable del proceso.

El servicio no construye sujetos a partir de nombres, IDs nativos observados,
IDs de tribu o la apariencia de un SteamID. Un sujeto almacenado con roles no
adquiere autoridad sin resolver válido y un par de emisor/namespace permitido.
No existe un resolver nativo de producción en este cambio. El proveedor de los
tests declara hechos de autenticación deliberadamente y sólo vive en el test.

## Una decisión

`Evaluate(scope, pluginId, command)` parte de denegación. El scope contiene
instancia, epoch del proceso, token de sesión, generación del propietario y
token de invocación. Todos los números deben ser distintos de cero y coincidir
exactamente con el scope devuelto por el resolver. Estos campos son
comprobaciones de ámbito; las garantías de hilo, callback y sesión vigente
siguen perteneciendo al adaptador/runtime real.

La ruta debe existir. La revisión de autoridad y la generación del principal
deben ser válidas; la lease debe haberse emitido y seguir sin caducar. Se
consulta una ACL nueva mediante SQLite por decisión. `SuiteStore` conserva deny
sobre cualquier allow y deny cuando no hay regla. No se mantiene caché de
decisiones positivas ni de principals. Una membresía o permiso revocados desde
otra conexión no sobreviven en una caché del servicio.

La consulta devuelve también la primera caducidad de las membresías que
coinciden. Si cruza ese límite antes de terminar, el servicio rechaza la decisión.
Antes de devolver el resultado comprueba de nuevo reloj, caducidad del principal,
revisión de autoridad, principal/scope exactos y generación de configuración.
Una desconexión, revocación/rebinding de autoridad, cambio de generación o reload
durante la consulta no conserva el allow anterior.

El reloj UTC lo instala el operador. Valores negativos, excepción o retroceso
respecto al último valor aceptado cierran la decisión hasta que el reloj alcance
el valor anterior. Un reload no reinicia este límite. El servicio no llama a UE,
no tiene workers y no registra datos de jugadores.

Una decisión describe el scope actual, no es una credencial reusable o un lease
para ejecutar después. El llamador real debe comprobar el scope de runtime y
ejecutar cualquier acción nativa en el callback autorizado. Tampoco se promete
una transacción única entre SELECT de ACL y una mutación de gameplay: un cambio
ACL posterior al SELECT no puede deshacer una acción ya admitida. La autoridad
local sí debe avanzar su revisión en toda revocación/rebinding y permitir que
`Resolve` rechace el principal retirado.

## Configuración y recarga

`Configure(policy)` devuelve `Configured` cuando publica la configuración;
no es una autorización del jugador. Cada intento avanza la generación. Una
configuración inválida cierra la admisión, en lugar de conservar reglas antiguas.
`Clear()` hace lo mismo sin publicar sustitución. Un Evaluate que empezó con la
generación anterior devuelve `ConfigurationChanged` al terminar.

Límites: una instancia ASCII de 1..64 bytes, hasta 32 pares confiables y hasta
128 rutas, ambas listas no vacías. No se permiten pares ni rutas duplicados.
Emisor/plugin usan tokens ASCII de 1..64 bytes; namespaces admiten además `.` y
`:`. Comandos tienen `/` seguido de ASCII minúsculo, números, `_` o `-`, con
2..64 bytes totales. Actions usan los segmentos exactos y límites de
`SuiteStore`: 128 bytes, hasta ocho segmentos separados por puntos, sin wildcard.
IDs del sujeto mantienen el contrato UTF-8 opaco del almacén.

Dependencias de store, autoridad y reloj deben permanecer vivas. El llamador
drena sus propias llamadas antes de destruir el servicio. Configuración y
consulta se pueden usar concurrentemente; los callbacks de autoridad/reloj
corren sin el mutex del servicio. El resolver y reloj deben cumplir su propio
contrato de concurrencia. Ninguno recibe punteros UE ni acceso a APIs de plugin.

## Verificación

`SuiteCommandPermissionsTests` usa bases SQLite reales y otra conexión para
revocar membresías/permisos. Sus ocho escenarios comprueban ámbito exacto por
comando/plugin/instancia/epoch/sesión/propietario/invocación, autoridad ausente o
no confiable, namespaces observados sin promoción, deny precedence, caducidad,
revocación sin caché, desconexión/rebinding durante la decisión, reload mientras
se consulta, configuración inválida que retira reglas, límites de reloj y
fallo real de almacenamiento. También cruza la caducidad de una membresía y de
un principal entre admisión y finalización.

Estas pruebas no acreditan autenticación Steam/Epic, un permiso en gameplay o
paridad completa con un plugin de permisos ArkApi. La integración necesita una
fuente de principal autenticada, administración operativa y los casos reales de
aceptación del comando y de cada acción.
