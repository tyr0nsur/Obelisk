# ObeliskNative: estrategia comercial y distribución

Fecha de investigación: 27 de octubre de 2026, Europe/Madrid.
Documento interno de decisión. Las capacidades propuestas, precios y objetivos
de aceptación son hipótesis de producto; este documento no activa un servicio,
no publica una oferta y no certifica paridad del catálogo.

## Decisión de producto

Construir un ecosistema freemium: Runtime Linux nativo, Hub de plugins y FlowArk
para operaciones. El runtime, el panel autohospedado y las funciones básicas
deben permitir administrar una comunidad sin suscripción. La facturación cubre
servicios gestionados, automatización avanzada de varios hosts, plugins premium
y soporte contratado. La implementación y el código del producto permanecen
privados; distribución gratuita y publicación de código son decisiones distintas.

La referencia de experiencia es descargar un artifact compatible, arrancar,
abrir el panel y preparar una instancia. Cfx documenta txAdmin incluido en
FXServer para Windows y Linux, con despliegue, control, permisos y monitorización.
Su página de descargas distingue plataforma, sistema operativo y ramas
Recommended/Latest. Se toma ese flujo como referencia de producto y se diseñan
interfaz, formatos e implementación propios.
[txAdmin oficial](https://docs.fivem.net/docs/resources/txAdmin/),
[descargas de artifacts](https://docs.fivem.net/docs/server-download/).

El nombre comercial principal sigue siendo ObeliskNative. Runtime significa
ejecución de plugins dentro de ASE; Hub significa catálogo, paquetes y sus
versiones; FlowArk es el origen del panel de operación de instancias y clusters.
Su código se recuperó e integró en `apps/flowark`, conservando rutas y variables
históricas. Estas tres piezas comparten contratos, con procesos y credenciales
separados cuando corresponde. El panel integrado y los artifacts siguen siendo
experimentales; su prueba local no cierra la aceptación del gameplay.

## Mercado comprobado y límites de la investigación

| Referencia primaria consultada | Hecho observado | Implicación para ObeliskNative |
| --- | --- | --- |
| [ASE Server API](https://ark-server-api.com/resources/ase-server-api.32/) y [AseApi](https://github.com/ArkServerApi/AseApi) | El framework oficial describe instalación Windows/Win64; AseApi declara MIT. | Hay un framework existente de acceso abierto. Cobrar únicamente por cargar plugins necesita un valor adicional claro. |
| [Catálogo ASE de pago](https://forum.ark-server-api.com/resources/categories/ase-paid-plugins.10/?order=rating_weighted) | La categoría muestra productos de autores distintos: Items+ y Lethal Decay a USD 29,99, Lethal Quests a USD 45 y ARK Guardian Evolved a EUR 100. | Existe venta por funcionalidad especializada. Los precios son los mostrados, sin equiparar alcance, impuestos o condiciones. |
| [WB Plugins](https://store.dopeark.com/) | El vendedor declara licencias perpetuas para ASE y renovación anual para ASA; distribuye y atiende mediante Discord. | El mercado mezcla pago único y mantenimiento. No imponer una promesa perpetua de actualizaciones ilimitadas. |
| [Takaro ASE](https://takaro.io/games/ark-survival-evolved), [release 0.2.0](https://github.com/gettakaro/connectors/releases/tag/ark-v0.2.0) y [release 0.3.0](https://github.com/gettakaro/connectors/releases/tag/ark-v0.3.0) | Existe un conector nativo Linux para el build 21241282. El 0.2.0 se publicó el 19 de octubre de 2026 a las 01:03 en Madrid; el 0.3.0, el 26 de octubre a las 14:30. La web todavía muestra 0.2.0 y la etiqueta en desarrollo. | No anunciar que somos el único o el primer producto Linux nativo. Tomar 0.3.0 como referencia publicada actual; contrastar versiones de web y releases. |
| [Documentación de Takaro ASE](https://takaro.io/docs/supported-games/official/ark) | El proveedor declara pruebas con cliente en staging para identidad, chat, inventario, teleports, moderación y apagado. Mapa y spawn locations requieren un protocolo aún no disponible en takaro.io. | El conector y los módulos del panel son competencia directa, con restricciones explícitas. Sus declaraciones no son pruebas ejecutadas por ObeliskNative. |
| [Precios de Takaro](https://takaro.io/pricing) | Gratis: un servidor. Mensual: EUR 7,99 para dos, 14,99 para cinco y 24,99 para ocho. Incluye módulos, API y Discord. | Un panel genérico de pago tiene poca diferenciación. El catálogo de gameplay, la migración y el control local necesitan demostrar valor propio. |

Los precios se consultaron en páginas de sus proveedores; pueden variar por
fecha, región, moneda o checkout. No se compraron licencias ni se ejecutaron
pruebas comparativas. La investigación no demuestra demanda comercial, cuota de
mercado o ausencia de otros competidores. El inventario interno del 14 de octubre
contiene 157 fichas, incluidos framework y duplicados; es una referencia fechada,
no una cifra de productos propios ni la totalidad del mercado actual.

Las notas de 0.3.0 añaden Game Profile e identidad del conector y corrigen el
nombre de dimensión del mapa en posiciones de protocolo v1. La API de releases
confirma publicación a las 13:30:37 UTC del día 26; la hora anterior convierte
ese valor a Europe/Madrid. Una release publicada no certifica todas las funciones
que se leen en una página comercial. No se leyó ni incorporó implementación del
conector. [Release 0.3.0](https://github.com/gettakaro/connectors/releases/tag/ark-v0.3.0),
[metadatos oficiales](https://api.github.com/repos/gettakaro/connectors/releases).

## Cliente inicial y motivo de compra

El primer cliente es el administrador que controla un VPS o dedicado Linux ASE,
mantiene varios mapas y quiere migrar funciones de comunidad sin administrar una
pila Windows adicional. Tiene que poder instalar el runtime en su proveedor;
una cuenta en un hosting cerrado no garantiza esa posibilidad.

El motivo de compra propuesto es conservar flujos de los jugadores y operar los
mapas desde una herramienta local, con configuración migrable, entregas
auditables y paquetes compatibles. El ahorro económico y de rendimiento debe
medirse antes de anunciarse. No se afirma que Linux siempre sea más barato o que
un plugin propio sea equivalente sólo por compartir comandos.

Los hosters pueden ser un segundo canal cuando haya instalación reproducible,
actualizaciones reversibles y soporte de versiones. Los autores de plugins son
un tercer grupo: necesitan SDK documentado, contratos estables, pruebas de
paquete y distribución de sus propios productos. No hay compromiso de alojar
paquetes de terceros ni acceso a sus fuentes en esta etapa.

## Oferta propuesta

Toda esta tabla describe el producto objetivo. Cada función debe mostrar su
estado real antes de habilitar su descarga o cobro.

| Componente | Community gratuito | Ingresos posibles |
| --- | --- | --- |
| Runtime | Ejecución Linux, SDK de consumo, controles locales seguros y plugins básicos aceptados. Sin cuota artificial de jugadores por licencia. | Soporte e ingeniería de compatibilidad contratados, distribución gestionada para hosters. |
| FlowArk autohospedado | Perfiles e instancias, operación local, consola protegida, permisos administrativos básicos, copias/restauración y métricas locales. El cluster básico del juego sigue disponible. | Orquestación avanzada entre hosts, políticas de equipo, historial alojado y operación gestionada. |
| Hub | Catálogo consultable, versiones, dependencias, estado de aceptación, instalación manual y comprobación de integridad. Publicación de plugins gratuitos propios. | Distribución de plugins premium, automatización gestionada de instalaciones y soporte de migración. |
| Suite | Essentials y funciones básicas que superen su aceptación; alcance visible por módulo. | Packs especializados completos con pruebas de gameplay y mantenimiento definidos. |

La seguridad básica, la exportación de datos, una copia recuperable y la
posibilidad de fijar una versión forman parte de la base. No deben depender de
un plan premium. El catálogo debe poder listar propuestas pendientes sin ofrecer
botones que aparenten instalarlas o ejecutarlas.

El cierre de catálogo se mide por contratos aceptados para una versión y una
configuración. Plugins privados o sin comportamiento documentado se registran
como pendientes de especificación. La paridad completa exige resolver esas
lagunas; agrupar 157 fichas en pocas familias no las convierte en equivalentes.
Usar el [contrato de paridad](GAMEPLAY_PARITY_CONTRACT.md) como criterio técnico.

## Precios de prueba, separados de los hechos del mercado

Hipótesis para entrevistar y pilotar, sin checkout activo ni promesa de precio:

| Oferta | Hipótesis | Qué se cobra |
| --- | --- | --- |
| Community | EUR 0 | Runtime, FlowArk local, Hub básico y suite básica aceptada. |
| Pro | EUR 19 al mes por organización, hasta cinco instancias con servicios Pro activos | Orquestación gestionada, historial alojado y automatizaciones avanzadas. La instalación local sigue siendo gratuita. |
| Network | EUR 49 al mes por organización, hasta quince instancias con servicios Pro activos | Operación de varios hosts, mayor retención y herramientas para equipos. La capacidad se ajusta al coste medido. |
| Migración asistida | EUR 149–299 por intervención de alcance fijo | Inventario, conversión de configuración, copia, ensayo de recuperación y acta de aceptación. No incluye desarrollar todo plugin ausente. |
| Plugins premium | Evaluar pago único por versión mayor con mantenimiento contratado, o suscripción por pack | Funcionalidad original terminada y un periodo de actualizaciones explícito. |

Comparar Pro con Takaro debe incluir el coste total y capacidades aceptadas,
no sólo número de servidores. Estos importes carecen de validación de disposición
a pagar. Posponer planes anuales y descuentos permanentes hasta conocer soporte
y retención. Las condiciones fiscales y de facturación se concretan al preparar
el checkout, según cliente y jurisdicción; no se ha contratado un proveedor.

Para plugins de terceros, una comisión inicial del 15 % sería otra hipótesis,
con gastos de cobro, devoluciones y soporte asignados expresamente. No presentar
esa comisión como estándar de mercado ni habilitar un marketplace antes de
poder entregar, actualizar y resolver una compra con trazabilidad.

## Piloto y costes que deciden si el precio funciona

Primero, entrevistar entre cinco y diez administradores con instalaciones
autorizadas y guardar su lista de funciones realmente utilizadas. Después,
seleccionar de tres a cinco pilotos con copia recuperable y alcance fijo.
Estos números son un diseño del piloto, no clientes conseguidos.

Medir tiempo hasta la primera instancia, conversión de configuraciones sin
intervención, casos de paridad aceptados, reinicios y fallos atribuibles al
runtime, minutos de soporte por comunidad, recuperación de copias, continuidad
tras actualización y disposición a seguir pagando. Una demostración usa partidas
de prueba y pruebas Steam/Epic separadas cuando la función los anuncia.

El margen mensual debe calcularse como ingreso cobrado menos comisiones,
infraestructura, almacenamiento, ancho de banda, soporte y reserva de
compatibilidad. Ejemplo puramente presupuestario: a EUR 19, treinta minutos de
soporte valorados internamente en EUR 25/h consumen EUR 12,50 antes del resto de
costes. Ese cálculo explica por qué la instalación, los diagnósticos y la
documentación deben reducir intervención. No establece un coste real medido.

No ofrecer atención 24/7 ni plazos de reparación sin cobertura humana y datos de
incidentes. Definir horario, canales, objetivo de primera respuesta y alcance de
cada intervención antes de vender soporte. Un objetivo de respuesta no garantiza
que una modificación del juego tenga solución inmediata.

## Artifacts, instalación y actualización

Publicar paquetes propios versionados para Linux x86_64 con runtime, launcher,
plantillas y panel según el componente. Un paquete identifica versión, ABI,
arquitectura, requisitos de libc, builds del juego aceptados, hashes, capacidades,
dependencias, cambios de esquema y estado de pruebas. El binario del juego y sus
assets permanecen en la instalación del operador.

Mantener canales stable, candidate y experimental. Recommended debe señalar un
artifact concreto con aceptación, no el último commit. El cliente conserva una
versión fijada y puede leer las diferencias antes de actualizar. El sistema de
firmas debe validar manifest y bytes desde una raíz de confianza distribuida
independientemente, con rotación de claves y protección frente a versiones
retiradas; HTTPS o un checksum descargado junto al ZIP no bastan como firma.

Instalar en staging, comprobar contenido y compatibilidad, conservar copia
recuperable y publicar la generación de forma atómica. Plugins cooperativos
pueden usar los controles de recarga existentes; una actualización de runtime,
cambio de esquema o plugin sin ese contrato necesita mantenimiento. No prometer
actualización universal sin reinicio. Un rollback de binarios necesita comprobar
también que los datos siguen siendo legibles por esa versión.

El Hub debe exponer dependencias, permisos operativos, condiciones de licencia,
notas de actualización y límites de recarga. Un plugin nativo corre dentro del
proceso del juego: una firma identifica el paquete, no demuestra aislamiento ni
ausencia de fallos. La revisión y los ensayos de cada paquete siguen siendo
necesarios. El SDK distribuido tiene que funcionar sin headers internos ni
punteros UE; su licencia de uso y distribución se define sin publicar por
accidente la implementación privada.

## Suscripciones, licencias y continuidad

La licencia gratuita del runtime y las funciones locales no necesitan comprobar
una suscripción en cada arranque. Pro separa el derecho comercial del principal
del jugador: comprar una licencia nunca concede administración dentro de ARK.
La identidad de organización, instalación e instancia no se deriva del nombre
del jugador, de un UID observado ni de la IP pública.

Para Pro, usar derechos firmados con identificador de instalación, alcance,
versión y expiración; guardar la clave de instalación con permisos privados y
permitir reemplazo de máquina desde el portal. Proponer siete días de gracia
offline para fallos de verificación, sujeto a pruebas y condiciones definitivas.
Durante una caída comercial el mundo debe seguir funcionando. La retirada de
una automatización premium se aplica en un punto seguro, conserva los datos y
no interrumpe una compra o mutación ya iniciada.

El backend de facturación procesa eventos autenticados e idempotentes,
reconcilia pagos y conserva un historial de cambios de derechos. Los secretos
de pagos y firmas permanecen fuera del proceso del juego. Las licencias de
plugins premium requieren su propia política de versión y mantenimiento. Las
expiraciones comerciales no deben convertir un resultado de gameplay incierto
en un reembolso o una segunda entrega automática.

## Condiciones técnicas antes de abrir ventas generales

| Bloque | Evidencia de salida requerida |
| --- | --- |
| Runtime | Arranque y apagado completo limpios repetidos, recuperación de fallos y ensayo prolongado. El SIGABRT histórico de apagado debe cerrarse con causa y prueba; hot reload correcto no lo resuelve. |
| Identidad y permisos | Correlación autenticada Steam/Epic con sesión actual, revocación y reconexión sin heredar autoridad. Nombre, ID nativo observado y token de sesión no sustituyen identidad autenticada. |
| Inventario y economía | Entrega exacta y estados inciertos demostrados con juego real, inventario lleno, caída, reintento y persistencia; fixture o booleano nativo no certifican entrega. |
| Suite | Registro por comando y dimensión de paridad. El usuario informa que ha probado comandos; esos informes se incorporan con caso/resultado, sin aceptar automáticamente el catálogo completo. |
| Mundo y cluster | Ownership, persistencia de homes, transferencias, cambios de tribu y concurrencia entre mapas probados para cada función anunciada. |
| FlowArk | Recuperar código existente, autenticar administración, separar permisos, auditar acciones y demostrar backup/restauración e inicio/parada. Una pantalla que muestra datos de muestra no acepta operaciones. |
| Hub | Paquetes reales, hashes y firmas, dependencias, versiones compatibles, instalación y recuperación; estados pending/fixture/installed/client-accepted visibles. |
| Operación comercial | Entrega reproducible, derechos y cancelación probados, datos exportables, condiciones de uso/mantenimiento y soporte publicadas antes del cobro. |

El 27 de octubre se reconstruyó el runtime y pasaron 158 CTests y 214 guardrails
del SDK. Artifacts pasó 24 tests; backend y frontend del panel pasaron 122 y 73,
además de lint/build y navegación real de escritorio/móvil. Hay un artifact
privado persistente firmado y preparado sin activación. La suite conserva seis
módulos y veinte verbos; permisos/inventario de gameplay siguen sin aceptación
nativa completa. Son series de evidencia separadas, no una cifra de paridad.
[Estado actual](OBELISKNATIVE_ECOSYSTEM.md),
[validación de integración](ECOSYSTEM_VALIDATION_2026-10-27.md).

## Orden de salida y mensaje utilizable

La recuperación de FlowArk, el Hub integrado y el artifact experimental firmado
ya tienen pruebas locales. El siguiente cierre es la operación del paquete en
un destino limpio, identidad/inventario y una migración útil completa; después,
validar un cluster de dos mapas. Sólo los módulos aceptados
pasan al catálogo instalable. El inventario restante sigue visible como trabajo
pendiente hasta superar sus propios contratos. La venta general empieza cuando
el piloto valida instalación, gameplay, continuidad y soporte.

Diagnóstico editorial: propuesta nueva basada en objetivo y evidencia técnica;
no hay una página comercial existente que deba conservarse.

Mensaje de desarrollo respaldable: «ObeliskNative desarrolla un runtime nativo
Linux para ASE, un Hub de plugins y herramientas de administración. La beta
publica el estado y las pruebas pendientes de cada función».

Tras demostrar instalación del paquete y operación local de FlowArk, podrá
afirmarse «Descarga el artifact, conecta tu instancia Linux y administra sus
plugins desde FlowArk». Para «mismos resultados de gameplay al migrar» hacen
falta contratos fijados y pruebas diferenciales aceptadas por módulo. Para
«todo el catálogo» debe reconciliarse además el universo de productos y cada
función; las 157 fichas o el número de tests no desbloquean esa frase.

El repositorio público muestra presentación, capturas autorizadas y métricas
con su alcance. El privado conserva implementación y bindings. Anuncios de
Discord enlazan versiones y checklist real, sin divulgar credenciales, UIDs
personales o detalles del adaptador. Este documento no ha sido publicado allí.
