# 105 — Simulador de sensores

Status: draft · Depends on: `102-sensor-registry`, `103-sensor-readings`

## 1. Context and objective

El prototipo todavía no tiene microcontrolador, pero la interfaz, el historial (103) y los avisos (104)
necesitan lecturas para mostrarse y probarse. Existe un generador de temperatura y humedad hecho por el
equipo, pero se comporta como un servidor que espera a que alguien le pida datos, y nadie se los pide: en
este sistema el dispositivo es quien envía cada lectura con la clave de su sensor (102 D4, 103 FR-1).
Además, cada valor sale al azar sin relación con el anterior, así que el historial parece ruido (la
temperatura salta de 18 a -1 y a 30 en tres lecturas).

Este spec convierte ese generador en un simulador que hace lo mismo que hará el dispositivo real: lee un
valor, lo envía a la recepción de lecturas con la clave de su sensor, obedece el intervalo que le
devuelve el sistema y repite. Los valores derivan poco a poco, como en un invernadero, y de vez en
cuando salen del rango óptimo para que 104 tenga algo que avisar.

**En este spec, "the system" es el simulador**, no el backend: es el sujeto que el perfil exige en las
viñetas EARS. Cuando una viñeta habla del backend, lo nombra como "la recepción de lecturas".

**Objective:** que una persona pueda poner a enviar lecturas creíbles de temperatura y humedad a sus sensores registrados, con el mismo contrato que usará el dispositivo real, sin tocar el backend.

## 2. Users

| Usuario | Relación con esta capacidad |
|---|---|
| Equipo de desarrollo | Arranca el simulador para llenar el historial y probar 103 y 104 sin hardware. |
| Quien presenta el prototipo | Lo arranca con un intervalo corto para que la interfaz cambie a la vista. |
| La recepción de lecturas (103) | Recibe las lecturas del simulador igual que las de un dispositivo. |

## 3. User stories

- Como equipo de desarrollo, quiero que el simulador envíe lecturas a mis sensores registrados con sus claves, para probar el historial y los avisos sin un microcontrolador.
- Como equipo de desarrollo, quiero que los valores cambien poco a poco y a veces salgan de rango, para que el historial se vea como un invernadero y 104 tenga lecturas que avisar.
- Como quien presenta, quiero forzar un intervalo de pocos segundos, para que los cambios se vean durante la presentación.
- Como equipo de desarrollo, quiero ver en la consola cada envío y su resultado, para saber si el sensor está conectado sin abrir la base de datos.

## 4. Functional requirements

### FR-1 — Configuración de los sensores simulados (RF3)
El simulador recibe la dirección del backend y uno o más sensores, cada uno con su id, su tipo
(temperatura o humedad, los de 102 D1) y su clave de ingesta. Una configuración incompleta se detecta
antes de enviar nada: un envío con datos a medias solo produciría rechazos difíciles de leer. La clave es
un secreto (regla 3 del perfil): entra por el entorno y nunca sale por la consola. Sirve a RF3, porque
simula el sensor conectado; no lo empareja.
- (a) WHEN el simulador arranca con una dirección y al menos un sensor con id, tipo y clave, the system shall empezar a enviar lecturas de cada sensor configurado.
- (b) IF falta la dirección, no hay ningún sensor, o un sensor no tiene clave o su tipo no es temperatura ni humedad, THEN the system shall terminar con un código de error y un mensaje que nombra el dato que falta, sin enviar ninguna lectura.
- (c) IF el intervalo de demostración no es un número de segundos mayor que cero, THEN the system shall terminar con un código de error sin enviar ninguna lectura.
- (d) The system shall omitir toda clave de ingesta en lo que escribe en la consola.

### FR-2 — Valores que derivan (no sirve a ningún RF; alimenta RF4 en 104)
Cada sensor lleva su propio valor, que avanza un paso pequeño desde el anterior y tiende a volver a su
banda óptima (18–24 °C, 70–90 %), con salidas ocasionales fuera de ella (D2). Los límites duros son los
del generador original: un invernadero de orquídeas no ve -5 °C ni 40 °C, y un sensor de humedad no
pasa de 0–100 %. Un decimal basta y cabe en lo que acepta la recepción (103 FR-1.e). Con una semilla, la
secuencia se repite: así una prueba o una demostración salen iguales cada vez.
- (a) The system shall generar cada valor de temperatura entre -1 y 30 °C y cada valor de humedad entre 0 y 100 %, ambos incluidos.
- (b) The system shall generar valores con a lo sumo un decimal.
- (c) The system shall generar cada valor de un sensor a no más de 1,0 °C (temperatura) o 3 % (humedad) del valor anterior del mismo sensor.
- (d) The system shall generar el primer valor de cada sensor dentro de su banda óptima.
- (e) WHEN se generan 10 000 valores seguidos de un sensor con una semilla fija, the system shall dejar entre el 60 % y el 85 % de ellos dentro de la banda óptima y al menos uno fuera de ella.
- (f) WHERE se indica una semilla, the system shall generar la misma secuencia de valores en cada ejecución con esa semilla.

### FR-3 — Enviar cada lectura (RF4)
El simulador envía cada valor a la recepción de lecturas del sensor, con su clave, exactamente como lo
hará el dispositivo (103 FR-1). La primera lectura de cada sensor sale al arrancar, para que la persona
compruebe la conexión de inmediato (103 FR-3.b). Cada envío deja una línea en la consola, que es la
única forma de ver qué pasa sin abrir la base de datos.
- (a) WHEN el simulador arranca, the system shall enviar de inmediato una primera lectura de cada sensor configurado.
- (b) WHEN le toca leer a un sensor, the system shall enviar a la recepción de lecturas el valor nuevo con la clave de ese sensor.
- (c) WHEN termina un envío, the system shall escribir en la consola una línea con la hora, el id y el tipo del sensor, el valor y el resultado.

### FR-4 — Respetar el intervalo (RF5)
La frecuencia la elige la persona en el backend (102), y la recepción la devuelve en cada respuesta (103
FR-1.b, D2). El simulador la obedece por sensor, así que un cambio hecho por la persona se aplica desde
la lectura siguiente, sin reiniciar nada. Como los intervalos se cuentan en minutos y una demostración
no puede esperar una hora, un intervalo de demostración en segundos los reemplaza todos (D4).
- (a) WHEN la recepción acepta una lectura, the system shall esperar el intervalo que devolvió para ese sensor antes de su lectura siguiente.
- (b) WHERE se indica un intervalo de demostración, the system shall esperar ese número de segundos entre lecturas de cada sensor en lugar del intervalo devuelto.
- (c) WHILE la recepción no ha aceptado ninguna lectura de un sensor, the system shall esperar 60 segundos entre sus intentos.

### FR-5 — Rechazos y caídas (RF4)
Un dispositivo real sigue intentando mientras el problema pueda arreglarse solo, y se detiene cuando no
(D5). Una clave inválida no se arregla sola: la persona tiene que darle la clave nueva. Un sensor
inactivo sí: la persona puede reactivarlo, y el simulador debe retomarlo sin reinicio. Una caída del
backend también pasa sola. Un sensor detenido no frena a los demás.
- (a) IF la recepción responde "Clave de sensor inválida", THEN the system shall dejar de enviar lecturas de ese sensor y escribir en la consola un mensaje que lo nombra.
- (b) IF la recepción responde "Sensor inactivo", THEN the system shall volver a intentar ese sensor tras su intervalo vigente.
- (c) IF la recepción no responde o responde con un error del servidor, THEN the system shall volver a intentar ese sensor tras su intervalo vigente sin terminar.
- (d) WHILE un sensor está detenido por clave inválida, the system shall seguir enviando las lecturas de los demás sensores.
- (e) IF todos los sensores configurados están detenidos, THEN the system shall terminar con un código de error.

## 5. Non-functional requirements

- **Security:** la clave de ingesta entra por el entorno, nunca por la línea de órdenes (quedaría en el historial de la terminal y en la lista de procesos) y nunca se escribe en la consola (FR-1.d, regla 3).
- **Isolation:** el simulador solo conoce las claves que se le dan; no usa el token de ninguna persona (103 §5).
- **Language:** los mensajes de la consola están en español.
- **Traceability:** FR-1 sirve a RF3; FR-2 a ninguno (da a 104 lecturas fuera de rango para RF4); FR-3 y FR-5 a RF4; FR-4 a RF5.
- **Data retention:** el simulador no guarda nada; cada lectura aceptada queda en el historial del backend (103 FR-1.f).
- **Timeliness:** con un intervalo de demostración de N segundos, cada sensor envía una lectura cada N segundos, más lo que tarde la respuesta.

## 6. Edge cases

| Situación | Comportamiento esperado |
|---|---|
| La persona cambia el intervalo del sensor mientras el simulador corre | Se aplica desde la respuesta siguiente (FR-4.a). |
| La persona regenera la clave (102 FR-4) | Ese sensor recibe "Clave de sensor inválida" y se detiene (FR-5.a); se reinicia el simulador con la clave nueva. |
| La persona desactiva el sensor y luego lo reactiva | Mientras está inactivo, reintenta cada intervalo; al reactivarlo retoma solo (FR-5.b). |
| El backend no está corriendo al arrancar | Reintenta cada 60 s sin terminar (FR-4.c, FR-5.c). |
| Dos sensores con intervalos distintos | Cada uno lleva su propio turno (FR-4.a). |
| Dos sensores del mismo tipo | Cada uno deriva por su cuenta (FR-2). |
| Un sensor de tipo distinto al que dice la configuración (p. ej. configurado como humedad pero registrado como temperatura) | El backend acepta el valor (no conoce el tipo del simulador); los valores no tendrán sentido. Es un error de configuración que el simulador no puede ver. |
| Una lectura fuera de los límites del sensor | Se envía igual; el aviso es de 104 (103 D4). |

## 7. Out of scope

- Firmware del microcontrolador, emparejamiento, hora propia del dispositivo y lecturas acumuladas sin conexión: `specs/backlog.md` (protocolo del dispositivo).
- Registrar los sensores o pedir sus claves desde el simulador: se hace con 102; el simulador recibe las claves ya creadas.
- Simular otros tipos de sensor (humedad del sustrato, LoRa): `specs/backlog.md`.
- Cambios en el backend: ninguno; el simulador usa 103 FR-1 tal como está.

## 8. Completion criteria

El spec se cumple cuando:
- con una dirección y dos sensores (temperatura y humedad) con sus claves, el simulador envía una lectura de cada uno al arrancar y luego una cada intervalo;
- una configuración incompleta o un intervalo de demostración inválido terminan con error sin enviar nada;
- ninguna clave aparece en la consola;
- los valores se quedan en sus límites duros, avanzan a pasos pequeños, pasan entre el 60 % y el 85 % del tiempo en su banda y salen de ella alguna vez;
- con una semilla fija la secuencia se repite;
- una clave inválida detiene solo ese sensor, un sensor inactivo o un backend caído se reintentan, y sin sensores vivos el simulador termina con error;
- el servidor anterior del generador ya no existe en el repositorio.

## 9. Open questions

None.

## 10. Decisions taken

- **D1 — El simulador vive en este repositorio** (respuesta de la persona dueña, 2026-11-16). *Por qué:* un solo repositorio que clonar, y sus pruebas corren junto a las del backend. *Descartado:* seguir en el repositorio aparte del generador o enlazarlo como submódulo.
- **D2 — Los valores derivan desde el anterior y tienden a volver a la banda óptima** (respuesta de la persona dueña, 2026-11-16). *Por qué:* el historial y los gráficos deben parecerse a un invernadero, y las salidas ocasionales siguen dando a 104 algo que avisar. Se conserva la proporción del generador original (alrededor del 70 % dentro de la banda). *Descartado:* valores independientes en cada lectura, como el generador original.
- **D3 — El simulador envía; no espera a que lo consulten** (acordado con la persona dueña, 2026-11-15). *Por qué:* es el contrato de 103 FR-1 y el del dispositivo real; cambiar al hardware no cambia nada en el backend. *Descartado:* el servidor del generador original, que el backend tendría que consultar.
- **D4 — El simulador obedece el intervalo del backend, con un intervalo de demostración en segundos que lo reemplaza.** *Por qué:* RF5 deja la frecuencia en manos de la persona; los minutos son demasiado lentos para presentar. *Descartado:* un intervalo propio del simulador, como el del generador original (1–60 s), que ignoraría lo que eligió la persona.
- **D5 — Clave inválida detiene ese sensor; sensor inactivo y backend caído se reintentan.** *Por qué:* reintentar una clave equivocada solo llena la consola; un sensor reactivado o un backend que vuelve deben retomarse sin intervención.
- **D6 — Un decimal.** *Por qué:* los sensores baratos de temperatura y humedad del aire entregan una décima, y cabe en los 2 decimales que acepta la recepción.
