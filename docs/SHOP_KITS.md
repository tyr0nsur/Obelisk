# Tienda y kits: catálogo y transacciones duraderas

`oShopKits` ofrece `/shop [pagina|id]` y `/kits [pagina|id]` con respuestas dirigidas al jugador que ejecutó el comando. Muestra entradas y condiciones configuradas, acepta argumentos y mayúsculas ASCII, y dispone de pausa, reanudación, parada y recarga cooperativa. Cada respuesta indica que el catálogo es informativo y que compras/entregas aún no están disponibles. No registra `/buy` ni `/kit`: falta una ruta nativa verificada que entregue objetos y demuestre el resultado.

El estado transaccional está implementado por separado en la biblioteca privada `SuiteStore`; no conecta las identidades observadas de ARK con cuentas autenticadas y no modifica jugadores, inventarios ni roles en vivo. Este documento describe código y fixtures; la evidencia de despliegue y de cliente debe registrarse por separado.

## Configuración del catálogo

Se inicia deshabilitado y exige una instancia permitida. Se lee una vez durante Init; editar y recargar publica una nueva generación del catálogo. No hay trabajadores privados, operaciones de disco desde callbacks ni llamadas UE. La configuración JSON admite únicamente estas claves; rechaza duplicados, campos desconocidos, números negativos/fraccionarios, IDs duplicados y textos UTF-8 inválidos.

```json
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": [],
  "catalog_revision": "operator-catalog-v1",
  "shop": [
    {"id": "starter", "name": "Paquete inicial", "description": "Describe el contenido que deseas ofrecer.", "price": 25}
  ],
  "kits": [
    {"id": "welcome", "name": "Bienvenida", "description": "Describe el kit que deseas ofrecer.", "max_claims": 1, "cooldown_seconds": 3600}
  ]
}
```

Las entradas del ejemplo son material de configuración, no evidencia de una entrega en ARK. `shop` y `kits` admiten hasta 64 entradas cada uno; los precios son unidades enteras no negativas hasta INT64_MAX. Un kit tiene límite cero para ilimitado y espera cero para ausencia de cooldown. IDs: 1–64 caracteres ASCII minúsculos, dígitos, guion o guion bajo, con letra inicial. Nombre: 80 bytes; descripción: 256 bytes; revisión: 128 bytes. Configuración: 32768 bytes. Se paginan tres entradas y la respuesta está acotada a 1024 bytes.

## Recibos y wallets privados

La migración aditiva del schema 1 al 2 crea `fulfillment_receipts` e índice de historial de kits dentro de una transacción. Conserva roles, permisos, memberships, saldos y operaciones idempotentes existentes. Un schema futuro o ajeno se rechaza. Se mantienen rutas privadas sin symlinks/hardlinks, conexión FULLMUTEX, prepared statements, WAL, `synchronous=FULL` y `BEGIN IMMEDIATE`.

`SuiteReceiptRequest` contiene sujeto con namespace explícito, producto, revisión, especificación completa de entrega, cantidad, precio unitario, instante UTC y política del kit. Deben proceder de un catálogo controlado por el servidor y una autoridad de identidad establecida fuera de esta biblioteca. No se aceptan precios o sujetos del comando del jugador como autoridad. Los textos de producto/revisión/especificación se copian en el recibo; no se resuelve una revisión futura en una entrega ya reservada.

`ReservePurchase` valida el producto cantidad × precio sin desbordamiento, comprueba fondos y confirma en una sola transacción el débito y el recibo. `ReserveKit` exige cantidad uno y precio cero; los recibos reservados, iniciados, entregados e inciertos cuentan para límite y cooldown. Un recibo con ausencia de entrega confirmada queda excluido. La historia se cuenta por namespace, ID opaco y producto, también después de reabrir la base o cambiar la revisión del catálogo.

Los IDs de recibo comparten espacio con las operaciones de wallet. Repetir exactamente el payload devuelve `Replayed=true`, estado actual y saldo original posterior a la reserva sin repetir el débito. Cambiar sujeto, producto, revisión, especificación, precio, cantidad, instante o política produce `PayloadConflict`. Un fallo que hace rollback no consume el ID. La especificación tiene máximo 4096 bytes UTF-8; el ID de recibo/attempt admite 128 bytes; las cantidades se acotan a un millón.

## Admitir y confirmar una entrega

```text
Reserved --BeginDelivery--> Attempting --resultado verificado--> Delivered
                                      --sin entrega verificado--> NoDelivery + refund
                                      --resultado desconocido--> Uncertain
```

`BeginDelivery(receiptId, attemptId)` persiste el intento antes de ejecutar una acción. Sólo el primer resultado `Ok` con `Replayed=false` admite una invocación. **Un replay de BeginDelivery nunca autoriza volver a invocar la acción**, incluso si el proceso anterior terminó antes de registrar su resultado. Los IDs de intento son únicos dentro del store; un intento diferente sobre un recibo ya iniciado se rechaza.

`CompleteDelivery` exige el mismo intento. `Delivered` requiere evidencia de que se entregó la especificación completa. `VerifiedNoDelivery` exige evidencia de que no se entregó nada y confirma el reembolso junto con el estado final en una transacción. Una entrega parcial o un resultado desconocido se clasifica `Uncertain`; no basta con que una función nativa haya retornado. Repetir un resultado final igual devuelve su resultado original; un resultado final distinto se rechaza.

Tras un fallo del proceso, un recibo `Attempting` sigue debitado y no se reintenta ni se reembolsa automáticamente. `Uncertain` es terminal en esta etapa y requiere una herramienta futura explícita de reconciliación. El sistema no afirma atomicidad entre SQLite y un inventario UE: son dos sistemas distintos. Esta política evita duplicar objetos o puntos cuando se pierde la confirmación.

Si un reembolso desborda el wallet por créditos posteriores o falla su escritura, la transacción hace rollback y conserva `Attempting`. Puede repetirse la finalización con la misma evidencia de ausencia de entrega después de resolver la causa. No se inventa un reembolso ya confirmado.

## Verificación y siguiente integración

`SuiteStoreTests` comprueba reservas/débitos, replay y colisiones entre journals, persistencia de intentos y estados inciertos, prohibición de reintentos/refunds inciertos, entrega confirmada, refund idempotente, fallos después del débito y durante el refund, desbordamiento de precio/refund, caducidad/límites de kits, límites bajo concurrencia de dos conexiones, separación de namespaces y migración 1→2 conservadora con rollback de conflicto.

`ShopKitsPluginIntegrationTests` carga el `.so` real mediante PluginManager y verifica rutas a dos orígenes, mayúsculas/argumentos, detalle y paginación, respuestas acotadas ante entradas inválidas, ausencia de comandos de compra ficticios, pausa/reanudación, recarga UTF-8 y precios, aislamiento de instancia y rechazo de configuraciones inválidas antes de registrar callbacks.

Para activar compras y reclamación faltan identidad/autoridad del sujeto, revisión nativa del inventario y entrega con evidencia observable, un adaptador que use el permiso apropiado, y aceptación de cliente con resultado y desconexiones. `/buy` y `/kit` se añadirán después de verificar ese contrato; no se conectan automáticamente a los recibos offline.
