# Verificación propia de entregas de objetos

`SuiteItemDelivery` es una biblioteca privada original, separada del runtime y
del SDK. Compara evidencia copiada de inventario antes y después de un intento.
No entrega objetos, autentica jugadores ni activa compras o kits. Todavía falta
un adaptador nativo que produzca toda la evidencia exigida.

La especificación contiene cantidad y una variante canónica que debe identificar
todas las propiedades relevantes: clase, objeto/blueprint, calidad y otros
atributos del producto. Coincidir únicamente por nombre o clase no basta. Las
instantáneas usan tokens de vida de inventario e ítems no reutilizables, sesión
y epoch; no punteros UE ni identificadores de cuenta.

El adaptador debe probar que ambas lecturas están completas, pertenecen al mismo
inventario y sesión, y que la llamada terminó con atribución exclusiva de sus
efectos. Una lectura ordinaria no prueba ese aislamiento. Objetos presentes en
varias listas nativas deben deduplicarse por identidad de vida antes de crear
la instantánea. El verificador rechaza duplicados, cantidades inválidas y listas
de más de 4096 ítems; no interpreta datos truncados como inventarios vacíos.

El resultado calcula el incremento, no el total de las pilas devueltas:

| Evidencia | Resultado para el recibo |
| --- | --- |
| Incremento exacto, variante y contexto iguales, otros objetos intactos | Delivered |
| Inventario íntegramente igual, intento terminado y atribución exclusiva probada | VerifiedNoDelivery |
| Cantidad parcial o excesiva | Uncertain, con delta observado |
| Lectura incompleta, cambio de sesión/inventario/variante, reducción o efecto ajeno | Uncertain, sin delta fiable |

El booleano de entrega nativa no es una entrada al verificador. El código actual
de ARK puede devolver éxito tras una entrega parcial. Una pila de 100 que pasa a
110 demuestra un incremento de 10 bajo los requisitos anteriores; no demuestra
que se hayan entregado 110 unidades. Varias pilas nuevas pueden completar la
cantidad cuando todas coinciden con la variante aceptada.

El consumidor persiste `BeginDelivery` antes de invocar el juego y sólo actúa si
el intento inicial fue admitido sin replay. Después usa `CompleteDelivery` con
el resultado comprobado. Las pruebas con SQLite real dejan un recibo parcial
como Uncertain sin refund/retry automático, rechazan sustituirlo por NoDelivery
y conservan estado y saldo tras reabrir. Un NoDelivery verificado reembolsa una
vez. Las pruebas no son evidencia de entrega en un cliente ARK.
