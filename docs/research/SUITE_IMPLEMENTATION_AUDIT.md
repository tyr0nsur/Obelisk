# Auditoría de implementación para una suite ObeliskNative

Fecha: 2026-10-14. Revisión de código y documentación actual, sin modificar C++, compilar, llamar al juego ni tocar el servidor. Ejecutable objetivo: ASE Linux public 361.7, SHA256 `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`. Cliente Epic 361.8 observado. El estado de cada efecto real está en [OPING_PROTOTYPE.md](../OPING_PROTOTYPE.md) y [NATIVE_LINUX_FUNCTION_STAGES.md](NATIVE_LINUX_FUNCTION_STAGES.md); esta auditoría no añade aceptación de gameplay.

La base permite construir ahora un paquete útil de información, configuración e historial de observaciones. La equivalencia amplia con ArkApi exige después operaciones concretas de jugadores, inventario, estructuras, dinos y tribus. La cantidad de fixtures o comprobaciones no representa funciones de juego disponibles.

## Qué está implementado

| Área | Implementación aprovechable | Límite actual |
| --- | --- | --- |
| Carga y configuración | `core/PluginManager`, `PluginConfig`: descubrimiento, ABI C versionada, metadata, token de propietario, config por instancia, carga `.so`, limpieza de registros. | La biblioteca de un plugin no equivale a un módulo completo de gameplay. Los plugins antiguos sin contrato cooperativo permanecen cargados cuando no puede acreditarse una descarga segura. |
| Control de plugins | `runtime/PluginControl` y `OwnerExecutionGate`: socket UNIX privado, credenciales `SO_PEERCRED`, cola al hilo del juego, generaciones, pausa/reanudación/retirada y drenaje con plazo. | Autoridad del operador Linux UID/root; ninguna autoridad de jugador. No permite detener hilos arbitrarios del plugin. El contrato actual exige callbacks administrados, `LifecycleCapabilities()==1` y `PrepareUnload`. |
| Comandos | `core/CommandDispatcher` y slots públicos de `ObeliskApi`: registro de `/name`, texto UTF-8 copiado, invocación y respuesta síncrona por token, propietario, hilo y callback exactos. | Coincidencia de mensaje completo. `/ping args` no coincide con `/ping`. Registro admite nombres ASCII de 2..64 bytes; texto entrante 1..4096 y reply 1..1024 bytes. No hay parser de argumentos, aliases, árbol de comandos ni control de acceso. |
| Respuesta dirigida | `hooks/NativeChatHook`: adaptador del ELF actual, clases y conexión comprobadas, wrapper RPC dirigido y TCHAR Linux UTF-32. | La aceptación de backend no demuestra recepción. La variante Direct en la ventana de chat tiene comprobación estática/arranque; su presentación concreta requiere la aceptación del cliente indicada en la documentación actual. No hay reply diferido ni broadcast público. |
| Identidad del comando | `GetCommandPlayerWithOwnerToken` entrega nombre e ID nativo copiados, flags de disponibilidad, límites y lifetime del callback. `/whoami` lo utiliza. | ID opaco; no storefront, principal autenticado, ID único garantizado ni handle de sesión. El nombre es presentación. Las copias no autorizan consultar o responder después. |
| Lifecycle actual | `NativeChatHook::CapturePlayerLifecycle/CompletePlayerLifecycle` y `PlayerLifecycleDispatcher`: owner de UFunction/receptor, layout y clase del controller comprobados; snapshot propio por frame. Login después de `K2_PostLogin` retornado; logout antes de `OnLogout`. | Observaciones sin garantía exactly-once. No snapshot inicial de conectados, session key público, vínculo exacto entre dos eventos ni envío a un jugador encontrado en una lista. `HandleNewPlayer` es diagnóstico y distingue login/respawn; su retorno no autentica. |
| Timers | `TimerManager`: worker administrado, handles por owner, cancelación, Gate por generación, pausa que conserva one-shot/deadlines y espera acotada, drenaje antes de descargar. | El callback corre en worker: no puede llamar funciones UE ni usar tokens de comando conservados. Sí puede hacer trabajo sobre copias propias, métricas o almacenamiento local. |
| Observadores históricos | Readers privados, dispatcher de chat/copied policy, inventario/item/estructura, census, reflexión de lifecycle y correlación de principals. Hay validación de formas/copias, pruebas de ownership y mecanismos de fallo. | Productores de reflexión requieren perfil/markers/debug gates; el scanner permanece desactivado por defecto. El SHA idéntico al histórico no activa esos layouts. No son bindings actuales aceptados para juego, lookup o mutación. |
| Catálogo SDK | `DescribeResourceKind`, `DescribeGameplayPolicyEventKind`, `oDescriptorCatalog`, ejemplos de policy/chat audit. | Los descriptors describen categorías/forma de payload; no proporcionan recurso, identidad, autoridad ni operación UE. |

La API de comandos documenta explícitamente la coincidencia exacta en `include/obelisk/ObeliskApi.h`. Cambiar silenciosamente ese slot a coincidencia por prefijo rompería su contrato. El ABI ya transporta el mensaje completo, así que añadir soporte de verbos/argumentos no exige investigar UE: puede hacerse mediante una nueva modalidad/slot o registro opt-in, manteniendo el registro exacto existente. Deben distinguirse `/cmd argumento`, `/cmdx`, argumentos vacíos, UTF-8, comillas y límites. Un parser dentro del plugin por sí solo no sirve mientras el runtime no le entregue `/cmd argumento`.

El registro actual puede admitir más de un callback para el mismo texto. Un paquete que sustituya `/whoami` o `/ping` de `oPing` necesita retirar esos registros/ese plugin o usar nombres distintos; no debe causar respuestas duplicadas.

## Permisos y autorización

`core/AuthzDecisionModel.{h,cpp}` implementa realmente una evaluación `Allow/Deny/Unknown`, límites de query, owner/capability, generación/scope del principal, procedencia, rate-limit y auditoría. Es un componente puro aprovechable para probar decisiones y motivos de rechazo. En el CMake actual se enlaza al test `PermissionsAdminDecisionModelTests`, no a `libobelisk`; no existe un consumidor de permisos en `PluginManager`, comandos o la API pública.

No contiene grupos, membresías, reglas, wildcards, caducidades, base de datos, gestión de políticas ni fuente de autoridad del juego. Los campos de entrada son declaraciones booleanas aportadas por el llamador: cumplimentarlos no valida la realidad correspondiente. `CompleteRuntimeOwnedQuery()` es un ejemplo artificial (`Handle=17`, `Generation=42`, acción de muestra), no un principal ni una autorización de producción. Además, `OperatorConfig` es autoridad reconocida pero no allow-capable en el modelo actual; renombrarla a `RuntimeOwned` desde un plugin no resuelve esa falta de integración.

`PlayerPrincipalRegistry` sí mantiene tokens internos con handle/generación/registry ID, invalidación, reactivación controlada y poda. El aplicador/correlador histórico de `ProcessEvent` lo utiliza cuando su observer experimental está habilitado; no debe describirse como código inexistente. Sin embargo, el observer obliga a `dispatchLimit==0`, está gated y usa perfiles históricos. El adaptador nativo vigente publica copias por `PlayerLifecycleDispatcher` y no enlaza esas observaciones a un token de ese registry. Ningún token de principal, listado o consulta de permisos se ofrece en el SDK público actual.

Las capabilities y tokens de plugin controlan qué biblioteca puede llamar al runtime. Son autorización de plugin, no roles de un jugador. El socket de operador sí tiene una autoridad concreta: la credencial del proceso Linux externo. Es la vía actual apropiada para decisiones administrativas del runtime.

Se puede implementar ahora un motor local de políticas, grupos y almacenamiento para desarrolladores, con sujeto opaco y fuente de operador explícita, y probar sus decisiones sin UE. Falta definir y validar cómo el sujeto de una petición real adquiere autoridad. Usar nombre, forma de SteamID o ID nativo copiado para conceder poderes de admin ARK transformaría una observación en una garantía ausente. El primer paquete puede publicar acciones informativas abiertas y conservar las modificaciones administrativas en el canal del operador.

## Persistencia y SQLite

No se encontró implementación SQLite/SQL, repositorio de jugadores, migrations ni servicio de persistencia en `core`, `hooks`, `api`, `runtime`, `ue`, `plugins`, `examples` o el CMake. La persistencia existente es configuración JSON y logging; los contadores, registros y callbacks son del proceso. La escritura de configuración usa mecanismos de validación y publicación que pueden reutilizarse como patrón de rutas/config, sin convertirlos en un almacén transaccional.

Lectura del entorno: existe `/lib/x86_64-linux-gnu/libsqlite3.so.0`; Python stdlib informa SQLite 3.45.1. Faltan `/usr/include/sqlite3.h` y `sqlite3.pc` en pkg-config. Un módulo C++ necesita una dependencia de desarrollo fijada/instalada o fuente vendorizada elegida por el proyecto. No se instaló nada en esta auditoría.

Una primera base local debe aislar datos por `instance_id`, usar prepared statements y migrations, límites de cola/retención, busy timeout y transacciones pequeñas. Los IDs nativos deben almacenarse como `TEXT`, conservando su forma opaca: pueden contener caracteres o exceder un entero firmado. Tokens de invocación/owner, punteros UE y handles de registro no se guardan como identificadores persistentes.

Los callbacks de juego pueden copiar una observación a una cola propia acotada y leer un snapshot en memoria. Un timer administrado puede escribirla a SQLite desde su worker sin llamadas UE y sin hilo propio. Se conserva así el contrato managed-only. Una respuesta de chat ocurre antes de retornar el callback, a partir de datos ya preparados; no se conserva su token para completar una consulta de disco más tarde.

La cola no es almacenamiento durable hasta que la transacción confirma. Pausar conserva estado; stop/reload requiere que `PrepareUnload` vacíe los pendientes de forma acotada y cierre recursos, o devuelva `false` para mantener biblioteca/estado cargados. El manager retira timers antes de `PrepareUnload`, por lo que esa función no puede esperar un futuro tick. Ante fallo de disco no debe anunciarse que una observación quedó guardada ni eliminar la cola para facilitar una descarga.

## Players y lifecycle reutilizable

La colección inmediata puede contener observaciones copiadas con `kind`, flags, nombre/ID opcionales, instancia, timestamp, epoch y sequence. Se puede añadir un identificador propio de arranque/cobertura del plugin para distinguir reinicios y gaps de reload. Epoch/sequence sirven para ordenar y desduplicar observaciones dentro de su contexto, no como identidad persistente o autoridad de sesión.

Un índice por ID observado puede producir “visto por última vez” y “última notificación”, con cobertura desde activación. No acredita un roster completo de jugadores online: faltan conectados previos a la carga, exact-once y session key, y el ID no promete unicidad. No se debe publicar ese índice como `GetOnlinePlayers()` ni reutilizarlo para kick/reply diferido.

`ServerListPlayers`, `ServerKickPlayer`, tribe y resource APIs aparecen en fixtures/catálogos históricos. No se halló un binding nativo actual público que permita llamar esas operaciones. Reutilizar sus nombres para orientar una investigación posterior es válido; reutilizar sus layouts como demostración actual no lo es.

## Primer paquete propuesto: oEssentials

Un paquete propio con un módulo de helpers para desarrolladores y un plugin de información e historial para administradores:

1. **Comandos útiles con la API actual:** `/help`, `/rules`, `/motd`, `/serverinfo` y `/seen`, registrados como texto exacto. Respuestas privadas basadas en config y copias; `/seen` describe observaciones desde activación, no conectados confirmados. `/serverinfo` muestra instancia, versión del paquete, capabilities y estado propio de almacenamiento; mapa/slots/uptime UE requieren datos nuevos o config claramente rotulada.
2. **Historial local:** journal de login/logout observados y uso de comandos, con SQLite por instancia y exportación/consulta desde una CLI local. Puede comenzar con config JSON e historial en memoria mientras se integra SQLite; debe indicar entonces que no es persistente. No necesita nuevas funciones UE.
3. **Helpers reutilizables:** copia segura de la tabla ABI, comprobación de slots/capabilities, registro/rollback por owner, límites y copia de UTF-8, formateo de replies, config scoping y contrato cooperativo. Estas piezas existen dispersas en los plugins y se pueden extraer sin construir una SDK de objetos UE.
4. **Siguiente ampliación sin reversing:** registro opt-in por verbo y lexer de argumentos sobre el texto copiado, probado en el dispatcher y SDK. Permite `/help comando`, páginas y consultas del historial. La coincidencia exacta anterior permanece disponible.
5. **Fundación de permisos separada:** motor local y store de políticas con autoridad del operador y sujetos explícitos; ninguna operación de admin de juego hasta tener el vínculo de autoridad y la operación nativa correspondientes. Los comandos informativos anteriores son utilizables sin esa promoción.

Este paquete aporta reglas/MOTD/información en juego, observaciones consultables por el administrador y un patrón reproducible para autores de plugins. No promete economía, homes, teleports, inventario, administración de tribus, online roster ni DLLs Windows. Esas funciones necesitan sus propios bindings y casos reales.

Validación del primer paquete: pruebas de helpers/ABI/límites, rollback y hot lifecycle; store temporal con migrations, reapertura, transacción fallida, cola llena y unload rechazado con pendientes; callbacks sintéticos para copias y cobertura de observaciones. La aceptación real debe confirmar sus comandos/respuestas y su registro de notificaciones con el cliente; mantener aparte Steam, dos jugadores y sesión desconectada. Esta propuesta no se ha implementado ni probado en esta auditoría.

## Fuentes de código revisadas

- `core/CommandDispatcher.{h,cpp}`; `include/obelisk/ObeliskCommandApi.h` y slots de `ObeliskApi.h`.
- `hooks/NativeChatHook.cpp`; `core/PlayerLifecycleDispatcher.{h,cpp}`; `include/obelisk/ObeliskPlayerLifecycleApi.h`.
- `core/AuthzDecisionModel.{h,cpp}` y sus entradas CMake; `PlayerPrincipalRegistry` y `hooks/ProcessEventPlayerPrincipalLifecycle{Observer,Applicator,Correlation}`.
- `core/PluginManager.{h,cpp}`, `PluginConfig`, `OwnerExecutionGate`, `TimerManager`; `runtime/PluginControl` y `loader/Bootstrap.cpp`.
- Plugins `oPing`, `oDescriptorCatalog`, `oProcessTimer`, `oChatLogger`, `oChatAudit`, `oPolicyAudit`; documentación actual y fixtures listados del SDK.

`plugins/README.md` y numerosos textos de mayo/junio conservan restricciones del antiguo cierre completo de SDK. La petición actual del operador de crear funciones concretas y una suite propia prevalece sobre esa planificación histórica; este informe usa los contratos actuales de código y distingue cada nueva capacidad de su aceptación real.
