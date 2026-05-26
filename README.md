# Obelisk: Linux-first Runtime for ARK: Survival Evolved

Este repositorio contiene Obelisk, un runtime nativo para servidores dedicados en Linux, inyectado mediante `LD_PRELOAD`.

## AI Context (Memoria de Agente)

Para mantener el contexto entre diferentes conversaciones de IA, toda la arquitectura, decisiones de diseño y reglas de código se documentan como **Agent Skills** en el directorio `agent-skills/`. 

Cualquier nuevo agente o sesión debe:
1. Leer el documento fundacional: `mvp.md`.
2. Leer los skills en `agent-skills/` para asimilar las reglas de ABI, el sistema de hooking en Linux, y cómo interactuar con Unreal Engine 4 usando reflection.

## Fases del Proyecto

- **Fase 0**: Base de conocimiento y Skills (Completada).
- **Fase 1**: Runtime Bootstrap, CMake, e inyección LD_PRELOAD (Completada).
- **Fase 2**: Instrumentación UE4 y Reversing.
- **Fase 3**: Hooking de `ProcessEvent`.

## Compilación

```bash
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
```

## Pruebas de inyección

```bash
LD_PRELOAD=./build/libobelisk.so /bin/echo "Test"
```
