# Obelisk

## Runtime/API/SDK Linux-first para modding de servidores UE4

---

# Visión del proyecto

Obelisk es un runtime moderno, una API C estable y una base de SDK para modding
de servidores dedicados Linux basados en Unreal Engine.

ARK: Survival Evolved es el harness de debug actual: sirve para validar loader,
hooks, ABI, logs y plugins contra un servidor UE4 Linux real. No debe definir la
primera impresión del proyecto ni convertirse en el contrato publico del SDK.

El objetivo NO es clonar ArkApi ni portar código Windows directamente.

El objetivo es construir una arquitectura:

* Linux-first
* reflection-driven
* modular
* mantenible
* orientada a procesos dedicados persistentes
* con ABI estable para plugins
* desacoplada de WinAPI
* menos dependiente de offsets frágiles

---

# Objetivos técnicos

## Objetivos principales

* Runtime nativo Linux
* Sistema de plugins `.so`
* Hooking mínimo y controlado
* Reflection UE4 como base principal
* API estable para plugins
* SDK gameplay reutilizable
* Compatibilidad con updates mediante tooling automático

---

# Filosofía arquitectónica

## Principios

### 1. Reflection over offsets

Priorizar:

* UObject
* UFunction
* ProcessEvent
* Reflection UE4

Sobre:

* offsets hardcodeados
* memory patching agresivo
* hooks frágiles

---

### 2. ABI estable

La comunicación runtime ↔ plugins debe usar:

* C ABI
* structs POD
* interfaces simples

Evitar:

* STL en interfaces públicas
* exceptions cruzando módulos
* RTTI compartido
* dependencias MSVC

---

### 3. Linux-native

Evitar dependencias:

* WinAPI
* DLL loaders
* PE parsing
* MinHook/Detours

Usar:

* ELF
* dlopen
* dlsym
* pthreads
* mprotect

---

### 4. Tooling-first

Los updates del binario objetivo pueden romper offsets y patrones.

Por eso Obelisk debe incluir tooling desde etapas tempranas:

* SDK generation
* reflection dumpers
* pattern scanners
* symbol tools
* validation tooling

---

# Arquitectura inicial

```text
obelisk/
├── runtime/
├── sdk/
├── plugins/
├── hooks/
├── ue/
├── loader/
├── tools/
├── examples/
├── docs/
└── tests/
```

---

# Componentes principales

## runtime/

Core runtime:

* lifecycle
* plugin manager
* event bus
* logging
* configuration
* API registry

---

## sdk/

Wrappers gameplay:

* Player
* Dino
* Tribe
* World
* Inventory
* Chat
* Structures

Objetivo:

Abstraer detalles UE4 internos.

---

## hooks/

Sistema de hooking Linux.

Responsabilidades:

* trampolines
* ProcessEvent interception
* function detours
* memory protection management

Bibliotecas potenciales:

* subhook
* funchook

---

## ue/

Capa Unreal Engine.

Responsabilidades:

* UObject access
* UFunction lookup
* FName handling
* reflection traversal
* ProcessEvent wrappers
* GObjects access

---

## loader/

Bootstrap runtime.

Responsabilidades:

* LD_PRELOAD integration
* runtime startup
* runtime shutdown
* plugin discovery

---

## tools/

Tooling interno.

Herramientas previstas:

* SDK generator
* symbol dumper
* signature scanner
* UObject dumper
* validation tools

---

## plugins/

Plugins cargados dinámicamente.

Formato:

```text
plugins/MyPlugin.so
```

---

# Stack tecnológico recomendado

| Área                | Tecnología       |
| ------------------- | ---------------- |
| Build system        | CMake            |
| Lenguaje            | C++20            |
| Logging             | spdlog           |
| Formatting          | fmt              |
| Hooking             | subhook/funchook |
| Binary analysis     | Capstone         |
| Debugging           | gdb              |
| Reverse engineering | Ghidra           |

---

# Dependencias recomendadas

## spdlog

[https://github.com/gabime/spdlog](https://github.com/gabime/spdlog)

---

## fmt

[https://github.com/fmtlib/fmt](https://github.com/fmtlib/fmt)

---

## subhook

[https://github.com/Zeex/subhook](https://github.com/Zeex/subhook)

---

## funchook

[https://github.com/kubo/funchook](https://github.com/kubo/funchook)

---

## Capstone

[https://github.com/capstone-engine/capstone](https://github.com/capstone-engine/capstone)

---

# Roadmap inicial

# Fase 0 — Harness de debug

## Objetivo

Levantar un proceso dedicado Linux funcional para validar el runtime. El harness
actual es ARK: Survival Evolved, pero no es el eje del producto.

## Requisitos

* Ubuntu 22.04 o Debian 12
* SteamCMD
* Dedicated server ASE Linux para el harness actual
* gdb
* clang
* cmake

---

# Fase 1 — Runtime bootstrap

## Objetivo

Cargar un runtime `.so` usando LD_PRELOAD.

## Resultado esperado

```text
Obelisk Runtime Loaded
```

## Ejemplo

```cpp
__attribute__((constructor))
void Start()
{
    printf("Obelisk Runtime Loaded\n");
}
```

## Ejecución

```bash
LD_PRELOAD=./libobelisk.so ./ShooterGameServer
```

---

# Fase 2 — Instrumentación UE4

## Objetivo

Entender cómo está estructurado el runtime UE4 Linux.

## Herramientas

* readelf
* objdump
* nm
* gdb

## Comandos útiles

```bash
readelf -Ws ShooterGameServer
```

```bash
nm -D ShooterGameServer
```

---

# Fase 3 — Hooking ProcessEvent

## Objetivo

Interceptar:

```cpp
UObject::ProcessEvent
```

## Importancia

La mayoría de llamadas gameplay UE4 pasan por ProcessEvent.

Esto permite:

* detectar eventos
* interceptar funciones
* registrar llamadas
* observar gameplay

## Resultado esperado

Loggear nombres de UFunctions ejecutadas.

---

# Fase 4 — Reflection UE4

## Objetivo

Acceder a:

* GObjects
* UObject
* UFunction
* FName

## Resultado esperado

Enumerar:

* players
* dinos
* actors
* world objects

---

# Fase 5 — Plugin loader

## Objetivo

Cargar plugins `.so` dinámicamente.

## Diseño recomendado

```cpp
extern "C" void Plugin_Load(API* api);
```

## Evitar

```cpp
class IPlugin
{
    virtual void Load() = 0;
};
```

---

# Fase 6 — Event Bus

## Objetivo

Sistema de eventos gameplay.

## Eventos iniciales

* OnPlayerJoin
* OnPlayerLeave
* OnChatMessage
* OnDinoSpawn

---

# Fase 7 — SDK gameplay

## Objetivo

Construir wrappers reutilizables.

Ejemplo:

```cpp
Player
World
Dino
Inventory
```

---

# ABI recomendada

## Correcto

```cpp
extern "C" __attribute__((visibility("default")))
bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out);

extern "C" __attribute__((visibility("default")))
bool ObeliskPlugin_Init(ObeliskApi* api, const ObeliskPluginInitContext* context);
```

---

## Incorrecto

```cpp
std::string
std::vector
std::unordered_map
```

En interfaces públicas.

---

# Primera API mínima

La primera API minima implementada vive en `api/ObeliskApi.h`: logging,
registro de callbacks `ProcessEvent`, llamada al `ProcessEvent` original,
metadatos ABI y contexto de inicializacion de plugin.

---

# Primer plugin recomendado

## ChatLogger

Objetivo:

Detectar mensajes de chat.

Ejemplo esperado:

```text
[CHAT] PlayerName: hola
```

---

# Prioridades técnicas

## Prioridad máxima

Construir:

* runtime estable
* reflection limpia
* tooling automático
* ABI consistente

## NO priorizar inicialmente

* economía
* comandos admin complejos
* UI
* scripting avanzado
* features gameplay masivas

---

# Riesgos técnicos

## Actualizaciones del binario objetivo

Cada update puede romper:

* signatures
* offsets
* reflection access
* UFunctions

---

## Hooking frágil

Hooking agresivo puede causar:

* crashes
* corruption
* incompatibilidades
* degradación rendimiento

---

## ABI inconsistente

Mezclar:

* GCC
* Clang
* STL
* exceptions

puede romper plugins.

---

# Objetivo a largo plazo

Construir un framework:

* moderno
* modular
* Linux-native
* reflection-driven
* mantenible
* estable para procesos dedicados persistentes

que eventualmente pueda superar las limitaciones arquitectónicas de ArkApi clásico.

---

# Recursos útiles

## UE4SS

[https://ue4ss.org](https://ue4ss.org)

[https://docs.ue4ss.com](https://docs.ue4ss.com)

---

## ArkServerApi

[https://github.com/ArkServerApi](https://github.com/ArkServerApi)

---

## Dumper-7

[https://github.com/Encryqed/Dumper-7](https://github.com/Encryqed/Dumper-7)

---

## Capstone

[https://github.com/capstone-engine/capstone](https://github.com/capstone-engine/capstone)

---

## Ghidra

[https://ghidra-sre.org](https://ghidra-sre.org)

---

# Primer milestone realista

```text
[✓] Runtime carga mediante LD_PRELOAD
[✓] Logging funcional
[✓] Plugin .so cargado
[✓] ProcessEvent hookeado
[ ] UFunctions enumeradas mediante reflection confiable
[ ] Primer evento gameplay decodificado mediante metadata reflejada
```

Cuando esto funcione:

Obelisk tendrá la base técnica real de un runtime/API/SDK moderno para modding
Linux, validado inicialmente con el harness de ARK.
