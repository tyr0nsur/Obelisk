# Plugins ASE Linux: mercado nativo y nueva marca

Fecha de consulta: 2026-10-14. Investigación de fuentes primarias; decisiones propuestas, sin cambiar marca ni publicar repositorios.

## Competidores y oportunidad

| Proyecto o señal | Qué acredita la fuente | Implicación para el proyecto |
| --- | --- | --- |
| [ArkServerApi/AseApi](https://github.com/ArkServerApi/AseApi/blob/main/version/version.vcxproj) | Proyecto de biblioteca dinámica con toolchain y plataforma Windows, además de interfaces del juego y plugins. | Referencia funcional y ecosistema establecido. No demuestra una API equivalente para el ejecutable ELF nativo de ASE. |
| [TBro1998/ASE-Server-Docker](https://github.com/TBro1998/ASE-Server-Docker) | El autor documenta ASE para Windows y ArkApi ejecutados mediante GE-Proton dentro de Docker. | Competidor real para alojar plugins en un host Linux. Nuestra propuesta es ejecutarlos sobre el servidor nativo Linux. |
| [XarminaEu/ue4ss-linux](https://github.com/XarminaEu/ue4ss-linux) | Mod loader Linux con Lua y biblioteca nativa; menciona Ark como ejemplo. Su sección Verified Games enumera Palworld UE5.1 y reconoce trabajo pendiente en funciones y versiones. | Es la alternativa técnica más cercana encontrada. Mencionar Ark no acredita una demostración equivalente de ASE con jugadores reales. |
| [ArkServers.io](https://arkservers.io/help/arkapi) | El proveedor explica que no admite ArkAPI porque requiere Windows y sus servidores usan Linux. | Señal concreta de una limitación comercial; no prueba cuántos clientes pagarían por resolverla. |
| [Marketplace ASE Paid Plugins](https://ark-server-api.com/resources/categories/ase-paid-plugins.10/) | Hay decenas de ofertas de plugins de pago, con ejemplos alrededor de 20–45 dólares y precios en euros. | El modelo de venta de plugins existe. Listados, reseñas y descargas no equivalen a ventas verificadas ni ingresos. |

En las fuentes revisadas no se encontró una solución equivalente con validación publicada de plugins sobre ASE Linux nativo y una prueba real comparable de comando/respuesta. Esto describe el resultado de la búsqueda, no demuestra inexistencia ni justifica anunciar «el primero».

La posición defendible es concreta: **plugins para ARK: Survival Evolved sobre su servidor Linux nativo, con avances demostrados y alcance documentado**. Aún no corresponde prometer compatibilidad binaria con plugins Windows, equivalencia completa con ArkApi, ventajas medidas de rendimiento o soporte para todos los builds.

## Nueva marca

Inicialmente se investigaron nombres completamente diferentes. Después, el
usuario eligió **ObeliskNative** para la presentación pública. El sufijo ayuda
a distinguirla de [arkutils/Obelisk](https://github.com/arkutils/Obelisk), que
también pertenece al ecosistema ARK. El ABI interno conserva Obelisk.

La consulta pública de GitHub por `ObeliskNative in:name` no devolvió
repositorios el 14 de octubre de 2026. Es una comprobación de coincidencias
públicas, no una garantía de disponibilidad en la cuenta ni de marca o dominio.

Los candidatos iniciales tienen coincidencias: [PrimalBridge™](https://www.primalhealthcoach.com/primalbridge-health-coach-employment-accelerator/) es un programa comercial de formación y empleo; [PrimalLinkWebsite](https://github.com/Reworks-Studios/PrimalLinkWebsite) es un repositorio existente y vacío, sin producto acreditado; [Tekora](https://github.com/OsdiliteStudios/Tekora) es un mod de Minecraft y también identifica una [empresa de software](https://tekora.dev/). Recomiendo descartarlos para reducir confusión.

| Candidato nuevo | Ventaja | Coste |
| --- | --- | --- |
| **Tekvyra** — «tek-vi-ra» | Recomendación si prima una marca original: breve y evocadora de tecnología y del mundo de ARK. | Necesita el subtítulo «Native Linux plugins for ARK: Survival Evolved» para explicar su función. |
| **Kernyra** — «ker-ni-ra» | Marca propia, corta, con una asociación técnica al núcleo o kernel. Puede crecer más allá de un único juego. | La asociación con ARK es menor y conviene fijar una pronunciación para la letra «y». |
| **PrimalRelay** | Opción descriptiva: «Primal» evoca ARK y «Relay» comunica conexión entre juego y plugins. | Más larga y menos distintiva; pronunciación inglesa menos inmediata para público español. |

La consulta pública de GitHub por nombre de repositorio devolvió cero resultados para estos tres candidatos alternativos. Las búsquedas web exactas y específicas de software/ARK no identificaron un producto coincidente; Kernyra apareció como una errata geográfica en una ficha de imagen, sin relación técnica observada. Estos resultados son limitados: no acreditan disponibilidad de dominios ni marcas. La presentación local usa ahora **ObeliskNative**, por elección del usuario; todavía no se creó un repositorio en GitHub ni se inventaron enlaces futuros.

## Monetización propuesta

La oportunidad está en resolver una necesidad operativa, no en cobrar por una lista extensa de funciones futuras. Recomiendo completar primero Steam, dos jugadores y sesiones desconectadas; después ofrecer uno o dos pilotos para administradores Linux que ya necesiten una función concreta.

Primera oferta posible: un plugin útil y acotado, instalación acompañada, compatibilidad de build documentada y mantenimiento con alcance pactado. Separar instalación, desarrollo a medida y mantenimiento permite conocer qué compra realmente el cliente. Los precios del marketplace sirven como referencia de oferta, no como previsión de ventas ni tarifa automática para un producto Linux nuevo.

Una estrategia viable es facilitar un runtime de evaluación y monetizar plugins, adaptación de funciones y soporte. El repositorio público puede mostrar avances y captar interés mientras la implementación permanece privada. No conviene fijar una suscripción, catálogo o promesa de servicio antes de comprobar interés real y coste de mantenimiento tras actualizaciones de ASE.

La licencia actual del proyecto es MIT. Esta licencia permite uso comercial y redistribución de lo que se entregue bajo sus términos; la ventaja comercial debería apoyarse en mantenimiento, compatibilidad comprobada y soporte, no en asumir exclusividad sobre copias MIT distribuidas. [Texto de MIT en Open Source Initiative](https://opensource.org/license/mit).

## Qué presentar ahora

El hito demostrable es Epic 361.8 conectado al servidor ASE público Linux nativo 361.7, con `/ping` y `pong` confirmados en el juego, chat ordinario y observaciones de reconexión. La base previa a las nuevas extensiones pasó 147 comprobaciones CTest; la implementación actual pasa 149/149 e incluye sus fixtures de identidad y ciclo de vida. Steam, separación entre dos jugadores y rechazo de una sesión antigua siguen pendientes. Las extensiones nuevas se han instalado y han pasado el arranque, pero todavía no se presentan como aceptadas en gameplay.

Publicar únicamente presentación, hoja de ruta y progreso agregado. Los datos operativos y la implementación permanecen en el repositorio privado. Mantener la diferencia entre pruebas automatizadas, observaciones y aceptación real evita vender como completo un prototipo prometedor.
