# Validación de ObeliskNative — 27 de octubre de 2026

## Resultado reproducible

| Componente | Comprobación | Resultado |
| --- | --- | --- |
| Runtime y módulos | Build CMake existente y CTest | 158/158 pasan; ejecutado hoy. |
| SDK público | `python3 scripts/test_public_sdk_guardrails.py` | 214/214 pasan. |
| Artifacts | `python3 scripts/test_obelisk_artifacts.py` | 24/24 pasan, con OpenSSL y ELF reales. |
| Backend del panel | `npm test` en `apps/flowark/server` | 122/122 pasan. |
| Frontend del panel | `npm test` en `apps/flowark/client` | 73/73 pasan. |
| Frontend del panel | `npm run lint` y `npm run build` | Pasan. |
| Dependencias de producción | `npm audit --omit=dev` en ambos paquetes | Sin vulnerabilidades conocidas en la consulta de hoy. |

El workflow de CI añade jobs de panel/Hub y empaquetado; sus comandos se han
ejecutado localmente. El resultado del runner remoto se verifica por separado.
Los guards de secretos (4) y del publicador Discord (23) también pasan.

Las series tienen alcances diferentes. No sumar estos números como pruebas de
paridad de gameplay. Los guards de SDK y parte del frontend son comprobaciones
de contrato/fuente; no ejecutan ARK.

## Navegador y transporte

Se usó Chromium headless ya instalado y el backend real en loopback, con una
cuenta propietaria privada. Login, catálogo de seis módulos, descubrimiento del
artifact, consulta de 157 referencias, cuatro perfiles de juego, jugadores,
consola y diagnóstico se renderizaron sin errores de JavaScript. Se verificó
escritorio de 1440 px y móvil de 390 px sin desbordamiento horizontal.

Una revisión de modo leyó la configuración real del laboratorio y devolvió
únicamente los ajustes afectados. No se confirmó su guardado ni se reinició ARK.
La consola impidió enviar comandos porque RCON está desactivado. Las pruebas
HTTP del backend cubren la conservación de tasas/secretos, el rechazo de una
revisión caducada o modificada y la declaración explícita de guardado parcial.

Una segunda prueba de navegador interceptó sólo los endpoints del Hub para
simular un runtime: primer inicio de plugin ausente, respuesta pendiente,
consulta todavía pendiente y posterior confirmación. Sólo emitió una mutación
simulada; nunca alcanzó el servidor de juego. También comprobó que un índice de
artifacts no disponible no oculta el catálogo nativo. Esta prueba valida la
interfaz, no una transición nueva de plugins en el juego.

## Artifact privado persistente

- Versión: `0.1.0-beta.20261027`, canal `experimental`, API 312.
- ID de manifiesto: `0fd26befb2cb445621db9b70965ae7d8b4ed94a969b04146daa73778bcff5c21`.
- Archivo: 19.173.263 bytes; 19 archivos internos.
- SHA-256 del archivo: `b5cc6614c08e895b0111ba8af7027b449eb3020d7d9a1eaee0ade832ac77f9bf`.
- Firma Ed25519 y contenido verificados con clave pública externa de confianza.
- Preparado en staging aislado; `activated=false`, `runtime_ready=false`.

Los archivos publicados para el panel viven fuera de Git en
`/servidor/obelisk/ecosystem/artifacts`; el staging está bajo `ecosystem/staging`.
Las claves permanecen en `ecosystem/keys`, con directorio privado y archivos
0600. No se incorporaron al repositorio ni al paquete. El artifact contiene el
runtime, seis módulos, SDK y avisos de licencia; excluye ARK, partidas y secretos.

## Acceso operativo del laboratorio

El servicio `obelisknative-panel-lab.service` ejecuta el panel como `tyronsur`,
escucha sólo en `127.0.0.1:3040` y carga configuración desde
`/servidor/obelisk/ecosystem/panel/config/panel.env`. El estado del panel y la
cuenta propietaria son nuevos; no se importaron usuarios ni secretos del ZIP.
La credencial inicial está en `config/owner-access.json` con modo 0600.

Para acceder desde otro equipo, crear un túnel SSH hacia el servidor:

```bash
ssh -N -L 3040:127.0.0.1:3040 tyronsur@TU_SERVIDOR
```

Abrir `http://127.0.0.1:3040`. Esta instalación es experimental y usa el modo
local de desarrollo; no tiene publicación HTTPS, dominio, checkout ni acceso
directo desde Internet. Una instalación pública requiere la configuración de
producción existente, su origen HTTPS y cookies seguras.

El laboratorio The Island está registrado con su configuración y socket nativo
reales. El proceso ARK continúa detenido. No se activó RCON, no se concedió
admin Epic y no se habilitó un script de ciclo de vida ficticio. El panel muestra
esas operaciones como no disponibles. El arranque/parada del laboratorio
necesita integrar su runner; la ruta histórica del panel sigue admitiendo los
scripts LinuxGSM que configure explícitamente cada operador.

## Cierres pendientes

Apagado limpio del runtime (SIGABRT histórico), aceptación prolongada con clientes
Steam/Epic, identidad autenticada por sesión, economía/entrega real de inventario,
homes persistentes, aceptación por cada equivalencia de catálogo, activación y
rollback de artifacts, y servicios comerciales. Ninguna prueba de este informe
declara esos cierres completos.
