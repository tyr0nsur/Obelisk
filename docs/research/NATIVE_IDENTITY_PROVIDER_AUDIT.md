# Native identity and provider audit

Fecha: 2026-10-14. Investigación original sobre el ejecutable Linux ASE 361.7,
Steam build 21241282, 86,269,536 bytes, SHA256
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
No se consultó código fuente de ArkApi. El binario se trató como datos y no se
ejecutó ninguna función del juego. Los nombres semánticos de candidatos sin
símbolo son inferencias de sus instrucciones, literales, registros e imports.

## Resultado que permite avanzar

Se localizaron las ramas nativas de verificación de identidad Steam y EOS, junto
con la representación compuesta que produce el ID numérico observado. Existe
una ruta concreta para investigar el sujeto persistente que necesitan permisos,
economía y homes. Todavía falta correlacionar el resultado de autenticación del
proveedor con la conexión y sesión actuales; ningún nuevo sujeto autenticado se
ha publicado en el SDK ni habilitado para conceder permisos o cobrar compras.

El ID actual puede contener marcadores Steam/EOS/Stadia. Esos marcadores también
se generan al parsear un número; identifican una representación y no prueban que
su poseedor haya sido autenticado. `IsValid` tampoco autentica: los dos cuerpos
encontrados únicamente comprueban que el campo numérico no sea cero.

## Método y reproducibilidad

Se usaron ELF PT_LOAD, `objdump`, imports dinámicos y FDE de `.eh_frame` del SHA
actual, y siete decompilaciones enfocadas Ghidra 12.1 con `-noanalysis`, ventana
acotada, 2 CPU y heap 2 GiB. Cada extracción duró aproximadamente 11 segundos y
comprobó que el archivo no había cambiado. El prefijo genérico
`ProcessEvent_candidate` del script Ghidra no identifica a estas funciones como
ProcessEvent; es un nombre de trabajo que el extractor asigna a cualquier entrada.

El verificador independiente es
[native_identity_provider_audit.py](../../scripts/research/native_identity_provider_audit.py):

```bash
python3 scripts/research/native_identity_provider_audit.py \
  --binary /servidor/ark/obelisk-lab/server/ShooterGame/Binaries/Linux/ShooterGameServer
```

Verifica bytes, literales, slots de vtable y presencia de nombres importados.
El modo opcional `--output` crea un archivo nuevo 0600 y rechaza sobrescrituras.
Su resultado mantiene explícitamente falsas la aceptación de gameplay y la
disponibilidad de un principal autenticado. Los artefactos enfocados se guardan
privados en `/servidor/ark/obelisk-lab/logs/identity-provider-*`.

Hay una trampa de procedencia relevante: el artefacto anterior
`identity-current-get-unique-id.run.json`, pese a llamarse current, pertenece al
SHA `951a5977...` y usa `0xfa1970`/offset `0x4b8`. No sirve como evidencia de esta
rama. Los puntos siguientes se extrajeron nuevamente del SHA `7e7ded49...`.

## Cadena exacta de la observación actual

| Punto | Evidencia del binario actual | Alcance |
| --- | --- | --- |
| Clase ShooterPlayerState | Binding `0x135c131`, nombre UTF32 `0x40d7234`, almacenamiento de clase `0x58eeb80` | Identifica la clase registrada de la entrada |
| GetUniqueIdString | Registro `0x135f517` con literal ASCII `0x4161040`, thunk `0x1536150`, helper de registro `0x1ccc140` | Identifica el nombre y la entrada nativa |
| Thunk de la clase | Call `0x153617f` a `0xfcf060` | Enlaza el registro con la implementación |
| Implementación vigente | `0xfcf060`: lee PlayerState `+0x4c8`, devuelve FString vacío si falta, llama virtual `+0x30` si existe | Identidad observada, sin verificación del proveedor |
| ToString de identidad compuesta | `0x354c420`: obtiene `+0x50` y formatea `%llu` (`0x403c8f8`) | La cadena actual es numérica y pierde datos de proveedor |
| Vtable usada en rama Steam | `0x46dcb60`, instalada por `0x350b69b`; `+0x30 -> 0x354c420` | Familia compuesta, vinculada estáticamente a la rama Steam candidata |
| Vtable usada en rama EOS | `0x46e1710`, instalada dentro de `0x356d2e0`; `+0x30 -> 0x354c420` | La misma representación numérica también aparece en la rama EOS |

La cadena no demuestra qué vtable recibió un jugador real ni conserva por sí
misma una cuenta estable. Será necesario comprobar ambas correlaciones mediante
observación pasiva en el callback válido y sin retener punteros UE en plugins.

## Representación compuesta y proveedor

El diagnóstico nativo `0x354c5d0` usa el literal `0x46d9874` que nombra Steam,
EOS, Stadia, OriginalEOSNetString, EpicAccountId, ProductUserId y máscaras. El
orden de sus argumentos permite vincular los campos siguientes:

| Campo privado | Significado observado |
| --- | --- |
| `+0x20`, FString | OriginalEOSNetString |
| `+0x30`, FString | EpicAccountId |
| `+0x40`, FString | ProductUserId |
| `+0x50`, uint64 | UniqueIdAsUint64 |
| `+0x58`, byte | Marcador EOS, getter `0x354c5b0` |
| `+0x59`, byte | Marcador Steam, getter `0x354c5a0` |
| `+0x5a`, byte | Marcador Stadia, getter `0x354c5c0` |

El constructor `0x35562e0` instala máscaras `0xe000000000000000`,
`0x6000000000000000` y `0x7fffffffffffffff` en `+0x08/+0x10/+0x18`.
En la rama numérica del parser `0x3552e90`, desde `0x3552f9d`, se escribe el
número en `+0x50` y se generan los flags EOS/Steam comparando las máscaras.
Por ello, una clasificación por bits es solamente procedencia de formato.
Los cuerpos `0x35304b0` y `0x358e4f0` hacen `uint64(+0x50) != 0`.

EpicAccountId y EOS ProductUserId deben conservar namespaces distintos. No se
debe trasladar el formato decimal de `/whoami` a uno de esos namespaces ni unir
una cuenta Steam y una Epic por nombre, caracteres coincidentes o un valor
numérico igual. Estos layouts permanecerían exclusivamente en el adaptador
privado si una futura investigación autoriza usarlos.

## Verificación EOS localizada

La entrada candidata `0x356d2e0` aparece en la vtable de interfaz
`0x46de690 + 0x238`. Construye la identidad compuesta, obtiene/valida la forma
EpicAccountId mediante los imports `EOS_EpicAccountId_FromString` e `IsValid`,
compara una cadena de cuenta con la identidad esperada y valida sintaxis de PUID
mediante `EOS_ProductUserId_FromString` e `IsValid`. Estos controles preceden
la verificación del token; no equivalen al resultado de esta última.

En `0x356d850..0x356d871` se llama a `EOS_Auth_VerifyIdToken@plt` (`0x646200`),
con callback `0x35a1310`. El callback evita la ruta normal si el resultado bruto
es `0x13`; en los demás casos despacha la captura. La closure `0x358a5f0`
convierte `ResultCode == 0` en bool y pasa la identidad capturada a virtual
`+0x258`, que en esta vtable apunta a `0x353a4d0`. Esa función emite el bool y la
identidad a delegados; no constituye por sí sola un caché de autenticación.

Epic documenta la conversión de EpicAccountId y verificación de ID tokens en
servidores. La conclusión del binario es más limitada: existe esa llamada y una
ruta de resultado, pero Obelisk todavía no recibe/correlaciona dicho resultado.
[Epic: retrieve and validate ID tokens](https://dev.epicgames.com/docs/epic-online-services/accounts-and-social/eos-epic-account-services/auth-interface/retrieve-and-validate-id-tokens?lang=en-US).

El bypass `DisableEOSServerAuth` es explícito. El literal se evalúa desde
`0x356d328`, se conserva en global privado `0x5a119d8` y, si está activo,
`0x356d34a` escribe ambos flags de salida a 1 sin llamar al proveedor. Además,
la implementación genérica `0x3549c00` escribe ambos flags a 1 de manera
incondicional. Un retorno booleano o flags de finalización sin procedencia no
pueden elevarse a autenticación. No se activó ni modificó este bypass.

## Rama Steam y límite temporal

`0x350b4d0`, virtual `0x46cec70 + 0x238`, comienza con ambos flags de salida a
0. Obtiene `SteamGameServer@plt` (`0x647080`), exige la forma válida y el marcador
Steam, separa una cadena de identificación/token, compara la cadena numérica
con la identidad solicitada y prepara un ticket en la cola interna. La vtable
Steam compuesta `0x46dcb60` se instala durante esta preparación. Las ramas de
fallo escriben flags 1/0; la rama preparada puede retornar con 0/0. El retorno
de la función inicia o termina una operación, sin probar su aceptación remota.

Se localizaron además registros explícitos de callbacks del servidor Steam:

| Registro propio | Target y datos | Interpretación limitada |
| --- | --- | --- |
| `0x353601b..0x3536032`, callback ID 201 | Target `0x350a610`, vtable wrapper `0x46dc3b0`, payload 16 bytes | Candidato GSClientApprove: copia uint64 en `+0/+8` del payload, busca la cuenta en el mapa protegido y escribe los bytes `+0x81/+0x82` del registro a `0/1`; copia la segunda identidad en dicho registro |
| `0x3536091..0x35360a5`, callback ID 202 | Target `0x350a8c0`, vtable wrapper `0x46dc3e0`, payload 140 bytes | Candidato GSClientDeny: busca por el primer uint64 y escribe los mismos bytes a `0/0` |

Los wrappers corresponden a member-function callbacks: conservan instancia,
target y ajuste `this`. Los tamaños 16/140 aparecen en `0x3549e90/0x3549ee0`.
La pareja de IDs, formas de payload y conducta coincide con los callbacks
legacy documentados por Steam. Es una inferencia de correspondencia, todavía sin
un callback real correlacionado por Obelisk. El segundo ID de la aprobación
corresponde al propietario de la licencia según el contrato Steam; no debe
reemplazar al sujeto que está jugando para asignar wallet o permisos.

Esta rama indica que hay que estudiar primero el recorrido legacy
`SendUserConnectAndAuthenticate -> GSClientApprove/GSClientDeny`. No se debe
asumir que la rama usa `BeginAuthSession/ValidateAuthTicketResponse_t` solo porque
esa API más reciente aparezca en documentación. Falta localizar la llamada
concreta de envío de ticket y el consumo de ese estado por la conexión. No se
asignó una firma o un slot Steam externo por comparación con otra versión de SDK.
Steam distingue los controles básicos de un ticket de su aceptación posterior.
[Steamworks: user authentication](https://partner.steamgames.com/doc/features/auth),
[ISteamGameServer: auth y callbacks](https://partner.steamgames.com/doc/api/isteamgameserver).

## Contrato mínimo para la siguiente etapa

El servicio residente deberá distinguir `Unknown`, `Observed`, `Pending`,
`Verified`, `Rejected` y `Revoked`. Solo `Verified` podría producir un principal
durable. La transición exige simultáneamente un resultado del proveedor exitoso
y no bypass, una cuenta canónica con namespace explícito, correlación con la
misma conexión/PlayerState, y sesión/token/epoch actuales. El callback tardío de
una sesión anterior debe descartarse, aunque se reutilice su dirección.

La salida futura puede copiar `{provider_namespace, account_subject,
session_token, process_epoch, verification_state}` a almacenamiento propio, sin
punteros, tokens JWT, tickets ni secretos del proveedor. La recepción y
correlación de callbacks permanecerían en el núcleo residente. Logout,
revocación o pérdida de conexión invalidarán autoridad antes de notificar a
plugins. La persistencia de homes necesita además un fingerprint del mundo;
un epoch de proceso no identifica un mapa o save.

La validación pendiente debe confirmar Steam y Epic por separado y juntos,
relogin con sujeto igual y sesión distinta, nombres iguales/renombrados,
callback pendiente/fallido/tardío, revocación, desconexión y reinicio de servidor.
Las pruebas negativas de token se desarrollarán primero con fixtures del
adaptador; no se alterará el cliente ni se llamará a funciones nativas sin un
binding y un alcance verificados. El informe de beta debe redactar identidades
y conservar solo plataforma, versión, tiempos y resultado de las correlaciones.
