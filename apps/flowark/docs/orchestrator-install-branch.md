# FlowARK orchestrator install branch

Este documento define la rama de trabajo para convertir el dashboard en orquestador
propio de ARK, con instalacion guiada tipo txAdmin, runtime de plugins por sistema
operativo y soporte futuro para Obelisk cuando el SDK este completo.

La rama no debe ejecutar acciones reales sobre servidores existentes hasta que cada
operacion tenga contrato, validaciones, locks, auditoria y confirmacion explicita.

## Objetivo

Construir una rama de instalacion/orquestacion que permita:

- Elegir desde el dashboard la ruta base donde alojar ARK, aunque la app viva en otro
  disco.
- Instalar y actualizar una unica copia de `serverfiles` con SteamCMD.
- Crear instancias por mapa sin duplicar los archivos pesados del juego.
- Generar parametros de cluster y configuraciones por instancia.
- Controlar ciclo de vida desde el dashboard con estado propio, PID real, locks y logs.
- Preparar instalacion automatica de Obelisk en Linux cuando el SDK este completo.
- Mantener ArkApi como ruta Windows, detectada por sistema operativo.
- Ofrecer instalacion opcional de mods de Steam Workshop con aviso claro de
  incompatibilidad para usuarios de Epic Games.

## Nombre de rama recomendado

`feature/orchestrator-install-wizard`

Si el worktree actual esta sucio, crear la rama desde una base limpia o desde una rama
de integracion preparada. No mezclar esta rama con cambios operativos live.

## Layout gestionado

La ruta base debe ser configurable en el wizard. Ejemplos validos:

```text
/servidor/ark
/mnt/ark-storage
/srv/flowark/ark
```

Estructura propuesta dentro de la ruta base:

```text
<arkRoot>/
  steamcmd/
  serverfiles/
    ShooterGame/
  instances/
    ragnarok/
      instance.json
      launch.env
      pid
      lock
      state.json
      logs/
      Saved/
        Config/LinuxServer/
    theisland/
    genesis2/
  cluster/
    clusterid.txt
    Saved/
  backups/
  mods/
    workshop/
  obelisk/
    lib/
    plugins/
    config/
    logs/
    state/instances/
  arkapi/
    Plugins/
```

`serverfiles` debe ser compartido. Las instancias solo deben contener estado ligero:
config, logs, locks, pid, saves o enlaces controlados si se decide usar enlaces. No se
debe copiar el juego completo por mapa.

## Wizard de despliegue

Fase 1, preflight de ruta:

- Campo de ruta base absoluto.
- Validar existencia o crear directorio.
- Comprobar escritura, propietario, permisos y espacio libre.
- Rechazar `/`, rutas relativas, rutas dentro de la app, rutas con symlinks peligrosos
  y montajes `noexec` si impiden ejecutar el binario.
- Mostrar resumen de disco y permisos antes de permitir continuar.

Fase 2, SteamCMD y serverfiles:

- Instalar SteamCMD en `<arkRoot>/steamcmd` si no existe.
- Instalar/actualizar ARK server en `<arkRoot>/serverfiles`.
- Guardar version, app id, fecha y ultimo resultado en estado propio.
- Ejecutar updates con lock global para no solapar arranques.

Fase 3, cluster:

- Definir nombre de cluster y cluster id.
- Elegir carpeta compartida de cluster.
- Generar parametros comunes: `-NoTransferFromFiltering`, cluster id y rutas necesarias.
- Validar puertos unicos para cada instancia: game, raw, query y RCON.

Fase 4, mapas:

- Crear instancia por mapa.
- Generar `Game.ini`, `GameUserSettings.ini`, parametros de arranque y `launch.env`.
- Guardar `instance.json` con id, mapa, puertos, rutas, runtime plugin y estado.
- Registrar la instancia en el inventario que hoy alimenta `nodes.json` o migrarlo a un
  `instances.json` gestionado.

Fase 5, runtime de plugins:

- Linux: preparar Obelisk, pero dejar instalacion real bloqueada hasta SDK completo.
- Windows: preparar ArkApi como ruta de compatibilidad.
- Mostrar solo el runtime que aplica al sistema operativo detectado.

## Deteccion de sistema operativo

El backend ya distingue `process.platform`. La rama debe formalizarlo asi:

- `linux`: runtime principal `Obelisk`.
- `win32`: runtime principal `ArkApi`.
- otros: sin runtime soportado.

El frontend no debe ofrecer instalar ArkApi en Linux ni Obelisk en Windows.

Contrato sugerido:

```json
{
  "host": {
    "platform": "linux",
    "family": "linux",
    "label": "Linux"
  },
  "deploymentTargets": {
    "linux": {
      "runtime": "Obelisk",
      "current": true,
      "available": false,
      "reason": "Pendiente de SDK estable"
    },
    "windows": {
      "runtime": "ArkApi",
      "current": false,
      "available": false
    }
  }
}
```

## Obelisk futuro

Cuando el SDK este completo, el panel de plugins debe poder:

- Detectar runtime instalado.
- Instalar o actualizar Obelisk desde un artefacto firmado o release local aprobado.
- Subir plugins `.so` a staging.
- Validar nombre, extension, tamano, hash y manifiesto.
- Publicar plugins con copia atomica al directorio activo.
- Habilitar o deshabilitar plugins por instancia.
- Leer logs por instancia.
- Mostrar estado por instancia: `not-installed`, `installed`, `disabled`,
  `enabled`, `restart-required`, `runtime-error`.

Hot reload:

- No asumir que ARK permite encender/apagar plugins en caliente de forma segura.
- La UI debe diferenciar `aplicar ahora` de `requiere reinicio`.
- Por defecto, instalar o quitar plugin debe marcar `restart-required`.
- Solo se debe habilitar accion en caliente para plugins que declaren soporte explicito
  en su manifiesto y que Obelisk lo exponga como capacidad real.

Marcadores y controles:

- Mantener marcadores por instancia bajo `obelisk/state/instances/<instanceId>/`.
- No permitir marcadores experimentales sin confirmacion fuerte.
- No escribir markers, reiniciar servidores ni leer logs live fuera de una operacion
  aprobada por el operador.

## ArkApi Windows

ArkApi queda como runtime Windows:

- Inventario de plugins `.dll`.
- Instalacion futura solo en hosts Windows.
- Contrato separado del de Obelisk.
- Sin mezclar acciones ArkApi con Linux.

El panel debe mostrar ArkApi en Linux solo como no aplicable, no como opcion instalable.

## Mods de Steam Workshop

La rama puede incluir mods como opcion independiente del runtime de plugins:

- Campo para lista de workshop ids.
- Validacion de ids numericos.
- Instalacion con SteamCMD en `<arkRoot>/mods/workshop`.
- Generacion de `ActiveMods=` o parametros equivalentes.
- Lock de update para que no coincida con arranque/parada.
- Estado por mod: `configured`, `downloading`, `installed`, `update-available`,
  `failed`.

Aviso obligatorio en UI antes de activar mods de Steam:

```text
Los mods de Steam Workshop requieren cliente Steam. Si activas mods de Steam,
los usuarios de Epic Games no podran entrar en ese servidor. Obelisk busca cubrir
plugins nativos en Linux sin Proton ni ArkApi, pero no convierte mods de Steam
Workshop en contenido compatible con Epic.
```

## Contratos API propuestos

Lectura:

- `GET /api/deploy/capabilities`
- `GET /api/orchestrator/readiness`
- `GET /api/orchestrator/preflight?root=<path>`
- `GET /api/plugins/status`

Mutaciones:

- `POST /api/orchestrator/config`
- `POST /api/orchestrator/install/steamcmd`
- `POST /api/orchestrator/install/serverfiles`
- `POST /api/orchestrator/instances`
- `POST /api/orchestrator/instances/:id/action`
- `POST /api/plugins/obelisk/install`
- `POST /api/plugins/obelisk/plugins/upload`
- `POST /api/plugins/obelisk/plugins/:plugin/action`
- `POST /api/mods/workshop/config`
- `POST /api/mods/workshop/install`

Todas las mutaciones deben requerir rol `owner`, audit log, lock por recurso y
confirmacion cuando cambien runtime, mods, serverfiles o ciclo de vida.

Estado inicial implantado en el dashboard:

- `GET /api/orchestrator/readiness`: devuelve configuracion, fases, preflight guardado,
  layout objetivo y plan LinuxGSM -> instancia nativa.
- `GET /api/orchestrator/preflight?root=<path>`: valida ruta base en modo read-only.
- `POST /api/orchestrator/config`: guarda solo preparacion en
  `orchestrator_config.json`; no crea rutas ni toca servidores.
- `POST /api/orchestrator/action`: registra auditoria y devuelve 501 mientras el modo
  sea `planning`.

## Estados de instancia

Estados minimos:

- `not-installed`
- `installed`
- `starting`
- `online`
- `rcon-ready`
- `stopping`
- `offline`
- `updating`
- `crashed`
- `locked`

El dashboard debe depender del estado propio y del PID real lanzado por el orquestador,
no de coincidencias fragiles por nombre de proceso.

## Migracion desde LinuxGSM

La rama debe incluir modo importacion:

- Leer mapas existentes desde `nodes.json`.
- Detectar scripts LinuxGSM existentes solo como fuente de configuracion.
- Copiar o importar configs a instancias gestionadas.
- No borrar LinuxGSM ni serverfiles antiguos.
- Permitir piloto de una instancia antes de migrar todo el cluster.

## Fases de implementacion

1. Contrato y UI bloqueada:
   - Ampliar capabilities.
   - Mostrar wizard de ruta base.
   - Mostrar Obelisk/ArkApi por OS.
   - Mostrar bloque de Workshop con aviso Epic.

2. Persistencia segura:
   - `orchestrator_config.json`.
   - Validadores de rutas.
   - Locks y audit log.

3. Instalacion serverfiles:
   - SteamCMD gestionado.
   - Updates con lock.
   - Estado y logs de job.

4. Instancias:
   - Crear instancia.
   - Generar configs y parametros.
   - Control start/stop/restart con PID propio.

5. Obelisk SDK:
   - Instalador de runtime.
   - Upload/staging/publicacion atomica de plugins.
   - Acciones por plugin segun capacidades reales.

6. Workshop opcional:
   - Gestion de ids.
   - Instalacion/update.
   - Aviso Epic obligatorio.

## Criterios de seguridad

- Ninguna accion destructiva o live sin confirmacion.
- Ningun start/stop/restart implicito por instalar plugin o mod.
- Locks por instancia y locks globales para SteamCMD/serverfiles.
- Paths siempre absolutos y contenidos dentro del root configurado.
- Rechazar symlinks en directorios gestionados sensibles.
- Redactar secretos y rutas internas sensibles en errores devueltos a UI.
- Tests para rutas, permisos, capabilities, rate limits y acciones bloqueadas.
