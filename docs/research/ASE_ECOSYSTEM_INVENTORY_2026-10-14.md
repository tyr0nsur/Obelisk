# Inventario verificable del ecosistema ASE — 14 de octubre de 2026

El objetivo autorizado es reproducir los resultados de gameplay de los plugins ArkApi de ASE con implementaciones originales de ObeliskNative. El trabajo comienza fijando qué producto, versión, configuración y escenario se comparan; una lista de nombres o comandos no certifica equivalencia.

Este snapshot contiene **157 fichas distintas** de las categorías públicas del catálogo: **4 oficiales, 91 gratuitas y 62 de pago**. Una ficha es el framework; quedan **156 registros de plugins o integraciones**, que no son necesariamente 156 productos distintos: Admins Permissions aparece con dos IDs. No se declara un censo de todos los plugins existentes ni paridad de ninguno por haber inventariado su ficha.

## Alcance y método

Consulta realizada a páginas primarias del editor/autor a través de ArkServerApi. Se recorrieron las diez páginas anunciadas de las tres categorías (1 + 5 + 4), extrayendo únicamente las tarjetas principales. Las recomendaciones, publicidad, sidebar y productos ASA no se mezclaron con ASE. Los 157 detalles públicos se recuperaron con HTTP 200 y se registraron sus URLs y SHA256 de respuesta HTML. La descarga ordinaria sin User-Agent produjo un 403 en el host desnudo; el host www con User-Agent de navegador devolvió el HTML público. No se inició sesión, adquirió un paquete ni descargó una DLL.

Las capacidades se resumen con redacción propia. Los tokens de comandos del JSON se extrajeron de documentación pública y aún necesitan revisar gramática, aliases, argumentos, configuración y casos de error. Una mención de Permissions, ArkShop, SQL, Discord o RCON no se presenta automáticamente como una dependencia obligatoria. La valoración de primitivas necesarias es una decisión técnica propia del proyecto, no una afirmación del proveedor.

No se consultaron cuerpos de implementación de terceros (.cpp, .h, etc.), no se copiaron configuraciones ni se incorporaron marcas/paquetes. Del repositorio oficial se consultaron sólo metadatos de directorio y su README general. Esta investigación no es una autorización de compatibilidad binaria con DLL Windows.

Las versiones y fechas son metadatos observados del catálogo, no versiones de binarios comprados o validados. El JSON separa `catalog_pagination_complete=true`, `ecosystem_complete=false` y `all_product_behavior_specified=false`.

| Fuente primaria | Páginas comprobadas | Registros | Cobertura |
| --- | ---: | ---: | --- |
| [Oficiales ASE](https://ark-server-api.com/resources/categories/ase-official-plugins.8/) | 1 | 4 | Todas las páginas anunciadas del snapshot |
| [Gratuitos ASE](https://ark-server-api.com/resources/categories/ase-free-plugins.9/) | 5 | 91 | Todas las páginas anunciadas del snapshot |
| [Pago ASE](https://ark-server-api.com/resources/categories/ase-paid-plugins.10/) | 4 | 62 | Todas las páginas anunciadas del snapshot |
| [Foro ASE](https://ark-server-api.com/forums/ase-plugins.7/) | 12 | 223 hilos | Índice de títulos; mezcla software, borrados, duplicados y anuncios |
| [Repositorio oficial ASE-Plugins](https://github.com/ArkServerApi/ASE-Plugins) | Directorio raíz y README | 20 entradas | AtlasShop excluido del objetivo ASE; metadatos no equivalen a contratos |

El foro y el repositorio amplían las referencias; sus cifras **no se suman** a las fichas como si fueran nuevos plugins. Quedan fuera del cierre cuantitativo ASA, Atlas, ASE Software, General Software, anuncios de otros sitios, plugins privados, fichas eliminadas y distribuidores no identificados. La integración externa de un plugin incluido sí se describe como parte de su comportamiento.

## Contratos que desbloquean la suite

La referencia visual, destinatarios, cambios de mundo, costes, límites, persistencia y fallos deben coincidir en escenarios fijados. Los siguientes resúmenes se basan en documentación pública y señalan brechas del prototipo; requieren todavía aceptación dentro del juego.

### ASE ArkShop — 3.05

[Ficha primaria](https://www.ark-server-api.com/resources/ase-arkshop.36/). Alcance: contrato público de jugador y persistencia; referencia 3.05.

Comandos documentados seleccionados: `/points`, `/buy <ID> <Amount>`, `/trade <CharacterName> <Amount>`, `/kit [KitName]`, `/buykit <KitName> <Amount>`, `/shop [Page]`, `/sell <ID> <Amount>`, `/shopsell [Page]`, `/shophelp`, `/shopfind <search>`.

- Saldo propio, catálogo paginado y búsqueda; compra y venta cambian inventario y moneda con cantidades verificadas.
- Un kit comprado se reclama mediante acción separada; preservar máximos, costes y cooldowns documentados para la configuración seleccionada.
- Referencia incluye recompensas por tiempo y dependencia Permissions; documenta SteamID para operaciones administrativas.

Brecha de ObeliskNative: oShopKits actual es catálogo informativo; no compra, vende, cobra ni entrega. Ledger y recibos privados offline no prueban paridad de juego.

### ASE Permissions — 2.1

[Ficha primaria](https://www.ark-server-api.com/resources/ase-permissions.35/). Alcance: administración de grupos y permisos; referencia 2.1.

Comandos documentados seleccionados: `Permissions.Add`, `Permissions.Remove`, `Permissions.AddTimed`, `Permissions.RemoveTimed`, `Permissions.PlayerGroups`, `Permissions.AddTribe`, `Permissions.RemoveTribe`, `Permissions.AddTribeTimed`, `Permissions.RemoveTribeTimed`, `Permissions.TribeGroups`, `Permissions.AddGroup`, `Permissions.RemoveGroup`, `Permissions.Grant`, `Permissions.Revoke`, `Permissions.GroupPermissions`, `Permissions.ListGroups`, `/groups`.

- Grupos permanentes y temporales de jugadores y tribus; concesión y revocación de permisos.
- La ficha presenta EOSID en comandos de cuenta; no normalizarlo por longitud ni tratar el ID nativo observado como EOSID verificado.

Brecha de ObeliskNative: Almacén propio probado offline; falta vincular permisos a cuenta verificada y administrar decisiones reales.

### ArkHomes — 1.32

[Ficha primaria](https://www.ark-server-api.com/resources/arkhomes.43/). Alcance: homes y destinos públicos; referencia 1.32.

Comandos documentados seleccionados: `/addhome <HomeName>`, `/removehome <HomeName>`, `/home <HomeName>`, `/listhomes`, `/tp <LocationName>`, `/tplist`.

- Los puntos persisten en SQLite; parámetros de retardo, cooldown y mensajes configurables.
- Condiciones por proximidad a base amiga o enemiga e integración de Permissions/ArkShop; viajes a puntos públicos del servidor.

Brecha de ObeliskNative: oHomes es de sesión y usa /sethome, /delhome, /homes; pierde puntos tras relogin/reload. Necesita persistencia, save identity, proximidad, permisos, costes y aliases de migración comprobados.

### Crosschat Evolved — 1.6.1

[Ficha primaria](https://www.ark-server-api.com/resources/crosschat-evolved.209/). Alcance: base y extensiones premium diferenciadas; referencia 1.6.1.

Comandos documentados seleccionados: `/online`, `/pm`, `/r`, `/ignore`, `/unignore`, `/chatmode`, `/tribelog`, `/enabletag`, `/disabletag`, `/setdiscord`.

- Chat entre mapas con servidor SQL; revisar separación entre funciones gratuitas y premium.
- La página describe comunicación privada y opciones de formato/integración; destinatarios y aislamiento necesitan escenarios con dos mapas y clientes.

Brecha de ObeliskNative: oAdvancedChat expone global y /tell sólo en servidor actual sobre sesiones observadas; no roster autoritativo, respuestas /r, cluster ni integración Discord.

### Advanced Messages — 2.22

[Ficha primaria](https://www.ark-server-api.com/resources/advanced-messages.52/). Alcance: mensajería, bienvenida y anuncios; referencia 2.22.

Comandos documentados seleccionados: `am.sendchat`, `am.sendserver`, `am.sendnotification`, `am.chatasplayer`, `am.reload`.

- Rutas diferentes para mensaje de chat cliente, chat servidor y notificación.
- Anuncios por intervalo, mensajes de bienvenida, destinatario concreto o global, colores y parámetros visuales.

Brecha de ObeliskNative: Respuesta al comando y chat a sesiones observadas no sustituyen anuncios con scheduler seguro ni protocolos de colores/iconos/notificación.

### Dino Colour Command — 2.5

[Ficha primaria](https://www.ark-server-api.com/resources/dino-colour-command.130/). Alcance: color de dino por región; referencia 2.5.

Comandos documentados seleccionados: `/sdc <Region> <Colour>`, `/cdc <DinoName> <Region> <Colour>`, `dcc.reload`.

- Identificar dino de destino; interpretar región y color por número o nombre según la configuración.
- Aplicar color replicado y persistente con decisión de propiedad, permiso y coste en los casos documentados.

Brecha de ObeliskNative: oWorldTools sólo copia ID de montura. No tiene selección de dino apuntado, mutation de color ni autoridad de propiedad.

### Dino Tracker — 2.0

[Ficha primaria](https://www.ark-server-api.com/resources/dino-tracker.125/). Alcance: búsqueda y seguimiento de dinos propios; referencia 2.0.

Comandos documentados seleccionados: `/track`, `/trackadmin`.

- Listado paginado y búsqueda parcial por nombre o especie con resultados útiles.
- Separar alcance de la tribu, administración y posibles funciones premium; localizar animales cargados o en stasis según el contrato seleccionado.

Brecha de ObeliskNative: Falta enumeración autoritativa de actores, nombres copiados y pertenencia real; consulta de una montura no equivale al censo.

### Structures Limit — 2.5.1

[Ficha primaria](https://www.ark-server-api.com/resources/structures-limit.115/). Alcance: política de construcción; referencia 2.5.1.

Comandos documentados seleccionados: `/ShowLimits`, `sl.reload`.

- Contar estructuras globales y por clase; aplicar límites con ownership real.
- Reconciliar demolición, carga, restart, cambio de tribu y merges; demostrar una denegación concreta al construir.

Brecha de ObeliskNative: Un ID de estructura apuntada no es contador ni hook de decisión; no anunciar límite sin prueba de bloqueo y reconciliación.

### Dino Limit — 1.9

[Ficha primaria](https://www.ark-server-api.com/resources/dino-limit.128/). Alcance: política de dinos; referencia 1.9.

Comandos documentados seleccionados: `/DinoLimits`, `dl.reload`, `UpdateDinos`, `GetDinoBp`.

- Límites por tribu y tipo; revisar tame, claim, cryo, upload/download, clonación, compra, merge y variantes.
- El alcance debe estar explícito por mapa/cluster y por integraciones de mods que la ficha presenta.

Brecha de ObeliskNative: Faltan censo, propiedad/tribu, hooks de decisiones y protocolo de transferencia; identidad de montura aislada no ofrece límites.

### Tribe Enforcer — 2.02

[Ficha primaria](https://www.ark-server-api.com/resources/tribe-enforcer.27/). Alcance: sincronización de tribus; referencia 2.02.

Comandos documentados seleccionados: `te.addplayer`, `te.reload`.

- Mismos miembros e identidad de tribu entre mapas mediante SQL; sincronizar invitación, expulsión, ascenso y descenso.
- Coordinar cambios de ownership y rol con transacciones y reconcilación; un merge no es cambiar un entero copiado.

Brecha de ObeliskNative: /tribe consulta un ID opaco local; no demuestra membresía autenticada, roles ni autoridad cross-map.

### RCON Scheduler — 1.38

[Ficha primaria](https://www.ark-server-api.com/resources/rcon-scheduler.64/). Alcance: calendario administrativo; referencia 1.38.

Comandos documentados seleccionados: `RconScheduler.Reload`.

- Ejecutar acciones al inicio, por intervalo o a horas de reloj real.
- Definir cronología tras reload, reinicio, cambio de hora y pausa; controlar duplicados de premios o acciones.

Brecha de ObeliskNative: Timers worker actuales no pueden tocar UE. Falta scheduler residente con ejecución main-thread y cancelación por generación.

### Fast Rejoin — 0.1

[Ficha primaria](https://www.ark-server-api.com/resources/fast-rejoin.94/). Alcance: reconexión de una cuenta; referencia 0.1.

- Al entrar una cuenta ya conectada, terminar la sesión anterior para permitir reconexión tras caída de cliente.
- Evitar doble sesión o expulsión de otra cuenta y probar reconexión Steam y Epic; conservar generación y expiración de tokens.

Brecha de ObeliskNative: Observaciones de login/logout y token de sesión no prueban identidad autenticada ni decisión de admisión.

### Lethal Trades — 2.02

[Ficha primaria](https://www.ark-server-api.com/resources/lethal-trades.22/). Alcance: intercambio en el mismo mapa; referencia 2.02.

Comandos documentados seleccionados: `/tradewith`, `/tradelock`, `/tradeconfirm`, `/tradecancel`.

- Presentar oferta mediante cajas de intercambio y obtener confirmación de ambas partes.
- Evitar pérdida o duplicación si cambian objetos, muere/se desconecta un jugador, se llena inventario o cae el proceso.

Brecha de ObeliskNative: No hay mutaciones y recibos verificados de inventario ni máquina de estados de negociación integrada.

## Dependencias y restricciones concretas

- **ArkShopUI** necesita la combinación de ArkShop oficial 3.02+, Permissions, plugin ArkShopUI y [mod cliente 2693727499](https://steamcommunity.com/sharedfiles/filedetails/?id=2693727499) según [su ficha](https://ark-server-api.com/resources/arkshopui.28/). La ficha limita la DLL aceptada. Crear una tienda por chat no demuestra equivalencia visual ni soporte de ese mod en Epic/Linux; el protocolo de UI y la matriz de clientes son entregas independientes.
- **Pull Prevention** declara dependencia del mod SuperStructures. La política debe probarse contra esa integración si forma parte del perfil elegido. [Ficha](https://ark-server-api.com/resources/pull-prevention.45/).
- **Cross Server Chat** está marcado obsoleto por su autor y remite a Crosschat Evolved. Se conserva como perfil histórico identificable; no se cuenta como una segunda implementación aceptada. [Ficha](https://ark-server-api.com/resources/cross-server-chat.46/).
- **Turrets Attack Noglins** requiere activación en el arranque para su efecto documentado; `plugins.load` no lo activa. **RCON Scheduler** exige servidor offline para instalar/actualizar DLL y distingue esa acción de recargar su calendario. Nuestros módulos deben documentar su propia capacidad de recarga por función. [Noglins](https://ark-server-api.com/resources/turrets-attack-noglins-free.204/), [Scheduler](https://ark-server-api.com/resources/rcon-scheduler.64/).
- **Permissions** presenta EOSID en comandos; **ArkShop** presenta SteamID. ObeliskNative debe verificar procedencia de cuenta y adaptar la migración por namespace/proveedor, sin inferirlo del número nativo actual. [Permissions](https://ark-server-api.com/resources/ase-permissions.35/), [ArkShop](https://ark-server-api.com/resources/ase-arkshop.36/).

## Orden de implementación original

1. Identidad verificada Steam/Epic y roster autoritativo: sujeto canónico, invalidación de sesión, account vs character, roles de tribu y admisión. Es la base para permisos, economía, listas, bans y cluster.
2. Cola y scheduler residentes: datos copiados, ejecución de juego en el hilo principal, cancelación por generación/sesión y deadlines. Permite anuncios, delays, cooldowns, IO externo y trabajos de mundo sin workers que llamen UE.
3. Inventario y recibos: especificar clase, cantidad, calidad, estado, serialización y consecuencias de entrega parcial. Un bool de “añadió algo” no prueba entrega exacta. Conectar ledger sólo cuando cobro/entrega puedan reconciliarse.
4. Permisos y ledger propios integrados: denegación por identidad desconocida, administración auditada, movimientos idempotentes y reservas durables. No otorgar autoridad desde display names, tokens o IDs observados.
5. Mundo y ownership: censo y búsqueda de actores, pertenencia/roles de tribu y reconciliación de carga/stasis/merge/transfer. Desbloquea tracker, límites, proximidad homes, estructuras y herramientas de dinos.
6. Hooks de decisión, cluster y UI: probar bloqueos reales, transporte con deduplicación y backpressure, visibilidad de HUD/chat y contratos externos. Completar por escenario y plataforma cada familia.

Primeras entregas útiles después de esas primitivas: anuncios/bienvenida y programación administrativa; aliases y persistencia de homes; saldo/transferencias y un kit vanilla comprobable; búsqueda de dinos y una mutación de color autorizada; límites con reconciliación; chat entre dos mapas y respuesta privada. Ninguna prioridad equivale a completar todos los productos de esa familia.

## Matriz de aceptación para cada referencia

| Campo | Evidencia exigida |
| --- | --- |
| Perfil | Producto, versión, configuración autorizada y escenario fijados |
| Entrada | Comando exacto, argumentos, alias, UI o evento automático |
| Salida | Texto/colores/iconos/notificación, formato, destinatarios y alcance |
| Gameplay | Objeto/actor concreto, cantidad/estado, propiedad, resultado replicado |
| Restricciones | Permisos, costes, cooldown, límites, ausencia de daño o de cobro en rechazo |
| Persistencia | Relogin, restart, mapa, personaje, cambio de tribu y config reload |
| Fallos | Inventario lleno, destino ausente, doble intento, crash y resultado incierto |
| Lifecycle | Pause/resume, stop/reload y cancelación de trabajos sin sesión/generación vieja |
| Clientes | Steam y Epic, separados y juntos, incluidas privacidad y nombres idénticos/UTF-8 |
| Registro | Fecha, prueba, esperado, observado, vídeo/captura y logs privados redactados |

Fixtures, reverse engineering estática, hashes de arranque y tests de biblioteca prueban sus respectivos niveles; no son evidencia de equivalencia del gameplay. El inventario no modifica el estado de aceptación cliente documentado en el proyecto.

## Catálogo completo de las tres categorías

Cada línea conserva una ficha aunque comparta nombre con otra. La descripción es una síntesis propia de la superficie pública; detalles o garantías comerciales del autor aún no se han demostrado por ObeliskNative. En el JSON figuran URL de página, versión, fechas, huellas, tokens candidatos, familia y primitivas requeridas. Cada ficha fija un `reference_profile` por ID/versión observada y una matriz de sintaxis, límites por defecto, persistencia, salida visual, GUI/mod de cliente, fallos/lifecycle y aceptación Steam/Epic. Las celdas están `Pending`; `ByeByeCorrupted` queda `NoDoc` porque la ficha sólo remite a implementación que no se consultó. No se rellenan valores por defecto desconocidos.

### Oficiales

| ID | Referencia y versión listada | Capacidad pública resumida | Familia |
| ---: | --- | --- | --- |
| 28 | [ArkShopUI](https://www.ark-server-api.com/resources/arkshopui.28/) · 3.05 | Interfaz visual de tienda mediante plugin y mod de cliente | `economy_ui` |
| 36 | [ASE ArkShop](https://www.ark-server-api.com/resources/ase-arkshop.36/) · 3.05 | Saldo, compras, venta, kits, transferencias y pagos por tiempo | `economy` |
| 35 | [ASE Permissions](https://www.ark-server-api.com/resources/ase-permissions.35/) · 2.1 | Grupos, permisos y asignaciones temporales para cuentas y tribus | `identity_permissions` |
| 32 | [ASE: Server API](https://www.ark-server-api.com/resources/ase-server-api.32/) · 3.56 | Carga de plugins del framework ASE para Windows | `framework` |

### Gratuitos

| ID | Referencia y versión listada | Capacidad pública resumida | Familia |
| ---: | --- | --- | --- |
| 517 | [Vote Rewards [UFS] ASE](https://www.ark-server-api.com/resources/vote-rewards-ufs-ase.517/) · 1.0 | Canjear recompensas por votos en el servicio UFS | `rewards_events` |
| 384 | [FarmSolo](https://www.ark-server-api.com/resources/farmsolo.384/) · 2.0 | Golpe de recolección del anquilosaurio transportado para jugar solo | `dino_tools` |
| 460 | [DP Crosschat - Servers+Discord /w Discord Bot](https://www.ark-server-api.com/resources/dp-crosschat-servers-discord-w-discord-bot.460/) · V2.1.1 | Chat y estado de servidores con integración de bot Discord | `chat_cluster` |
| 419 | [X Chatlog](https://www.ark-server-api.com/resources/x-chatlog.419/) · v1.3 | Enviar distintos canales de chat a webhooks separados | `chat_cluster` |
| 425 | [X Notify](https://www.ark-server-api.com/resources/x-notify.425/) · v1.3 | Avisos de entrada y salida entre mapas del mismo host | `chat_cluster` |
| 420 | [X Data Plus](https://www.ark-server-api.com/resources/x-data-plus.420/) · v1.3 | Historial de jugadores, actividad, tiempo y bajas en MySQL | `identity_data` |
| 388 | [Blocked Commands](https://www.ark-server-api.com/resources/blocked-commands.388/) · V1.4 | Bloqueo temporal de comandos configurable para inicio de wipe | `operations_scheduler` |
| 473 | [TazzStatLimits](https://www.ark-server-api.com/resources/tazzstatlimits.473/) · V1 | Límites de estadísticas definidos por tipo de objeto | `inventory_items` |
| 185 | [ARK SE Tip4Serv Donation Webstore](https://www.ark-server-api.com/resources/ark-se-tip4serv-donation-webstore.185/) · 2.0.2 | Integración de tienda web con órdenes autenticadas por HMAC | `economy_external` |
| 465 | [X Shop](https://www.ark-server-api.com/resources/x-shop.465/) · v1.3 | Ampliaciones de precios y cooldowns de temporada sobre ArkShop | `economy` |
| 461 | [Caged](https://www.ark-server-api.com/resources/caged.461/) · V1 | Temporizador persistente de cautiverio iniciado por el jugador | `player_tools` |
| 457 | [0xCrossServerChat](https://www.ark-server-api.com/resources/0xcrossserverchat.457/) · f5d64a0 | Chat entre mapas, moderación y retransmisión opcional a Discord | `chat_cluster` |
| 400 | [HarvestX](https://www.ark-server-api.com/resources/harvestx.400/) · V1.5 | Ajustar la cantidad recolectada de recursos específicos | `rates_balance` |
| 455 | [0xDinoBalancer](https://www.ark-server-api.com/resources/0xdinobalancer.455/) · 16959a0 | Balance configurable por especie de dinos domesticados | `rates_balance` |
| 454 | [DediPlus](https://www.ark-server-api.com/resources/dediplus.454/) · V1 | Descarga a almacenamiento dedicado y extracción de recursos cercanos | `structures_inventory` |
| 439 | [X Saddlegun](https://www.ark-server-api.com/resources/x-saddlegun.439/) · v1.0 | Arma que equipa monturas de inventario a dinos de la tribu | `dino_tools` |
| 438 | [NeuterGun](https://www.ark-server-api.com/resources/neutergun.438/) · 1.0 | Castración de dinos propios mediante arma y comando configurable | `dino_tools` |
| 437 | [WaterEverywhere](https://www.ark-server-api.com/resources/watereverywhere.437/) · 1.0 | Suministro de agua a tuberías nuevas y existentes | `structures_policies` |
| 432 | [ShadowTicketsPlugin](https://www.ark-server-api.com/resources/shadowticketsplugin.432/) · 1.0 | Tickets de soporte entre jugadores y personal de Discord | `chat_support` |
| 209 | [Crosschat Evolved](https://www.ark-server-api.com/resources/crosschat-evolved.209/) · 1.6.1 | Chat de cluster gratuito; extensiones premium de comunicación | `chat_cluster` |
| 407 | [AdminESP](https://www.ark-server-api.com/resources/adminesp.407/) · 2026-06-09 | Visualización administrativa de jugadores y estructuras con ámbitos | `player_admin` |
| 402 | [StructureToggle](https://www.ark-server-api.com/resources/structuretoggle.402/) · 1.1 | Encender o apagar estructuras cercanas filtradas por clase y tribu | `structures_policies` |
| 401 | [TameBlock](https://www.ark-server-api.com/resources/tameblock.401/) · V1 | Restringir tame, claim y liberación de cryopod por fases de wipe | `dino_policies` |
| 399 | [AutoDinoXP](https://www.ark-server-api.com/resources/autodinoxp.399/) · 1.2 | Aplicar una cantidad objetivo de XP al tame o claim | `dino_tools` |
| 376 | [KillLogs](https://www.ark-server-api.com/resources/killlogs.376/) · V1.2 | Registrar bajas de jugadores y dinos en distintos destinos | `identity_data` |
| 276 | [Anti Dino Mesh](https://www.ark-server-api.com/resources/anti-dino-mesh.276/) · 1.1 | Control de dinos dentro de regiones configuradas contra mesh | `dino_policies` |
| 375 | [PlayerData](https://www.ark-server-api.com/resources/playerdata.375/) · V1 | Historial de identidad, tribu, mapa, conexiones e IP | `identity_data` |
| 365 | [HM Shop - Web Shop System for ARK](https://www.ark-server-api.com/resources/hm-shop-web-shop-system-for-ark.365/) · 2026-02-27 | Órdenes y gestión mediante tienda web externa | `economy_external` |
| 330 | [Shadow Link](https://www.ark-server-api.com/resources/shadow-link.330/) · 1.0 | Vincular cuenta del juego y Discord mediante código de un uso | `identity_external` |
| 314 | [Events Manager ASE](https://www.ark-server-api.com/resources/events-manager-ase.314/) · 1.0 | Programar eventos del plugin Server Events en varios servidores | `rewards_events` |
| 213 | [MessagePlus](https://www.ark-server-api.com/resources/messageplus.213/) · 1.51 | Formato de chat con colores, iconos y avisos Discord | `chat_cluster` |
| 287 | [RewardsEvolved](https://www.ark-server-api.com/resources/rewardsevolved.287/) · 1.0 | Entregar recompensas configuradas, fijas o aleatorias | `rewards_events` |
| 279 | [Sh Info System](https://www.ark-server-api.com/resources/sh-info-system.279/) · 1.1 | Persistir estado de servidor y datos de jugador para integraciones | `identity_data` |
| 277 | [Kick All](https://www.ark-server-api.com/resources/kick-all.277/) · 1.0 | Expulsión de jugadores del mapa con excepción del ejecutor local | `player_admin` |
| 214 | [SkipDay](https://www.ark-server-api.com/resources/skipday.214/) · 1.1 | Votación de jugadores conectados para saltar la noche | `operations_scheduler` |
| 211 | [Offline Shaming FREE](https://www.ark-server-api.com/resources/offline-shaming-free.211/) · 2.0 | Avisos de ataques a tribus desconectadas, con integración de cluster | `combat_pvp` |
| 205 | [No Fly List FREE](https://www.ark-server-api.com/resources/no-fly-list-free.205/) · 1.05 | Restringir vuelo o montura según criatura y mapa | `dino_policies` |
| 204 | [Turrets Attack Noglins! FREE](https://www.ark-server-api.com/resources/turrets-attack-noglins-free.204/) · 1.0 | Permitir a torretas atacar Noglins | `combat_pvp` |
| 203 | [Engram Resource Puller FREE](https://www.ark-server-api.com/resources/engram-resource-puller-free.203/) · 1.03 | Transferir recursos cercanos hacia recetas de una estructura | `structures_inventory` |
| 202 | [Item Collector FREE](https://www.ark-server-api.com/resources/item-collector-free.202/) · 1.11 | Recolectar objetos de dinos propios hacia estructuras configuradas | `structures_inventory` |
| 201 | [No Explorer Note XP FREE](https://www.ark-server-api.com/resources/no-explorer-note-xp-free.201/) · 1.02 | Control de XP y bonificaciones de notas de explorador | `player_tools` |
| 200 | [Color Things FREE](https://www.ark-server-api.com/resources/color-things-free.200/) · 1.0 | Colorear dinos, estructuras y equipamiento mediante comandos | `cosmetics` |
| 199 | [AutoCrafting FREE](https://www.ark-server-api.com/resources/autocrafting-free.199/) · 1.02 | Fabricación automática seleccionando recetas en carpeta de inventario | `structures_inventory` |
| 198 | [Dino Utilities FREE](https://www.ark-server-api.com/resources/dino-utilities-free.198/) · 1.31 | Utilidades de reproducción, crianza, monturas, cryopods y atributos | `dino_tools` |
| 197 | [No Building On Spawn Points FREE](https://www.ark-server-api.com/resources/no-building-on-spawn-points-free.197/) · 1.02 | Restringir construcción alrededor de puntos de aparición | `structures_policies` |
| 196 | [Structure Utilities FREE](https://www.ark-server-api.com/resources/structure-utilities-free.196/) · 1.07 | Salud, inventarios, límites y utilidades para estructuras | `structures_policies` |
| 195 | [AutoSaddles FREE](https://www.ark-server-api.com/resources/autosaddles-free.195/) · 1.01 | Equipar monturas automáticamente tras domesticar dinos elegibles | `dino_tools` |
| 194 | [Player Utilities FREE](https://www.ark-server-api.com/resources/player-utilities-free.194/) · 1.14 | Utilidades de jugador, recuperación, reparación y herramientas de estructuras | `player_tools` |
| 193 | [PLANNED PVP](https://www.ark-server-api.com/resources/planned-pvp.193/) · 1.13 | Programar periodos PvP y políticas de protección PvE | `combat_pvp` |
| 192 | [ByeByeCorrupted](https://www.ark-server-api.com/resources/byebyecorrupted.192/) · 1.0 | Referencia pública de utilidad para criaturas corruptas; contrato no detallado | `dino_policies` |
| 167 | [Vaultorama - Virtual Vaults](https://www.ark-server-api.com/resources/vaultorama-virtual-vaults.167/) · v1.2 | Almacenes virtuales de inventario con recuperación y transporte | `inventory_items` |
| 169 | [Stats Balance - Litings [DinoBalance]](https://www.ark-server-api.com/resources/stats-balance-litings-dinobalance.169/) · v1.0 | Ajustes de balance de estadísticas de criaturas | `rates_balance` |
| 166 | [SpawnItem](https://www.ark-server-api.com/resources/spawnitem.166/) · 1.1 | Generación configurada de objetos; gramática pendiente de revisión | `inventory_items` |
| 160 | [RIP](https://www.ark-server-api.com/resources/rip.160/) · Version v1.1 | Comando de suicidio para el propio jugador | `player_tools` |
| 61 | [No Wander+](https://www.ark-server-api.com/resources/no-wander.61/) · 1.87 | Utilidades de crianza y reproducción sin necesidad de wander | `dino_tools` |
| 155 | [Teleport](https://www.ark-server-api.com/resources/teleport.155/) · 1.0 | Solicitudes y aceptación de teleport entre jugadores | `player_homes` |
| 154 | [Admins Permissions](https://www.ark-server-api.com/resources/admins-permissions.154/) · 1.2 | Permisos por comando administrativo; ficha duplicada por revisar | `identity_permissions` |
| 153 | [Plugin Crash Manager](https://www.ark-server-api.com/resources/plugin-crash-manager.153/) · 1.1 | Gestión de fallos de plugins según contrato público | `operations_runtime` |
| 152 | [Unicode RCON](https://www.ark-server-api.com/resources/unicode-rcon.152/) · 1.2 | Tratamiento Unicode de comandos y respuestas RCON | `operations_runtime` |
| 145 | [Chat Icons](https://www.ark-server-api.com/resources/chat-icons.145/) · 1.03 | Iconos configurables para el chat | `cosmetics_chat` |
| 135 | [Admins Permissions](https://www.ark-server-api.com/resources/admins-permissions.135/) · 1.2 | Permisos por comando administrativo; ficha duplicada por revisar | `identity_permissions` |
| 134 | [Kill Feed](https://www.ark-server-api.com/resources/kill-feed.134/) · 2.3 | Mensajes de bajas con formato configurable | `chat_cluster` |
| 133 | [Players Online List](https://www.ark-server-api.com/resources/players-online-list.133/) · 1.3 | Listados de jugadores e identificadores para administración | `identity_data` |
| 132 | [Better Spawn Distribution](https://www.ark-server-api.com/resources/better-spawn-distribution.132/) · 1.1 | Distribución configurable de niveles de criaturas salvajes | `dino_policies` |
| 131 | [Remove Personal Ownership](https://www.ark-server-api.com/resources/remove-personal-ownership.131/) · 1.1 | Quitar la propiedad personal de estructuras | `structures_policies` |
| 130 | [Dino Colour Command](https://www.ark-server-api.com/resources/dino-colour-command.130/) · 2.5 | Comandos de color por región de dinosaurio | `cosmetics` |
| 128 | [Dino Limit](https://www.ark-server-api.com/resources/dino-limit.128/) · 1.9 | Límites de dinos por tipo y tribu con transferencias y cryopods | `dino_policies` |
| 125 | [Dino Tracker](https://www.ark-server-api.com/resources/dino-tracker.125/) · 2.0 | Encontrar dinos propios con búsqueda, categorías y páginas | `dino_tools` |
| 117 | [Command Logger](https://www.ark-server-api.com/resources/command-logger.117/) · 1.8 | Auditoría de comandos de chat, consola y RCON | `identity_data` |
| 115 | [Structures Limit](https://www.ark-server-api.com/resources/structures-limit.115/) · 2.5.1 | Límites globales y por clase de estructuras | `structures_policies` |
| 112 | [ARK Token Bank](https://www.ark-server-api.com/resources/ark-token-bank.112/) · 1.4 | API de saldos de tokens compartidos para otros plugins | `economy` |
| 94 | [Fast Rejoin](https://www.ark-server-api.com/resources/fast-rejoin.94/) · 0.1 | Resolver sesión anterior al reconectar una misma cuenta | `identity_sessions` |
| 93 | [Tidy Dams](https://www.ark-server-api.com/resources/tidy-dams.93/) · 1.3 | Limpiar diques de castor conservando la madera en un caché | `structures_inventory` |
| 65 | [Tribe Log Relay](https://www.ark-server-api.com/resources/tribe-log-relay.65/) · 2.20 | Enviar registros de tribu a destinos Discord autorizados | `chat_support` |
| 64 | [RCON Scheduler](https://www.ark-server-api.com/resources/rcon-scheduler.64/) · 1.38 | Ejecutar comandos según inicio, intervalo o calendario real | `operations_scheduler` |
| 63 | [PvP+](https://www.ark-server-api.com/resources/pvp.63/) · 1.82 | Políticas PvP de daño visible, colocación y métodos de raid | `combat_pvp` |
| 62 | [PvP Cooldowns](https://www.ark-server-api.com/resources/pvp-cooldowns.62/) · 1.31 | Cooldowns de combate que restringen acciones y comandos | `combat_pvp` |
| 53 | [All Engrams](https://www.ark-server-api.com/resources/all-engrams.53/) · 1.8 | Desbloqueo de engramas por nivel, selección y permisos | `player_tools` |
| 52 | [Advanced Messages](https://www.ark-server-api.com/resources/advanced-messages.52/) · 2.22 | Anuncios, bienvenida, avisos y mensajes dirigidos o globales | `chat_announcements` |
| 51 | [Wild Dino Spawn Control](https://www.ark-server-api.com/resources/wild-dino-spawn-control.51/) · 1.3 | Control de cantidad y nivel de criaturas salvajes al aparecer | `dino_policies` |
| 50 | [GenderChanger](https://www.ark-server-api.com/resources/genderchanger.50/) · 1.4 | Cambio de género de dino con permisos y sistema opcional de tokens | `dino_tools` |
| 49 | [Kill Unclaimeds](https://www.ark-server-api.com/resources/kill-unclaimeds.49/) · 1.2 | Limpiar criaturas sin reclamar tras un intervalo | `dino_policies` |
| 48 | [Tame Disabler](https://www.ark-server-api.com/resources/tame-disabler.48/) · 1.0 | Bloquear tame de criaturas por tipo y fecha del wipe | `dino_policies` |
| 47 | [Day Changer](https://www.ark-server-api.com/resources/day-changer.47/) · 1.3 | Modificar o mantener el día del mapa mediante configuración | `operations_scheduler` |
| 46 | [Cross Server Chat](https://www.ark-server-api.com/resources/cross-server-chat.46/) · 1.9 | Chat de cluster antiguo declarado obsoleto por su autor | `chat_cluster` |
| 45 | [Pull Prevention](https://www.ark-server-api.com/resources/pull-prevention.45/) · 1.0 | Restringir transferencias de recursos del mod Super Structures | `structures_inventory` |
| 44 | [Anti PvE Griefing](https://www.ark-server-api.com/resources/anti-pve-griefing.44/) · 1.2 | Protección contra acceso, arrastre, robo y otras formas de griefing | `combat_pvp` |
| 43 | [ArkHomes](https://www.ark-server-api.com/resources/arkhomes.43/) · 1.32 | Homes persistentes y destinos públicos con controles de cercanía | `player_homes` |
| 42 | [Mission Disabler](https://www.ark-server-api.com/resources/mission-disabler.42/) · 1.21 | Impedir inicio de misiones seleccionadas | `operations_world` |
| 30 | [Lethal ORP](https://www.ark-server-api.com/resources/lethal-orp.30/) · 1.48 | Protección de bases desconectadas y estados de raid por tribu | `combat_pvp` |
| 29 | [Creatures+](https://www.ark-server-api.com/resources/creatures.29/) · 1.33 | Reasignación de puntos y ajustes de crianza, imprint y montura | `dino_tools` |

### Pago

| ID | Referencia y versión listada | Capacidad pública resumida | Familia |
| ---: | --- | --- | --- |
| 549 | [KDV_DamageNumbers [ASE] \| NEXT GENERATION DAMAGE NUMBERS](https://www.ark-server-api.com/resources/kdv_damagenumbers-ase-next-generation-damage-numbers.549/) · 1.0.0 | Indicadores de daño configurables con alcance y visibilidad | `cosmetics_hud` |
| 537 | [Mega Spyglass + GPS [PAID] Server-Side Spyglass Stats + Live GPS HUD](https://www.ark-server-api.com/resources/mega-spyglass-gps-paid-server-side-spyglass-stats-live-gps-hud.537/) · 2026-09-14 | Estadísticas de objetivo y coordenadas en interfaz de jugador | `cosmetics_hud` |
| 536 | [🦖 TuF AutoStats (Babies&Tamed) — Smart Dino Management for ARK: Survival Evolved](https://www.ark-server-api.com/resources/t-rex-tuf-autostats-babies-tamed-smart-dino-management-for-ark-survival-evolved.536/) · 2026-09-14 | Asignación automática de estadísticas para bebés y dinos domesticados | `dino_tools` |
| 19 | [Lethal Decay](https://www.ark-server-api.com/resources/lethal-decay.19/) · 2.08 | Decaimiento configurable de construcciones por actividad y reglas | `structures_policies` |
| 17 | [Auto Crafter](https://www.ark-server-api.com/resources/auto-crafter.17/) · 2.02 | Fabricación automática y ajustes de estructuras | `structures_inventory` |
| 20 | [Lethal Loot](https://www.ark-server-api.com/resources/lethal-loot.20/) · 2.13 | Cajas, eventos y atributos configurados para objetos, dinos y huevos | `rewards_events` |
| 506 | [X Tamegun + Cryogun](https://www.ark-server-api.com/resources/x-tamegun-cryogun.506/) · v1.2 | Herramientas para domesticar y guardar dinos en cryopods | `dino_tools` |
| 505 | [X OSD](https://www.ark-server-api.com/resources/x-osd.505/) · v1.2 | Ajustes de defensas y recompensas de eventos OSD | `rewards_events` |
| 504 | [X Autobuff](https://www.ark-server-api.com/resources/x-autobuff.504/) · v1.2 | Automatizar buffs de dinos individuales o grupos elegibles | `dino_tools` |
| 503 | [X Healboost](https://www.ark-server-api.com/resources/x-healboost.503/) · v1.0 | Cambiar magnitudes de curación según fuente y destinatario | `rates_balance` |
| 502 | [X Wipe](https://www.ark-server-api.com/resources/x-wipe.502/) · v1.0 | Reglas, restricciones y eventos asociados a etapas del wipe | `operations_scheduler` |
| 501 | [X Mutes](https://www.ark-server-api.com/resources/x-mutes.501/) · v1.3 | Control de silencios de jugadores y comunicación | `chat_moderation` |
| 500 | [X Playername](https://www.ark-server-api.com/resources/x-playername.500/) · v1.2 | Nombre visible del jugador derivado de reglas configurables | `identity_names` |
| 499 | [X Adminlink](https://www.ark-server-api.com/resources/x-adminlink.499/) · v1.2 | Flujo de autorización administrativa mediante vinculación externa | `identity_external` |
| 498 | [X Bans + Alts](https://www.ark-server-api.com/resources/x-bans-alts.498/) · v1.2 | Baneos compartidos y observaciones de cuentas alternativas | `identity_bans` |
| 497 | [X Builder](https://www.ark-server-api.com/resources/x-builder.497/) · v1.0 | Ajustes de construcción y estructuras configurados por permisos | `structures_policies` |
| 475 | [TournamentX ($20)](https://www.ark-server-api.com/resources/tournamentx-20.475/) · V1 | Desafíos y torneos entre jugadores con recompensas | `rewards_events` |
| 466 | [CryoSicknessTime](https://www.ark-server-api.com/resources/cryosicknesstime.466/) · 2.6 | Duración de cryosickness diferenciada por reglas de permisos | `dino_policies` |
| 459 | [BreedingX ($20)](https://www.ark-server-api.com/resources/breedingx-20.459/) · V1 | Comandos y ajustes para reproducción y cooldowns | `dino_tools` |
| 453 | [CustomCryos ($20)](https://www.ark-server-api.com/resources/customcryos-20.453/) · V1 | Cryopods y arma de cryo con reglas de elegibilidad | `dino_tools` |
| 18 | [Items+](https://www.ark-server-api.com/resources/items.18/) · 3.07 | Protección, persistencia y modificaciones de inventario y objetos | `inventory_items` |
| 258 | [Lethal Limits Evolved](https://www.ark-server-api.com/resources/lethal-limits-evolved.258/) · 1.05 | Límites por tribu para estructuras y dinos | `world_limits` |
| 21 | [Lethal Sightings](https://www.ark-server-api.com/resources/lethal-sightings.21/) · 2.09 | Aparición de criaturas raras con recompensas y destinos | `rewards_events` |
| 413 | [KOTH ($20)](https://www.ark-server-api.com/resources/koth-20.413/) · V1 | Eventos automáticos de control de una zona | `rewards_events` |
| 389 | [DinoSpawnX ($20)](https://www.ark-server-api.com/resources/dinospawnx-20.389/) · V1 | Control de apariciones de dinos configurados | `dino_policies` |
| 387 | [MissionBPs ($20)](https://www.ark-server-api.com/resources/missionbps-20.387/) · V1 | Ajustar recompensas de blueprints de misiones | `inventory_items` |
| 385 | [TazzTribescore ($20)](https://www.ark-server-api.com/resources/tazztribescore-20.385/) · V1 | Puntuaciones y clasificación de tribus | `identity_data` |
| 383 | [AdminAccess ($20)](https://www.ark-server-api.com/resources/adminaccess-20.383/) · V1 | Acceso administrativo temporal a estructuras | `player_admin` |
| 382 | [PaintSaver ($20)](https://www.ark-server-api.com/resources/paintsaver-20.382/) · V1 | Guardar y aplicar conjuntos de pintura | `cosmetics` |
| 378 | [AdminESP ($20)](https://www.ark-server-api.com/resources/adminesp-20.378/) · V1 | Visualización administrativa de jugadores y estructuras | `player_admin` |
| 377 | [DinoBuffs ($20)](https://www.ark-server-api.com/resources/dinobuffs-20.377/) · V1 | Bonificaciones de estadísticas y buffs temporales por especie y grupo | `dino_tools` |
| 361 | [SH Cross Chat ASE](https://www.ark-server-api.com/resources/sh-cross-chat-ase.361/) · 1.0 | Chat entre mapas, bot Discord y formato por permisos | `chat_cluster` |
| 219 | [🛡️ SR's Newbie Protection Evolved](https://www.ark-server-api.com/resources/shield-srs-newbie-protection-evolved.219/) · 2.0 | Protección temporal de nuevos jugadores contra daño y raid | `combat_pvp` |
| 26 | [Server Events](https://www.ark-server-api.com/resources/server-events.26/) · 2.03 | Eventos de mundo abierto con bosses y recompensas configuradas | `rewards_events` |
| 22 | [Lethal Trades](https://www.ark-server-api.com/resources/lethal-trades.22/) · 2.02 | Intercambio de objetos entre jugadores del mismo mapa | `inventory_trades` |
| 323 | [Smooth Transfer](https://www.ark-server-api.com/resources/smooth-transfer.323/) · 1.25 | Persistir inventario durante transferencias y recuperación tras muerte | `inventory_items` |
| 322 | [Dino Structure Limiter](https://www.ark-server-api.com/resources/dino-structure-limiter.322/) · 1.30 | Límites de estructuras y dinos con merges y cryopods | `world_limits` |
| 321 | [MAGA](https://www.ark-server-api.com/resources/maga.321/) · 2.52 | Reglas combinadas de PvP, ORP, spam y restricciones de acciones | `combat_pvp` |
| 320 | [PVPVE](https://www.ark-server-api.com/resources/pvpve.320/) · 1.43 | Coexistencia de jugadores PvP y PvE con políticas de daño | `combat_pvp` |
| 171 | [📦 SR's Death Retriever Evolved](https://www.ark-server-api.com/resources/package-srs-death-retriever-evolved.171/) · 1.7.2 | Recuperar cachés de muerte con permisos y costes configurados | `player_tools` |
| 294 | [Cluster Wide Minigames, Lottery & Challenges](https://www.ark-server-api.com/resources/cluster-wide-minigames-lottery-challenges.294/) · 1.0 | Minijuegos, sorteos y desafíos sincronizados entre mapas | `rewards_events` |
| 291 | [Open Control ASE](https://www.ark-server-api.com/resources/open-control-ase.291/) · 1.1 | Permisos de acceso y multiuso de estructuras por grupo | `structures_policies` |
| 288 | [Battle Pass](https://www.ark-server-api.com/resources/battle-pass.288/) · 1.0 | Objetivos y recompensas de pase gratuito y premium | `rewards_events` |
| 268 | [ssAnticheat ASE](https://www.ark-server-api.com/resources/ssanticheat-ase.268/) · V2.5 | Detecciones y protección de exploits; contrato completo pendiente | `antiabuse` |
| 187 | [Breednator](https://www.ark-server-api.com/resources/breednator.187/) · v1.4 | Retirar cryosickness de bebés al liberar cryopods | `dino_policies` |
| 223 | [DCPlayerOnline](https://www.ark-server-api.com/resources/dcplayeronline.223/) · 1.3 | Mostrar actividad y jugadores del servidor mediante bot Discord | `chat_cluster` |
| 55 | [AutoBases](https://www.ark-server-api.com/resources/autobases.55/) · 1.7 | Crear y desplegar plantillas de bases con dinos y contenido | `structures_templates` |
| 103 | [RateControl](https://www.ark-server-api.com/resources/ratecontrol.103/) · 2.0 | Rates y estadísticas por tribu, permisos y calendario | `rates_balance` |
| 191 | [ARK Guardian Evolved](https://www.ark-server-api.com/resources/ark-guardian-evolved.191/) · 1.5 | Protección contra exploits y trampas con documentación externa | `antiabuse` |
| 23 | [Lethal Quests](https://www.ark-server-api.com/resources/lethal-quests.23/) · 2.09 Beta 3 | Estadísticas, cadenas de misiones y recompensas diarias o semanales | `rewards_events` |
| 179 | [KalsComms A:SE](https://www.ark-server-api.com/resources/kalscomms-a-se.179/) · 2.4 | Chat de cluster y estilos mediante servicio NGC-Core | `chat_cluster` |
| 177 | [NGC-Core Plugin A:SE](https://www.ark-server-api.com/resources/ngc-core-plugin-a-se.177/) · 2.4 | Comunicación y datos compartidos para módulos del cluster | `operations_cluster` |
| 24 | [Name Control+](https://www.ark-server-api.com/resources/name-control.24/) · 2.06 | Validación y modificación de nombres de jugador, tribu y dino | `identity_names` |
| 146 | [Cosmetic Giver](https://www.ark-server-api.com/resources/cosmetic-giver.146/) · 1.3 | Asignar objetos cosméticos al respawn de cuentas elegibles | `cosmetics` |
| 138 | [Foppa's Vote Rewards](https://www.ark-server-api.com/resources/foppas-vote-rewards.138/) · 3.2.1 | Canjear votos con kits y recompensas según permisos | `rewards_events` |
| 137 | [Player Activity](https://www.ark-server-api.com/resources/player-activity.137/) · 1.1 | Registrar conexiones, transferencias y duración de actividad | `identity_data` |
| 136 | [Damage Control](https://www.ark-server-api.com/resources/damage-control.136/) · 1.5.1 | Modificar daño por criatura, arma, jugador y estructura | `rates_balance` |
| 102 | [HWIDBans](https://www.ark-server-api.com/resources/hwidbans.102/) · 3.3 | Baneos, restricciones de acceso y señales de cuentas alternativas | `identity_bans` |
| 27 | [Tribe Enforcer](https://www.ark-server-api.com/resources/tribe-enforcer.27/) · 2.02 | Sincronizar identidad, miembros y roles de tribu entre mapas | `tribes_cluster` |
| 25 | [No Double Login](https://www.ark-server-api.com/resources/no-double-login.25/) · 2.05 | Evitar sesiones simultáneas de una cuenta en varios mapas | `identity_sessions` |
| 56 | [VanillaModifier](https://www.ark-server-api.com/resources/vanillamodifier.56/) · 2.43 | Modificar estructuras, crafting, puertas y extracción de recursos | `structures_policies` |
| 54 | [AntiStructureMesh](https://www.ark-server-api.com/resources/antistructuremesh.54/) · 1.15 | Detectar y restringir estructuras fuera de zonas válidas | `structures_policies` |

## Referencias adicionales y lagunas

El índice del foro incluye anuncios como [Biome Spawner PRO](https://www.ark-server-api.com/threads/biome-spawner-pro-paid-safe-custom-dino-spawns-for-ase.6519/) que no se han emparejado con las tres categorías del catálogo. Es una señal de que el catálogo paginado no cierra todo el ecosistema. Su hilo queda como contrato pendiente; no se infiere una versión, disponibilidad ni conjunto completo de comandos.

El repositorio oficial añade las siguientes entradas sin correspondencia afirmada con una ficha actual: `AlternativeCommands`, `AntiFlyerCarry`, `ArkAdvert`, `CustomChat`, `DinoColors`, `ExtendedRcon`, `NoCollision`, `SafeZone`, `ShopRewards`, `TribeMotd`. Los nombres prueban existencia en el directorio, no una especificación de gameplay. `AtlasShop` pertenece a Atlas y se excluye del objetivo ASE. [Directorio y README oficial](https://github.com/ArkServerApi/ASE-Plugins).

Las dos fichas [Admins Permissions 135](https://ark-server-api.com/resources/admins-permissions.135/) y [154](https://ark-server-api.com/resources/admins-permissions.154/) se mantienen hasta resolver su relación. Un hilo marcado `[Deleted]` se registra como tal sin anunciar que el plugin esté disponible. El JSON conserva los 223 títulos del foro y los 20 metadatos del repositorio como referencias separadas, sin sumar duplicados.

Queda por fijar configuración y contrato completo por producto, obtener evidencias autorizadas de comportamiento de referencias de pago cuando la documentación sea insuficiente, priorizar perfiles reales de migración y aceptar cada caso Steam/Epic. Los productos con dependencias de cliente requieren un alcance explícito. Anticheat y métricas de “detecciones” necesitan pruebas propias concretas; no se traslada la cifra comercial del proveedor a ObeliskNative.

[Snapshot JSON verificable](ase-ecosystem-inventory-20261014.json). [Plan de suite existente](ARKAPI_PLUGIN_SUITE_PARITY.md).
