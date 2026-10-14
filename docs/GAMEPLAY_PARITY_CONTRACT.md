# Paridad de gameplay con implementación propia

Objetivo solicitado el 14 de octubre de 2026: que los jugadores puedan conservar
sus flujos de ASE al migrar desde plugins ArkApi, con implementaciones originales
nativas de ObeliskNative. No se incorpora código fuente de esos plugins ni del
framework. Los contratos se derivan de documentación pública y observaciones
registradas, y se implementan sobre la ABI C y el adaptador Linux propios.

## Universo de comparación

El [inventario fechado](research/ASE_ECOSYSTEM_INVENTORY_2026-10-14.md) fija IDs,
versiones observadas y enlaces primarios. Sus 157 fichas incluyen un framework y
156 registros de plugins/integraciones, con duplicados de producto identificados.
El repositorio y los anuncios del foro amplían referencias, pero no se suman como
productos únicos sin reconciliación. Plugins privados, retirados o sin contrato
público permanecen fuera del cierre verificable hasta obtener documentación u
observaciones. El snapshot no afirma abarcar todo producto existente.

Para cada referencia se fija versión, configuración, mapa, cliente/plataforma y
escenario. Una nueva versión o un comportamiento no documentado añade casos;
no modifica silenciosamente una equivalencia ya aceptada. Se distinguen las
variantes gratuitas/premium y las funciones que requieren mods de cliente.

## Qué debe coincidir en juego

| Dimensión | Contrato y evidencia necesarios |
| --- | --- |
| Entrada | Comandos, aliases, argumentos, mayúsculas, espacios, búsqueda, páginas y errores de uso |
| Presentación | Canal de chat/notificación, emisor, destinatarios, rich text, iconos, localización y textos configurados |
| Efecto | Actor correcto, cantidad exacta, blueprint/calidad, colores, propiedad y réplica visible |
| Autorización | Sujeto verificado, grupos/tribus, privilegios, permisos y revocación; ninguna autoridad por nombre |
| Límites | Cuotas, cooldown, retardo, restricciones por estado/distancia/mapa y antiabuso |
| Persistencia | Reconexión, cambio de personaje, recarga, reinicio, expiración y transferencias de mapa |
| Fallos | Inventario lleno, entrega parcial, desconexión, DB/broker caído y resultado incierto sin duplicación |
| Administración | Configuración y migración reproducibles, acciones auditadas y transiciones cooperativas seguras |

Las configuraciones internas pueden ser distintas; un adaptador de migración
puede preservar los ajustes del administrador con un informe de campos y
semánticas. Un comando parecido, una respuesta de éxito o una consulta nativa no
certifican la dimensión correspondiente. Los defaults del prototipo tampoco
se presentan como defaults de otro producto.

Cada caso tiene ID, fuente del comportamiento esperado, entrada/estado previo,
resultado esperado, estado posterior, plataforma y observación real. Los estados
son contrato pendiente, implementado, probado en fixture, instalado y aceptado
con clientes. Se puede registrar una diferencia explícita; no se llama paridad.
Se cierra una función cuando pasan sus casos y se conserva su referencia fijada.

## Dependencias comunes antes de multiplicar plugins

1. Identidad y sesiones: autenticar Steam/Epic y correlacionar la aprobación con
   la conexión actual; separar sujeto jugador del propietario de licencia y
   proveedor observado de autenticación. Rechazar sesión/generación anterior.
2. Permisos: resolver una autoridad explícita, evaluar cada acción contra estado
   vigente, comprobar expiración durante la decisión y revalidar al ejecutar.
3. Inventario y economía: probar una entrega vanilla exacta con variante y
   cantidad completas, persistir el intento y reconciliar outcomes inciertos.
4. Ejecución main-thread: scheduler residente, cancelación por dueño/generación,
   destinos vigentes y readiness; los timers worker actuales no llaman UE.
5. Mundo: identidades/lifetimes y censo autoritativo, tribus/ownership y hooks de
   decisión precisos; las consultas de montura/estructura no son enumeración.
6. Cluster: persistencia compartida, deduplicación/backpressure y protocolo de
   transferencia. Un epoch de proceso no identifica una partida persistente.

Sobre estas primitivas se cierran Shop/Kits, Homes/teleports, mensajería y
recompensas, administración, dinos/estructuras/tribus y políticas/integraciones.
La pertenencia a una familia no acepta todos los productos de esa familia.

## Incremento implementado en esta etapa

[SuiteCommandPermissions](SUITE_COMMAND_PERMISSIONS.md) exige autoridad confiable
y scope exacto de instancia/sesión/generación/invocación. Consulta SQLite en cada
decisión, detecta cambios de principal/config y expiración durante un resolver
lento. Permanece privado y offline: falta el productor autenticado del juego.

[SuiteItemDelivery](SUITE_ITEM_DELIVERY.md) verifica incrementos de pilas y
cantidades exactas bajo snapshots completos y atribución exclusiva. Entregas
parciales/excesivas o evidencia incompleta quedan Uncertain. Sus pruebas con
recibos duraderos impiden refund/retry automático de una entrega parcial.
Todavía falta el adaptador nativo que produzca esa evidencia de forma verificada.

La [auditoría de identidad](research/NATIVE_IDENTITY_PROVIDER_AUDIT.md) sigue los
callbacks Steam/EOS del ejecutable actual; no expone autenticación en el SDK.
La [auditoría de inventario](SUITE_ITEM_DELIVERY.md#anclas-nativas-del-ejecutable-actual)
corrobora cantidades/metadata y la ruta de stacking, sin ejecutar una entrega.

El laboratorio conserva seis módulos y 20 verbos. La guía beta mantiene sus
casos de cliente pendientes. Esta etapa no activa compras, kits, permisos de
juego, homes duraderos ni otras mutaciones, y no declara equivalencia completa.
