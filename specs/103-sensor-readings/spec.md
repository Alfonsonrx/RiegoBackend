# 103 — Lecturas de sensores

Status: draft · Depends on: `001-accounts-auth`, `002-database-foundation`, `102-sensor-registry`

## 1. Context and objective

Es el núcleo del brief: los sensores "envían datos al sistema", el sistema los almacena (RF4), mantiene
un historial de las condiciones ambientales con la frecuencia que eligió la persona (RF5) y permite ver
"en tiempo real" la humedad y la temperatura (RF7). Esta capacidad recibe las lecturas de cada
dispositivo, las guarda sin tocarlas, devuelve el historial y muestra las condiciones actuales. Avisar
cuando una lectura sale de rango es de 104.

**Objective:** que cada lectura enviada por un sensor activo quede guardada sin cambios y que su dueño/a pueda consultar el historial y las condiciones actuales de sus sensores.

## 2. Users

| Usuario | Relación con esta capacidad |
|---|---|
| Dispositivo (sensor) | Envía lecturas con la clave de su sensor (102 D4) y aprende el intervalo que debe usar. |
| Cultivador/a | Consulta el historial y las condiciones actuales de sus sensores. |
| 104 (notificaciones) | Reacciona a cada lectura guardada. |

## 3. User stories

- Como dispositivo, quiero enviar un valor con mi clave, para que el sistema lo guarde sin que yo conozca la contraseña de nadie.
- Como dispositivo, quiero saber cada cuántos minutos debo leer, para respetar la frecuencia que eligió la persona.
- Como cultivador/a, quiero ver el historial de un sensor en un rango de fechas, para entender cómo se comportó mi invernadero.
- Como cultivador/a, quiero ver el último valor de cada sensor, para decidir si regar o ventilar ahora.

## 4. Functional requirements

### FR-1 — Recibir una lectura (RF4, RF5)
El dispositivo envía un valor numérico y la clave de su sensor. El sistema pone la hora de recepción
(el reloj de un microcontrolador se desvía, D1) y responde con el intervalo vigente, de modo que la
frecuencia que eligió la persona (RF5) llega al dispositivo sin que este guarde credenciales de usuario.
Un sensor desactivado no registra. Una lectura guardada nunca se toca: el historial es la prueba (D4).
- (a) WHEN un dispositivo envía un valor numérico válido para un sensor activo con la clave de ingesta vigente de ese sensor, the system shall guardar la lectura con el momento de recepción.
- (b) WHEN se guarda una lectura, the system shall responder con su id, el id del sensor, el valor, el momento y el intervalo de lectura vigente del sensor en minutos.
- (c) IF el sensor no existe, o la clave falta o no es la vigente del sensor (incluida una clave ya reemplazada), THEN the system shall rechazar la lectura con el mensaje "Clave de sensor inválida" y no guardar nada.
- (d) IF el sensor está inactivo, THEN the system shall rechazar la lectura con el mensaje "Sensor inactivo" y no guardar nada.
- (e) IF el valor no es un número con a lo sumo 3 dígitos enteros y 2 decimales, THEN the system shall rechazar la lectura y no guardar nada.
- (f) The system shall dejar sin cambios cada lectura guardada: ninguna operación del sistema la modifica ni la borra.

### FR-2 — Historial de un sensor (RF5)
La persona pide las lecturas de uno de sus sensores, de la más reciente a la más antigua, acotadas por un
rango de fechas y por una cantidad máxima para que la respuesta no crezca sin límite (D5).
- (a) WHEN un usuario autenticado pide las lecturas de un sensor suyo, the system shall responder con las lecturas guardadas de ese sensor, de la más reciente a la más antigua.
- (b) WHERE el usuario indica un momento de inicio, un momento de fin o ambos, the system shall responder solo con las lecturas cuyo momento está dentro de ese rango, con los extremos incluidos.
- (c) The system shall responder como máximo con el número de lecturas que el usuario pida, y con 100 si no pide ninguno.
- (d) IF el usuario pide más de 1000 lecturas, THEN the system shall rechazar la petición.
- (e) IF el momento de inicio es posterior al momento de fin, THEN the system shall rechazar la petición.
- (f) IF el sensor no existe o es de otro usuario, THEN the system shall responder "Sensor no encontrado".

### FR-3 — Condiciones actuales (RF7, RF3)
"Tiempo real" es la última lectura guardada de cada sensor activo, que la persona consulta cuando
quiere (D3). Que un sensor aún no tenga lecturas dice que todavía no está enviando datos: así la persona
comprueba la conexión de RF3.
- (a) WHEN un usuario autenticado pide las condiciones actuales, the system shall responder, por cada sensor activo suyo, con su id, nombre, tipo, unidad, límites, y el valor y el momento de su última lectura.
- (b) WHILE un sensor activo no tiene ninguna lectura guardada, the system shall responderlo en las condiciones actuales con el valor y el momento vacíos.
- (c) The system shall omitir los sensores inactivos y los de otros usuarios en las condiciones actuales.

## 5. Non-functional requirements

- **Security:** el historial y las condiciones actuales exigen token (001 FR-3); la recepción de lecturas exige la clave del sensor y no acepta el token de la persona en su lugar; la clave se compara en tiempo constante y un sensor inexistente recibe el mismo rechazo que una clave errónea.
- **Isolation:** el historial y las condiciones filtran por la cuenta dueña del sensor; un sensor ajeno responde "no encontrado" (regla 1).
- **Language:** los mensajes visibles están en español, tal como se citan arriba.
- **Traceability:** FR-1 sirve a RF4 y RF5; FR-2 a RF5; FR-3 a RF7 y RF3.
- **Data retention:** ninguna operación modifica ni borra lecturas (FR-1.f); desactivar un sensor o cambiar su intervalo las conserva.
- **Timeliness:** una lectura guardada aparece en el historial y en las condiciones actuales en la consulta siguiente.

## 6. Edge cases

| Situación | Comportamiento esperado |
|---|---|
| Dos lecturas seguidas con menos tiempo que el intervalo | Se guardan ambas; el intervalo es una instrucción al dispositivo, no un filtro (D2). |
| Valor fuera de los límites del sensor | Se guarda igual; el aviso es de 104 (D4). |
| Dispositivo con reloj propio o lecturas acumuladas sin conexión | Se guarda la hora de recepción; la hora propia es del protocolo del dispositivo (backlog). |
| Clave reemplazada (102 FR-4) | La clave vieja se rechaza con "Clave de sensor inválida". |
| Sensor sin lecturas | Historial vacío; en condiciones actuales aparece con valor y momento vacíos. |
| Rango sin lecturas | Lista vacía, no error. |
| Valor negativo (temperatura bajo cero) | Válido mientras entre en 3 enteros y 2 decimales. |
| Un token de persona en lugar de la clave | "Clave de sensor inválida". |
| Sensor desactivado | Rechaza lecturas nuevas; su historial sigue consultable. |

## 7. Out of scope

- Avisos por lecturas fuera de rango: 104.
- Protocolo del dispositivo (hora propia, reintentos, lotes de lecturas): `specs/backlog.md`.
- Gráficos, promedios por hora o por día y política de retención o purga: `specs/backlog.md`.
- Actualización en vivo por empuje: `specs/backlog.md`.
- Borrar o corregir lecturas: no se hace (FR-1.f).

## 8. Completion criteria

El spec se cumple cuando:
- un dispositivo con la clave vigente guarda una lectura y recibe el intervalo del sensor;
- clave ajena, reemplazada o ausente, sensor inactivo o inexistente y valores mal formados se rechazan sin guardar nada;
- el historial sale del más reciente al más antiguo, respeta rango y tope, y rechaza topes mayores a 1000 y rangos invertidos;
- las condiciones actuales muestran el último valor de cada sensor activo propio y valores vacíos si aún no hay lecturas;
- ninguna operación modifica ni borra una lectura;
- las rutas de consulta sin token se rechazan.

## 9. Open questions

None.

## 10. Decisions taken

- **D1 — El momento de la lectura es el de recepción del sistema.** *Por qué:* el reloj de un microcontrolador se desvía y se reinicia en cero al perder energía; fiarse de él ensuciaría el historial. *Costo:* una lectura acumulada sin conexión queda con la hora en que llega (backlog).
- **D2 — El sistema no impone el intervalo: guarda cada lectura recibida y le dice el intervalo al dispositivo en cada respuesta.** *Por qué:* RF5 pide que la persona elija la frecuencia; rechazar lecturas "demasiado rápidas" perdería datos de un dispositivo que reintenta. *Descartado:* rechazar lecturas que lleguen antes del intervalo.
- **D3 — "Tiempo real" es la última lectura guardada, consultada por la interfaz.** *Por qué:* los sensores leen cada N minutos (el brief da "cada 1 hora" de ejemplo); empujar datos en vivo no aporta nada. *Descartado:* WebSocket o eventos del servidor (backlog).
- **D4 — Las lecturas fuera de los límites se guardan igual.** *Por qué:* son datos reales del invernadero; qué hacer con ellas es de 104.
- **D5 — Historial acotado por rango de fechas y por un tope de 1000, sin desplazamiento por páginas.** *Por qué:* el rango de fechas ya permite recorrer cualquier tramo; el tope protege al sistema. *Descartado:* paginación por desplazamiento (se vuelve lenta y repite datos si llegan lecturas mientras se pagina).
- **D6 — Un sensor inactivo no registra.** *Por qué:* la persona lo desactivó para que deje de medir; aceptar sus lecturas contradice esa orden.
