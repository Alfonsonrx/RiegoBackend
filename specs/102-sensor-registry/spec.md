# 102 — Registro de sensores

Status: draft · Depends on: `001-accounts-auth`, `002-database-foundation`

## 1. Context and objective

El brief pide integrar sensores de humedad que se conectan por Bluetooth o Wi-Fi (RF3) y que el historial
se registre "con una frecuencia seleccionada por el usuario" (RF5). Esta capacidad es el lado del sistema
de esa integración: la persona registra sus sensores, elige cada cuánto se leen, fija los límites óptimos
y recibe la clave con la que el dispositivo enviará lecturas (103). Emparejar el dispositivo (Bluetooth o
Wi-Fi) ocurre fuera del sistema (§7).

**Objective:** que cada cultivador/a registre sus sensores de humedad y temperatura, elija su frecuencia de lectura y sus límites, y obtenga la clave con la que cada dispositivo se identifica.

## 2. Users

| Usuario | Relación con esta capacidad |
|---|---|
| Cultivador/a | Dueño/a de sus sensores: los registra, los ve, los cambia y regenera su clave. |
| Dispositivo (sensor) | Usa la clave de ingesta que entrega este spec para enviar lecturas (103). |
| 104 (notificaciones) | Lee los límites de cada sensor para avisar cuando una lectura sale de rango. |

## 3. User stories

- Como cultivador/a, quiero registrar un sensor con su tipo, su conexión y cada cuántos minutos se lee, para empezar a monitorear mi invernadero.
- Como cultivador/a, quiero que un sensor nuevo traiga límites razonables de fábrica, para recibir avisos sin configurarlo todo.
- Como cultivador/a, quiero ajustar el intervalo y los límites, o desactivar el sensor, para adaptarlo a mi cultivo sin perder su historial.
- Como cultivador/a, quiero pedir una clave nueva si pierdo la del dispositivo, para recuperar el sensor sin registrarlo otra vez.

## 4. Functional requirements

### FR-1 — Registrar un sensor (RF3, RF5)
Un sensor es un dispositivo del invernadero: nombre, tipo (humedad o temperatura), conexión (Wi-Fi o
Bluetooth, las del brief), intervalo de lectura en minutos (la frecuencia que elige la persona, RF5) y
límites óptimos. La unidad sale del tipo, para que no se contradigan. Si la persona no da un límite,
parte del valor óptimo del brief (D3). El dispositivo se identifica con una clave secreta que se muestra
una sola vez, porque guardarla en claro la haría robable desde la base (D4).
- (a) WHEN un usuario autenticado envía un nombre, un tipo de sensor, un tipo de conexión y un intervalo de lectura válidos, the system shall crear un sensor activo de su propiedad.
- (b) WHEN se crea un sensor, the system shall responder con sus datos y una clave de ingesta que se muestra una sola vez.
- (c) The system shall guardar la clave de ingesta únicamente como hash de un solo sentido.
- (d) The system shall fijar la unidad de cada sensor según su tipo: "%" para humedad y "°C" para temperatura.
- (e) WHEN se crea un sensor sin enviar un límite, the system shall fijar ese límite en el valor de su tipo: inferior 70 y superior 90 para humedad, inferior 18 y superior 24 para temperatura.
- (f) IF el tipo de sensor no es "humidity" ni "temperature", THEN the system shall rechazar la petición y no crear ningún sensor.
- (g) IF el tipo de conexión no es "wifi" ni "bluetooth", THEN the system shall rechazar la petición y no crear ningún sensor.
- (h) IF el intervalo de lectura no es un número entero de minutos mayor o igual que 1, THEN the system shall rechazar la petición y no crear ningún sensor.
- (i) IF el límite inferior resultante es mayor que el límite superior, THEN the system shall rechazar la petición y no crear ningún sensor.
- (j) IF un límite no es un número con a lo sumo 3 dígitos enteros y 2 decimales, THEN the system shall rechazar la petición y no crear ningún sensor.

### FR-2 — Ver mis sensores (RF3)
La persona ve sus sensores con todos sus datos, pero nunca la clave: la clave solo existe en claro en el
instante en que se entrega.
- (a) WHEN un usuario autenticado pide sus sensores, the system shall responder con el id, nombre, tipo, unidad, conexión, intervalo, límites y estado activo de cada sensor suyo.
- (b) The system shall omitir los sensores de otros usuarios en las respuestas de cada usuario.
- (c) The system shall omitir la clave de ingesta y su hash en las respuestas de consulta y de cambio.
- (d) WHEN un usuario autenticado pide un sensor suyo por su id, the system shall responder con los datos de ese sensor.
- (e) IF el sensor pedido no existe o es de otro usuario, THEN the system shall responder "Sensor no encontrado".

### FR-3 — Cambiar un sensor (RF5)
La persona ajusta nombre, frecuencia, límites y estado activo. Tipo, unidad y conexión no cambian: el
significado de las lecturas ya guardadas depende de ellos (D6). Desactivar conserva el sensor y su
historial (D5).
- (a) WHEN un usuario autenticado cambia el nombre, el intervalo de lectura, los límites o el estado activo de un sensor suyo, the system shall guardar el cambio y responder con el sensor actualizado.
- (b) WHEN el usuario deja vacío un límite, the system shall guardar el sensor con ese límite vacío.
- (c) IF el cambio deja el límite inferior mayor que el superior, THEN the system shall rechazar el cambio y dejar el sensor como estaba.
- (d) IF el intervalo del cambio no es un número entero de minutos mayor o igual que 1, THEN the system shall rechazar el cambio y dejar el sensor como estaba.
- (e) IF el cambio incluye el tipo, la unidad o la conexión del sensor, THEN the system shall rechazar el cambio y dejar el sensor como estaba.
- (f) IF el sensor no existe o es de otro usuario, THEN the system shall responder "Sensor no encontrado" y no modificar ningún sensor.

### FR-4 — Regenerar la clave de ingesta (RF3)
Si la persona pierde la clave del dispositivo, pide otra; la anterior deja de servir (103 FR-1.c).
- (a) WHEN un usuario autenticado pide una clave nueva para un sensor suyo, the system shall reemplazar la clave guardada del sensor por la de una clave nueva.
- (b) WHEN se regenera la clave, the system shall responder con la clave nueva, que se muestra una sola vez.
- (c) IF el sensor no existe o es de otro usuario, THEN the system shall responder "Sensor no encontrado" y no modificar ninguna clave.

## 5. Non-functional requirements

- **Security:** todas las operaciones exigen token (001 FR-3); la clave de ingesta es aleatoria de 256 bits y solo se guarda su hash (regla 3 del perfil); no aparece en respuestas de consulta ni de cambio.
- **Isolation:** toda lectura y cambio filtra por la cuenta dueña; un sensor ajeno responde "no encontrado" (regla 1).
- **Language:** los mensajes visibles están en español, tal como se citan arriba.
- **Traceability:** FR-1 sirve a RF3 y RF5; FR-2 y FR-4 a RF3; FR-3 a RF5.
- **Data retention:** cambiar o desactivar un sensor no modifica ninguna lectura ya guardada.

## 6. Edge cases

| Situación | Comportamiento esperado |
|---|---|
| Dos sensores con el mismo nombre | Permitidos; se distinguen por id. |
| Solo se envía el límite inferior al crear | El superior toma el de su tipo; si el inferior supera a ese superior, se rechaza (FR-1.i). |
| Tipo con otras mayúsculas ("Humidity") | Rechazado: solo los valores exactos de FR-1.f. |
| Se pierde la clave | Se pide una nueva (FR-4); no se puede recuperar la anterior. |
| Sensor desactivado | Conserva datos e historial; 103 rechaza lecturas nuevas. |
| Intervalo cambiado con lecturas ya guardadas | Las lecturas no cambian; el dispositivo conoce el intervalo nuevo en su próxima respuesta (103 FR-1.b). |
| Cambio que envía un límite vacío y otro lleno | Se guarda el vacío y se revisa el orden con el que quede (FR-3.b, FR-3.c). |

## 7. Out of scope

- Emparejar el dispositivo por Bluetooth o Wi-Fi, instalarlo y mostrar instrucciones si la conexión falla (RF3): firmware e interfaz web, `specs/backlog.md`.
- Comprobar que el sensor "está conectado": se ve por su última lectura, 103 FR-3.
- Recibir y consultar lecturas: 103.
- Avisos por lecturas fuera de rango: 104.
- Borrar sensores, compartirlos entre cuentas, otros tipos de sensor (humedad del sustrato) u otras conexiones (LoRa): `specs/backlog.md`.

## 8. Completion criteria

El spec se cumple cuando:
- una persona autenticada registra un sensor válido y recibe sus datos con unidad y límites completos y una clave;
- los datos inválidos de FR-1.f–j se rechazan sin crear nada;
- el listado y la consulta por id muestran solo sensores propios y nunca la clave ni su hash;
- cambiar nombre, intervalo, límites o estado funciona, y cambiar tipo, unidad o conexión se rechaza;
- regenerar la clave entrega una nueva y la anterior ya no está guardada;
- cada operación sin token se rechaza.

## 9. Open questions

None.

## 10. Decisions taken

- **D1 — Listas cerradas de tipos y conexiones tomadas del brief:** tipos humedad ("humidity") y temperatura ("temperature"), conexiones "wifi" y "bluetooth". *Por qué:* el brief habla de humedad del aire, temperatura, Bluetooth y Wi-Fi; los comentarios del código mencionan humedad del suelo y LoRa, que ningún requisito pide. Se amplían cuando un requisito lo pida.
- **D2 — La unidad sale del tipo, no la envía la persona.** *Por qué:* evita "temperatura en %".
- **D3 — Límites por defecto según el tipo** (respuesta de la persona dueña, 2026-11-13): humedad 70–90 % (supuesto: ±10 alrededor del 80 % del brief) y temperatura 18–24 °C (el brief la da como "18 ºC – 24 ºC (noche – día)", se toma como una sola banda). *Por qué:* sin límites, RF4 ("si la humedad sale del rango óptimo, avisar") no se cumpliría por omisión.
- **D4 — Cada sensor tiene su propia clave de ingesta** (respuesta de la persona dueña, 2026-11-13). Enmienda la regla 2 del perfil: la recepción de lecturas (103) se autentica con esa clave, no con el token de la persona. *Por qué:* el microcontrolador no debe guardar la contraseña de su dueña ni depender de un token que vence. *Descartado:* usar el token de la persona.
- **D5 — Los sensores no se borran, se desactivan.** *Por qué:* RF5 pide historial; borrar un sensor borraría o dejaría huérfanas sus lecturas.
- **D6 — Tipo, unidad y conexión no cambian después de crear el sensor.** *Por qué:* una lectura de "65" solo significa algo con su tipo y su unidad; para cambiarlos se registra otro sensor.
