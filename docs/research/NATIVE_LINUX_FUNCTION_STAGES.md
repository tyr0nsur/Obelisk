# Etapas de funciones nativas Linux

Fecha: 2026-10-14. Objetivo: ampliar el prototipo mediante funciones concretas
del servidor ASE Linux public, conservando el mundo y personaje actuales de
TheIsland. El ejecutable de referencia tiene SHA256
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.

Cada función necesita evidencia propia. Un nombre encontrado en una captura,
un layout histórico, una compilación o un arranque no demuestra una operación
de juego. Tampoco transforma los plugins actuales en una SDK completa o estable.
El catálogo privado `native-linux-function-catalog.json` queda fuera del árbol
Git; registra propietarios, procedencia y estados sin publicar bindings del
adaptador. Este documento conserva la ruta de trabajo y sus límites.

## Cómo se registra el avance

| Estado | Evidencia requerida |
| --- | --- |
| Nombre candidato | Nombre y clase de origen identificados; todavía sin binding utilizable. |
| Metadata verificada | Registro o constructor vinculado a su clase propietaria en el ejecutable fijado. |
| ABI enfocada | Wrapper, thunk o llamada comprobados: argumentos, retorno, ownership y tamaños. |
| Arranque verificado | El adaptador correspondiente valida el perfil realmente cargado y se activa. |
| Cliente real | Un cliente confirma el efecto concreto; se identifica qué cliente y qué escenarios faltan. |

Estos estados se anotan por función y por variante. La notificación de chat y
el mensaje en el chat privado son rutas diferentes: la aceptación de la primera
no valida la segunda. Las 51 comprobaciones del perfil de identidad/lifecycle y
las 16 adicionales de la ruta Direct suman 67 puntos de instrucciones en fuente;
no representan 67 APIs, 67 efectos de juego ni un porcentaje de cobertura del
servidor. La validación anterior de arranque cubre 51 puntos; el nuevo runtime instalado
valida los 67. La presentación de Direct en el cliente permanece pendiente.

## Etapas

| Etapa | Funciones o datos necesarios | Estado y siguiente evidencia |
| --- | --- | --- |
| ChatReplies | `ShooterPlayerController.ServerSendChatMessage`, `ClientServerChatMessage`, `ClientServerChatDirectMessage` | `/ping` y notificación dirigida confirmados con Epic. La variante Direct tiene investigación enfocada; falta corroborar su presentación en el cliente. Steam y separación entre dos jugadores siguen pendientes. |
| LoginInfo | `ShooterPlayerState.GetUniqueIdString`, nombre copiado de PlayerState, `GameMode.K2_PostLogin`, `ShooterGameMode.OnLogout`, `HandleNewPlayer` | `/whoami` y entrega de eventos tipados de login y logout observados con Epic. Relogin tipado y conexiones interrumpidas siguen pendientes. Un retorno de HandleNewPlayer no constituye autenticación. |
| HotControl | Canal local del runtime; despacho controlado al hilo del juego; operaciones permitidas de plugin/configuración | Barrera de generaciones, ocho familias y canal UNIX privado verificados. Trece peticiones reales ejecutaron pausa/reanudación, dos recargas y parada/arranque de oPing sin cambiar el PID del servidor. Contrato managed-only requerido; instalación de nuevos IDs y plugins con workers propios quedan fuera. Los hooks nativos permanecen residentes. |
| Permissions | Fuente de autoridad elegida y consultas pequeñas; candidatos de administración como `ServerKickPlayer` | Nombres y metadata históricos orientan el análisis. Todavía no existe una API de permisos validada. Los nombres e IDs copiados del jugador no conceden autoridad. |
| Players | `ServerListPlayers` y observaciones actuales; después operaciones concretas elegidas para un plugin | Identidad de la invocación actual funciona. Listado, destino persistente y operaciones posteriores requieren su propio contrato y validación de desconexión. |
| Structures | `PrimalStructure.AllowStructureAccess`, `IsAllowedToDemolish`, `SetVariant`; `PrimalStructureItemContainer.VerifyPinCode` | Candidatos en fixtures históricos del mismo SHA. Verificar nuevamente registro, propietario y ABI antes de observar una estructura real. |
| Inventory | `ServerRequestInventoryUseItem`, `ServerRequestInventoryUseItemWithActor`; `PrimalItem.CanUse`, `CanRepair`, `CraftBlueprint` | Candidatos históricos. Comenzar con una observación pequeña y copiada; mutación, arrays y ownership necesitan pruebas específicas. |
| Dinos | `PrimalDinoCharacter.AllowCarryCharacter`, `AddPassenger` | Candidatos históricos; falta binding actual verificado, presupuesto y escenario de juego. |
| Tribes | `ShooterPlayerController.IsInTribe`, `AllowTribeGroupPermission`, `ServerRequestTribeLog`, `ClientReceiveMyTribeOnlineList` | Candidatos históricos; verificar los significados de pertenencia, permisos y retorno. No derivar autoridad ni identidad de tribu de índices o texto. |

## Análisis dirigido del ejecutable

1. Elegir una necesidad de plugin y una función pequeña de la etapa correspondiente.
2. Corroborar el nombre con su registro o constructor y clase declaradora. Separar
   esa clase del objeto receptor y de sus subclases en ejecución.
3. Seguir solamente el wrapper, exec thunk, implementación y llamador pertinentes.
   Comprobar por separado tamaño lógico de parámetros y almacenamiento padded.
4. Registrar la ABI SysV, retorno, propiedad de buffers, hilo permitido y validez
   del objeto. Un nombre no produce un offset ni habilita una llamada.
5. Añadir el binding privado al perfil del SHA actual con bytes y procedencia
   verificables. Los fixtures históricos permanecen candidatos hasta ese paso.
6. Comprobar la operación mediante fixtures significativos, arranque y un caso de
   cliente real. Registrar rechazos y escenarios pendientes junto al éxito.

El trabajo utiliza las capturas y análisis enfocados existentes y Ghidra/REA
cuando la función elegida lo requiera. No exige un autoanálisis global del ELF ni
un dump completo de UE para avanzar. Los datos públicos del plugin deben ser
copiados y tener un lifetime documentado; los punteros UE quedan en el adaptador.

## Configuración y conservación del mundo

La configuración archivada de mayo se prepara por separado del código y de los
guardados. TheIsland conservará el mundo y personaje actuales. No se encontraron
guardados históricos recuperables. Los INIs ya están instalados y A2S confirma TheIsland,
70 slots y protección de contraseña. Se conserva el hash del perfil actual y
el mundo respaldado. Los efectos de los rates y el personaje visible requieren
comprobación con el cliente. La configuración de acceso actual debe prevalecer sobre las
contraseñas del archivo antiguo y RCON permanece deshabilitado.

Antes de aplicar configuración se coordina un guardado y backup del estado
actual. La etapa HotControl no debe usarse para prometer que todos los INIs,
hooks o plugins pueden cambiarse sin reiniciar. Los estados de esta tabla tampoco
modifican los contratos históricos de promoción o estabilidad de módulos.


## Current suite increment

The current increment adds copied position/rotation, native tribe ID, mount
ID pair and aimed structure ID through independently checked current bindings.
Scoped destination tokens invalidate on logout/relogin; old invocations cannot
read/send into successor sessions. Thirty-two live requests verified the four
new plugin lifecycles, following a core upgrade; they do not validate game query,
message or teleport effects. Shop fulfillment remains disabled because the
native boolean permits partial delivery. Persistent identity, precise inventory
receipts and domain mutations remain separate stages. The newer suite audit
supersedes the older new-plugin-discovery limitation in the table above.
