# Obelisk 🏺

**Obelisk** es un framework de inyección y hooking nativo en C++ para servidores dedicados de *ARK: Survival Evolved* en Linux. 

Dado que el binario de Linux (`ShooterGameServer`) es un ejecutable *Stripped* (sin símbolos ni nombres expuestos), crear *mods* en C++ históricamente ha sido casi imposible sin usar complejas herramientas de Windows. Obelisk soluciona esto inyectándose en el espacio de memoria del servidor mediante `LD_PRELOAD`, utilizando escaneo heurístico de memoria (Memory Probing) para localizar las funciones maestras del motor gráfico (Unreal Engine 4) e instalar desvíos (Hooks).

## ✨ Características Principales
- **Inyección Segura:** Se inyecta exclusivamente en el proceso del juego, ignorando comandos del sistema operativo u herramientas como LinuxGSM, evitando crasheos o *segfaults* del Kernel.
- **Dynamic Memory Probing:** Busca firmas, VTables y offsets en caliente usando llamadas seguras al Kernel de Linux (`/dev/random`). ¡No necesitas Dumper-7!
- **Plugin Manager Integrado:** Carga automáticamente cualquier librería `.so` programada en C++ desde la carpeta `ObeliskPlugins`.
- **Event API:** Proporciona un sistema de subscripción ultra rápido y seguro para interceptar `ProcessEvent` milisegundos antes de que ocurra en el juego.

---

## 🛠️ Instalación en LinuxGSM

1. **Compilar el proyecto:**
   ```bash
   mkdir build && cd build
   cmake ..
   cmake --build . -j$(nproc)
   ```
   Esto generará `libobelisk.so`.

2. **Preparar el Servidor:**
   Asegúrate de que `ObeliskRun.sh` y `libobelisk.so` (o un symlink) están en la carpeta base de los binarios del servidor de ARK (`ShooterGame/Binaries/Linux/`).

3. **Configurar LinuxGSM:**
   Modifica tu archivo de configuración común de instancia de LinuxGSM (ej. `lgsm/config-lgsm/arkserver/common.cfg`) y añade la siguiente línea para delegar el arranque a Obelisk:
   ```ini
   executable="./ObeliskRun.sh"
   ```

4. **Reiniciar:**
   ```bash
   ./arkserver restart
   ```

---

## 🔌 Creación de Plugins

Para crear un plugin, simplemente debes exportar la función `ObeliskPlugin_Init` en tu librería compartida en C++.

```cpp
#include "api/ObeliskApi.h"

// Función de intercepción
bool OnMyProcessEvent(void* caller, void* function, void* parms) {
    // Si devuelves false, bloqueas la ejecución en Unreal Engine
    return true; 
}

// Punto de entrada del Plugin
extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api) {
    api->LogInfo("¡Mi primer plugin cargado con éxito!");
    api->RegisterPreProcessEvent(OnMyProcessEvent);
    return true;
}
```

Coloca tu plugin compilado (`MiPlugin.so`) en `/ShooterGame/Binaries/Linux/ObeliskPlugins/` y el servidor lo cargará automáticamente en su próximo arranque.

---

## 🚀 Estado de Desarrollo

Obelisk es actualmente estable (v1.0) en lo que respecta a su **Core Engine**:
- [x] Inyección `LD_PRELOAD`.
- [x] Memory Scanner y Offset Finder Dinámico.
- [x] Subhook / Trampoline Hooking en `UObject::ProcessEvent`.
- [x] Plugin Manager y C-API para desarrolladores.

### Próximos Pasos (Plugins Avanzados)
El framework subyacente está listo, pero para crear plugins complejos (como sistemas avanzados de Whitelist o interceptación de Chat), es necesario expandir la capa de **Reflexión de Unreal Engine** de Obelisk (`ue/Reflection.cpp`), la cual actualmente incluye soporte básico para inspección de memoria cruda de `FString` y `FName`.

*Construido para soportar los servidores más grandes de la comunidad hispana.*
