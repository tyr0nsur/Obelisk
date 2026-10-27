# ObeliskNative: estado del ecosistema

Actualizado el 27 de octubre de 2026. Ésta es la referencia actual de producto
para Runtime, Hub y panel; los documentos `PLUGIN_HUB_*` conservan decisiones de
planificación anteriores y no describen por sí solos el alcance vigente.
El [contrato de paridad](GAMEPLAY_PARITY_CONTRACT.md) sigue definiendo qué debe
demostrarse antes de aceptar equivalencia de gameplay.

## Qué se está construyendo

ObeliskNative reúne un runtime de plugins Linux nativos para ARK: Survival
Evolved, un Hub de paquetes y un panel de operación. El panel parte de FlowArk,
el proyecto propio recuperado en [`apps/flowark`](../apps/flowark/); se reutiliza
esa base en lugar de mantener otro panel independiente. La marca de producto
es ObeliskNative. Nombres internos `FLOWARK_*` y rutas conservadas son detalles
de compatibilidad de la instalación.

La fuente sigue privada. El repositorio público muestra presentación, progreso,
métricas y capturas autorizadas. Runtime gratuito significa distribución bajo
condiciones definidas, no publicación automática del código. La licencia MIT
actual del repositorio y los avisos de dependencias se preservan; la futura
oferta comercial debe definir su alcance sin asumir que privacidad del
repositorio equivale a una prohibición de redistribución.

## Componentes y frontera actual

| Componente | Implementado o recuperado | Pendiente para uso general |
| --- | --- | --- |
| Runtime | Adaptador Linux para el ejecutable ASE fijado; comandos, contextos copiados y ciclo cooperativo de plugins. | Apagado limpio, ensayos prolongados, autenticación Steam/Epic correlacionada y ampliaciones nativas por función. |
| Suite | Seis módulos propios y veinte verbos documentados; controles de ciclo probados en servidor. | Aceptación completa de cliente por comando y paridad por producto/escenario. |
| Panel | Código FlowArk recuperado: frontend React/Vite y backend Express, perfiles, permisos, estado, auditoría y rutas operativas existentes. | Panel integrado en laboratorio local; faltan ensayos operativos del juego, recuperación y despliegue público. |
| Hub local | API de catálogo propio, referencias ASE, instancias registradas, control de plugins por socket y descubrimiento de artifacts. | Aceptación de controles contra el runtime real y registro/distribución de productos de terceros. |
| Artifacts | Empaquetado determinista, manifiesto firmado Ed25519, verificación externa y staging aislado de sólo lectura. | Activación, updater de producción, rollback de datos y catálogo estable. |

El servidor de referencia es la rama pública ASE, build 21241282, binario Linux
361.7; la prueba inicial fue con cliente Epic 361.8. El perfil nativo se fija a
un hash concreto. No se extrapola compatibilidad a ASA, Windows, otras builds o
cualquier mapa por compartir nombre comercial.

La recuperación de FlowArk tiene manifiesto y exclusiones:
[registro de recuperación](../apps/flowark/docs/RECOVERY_2026-10-27.md).
No se recuperaron secretos, estado de administradores/jugadores, dependencias,
binarios compilados, el bot de Discord ni implementaciones ArkApi archivadas.
El dashboard recuperado contiene pantallas y rutas históricas; una ruta con
respuesta 501 sigue siendo una función pendiente.

El servicio `obelisknative-panel-lab` está activo en `127.0.0.1:3040` con Node 24;
su JWT y credenciales se configuran fuera de Git en estado privado. No se cambió
nginx ni se abrió el panel a Internet. El servidor ARK está detenido; el panel
se valida por separado. La prueba real de navegador cubrió login,
Hub con seis módulos, artifacts, 157 referencias, jugadores, consola bloqueada
con RCON desactivado y diagnóstico. Se revisaron escritorio de 1440 px y móvil
de 390 px sin desbordamiento horizontal ni errores de página.

Los cuatro perfiles PvE, PvP, Hardcore PvE y Hardcore PvP tienen revisión de
configuración. El navegador comprobó las vistas y previews sin persistir cambios.
Guardar un modo requiere su propia confirmación, afecta archivos y exige
reiniciar el mapa; no se aceptó un cambio de modo en gameplay durante esta prueba.

## Catálogo real y referencias

| Módulo propio | Función disponible en el prototipo | Límite que debe mostrar el Hub |
| --- | --- | --- |
| oPing | `/ping`, `/whoami`; respuesta y observaciones de nombre/ID nativo. | ID opaco observado, sin promesa de autenticación de cuenta. |
| oEssentials | `/help`, `/rules`, `/motd`, `/serverinfo` configurables. | Las pruebas de interfaz/UTF-8 se aceptan con cliente, por separado de fixtures. |
| oShopKits | `/shop`, `/kits`; catálogos informativos. | Compras, cobro y entrega de kits siguen deshabilitados. Los recibos privados no son una tienda viva. |
| oAdvancedChat | `/chathelp`, `/chatlist`, `/chatglobal`, `/tell`. | Destinos de sesiones observadas, no censo autoritativo; chat actual del servidor, sin chat de cluster aceptado. |
| oHomes | `/sethome`, `/homes`, `/delhome`, `/home`. | Puntos de sesión; reconexión/recarga los pierde. El movimiento propio requiere aceptación real y controles de estado. |
| oWorldTools | `/whereami`, `/tribe`, `/dino`, `/structure`. | Consultas propias, montura y estructura apuntada; sin censo global ni mutaciones de esos dominios. |

Las 157 fichas del snapshot ASE del 14 de octubre son referencias externas,
incluidos framework y posibles duplicados. El endpoint de referencias las marca
`reference_pending` y `available: false`. No son 157 plugins ObeliskNative
instalables. Una ficha sólo se convierte en producto propio tras definir su
contrato, implementar la función original y aceptar sus escenarios.

El usuario informa haber probado comandos; ese informe se conserva como tal.
Para cerrar una prueba hay que registrar qué comando, plataforma, resultado y
escenario se aceptaron. No aceptar las 88 pruebas beta, Steam, dos jugadores,
inventario, persistencia y todo el catálogo a partir de una confirmación general.
[Guía beta](BETA_TESTER_GUIDE.md),
[estado de suite](SUITE_STATUS.md),
[inventario de referencia](research/ASE_ECOSYSTEM_INVENTORY_2026-10-14.md).

## Tres planos de autoridad distintos

La sesión del panel autoriza acciones administrativas del panel según roles y
permisos. Los permisos de control de plugins no convierten un usuario del panel
en administrador del juego. El control nativo emplea una instancia registrada y
su socket privado; el navegador no elige comandos de shell, rutas, scripts o
destinos arbitrarios. Véase la [API local del Hub](../apps/flowark/docs/HUB_LOCAL_API.md).

La consola histórica del panel usa RCON cuando está configurado en la instancia.
`configured` no equivale a conectividad y `reachable: null` significa que no se
ha sondeado. El socket del runtime no habilita RCON ni ejecuta cualquier cheat de
ARK. Las herramientas de allowlist basadas en Steam ID tampoco prueban una
concesión correcta a un jugador Epic identificado sólo por su UID opaco.

Los permisos/economía del gameplay necesitan el productor de identidad
autenticada y la sesión vigente. Un nombre, un token de sesión o un ID observado
no tienen esa autoridad. Mantener esa separación también en los botones,
diagnósticos y mensajes de error del panel.

## Artifacts y aceptación de distribución

[La herramienta de artifacts](ARTIFACTS.md) produce un tar.gz con diecinueve
archivos: dos bibliotecas del runtime, seis plugins, siete archivos del SDK y
cuatro avisos de licencia. No incluye ARK, partidas, configuraciones o claves.
El manifiesto, la firma y el índice quedan separados del tar. El índice es
descubrimiento: el consumidor debe verificar con una clave externa confiable.

El 27 de octubre pasaron 24 pruebas del pipeline con OpenSSL real y ELF de
fixture. También se construyó y verificó un artifact de 19.173.263 bytes desde
el build real, se preparó y revalidó su staging y se compiló un consumidor C del
SDK instalado. Se usó una clave temporal de prueba y se retiraron esos archivos
al terminar. Es evidencia de empaquetado/consumo; no se activó ese artifact ni
se publicó una descarga pública.

El operador creó después una publicación privada persistente en
`/servidor/obelisk/ecosystem/artifacts`, con staging en su directorio aislado.
El ID del manifiesto es
`0fd26befb2cb445621db9b70965ae7d8b4ed94a969b04146daa73778bcff5c21`.
El paquete conserva diecinueve archivos y 19.173.263 bytes; firma con clave
externa confiable, hashes y staging volvieron a pasar. Se mantiene
`runtime_ready=false` y no se activó el artifact sobre el juego.

Todos los manifests de esta revisión indican `experimental` y
`runtime_ready=false`. La firma no permite presentar un plugin como aceptado en
juego. El número de CTests del runtime y los tests del panel/artifacts se
publican en series distintas, con fecha y alcance.
El build nativo se reconstruyó el 27 de octubre y pasó 158/158 CTests. Los
24 tests de artifacts pasan por separado. La ejecución actual también cerró
214/214 guardrails del SDK, 122/122 tests del backend, 73/73 del frontend y
lint/build del panel. Las pruebas del panel incluyen transporte aislado y no
sustituyen gameplay real. [Validación integrada](ECOSYSTEM_VALIDATION_2026-10-27.md).

## Freemium propuesto

La base gratuita prevista incluye runtime, Hub básico, panel autohospedado y
plugins básicos aceptados. La monetización propuesta cubre operación gestionada,
automatización avanzada entre hosts, plugins premium y soporte/migración
contratados. Son decisiones de oferta en preparación; no hay checkout ni
suscripción habilitados por estos documentos.

Las hipótesis iniciales son Pro a EUR 19/mes hasta cinco instancias y Network a
EUR 49/mes hasta quince, aplicadas a servicios premium. Deben validarse con
pilotos y costes antes de publicarse como tarifas. La base local y la
exportación/recuperación de datos continúan disponibles. El desarrollo se
compara con alternativas existentes, incluido Takaro; no se reivindica ser el
único runtime Linux nativo.
[Investigación y propuesta comercial](COMMERCIAL_STRATEGY_2026-10-27.md).

## Próximos cierres verificables

1. Cerrar operaciones de panel/Hub contra el runtime real en una ventana
   controlada. La integración de interfaz/API ya tiene pruebas; comprobar
   permisos, resultados pendientes y auditoría de cada operación de juego.
2. Probar instalación y recuperación del artifact privado persistente en un
   destino limpio, conservando su clave de confianza externa y sus límites.
3. Resolver el apagado completo y cerrar identidad/inventario nativos antes de
   activar permisos, compras/kits y persistencia de cuenta.
4. Aceptar un flujo útil completo con Steam y Epic, luego dos mapas con
   persistencia y concurrencia reales. Expandir el catálogo por contratos,
   sin convertir referencias pendientes en botones instalables.
5. Validar soporte, entrega y continuidad con pilotos antes de ventas generales.

Los documentos históricos se conservan para procedencia e investigación. Cuando
contradigan el ámbito comercial y de suite solicitado después, esta referencia
y las instrucciones actuales del operador describen la dirección vigente. Los
controles de evidencia, ownership y seguridad de cada superficie siguen
aplicándose; ninguna declaración comercial los sustituye.
