# ObeliskNative Panel y Hub

Panel experimental para administrar instancias Linux de ARK: Survival Evolved y
los plugins originales de ObeliskNative. Recupera el proyecto propio FlowArk y
conserva `apps/flowark`, variables `FLOWARK_*` y nombres de despliegue existentes
como rutas de compatibilidad. La marca visible del producto es ObeliskNative.

La recuperación y la integración no certifican producción, autenticación de
cuentas del juego o paridad de todos los plugins ASE. El estado vigente está en
[ObeliskNative Ecosystem](../../docs/OBELISKNATIVE_ECOSYSTEM.md), y la procedencia
en [Recovery](docs/RECOVERY_2026-10-27.md). La implementación permanece privada.

## Alcance actual

El panel recuperado contiene frontend React/Vite y backend Express con sesiones,
roles administrativos, inventario de mapas, configuración, auditoría y rutas
operativas. El Hub añade catálogo propio, referencias ASE, registro local de
instancias, control cooperativo por socket y descubrimiento de artifacts.

El catálogo propio contiene seis módulos de prototipo: oPing, oEssentials,
oShopKits, oAdvancedChat, oWorldTools y oHomes. Las 157 fichas del inventario ASE
son referencias pendientes y no están disponibles para instalación. Shop/Kits
ofrece catálogos informativos; las compras y entregas siguen deshabilitadas.
Homes conserva puntos sólo durante la sesión; reconectar o recargar los pierde.

Los controles nativos operan sobre sockets privados registrados por el operador.
Son un transporte distinto de RCON. La consola RCON requiere configuración real
de cada instancia; tener un puerto configurado no demuestra conectividad. La
identidad del panel tampoco acredita autenticación Steam/Epic de un jugador.

Las rutas históricas de aprovisionamiento que devuelven 501 continúan pendientes.
Los ajustes guardados en INI se aplican después del reinicio del mapa que los
necesite. Guardar un formulario no significa haber cambiado el mundo activo.
El panel debe mostrar configuración, conectividad y resultado confirmado o
pendiente por separado.

## Desarrollo y comprobaciones

Utilizar Node.js 24 y npm compatibles con los lockfiles. Desde la raíz privada
de Obelisk:

```bash
node --version
npm --prefix apps/flowark/server ci --ignore-scripts
npm --prefix apps/flowark/client ci --ignore-scripts

node --check apps/flowark/server/server.js
npm --prefix apps/flowark/server test
npm --prefix apps/flowark/client test
npm --prefix apps/flowark/client run lint
npm --prefix apps/flowark/client run build
```

El backend no declara un script `lint`; su comprobación de sintaxis y sus tests
son pasos separados. La instalación bloqueada evita ejecutar scripts npm de
dependencias durante recuperación. Los resultados se registran tras ejecutar
cada comprobación; esta lista de comandos no declara que todas hayan pasado.

Para desarrollo del frontend:

```bash
npm --prefix apps/flowark/client run dev
```

El backend se inicia con `npm --prefix apps/flowark/server start` después de
preparar su entorno y estado privado. No inicia automáticamente un servidor ARK
ni concede acceso a rutas del host. El flujo de producción utiliza los archivos
compilados del cliente y una configuración de servicio revisada.

## Configuración del operador

Mantener secretos y datos mutables fuera del checkout. `DASHBOARD_DATA_DIR`
señala el directorio persistente privado; la configuración inicial incluye un
JWT propio y credenciales de bootstrap temporales. La configuración de
producción exige `NODE_ENV`, bind local, origen HTTPS explícito y un estado de
administradores válido. Los nombres y plantillas existentes están en
[Deployment](DEPLOYMENT.md); revisar sus rutas históricas antes de usarlas.

`OBELISK_HUB_INSTANCES_FILE` apunta al registro privado de instancias y sockets
autorizados. `OBELISK_HUB_ARTIFACTS_DIR` apunta al directorio privado de artifacts.
El navegador recibe metadatos, sin elegir rutas de host o comandos arbitrarios.
El índice de artifacts es descubrimiento; la firma se verifica por separado con
una clave pública externa confiable antes del staging.

Las lecturas del Hub requieren operador o propietario. Mutar plugins exige
además el permiso específico; CSRF, auditoría y controles de sesión continúan
aplicándose. Una operación pendiente se consulta antes de repetirla. Un fallo de
transporte no autoriza a suponer que el runtime no recibió la petición.

El JSON persistente recuperado tiene bloqueo y escritura atómica para un
filesystem compartido en un host. No se presenta como almacenamiento distribuido
para varios procesos en hosts diferentes. Copias, restauración, cambios de
esquema y migración de estado necesitan ensayos propios antes de producción.

## Documentación relacionada

- [Contrato de la API local del Hub](docs/HUB_LOCAL_API.md).
- [Recuperación y exclusiones](docs/RECOVERY_2026-10-27.md).
- [Empaquetado, firmas y staging de artifacts](../../docs/ARTIFACTS.md).
- [Comandos y aceptación beta](../../docs/BETA_TESTER_GUIDE.md).
- [Estrategia comercial propuesta](../../docs/COMMERCIAL_STRATEGY_2026-10-27.md).
- [Notas históricas de despliegue](DEPLOYMENT.md) y
  [registro histórico de preparación](PRODUCTION_READINESS.md).

El modelo propuesto ofrece runtime, panel autohospedado y Hub básico gratuitos,
con plugins premium, servicios gestionados y soporte contratado. Ese modelo no
activa facturación ni cambia las licencias existentes. Mantener los avisos de
dependencias y definir las condiciones de distribución antes de publicar paquetes.
