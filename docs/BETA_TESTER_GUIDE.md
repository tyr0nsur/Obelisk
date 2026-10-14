# ObeliskNative — guía de comandos y aceptación beta

Actualización: 14 de octubre de 2026. Inventario contrastado con los seis módulos
y su configuración activa. Las secciones siguientes están pensadas para lectura
en Discord. Adjunta este documento como guía completa junto al resumen de
comandos; la numeración permite localizar cada etapa y reportar sus casos.

## Mensaje 1 — estado y preparación

**ObeliskNative · beta de ARK: Survival Evolved para Linux**

Tenemos seis módulos y 20 comandos de chat para probar en TheIsland: utilidades, catálogo de tienda/kits, homes de sesión, chat avanzado y consultas de dinos, estructuras y tribus.

**Cómo probar:** entra al servidor y escribe los comandos en el **chat del juego**, una vez cargado tu personaje. No se escriben en el menú principal ni requieren la consola administrativa. Las credenciales de acceso se facilitan por el canal privado que indique la administración.

**Qué está comprobado:** un cliente real Epic 361.8 recibió `pong`, confirmó nombre/ID nativo y chat ordinario en las versiones anteriores. Se registraron observaciones de login y logout. El nuevo conjunto pasó 156 pruebas CTest y 32 operaciones de módulos en el servidor sin cambiar el proceso durante esas operaciones.

**Qué sigue pendiente:** aceptación con clientes reales de los comandos nuevos, presentación en la caja de chat, Steam, privacidad entre jugadores, nuevo relogin y desplazamiento de homes. Los tests automáticos y los módulos cargados no confirman esos resultados.

Homes guarda puntos solo durante la sesión. Tienda/kits muestra información: todavía no compra, cobra ni entrega objetos. Dino/estructura/tribu son consultas. El cierre completo del servidor tiene un fallo conocido pendiente de resolver; esta es una beta, no una certificación de producción.

Cada caso empieza como **PENDIENTE**. Usa **OK**, **FALLO**, **BLOQUEADA** o **NO EJECUTADA**, con evidencia y plataforma.

## Mensaje 2 — utilidades e identidad

**Comandos · utilidades**

- `/ping` → responde `pong` al jugador que lo envía.
- `/whoami` → `Nombre: … | ID nativo: …`. Ese ID es una observación nativa; no se presenta como cuenta autenticada Steam/Epic ni concede permisos.
- `/help` → inventario de los 20 comandos y ayuda configurada del servidor.
- `/rules` → normas configuradas.
- `/motd` → bienvenida configurada.
- `/serverinfo` → información configurada de TheIsland/ObeliskNative.
- `/help rules` o `/help /rules` → normas.
- `/help motd` o `/help /motd` → bienvenida.
- `/help info`, `/help serverinfo` o `/help /serverinfo` → información.

**Sintaxis:** `/ping` y `/whoami` deben escribirse exactamente en minúsculas, sin argumentos ni espacios añadidos. `/PING` y `/ping extra` no son esos comandos y siguen el chat original de ARK.

Los otros 18 verbos aceptan mayúsculas ASCII: `/HELP`, `/SHOP`, `/WHEREAMI`, etc. Los argumentos se separan con espacios o tabuladores; no antepongas espacios al `/`. Los prefijos como `/helpful` no deben activar `/help`.

Una respuesta privada debe verla únicamente quien ejecuta el comando. Comprueba dónde aparece: la caja de chat o la notificación superior. La prueba antigua de `Server message: pong` no confirma la presentación nueva en la caja de chat.

No publiques capturas de `/whoami` con nombres reales o IDs completos; ocúltalos antes de compartirlas fuera del canal de pruebas autorizado.

## Mensaje 3 — tienda, kits y consultas del mundo

**Comandos · tienda y kits**

- `/shop` o `/shop 1` → primera página de la tienda.
- `/shop recursos_demo` → detalle de “Recursos de muestra”; precio configurado: 1.000 puntos.
- `/kits` o `/kits 1` → primera página de kits.
- `/kits inicio_demo` → detalle de “Kit de inicio de muestra”; límite configurado: 1, espera: 86.400 s.
- Sintaxis completa: `/shop [pagina|id]` y `/kits [pagina|id]`.

Son datos de catálogo. El mensaje incluye: `Catalogo informativo. Compras y entregas de kits aun no estan disponibles.` Los precios/límites no activan cobros ni reclamaciones. No hay comandos `/buy` ni `/kit` implementados. La página muestra hasta tres entradas; ahora hay una entrada de cada tipo.

**Comandos · mundo, todos sin argumentos**

- `/whereami` → posición X/Y/Z de tu personaje, en unidades del mundo con dos decimales. No son coordenadas GPS de latitud/longitud.
- `/tribe` → ID nativo de tu tribu o `No perteneces a una tribu.`
- `/dino` → pareja de IDs del dino que tienes montado. A pie: `Monta un dino para consultar su ID.`
- `/structure` → ID de la estructura a la que apuntas. Sin estructura válida: `Apunta a una estructura para consultar su ID.`

Consultan el contexto de quien envía el comando. No buscan otro jugador, enumeran el mapa ni cambian dinos, estructuras, propiedad o permisos. El ID de tribu observado tampoco decide autorizaciones.

## Mensaje 4 — homes de sesión

**Comandos · homes**

- `/sethome base` → guarda tu posición actual como `base`.
- `/homes` → lista tus puntos de esta sesión.
- `/home base` → intenta llevar a tu personaje al punto guardado.
- `/delhome base` → elimina ese punto.

Nombre: entre 1 y 32 caracteres, solo letras minúsculas `a-z`, números, `_` y `-`. `base_2` es válido; `Base`, `casa azul` y `café` no. El verbo acepta mayúsculas, el nombre conserva estas reglas.

Configuración actual: **3 puntos por sesión**, **30 segundos** de espera después de un desplazamiento aceptado por el motor. Actualizar un nombre existente sustituye su posición y no ocupa otro punto.

Los puntos desaparecen al **reconectar**, **recargar el módulo** o **pararlo e iniciarlo**. Pausa/reanudación conserva los puntos. No hay homes persistentes de cuenta ni entre mapas en esta beta.

`/home` exige personaje vivo, despierto y sin montura, y usa comprobación de colisiones. Conserva la orientación actual. Una respuesta de posición confirmada significa que una nueva consulta encontró el personaje cerca del punto; hay que comprobar también el movimiento en el cliente.

Si aparece `Desplazamiento pendiente de confirmar`, espera antes de reintentar: puede haberse aceptado el movimiento y consumido la espera. Si aparece que no pudo aceptarse, registra el estado del personaje.

Primera prueba: un punto cercano, en terreno abierto y seguro, con la administración presente.

## Mensaje 5 — chat avanzado

**Comandos · chat avanzado**

- `/chathelp` → instrucciones y tu token de sesión actual.
- `/chatlist` o `/chatlist 1` → destinos observados, ocho por página.
- `/chatglobal Hola equipo` → mensaje con prefijo `[Global]` a las sesiones observadas de este servidor, incluido el emisor.
- `/tell <sesion> Hola` → privado al token de sesión indicado y copia al emisor. Sustituye `<sesion>` por el número actual mostrado en `/chatlist` o `/chathelp` del destinatario.

El token es temporal; no es el ID nativo de `/whoami`, una cuenta, un nombre de jugador ni un ID de Discord. Dos jugadores pueden tener el mismo nombre: usa siempre su token.

La lista contiene **sesiones observadas**, no un censo garantizado de todos los jugadores conectados. Para preparar una prueba, ambos participantes pueden enviar primero `/chathelp` o un mensaje normal. Máximo de lista actual: 64 sesiones; si no puede obtenerse completa, el módulo rechaza la operación y lo explica.

Mensajes: **1–512 bytes UTF-8**, sin saltos de línea ni caracteres de control. Conserva acentos y emoji válidos. Límite compartido de `/chatglobal` y `/tell`: **5 envíos por cada ventana de 3 segundos**, por sesión. `/chathelp` y `/chatlist` no gastan ese límite.

El envío nativo no confirma recepción del cliente. No hay chat entre mapas, canales local/tribu del módulo ni puente Discord activo en estos comandos. El silenciamiento administrado del módulo afecta a sus envíos, no al chat normal de ARK.

## Mensaje 6 — pruebas de entrada y sintaxis

**Etapa 1 · plataformas y comandos básicos**

Repite los casos en Epic y Steam; anota la versión exacta del cliente. Después realiza una sesión conjunta Steam + Epic.

- [ ] **P01** Entrar, cargar personaje en TheIsland y enviar chat normal → entrega normal, sin desconexión.
- [ ] **P02** `/ping` → un `pong`, en la interfaz prevista, sin repetir el comando al resto del servidor.
- [ ] **P03** `/whoami` → tu nombre e ID nativo disponibles o explicación clara; no los de otro jugador.
- [ ] **P04** `/help`, `/rules`, `/motd`, `/serverinfo` → textos correctos y legibles, incluidos acentos.
- [ ] **P05** Todas las variantes de tema de `/help` documentadas → mismo texto del tema correspondiente.
- [ ] **P06** `/help desconocido` y `/rules extra` → explicación del uso; el juego sigue respondiendo.
- [ ] **P07** `/HELP RULES`, `/SHOP`, `/WHEREAMI`, `/HOMES`, `/CHATHELP` → variantes de verbo reconocidas.
- [ ] **P08** `/PING`, `/WHOAMI`, `/ping extra`, `/whoami extra` → no ejecutan los comandos exactos; siguen el chat original.
- [ ] **P09** `/helpful`, `/shopping`, `/homebase`, un comando desconocido y texto normal → no disparan un comando por coincidencia parcial.
- [ ] **P10** Separación con varios espacios y, si el cliente lo permite, tabulador → argumentos correctos; espacios antes de `/` no activan comandos.
- [ ] **P11** Repetir comandos desde cada modo de chat disponible: global, tribu, local y alianza → las respuestas del módulo mantienen el destinatario esperado y el chat ordinario mantiene su canal.

No marques Steam como OK por haber configurado crossplay: requiere un cliente Steam real.

## Mensaje 7 — privacidad y reconexión

**Etapa 2 · dos jugadores y ciclo de sesión**

Usa jugadores A y B; un tercero C permite comprobar mejor los privados. Cada participante debe registrar su propia pantalla.

- [ ] **I01** A envía `/ping` y luego B → cada uno ve únicamente su respuesta.
- [ ] **I02** A/B alternan `/whoami`, `/whereami`, `/tribe`, `/shop`, `/homes` → cada respuesta y dato corresponden al emisor.
- [ ] **I03** A envía `/tell <token_B> prueba` → A y B lo ven; C no ve el privado ni el texto del comando original.
- [ ] **I04** Nombres iguales o similares, si es viable → `/tell` distingue por token y no elige por nombre.
- [ ] **I05** Anotar token de B, desconectar B y repetir `/tell` hacia ese token → destino no disponible; no llega a otro jugador.
- [ ] **I06** B reconecta, obtiene token nuevo y recibe un privado nuevo → token anterior sigue rechazado.
- [ ] **I07** Reconectar varias veces → siguen funcionando chat ordinario y `/ping`; no llegan respuestas de una sesión anterior.
- [ ] **I08** Administración corrobora en logs privados login, logout y **nuevo relogin**, con orden y sesión correctos. La observación anterior de relogin de juego no cerró este caso del evento nuevo.
- [ ] **I09** Cancelar una conexión de prueba antes de completar la entrada, coordinado con administración → no queda un destino utilizable; no se confunde una entrada iniciada con una sesión activa ni con autenticación.
- [ ] **I10** A/B envían comandos casi a la vez → ninguna mezcla de nombre, destino, posición o contenido.

El tester confirma pantallas; administración confirma eventos y rechazo de contextos antiguos. Los logs completos permanecen privados.

## Mensaje 8 — aceptación de chat avanzado

**Etapa 3 · chat avanzado**

- [ ] **A01** Ambos envían `/chathelp`, luego `/chatlist` → tokens actuales y nombres legibles; lista como sesiones observadas.
- [ ] **A02** `/chatlist 0`, `/chatlist abc`, `/chatlist 999` y `/chathelp extra` → error de uso o página inexistente, sin romper el chat.
- [ ] **A03** `/chatglobal Hola ñ 😀` → `[Global]` y nombre correcto en emisor y destinos observados, una sola vez cada uno.
- [ ] **A04** Privado con texto UTF-8 → prefijo `[Privado]`, destinatario correcto y copia al emisor; no aparece como chat público.
- [ ] **A05** `/tell` sin argumentos, sin mensaje, destino `0`, nombre en vez de token o token inexistente → explicación clara y ningún envío al destinatario equivocado.
- [ ] **A06** Esperar al menos 3 s sin global/privado para limpiar gastos anteriores. Enviar seis en menos de 3 s, coordinado → cinco admitidos, sexto limitado. Esperar otros 3 s sin envíos → vuelve a admitir.
- [ ] **A07** Mientras A está limitado, B envía → límite independiente por sesión; `/chathelp` sigue disponible.
- [ ] **A08** Texto vacío o superior a 512 bytes → rechazo si llega al módulo. Si el cliente lo corta antes, registrar BLOQUEADA por UI y longitud realmente enviada.
- [ ] **A09** Administración activa temporalmente un mute de la sesión de A → global/privado del módulo rechazados; chat normal de ARK sigue funcionando. Restablecer configuración al terminar.
- [ ] **A10** Destinatario se desconecta durante la prueba → no hay envío a una sesión reutilizada; registrar aviso si desaparece durante el envío.
- [ ] **A11** Saltos de línea/caracteres de control → rechazo si llegan al módulo; si la UI impide enviarlos, NO EJECUTADA en cliente y evidencia automática por separado.

Paginación con más de ocho destinos y lista incompleta con más de 64 requieren una prueba administrada; no se dan por aceptadas por fixtures.

## Mensaje 9 — aceptación de tienda y kits

**Etapa 4 · catálogo informativo**

- [ ] **S01** `/shop` y `/shop 1` → “Recursos de muestra”, 1.000 puntos y aviso de entrega no disponible.
- [ ] **S02** `/shop recursos_demo` → nombre, descripción, precio configurado y mismo aviso.
- [ ] **S03** `/kits` y `/kits inicio_demo` → kit correcto; detalle con límite 1 y espera 86.400 s, como información.
- [ ] **S04** `/SHOP RECURSOS_DEMO` y `/KITS INICIO_DEMO` → detalle equivalente; aquí se admiten variantes ASCII del ID.
- [ ] **S05** `/shop 0`, `/shop 1 extra`, `/kits 0` → uso correcto; `/shop 2` y `/kits 2` → fuera de rango con el catálogo actual de una entrada.
- [ ] **S06** ID desconocido, número desbordado o argumentos extra → respuesta acotada, sin cerrar el cliente ni el servidor.
- [ ] **S07** Repetir consultas → no cambia inventario, saldo ni contador de reclamación. El aviso sigue presente.
- [ ] **S08** `/buy` y `/kit` → no realizan compras ni entregas; son comandos no registrados del módulo y siguen el chat original.
- [ ] **S09** Administración prepara cuatro entradas de prueba y coordina recarga → páginas de tres entradas, detalle correcto y configuración nueva visible; restaurar el catálogo de beta.
- [ ] **S10** Dos jugadores consultan a la vez → respuestas privadas sin mezclar origen.

No se acepta “tienda terminada” con estos casos. Entrega exacta de objetos, autoridad de cuenta, cobro/recibo y recuperación tras fallos pertenecen al siguiente hito; permanecen desactivados en juego.

## Mensaje 10 — aceptación de consultas

**Etapa 5 · personaje, tribu, dino y estructura**

- [ ] **W01** `/whereami` quieto en un lugar conocido → X/Y/Z finitos y legibles; mover a un segundo lugar cambia la posición.
- [ ] **W02** Saltar o cambiar de altura → Z coherente; confirmar que son unidades del mundo, no GPS.
- [ ] **W03** Montar un dino y usar `/whereami` → consulta del personaje actual, sin datos de otro jugador ni selección de un actor arbitrario.
- [ ] **W04** Personaje sin tribu `/tribe` → `No perteneces a una tribu.`; personaje con tribu → ID coherente con evidencia del administrador.
- [ ] **W05** Dos miembros de la misma tribu y uno de otra → observaciones coherentes; no conceden permisos.
- [ ] **W06** `/dino` a pie → indicación de montar; montar un dino → pareja de IDs; cambiar a otro → IDs del dino actual.
- [ ] **W07** Apuntar a una estructura con `/structure` → ID; cambiar a otra → observación del objetivo actual.
- [ ] **W08** Apuntar al cielo, suelo, jugador o dino → no responde con el ID de una estructura anterior.
- [ ] **W09** Estructura propia y, con autorización, de otra tribu → solo consulta; no cambia propiedad, acceso, contenido ni vida.
- [ ] **W10** Añadir argumentos a los cuatro comandos → uso “sin argumentos”; no consulta a jugadores por nombre.
- [ ] **W11** Dos jugadores en lugares/monturas/objetivos distintos → cada consulta corresponde a su propio contexto.
- [ ] **W12** Desmontar, desconectar o cambiar objetivo entre consultas → no conserva una observación antigua como destino permanente.

No hay spawn, tame, demolición, transferencia o edición de dinos/estructuras/tribus en estos comandos.

## Mensaje 11 — aceptación de puntos home

**Etapa 6 · guardar, listar y eliminar homes**

- [ ] **H01** `/homes` en sesión nueva → `Sin puntos de esta sesión. Usa /sethome nombre.`
- [ ] **H02** `/sethome base` en zona segura, luego `/homes` → guardado y nombre `base` visible únicamente para el dueño.
- [ ] **H03** Guardar `base`, `playa` y `base_2`; intentar un cuarto nombre → límite de tres puntos.
- [ ] **H04** Con tres puntos, mover y repetir `/sethome base` → actualiza `base` sin consumir un cuarto hueco.
- [ ] **H05** `/delhome playa` → eliminado; repetir → no existe; guardar otro punto después → hueco disponible.
- [ ] **H06** `/home inexistente` y `/delhome inexistente` → no existe, sin movimiento.
- [ ] **H07** Nombre vacío, `Base`, `casa azul`, acentos o más de 32 caracteres → explicación de las reglas, sin guardar/eliminar/mover.
- [ ] **H08** Nombre de exactamente 32 caracteres válidos y nombres con números, `_`, `-` → aceptados dentro del límite.
- [ ] **H09** `/homes extra` → uso; `/SETHOME base` → verbo aceptado sin convertir `Base` en un nombre válido.
- [ ] **H10** A/B guardan el mismo nombre en lugares distintos → cada lista y desplazamiento usa solo los puntos propios.

El almacenamiento persistente de cuenta no está conectado a estos comandos. Ver puntos guardados durante la sesión no demuestra persistencia después de reconectar o reiniciar.

## Mensaje 12 — aceptación de desplazamientos home

**Etapa 7 · movimiento, espera y estados**

Prueba inicial supervisada, a pie, despierto, vivo y en terreno abierto. Guarda `base`, aléjate poco y usa `/whereami` antes/después con evidencia visual. Para probar estados y colisiones, espera primero a que venza el cooldown: un rechazo por espera no verifica esos casos.

- [ ] **H11** `/home base` → respuesta y movimiento real cerca del punto; sin caída peligrosa, bloqueo ni desincronización del personaje.
- [ ] **H12** Girar antes de `/home base` → conserva la orientación actual.
- [ ] **H13** Tras movimiento aceptado, repetir antes de 30 s → `Espera antes de volver a usar /home.`; después de la espera vuelve a admitirse.
- [ ] **H14** Si responde “pendiente de confirmar” → registrar posición/interfaz y esperar; no confundir esa respuesta con llegada confirmada ni repetir inmediatamente.
- [ ] **H15** Con montura → rechazo, no mueve al personaje ni al dino; desmontado y apto → vuelve a permitir.
- [ ] **H16** Personaje dormido o muerto/dying, en caso administrado donde pueda originarse el comando → rechazo sin movimiento. Si la UI impide emitirlo, registrar NO EJECUTADA, sin inventar aceptación.
- [ ] **H17** Destino temporalmente obstruido en una prueba segura supervisada → colisión tratada sin entrar en geometría ni saltarse el estado permitido. Registrar resultado real, no asumir que todo obstáculo fuerza el mismo rechazo.
- [ ] **H18** Movimiento rechazado por el motor → no consume la espera de éxito; tras resolver la causa puede probarse de nuevo de forma controlada.
- [ ] **H19** Inmediatamente después del movimiento → chat y movimiento ordinario siguen funcionando.

El motor puede aceptar antes de que la pantalla refleje el cambio. Las capturas deben mostrar posición y resultado, además del texto del módulo.

## Mensaje 13 — homes y ciclo de módulos

**Etapa 8 · aislamiento y conservación de estado**

Las acciones de módulos las ejecuta la administración; los testers confirman el resultado en juego.

- [ ] **H20** Guardar punto, desconectar y reconectar → `/homes` vacío y `/home base` no existe en la sesión nueva.
- [ ] **H21** Otro jugador intenta usar ese mismo nombre → no hereda el punto del jugador que salió.
- [ ] **H22** Guardar punto y coordinar pausa de oHomes → sus comandos dejan de ejecutarse; el resto de módulos y chat normal continúa.
- [ ] **H23** Reanudar oHomes en la misma sesión → puntos conservados; la espera sigue midiendo tiempo real, no se reinicia por la pausa.
- [ ] **H24** Recargar oHomes → puntos vacíos; `/home base` no usa el punto antiguo. Repetir guardar/mover en la generación nueva.
- [ ] **H25** Parar e iniciar oHomes → mismo borrado de puntos; no quedan dos respuestas al mismo comando.
- [ ] **H26** A y B envían comandos durante una transición coordinada → no mezcla de puntos, movimiento por otra sesión ni respuesta tardía de la generación anterior.

Durante pausa/parada los comandos de ese módulo **no se ejecutan y pueden seguir el chat original de ARK**. No uses mensajes sensibles para probarlos; reanudar no debe generar trabajo aplazado.

Cambiar de mapa o sustituir la partida no es una prueba admitida de homes de esta beta fija TheIsland. Los puntos de sesión no incluyen una garantía de viaje entre mapas o partidas.

## Mensaje 14 — operaciones administradas y estabilidad

**Etapa 9 · módulos en caliente y servidor**

Solo administración: operaciones disponibles **status, start, pause, resume, stop, reload**, mediante el control local autorizado del servidor. No son comandos de chat ni se concede acceso del sistema a los testers.

- [ ] **L01** Para cada módulo, pausa/reanudación → deja de atender y vuelve a atender; otros módulos siguen activos.
- [ ] **L02** Recarga y parada/inicio → un registro por comando, sin respuesta doble, cuelgue o callback antiguo; el proceso del juego sigue siendo el mismo.
- [ ] **L03** Recarga con configuración válida temporal → textos/prefijos/catálogo nuevos visibles; restaurar ajustes acordados.
- [ ] **L04** Operaciones mientras hay clientes conectados y chat normal → sesiones y chat ordinario siguen funcionando.
- [ ] **L05** Administración compara eventos privados de login/logout/relogin tras recargar oPing → no duplicados ni retención de una sesión cerrada.
- [ ] **E01** Sesión sostenida con consultas/privados/desplazamientos controlados → no desconexiones, fallos, crecimiento anómalo o spam de errores. Registrar duración y participantes.
- [ ] **E02** TheIsland, personaje y mundo actuales conservados; tasas de XP/tame/recolección/cría restauradas comprobadas por efecto real en juego.
- [ ] **E03** En una ventana acordada, guardar/cerrar el servidor completo → administración registra resultado y revisa integridad al reabrir. **El SIGABRT conocido deja este caso pendiente hasta corregirlo.**

Las 32 operaciones ya registradas verifican control de módulos; no cierran L01–L05 con clientes ni E03. No reinicies el servidor entero para una prueba de módulo.

## Mensaje 15 — reportar resultados y cerrar etapas

**Plantilla de reporte beta**

```text
Caso: H11
Estado: OK / FALLO / BLOQUEADA / NO EJECUTADA
Plataforma y versión: Epic o Steam + versión exacta
Fecha, hora y zona horaria:
Mapa: TheIsland
Participantes: A/B/C (alias de prueba)
Comandos y pasos:
Esperado:
Resultado real y respuesta exacta:
Captura/vídeo:
¿Se reproduce? ¿Cuántas veces?
Observaciones: posición, montura, tribu, conexión, módulo...
```

En una incidencia, incluye el paso mínimo que permite repetirla. Conserva el texto exacto del error. Administración añade la versión del despliegue y la correlación de eventos, sin publicar logs completos.

Comparte la evidencia en el canal de beta indicado. Oculta IP, contraseñas, IDs nativos completos y nombres reales antes de publicar fuera del grupo autorizado. Usa alias A/B/C y tokens de prueba actuales para describir destinatarios.

**Cierre por etapas:** registrar primero comandos/utilidades, después Steam + Epic y privacidad, después chat, catálogo, consultas y homes. Cada caso exige resultado real y evidencia. Un caso bloqueado o no ejecutado queda pendiente, aunque tenga tests automáticos.

Privacidad de respuestas/privados, rechazo de sesiones antiguas, movimiento controlado de homes y cierre íntegro del servidor requieren validación explícita antes de ampliar el piloto. Las entregas de tienda/kits siguen siendo otro hito desactivado.

Avances públicos del proyecto: https://github.com/tyr0nsur/ObeliskNative
