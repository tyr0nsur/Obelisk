# Suite propia ObeliskNative para administradores de ASE

Investigación: 2026-10-14. Objetivo: paridad funcional progresiva con usos de
plugins ArkApi en ARK: Survival Evolved. Este documento y
`obelisk-suite-catalog.json` distinguen el prototipo implementado de utilidades y
el plan de módulos posteriores. No anuncian compatibilidad binaria con DLL,
cobertura completa ni aceptación Steam/Epic de la suite. Las prioridades son una
decisión del proyecto, no un ranking de ventas.

El primer módulo útil es **oEssentials**: `/help`, `/rules`, `/motd` y
`/serverinfo`, con texto configurado por el administrador y respuesta únicamente
al emisor. `/help rules|motd|info` usa argumentos opt-in. Ya tiene pruebas de
biblioteca real y controles de carga/pausa/recarga verificados en el servidor;
la aceptación de sus respuestas con clientes Epic y Steam sigue pendiente.
Conserva suscripciones durante pause/resume y carga una configuración nueva en
otra generación. No necesita inventario, grupos, moneda, un ID persistente ni
workers propios. [Estado del prototipo](../OPING_PROTOTYPE.md#suite-foundation-deployment--14-october-2026).

## Qué ofrece el ecosistema y qué derechos se han comprobado

ArkApi es el framework que carga plugins. La página oficial de ASE documenta
instalación Windows/Win64; no constituye una API nativa Linux. Permissions y
ArkShop son plugins separados, y otros productos tienen autores, dependencias y
condiciones comerciales independientes. [ASE Server API](https://ark-server-api.com/resources/ase-server-api.32/),
[catálogo oficial ASE](https://ark-server-api.com/resources/categories/ase-official-plugins.8/).

Los repositorios de [AseApi](https://github.com/ArkServerApi/AseApi) y
[ASE-Plugins](https://github.com/ArkServerApi/ASE-Plugins) incluyen licencias MIT
con avisos de copyright. Esto permite estudiar esos archivos y considerar su
reutilización conservando los avisos aplicables; no convierte todo el catálogo
en código libre. Las fichas oficiales también prohíben republicar sus paquetes.
No se redistribuyeron DLL, paquetes comerciales o configuraciones de autores
para esta investigación. [Licencia del framework](https://github.com/ArkServerApi/AseApi/blob/main/LICENSE),
[licencia de plugins públicos](https://github.com/ArkServerApi/ASE-Plugins/blob/master/LICENSE.TXT).

| Referencia primaria | Necesidad del administrador | Clasificación comprobada |
| --- | --- | --- |
| [ASE Permissions](https://ark-server-api.com/resources/ase-permissions.35/) | Grupos, permisos individuales, asignaciones temporales y grupos de tribu; almacenamiento SQLite o servidor SQL | Plugin oficial distinto del loader |
| [ASE ArkShop](https://ark-server-api.com/resources/ase-arkshop.36/) | Saldo, compras, ventas, kits, transferencias de puntos y recompensas por tiempo; depende de Permissions | Plugin oficial distinto de Permissions |
| [Crosschat Evolved](https://ark-server-api.com/resources/crosschat-evolved.209/) | Chat entre mapas; ampliación con Discord, grupos y herramientas remotas | Base gratuita y funciones premium del autor Pelayori; licencia de código no verificada aquí |
| [ASE-Plugins](https://github.com/ArkServerApi/ASE-Plugins) | Referencias públicas AdminsPermissions, AlternativeCommands, ArkHomes, ArkAdvert, CustomChat, StructuresLimit, AntiFlyerCarry, DinoColors, ShopRewards y TribeMotd | Árbol público con licencia MIT; cada adaptación necesita comprobar archivos/dependencias concretos |
| [Tribe Enforcer](https://ark-server-api.com/resources/tribe-enforcer.27/) | Consistencia de miembros y tribus entre mapas | Producto pagado de Lethal; no es una función del framework |
| [Items+](https://ark-server-api.com/resources/items.18/) | Protección y conservación de inventario y otros ajustes de objetos | Producto pagado de Lethal; su autor limita la recarga de determinados subsistemas |
| [catálogo ASE de pago](https://ark-server-api.com/resources/categories/ase-paid-plugins.10/) | También hay límites de estructuras/dinos, decay, políticas de nombres, eventos y utilidades | Productos independientes; presencia en el catálogo no autoriza copiar implementación, marca o paquete |

Estos ejemplos permiten identificar capacidades funcionales. Las condiciones y
versiones consultadas pueden cambiar. Un equivalente propio tendrá código,
configuración y pruebas propios; el nombre del producto de referencia no implica
afiliación, portabilidad de su DLL ni derecho a reutilizar sus contenidos.

La ficha ASE de Permissions nombra EOSID y la de ArkShop nombra SteamID. Esa
discrepancia documental exige corroborar el esquema y la procedencia del ID al
migrar; no autoriza convertir un ID numérico observado en una cuenta Steam o Epic.
[Permissions](https://ark-server-api.com/resources/ase-permissions.35/),
[ArkShop](https://ark-server-api.com/resources/ase-arkshop.36/).

## Frontera actual del prototipo

La ABI actual de 272 bytes permite registrar comandos, responder dentro de su
callback, obtener nombre/ID nativo copiados y observar login/logout tipados.
Los strings prestados caducan al salir del callback. El token de comando tampoco
sirve para una respuesta posterior, para otra generación o para una reconexión.
El ID nativo es una observación opaca: todavía no promete procedencia,
persistencia, unicidad ni autorización. Véanse
[`ObeliskCommandApi.h`](../../include/obelisk/ObeliskCommandApi.h) y
[`ObeliskPlayerLifecycleApi.h`](../../include/obelisk/ObeliskPlayerLifecycleApi.h).
La extensión de registro con opciones acepta argumentos expresamente solicitados
y preserva el comportamiento exacto de registros anteriores. Sus pruebas de
fixture no sustituyen la aceptación cliente de los comandos de oEssentials.

Hay timers de proceso, pero sus callbacks son de worker y no deben llamar UE.
No hay en esa tabla una API pública verificada de broadcast, respuestas
asíncronas, listado autoritativo de jugadores, permisos, tribus, entrega de
objetos, spawn de dinos o modificación de resultados de políticas. Los enums y
dispatchers históricos de observación no demuestran esas operaciones.
La nueva biblioteca SQLite propia de permisos/wallets permanece offline; no
concede autoridad nativa ni integra una tienda viva. La herramienta de
[inspección de migración](../ARKAPI_MIGRATION.md) sólo produce informes de copias
Permissions/ArkShop y bloquea importación automática de administración.

La aceptación Epic del recorrido inicial y las pruebas de control ya registradas
se mantienen en [`OPING_PROTOTYPE.md`](../OPING_PROTOTYPE.md). Este catálogo no
añade evidencia de gameplay. El objetivo sigue siendo el binario Linux public
ASE fijado en ese documento; no se extrapola a ASA u otra compilación.

## Catálogo funcional propio y orden de entrega

P0 usa primitivas actuales. P1 crea las bases de cuentas y control. P2 entrega
economía/juego y comunicación entre mapas. P3 cubre políticas avanzadas y cluster.
Cada ampliación empieza por una función nativa concreta del binario fijado,
con metadata/ABI, prueba de arranque y aceptación con clientes separados.

| Módulo propuesto | Prioridad y primera entrega | Primitiva que falta para completar su objetivo |
| --- | --- | --- |
| oEssentials | P0 implementado: ayuda, reglas, MOTD e información configurable; aceptación cliente pendiente | Ninguna para respuestas síncronas de texto |
| Identity, servicio residente | P1: cuenta con namespace/proveedor verificado y sesión invalidable | Corroborar procedencia/autenticación y estabilidad del sujeto Steam/Epic; no es el snapshot actual |
| oPermissions | P1: grupos, decisiones de acceso y expiración; denegar autoridad desconocida | Identity y administración local autenticada; consumidores de permisos |
| oPlayerTools | P1: consulta propia; después lista administrativa, kick/ban/whitelist y homes | Jugadores/sesiones autoritativos; acciones tipadas main-thread y comprobación de permiso en ejecución |
| oEconomy | P1: saldo y movimientos de moneda virtual propios, sin entrega de objetos | Identity y ledger persistente transaccional; transferencias protegidas y administración auditada |
| oShopKits | P2: catálogo y kits, empezando por un objeto vanilla permitido | Entrega/retirada de inventario y recibos verificables; dinos/XP/engramas son incrementos independientes |
| oCrossChat | P2: sólo chat global entre dos mapas; integración Discord posterior | Captura normal verificada, broadcast main-thread y cola residente; la API de Reply no equivale a broadcast |
| oScheduledRewards | P2: un premio de moneda por intervalo, con regla durable de deduplicación | Sesiones autoritativas, Identity, ledger y scheduler residente seguro |
| oStructurePolicies | P3: contar y observar; después un límite o denegación precisa | Identidad de estructura/tribu, reconciliación de mundo y hook de decisión verificado; observar no bloquea |
| oDinoPolicies | P3: consulta; después una política de carry/tame o límite | Identidad/ownership de dinos, decisiones tipadas y reconciliación; colores/spawn separados |
| oTribes | P3: lectura y MOTD con membresía verificada; sincronización de cluster después | Membership/roles reales y modelo persistente de tribu; merges/transferencias requieren protocolo propio |

El JSON conserva dependencias, estado de implementación, referencias y aceptación
por módulo. Un objetivo grande como Shop se divide en saldo, compras de moneda,
entrega de objetos y spawn; que uno pase no convierte los demás en compatibles.

## Aceptación común Steam/Epic y recarga

1. Probar un cliente Epic y uno Steam, juntos y por separado, incluyendo nombres
   iguales, nombres UTF-8, desconexión/reconexión y cambio de personaje. El nombre
   nunca es clave de cuenta ni criterio de autorización.
2. Comprobar que una respuesta privada llega sólo al emisor, que los tokens viejos
   caducan y que un resultado pendiente no llega a otra sesión/generación. El
   formato visible de chat necesita aceptación independiente de la notificación.
3. Pause debe impedir entrada de callbacks sin borrar estado/suscripciones;
   resume conserva handles y timers vencidos. Stop/reload cierra admission, drena
   callbacks y destrucciones pendientes antes de Shutdown/dlclose. La generación
   siguiente tiene binding/token nuevos; los antiguos permanecen inválidos.
4. El contrato actual managed-only admite plugins sin workers, callbacks externos
   o tareas que sigan usando su userdata. PrepareUnload ocurre después de limpiar
   registries: no puede ser el momento de detener un worker que aún usa ese dato.
   Un deadline, cleanup fallido o excepción conserva el mapa; fallos terminales
   aparecen en status y no se fuerzan ni se repite Shutdown.
5. Una validación de configuración se puede hacer antes de publicar el candidato.
   La recarga actual retira el plugin viejo antes de Init del nuevo: una config
   inválida puede dejarlo parado. No prometer rollback automático de código ni
   recuperación de estado sólo en memoria. Guardar la configuración válida previa
   y probar recuperación explícita.
6. Módulos que necesiten I/O asíncrono deben esperar un servicio residente que
   entregue datos copiados y cancele trabajos por generación, o declarar stop/
   reload no disponibles. No ampliar el contrato managed-only por una promesa de
   cerrar hilos al final. Ningún worker llama UE ni guarda pointers/tokens de Reply.

## Persistencia y migración

Una cuenta futura necesita al menos cluster, proveedor verificado y sujeto
canónico. No inferir el proveedor por longitud/formato; no usar display name,
invocation token ni process epoch como clave persistente. Probar estabilidad al
reiniciar y al cruzar mapas antes de importar permisos/saldos. Las observaciones
de login/logout pueden repetirse o faltar: no bastan para facturar tiempo conectado.

Para una instancia, se propone un almacén transaccional local con esquema
versionado; SQLite es una opción a evaluar. Para cluster, usar un servicio de
persistencia compartido con concurrencia real, no un archivo WAL en un share de
red. SQLite documenta atomicidad de sus transacciones y límites de WAL entre
hosts; estas propiedades no hacen atómica una mutación del mundo UE junto con
la base de datos. [Atomic commit](https://www.sqlite.org/atomiccommit.html),
[WAL](https://www.sqlite.org/wal.html).

El ledger conserva movimientos inmutables, importes enteros con límites, claves
idempotentes, saldo y cambio en la misma transacción. Transferencias nunca se
resuelven por nombre ambiguo. Las recompensas usan una clave durable de cuenta,
regla y periodo; reinicio/reload/clock rollback no deben crear otro premio. El
tiempo pausado y el tiempo conectado deben tener una política explícita y probada.

Compras/kits requieren reserva, entrega y recibo reconciliable. Si el proceso cae
después de dar un objeto pero antes de registrar el recibo, no se puede prometer
exactly-once sin una evidencia persistente del lado del mundo. Un resultado
incierto queda bloqueado para revisión/reconciliación; no regalar otra copia ni
reembolsar automáticamente mientras el primer objeto pueda existir.

La importación usa copias autorizadas por el operador, conserva la fuente y hace
dry-run de esquema, proveedor, tipos, totales y cuentas ambiguas. No reemplazar
en vivo tablas ArkShop/Permissions ni inventar datos cuando una base antigua no
esté disponible. Guardar backup, versión y reporte de conciliación; los saldos
de Obelisk empiezan según una política propia explícita. No se importó nada aquí.

## Aceptación funcional específica

| Área | Primer caso que debe demostrar utilidad | Casos que impiden anunciar paridad |
| --- | --- | --- |
| Permissions | Grupo local habilita un comando protegido sólo a su cuenta verificada | Suplantación por nombre/ID desconocido, permiso vencido activo, fallo DB que concede acceso |
| Economy | Dos cuentas transfieren una cantidad válida y conservan totales tras reinicio | Doble movimiento por retry/reload, saldo negativo por carrera, overflow o cuenta Steam/Epic mezclada |
| Shop/Kits | Un kit vanilla entrega exactamente el contenido aceptado y registra el consumo | Inventario lleno, entrega parcial, muerte/transfer durante la operación, recibo incierto después de crash |
| Crosschat | Un mensaje global viaja una vez entre dos mapas y aparece con origen correcto | Bucles de eco, envío de chat local/tribu por defecto, duplicados al reconectar broker, backpressure sin límite |
| Player/Admin tools | Consulta propia y kick protegido afectan al destino correcto | Actor desconectado, destino ambiguo, sesión nueva reutilizando una antigua referencia |
| Structures/Dinos | Un límite preciso respeta ownership y vuelve a contar después de restart | Contador que deriva por demolición, muerte, transferencia, stasis, carga o tribu cambiada; hooks de observación tratados como bloqueo |
| Tribes | Miembros con igual tribu ven su MOTD; otro jugador no puede editarlo | ID reutilizado, rol revocado, mapas divergentes, merge que cambia ownership sin reconciliación |
| Rewards | Un intervalo concede un movimiento durable y auditable a la cuenta correcta | Duplicación al relogin/reload/restart, sesión inferida por eventos incompletos, premio mientras la regla está pausada |

Las primeras implementaciones deben seguir este orden hasta el primer resultado
útil, manteniendo mundo/personajes actuales y hooks nativos residentes. El
catálogo no sustituye evidencias ni obliga a desarrollar toda la suite antes de
publicar un módulo pequeño verificado.
