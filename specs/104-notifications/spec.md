# 104 — Notificaciones

Status: draft · Depends on: `001-accounts-auth`, `002-database-foundation`, `101-irrigation-schedule`, `103-sensor-readings`

## 1. Context and objective

El brief pide que la aplicación "recuerde al usuario cuándo es el momento de regar" (RF2) y, cuando la
humedad sale del rango óptimo, que "notifique al usuario" (excepción de RF4). Esta capacidad produce esas
notificaciones y deja que la persona las vea y las marque como leídas. Las notificaciones son una lista
dentro de la aplicación (D1): la interfaz web la consulta.

**Objective:** que cada cultivador/a reciba, dentro de la aplicación, un aviso cuando llega la hora de una entrada de riego y cuando un sensor suyo sale de su rango, y pueda ver y marcar esos avisos como leídos.

## 2. Users

| Usuario | Relación con esta capacidad |
|---|---|
| Cultivador/a | Recibe, lee y marca como leídos sus avisos. |
| El sistema | Crea los avisos al llegar la hora de una entrada (101) y al guardar una lectura fuera de rango (103). |

## 3. User stories

- Como cultivador/a, quiero que el sistema me avise cuando es hora de regar, para no depender de mi memoria.
- Como cultivador/a, quiero un aviso cuando la humedad o la temperatura salen de mi rango, para reaccionar a tiempo.
- Como cultivador/a, quiero ver solo los avisos que no he leído, para saber qué falta atender.
- Como cultivador/a, quiero no recibir un aviso por cada lectura mientras el problema sigue, para que los avisos sigan siendo útiles.

## 4. Functional requirements

### FR-1 — Recordatorio de riego (RF2)
Cuando llega el momento de una entrada activa, su dueño/a recibe un aviso, una sola vez por momento
programado. Si el sistema estaba apagado en ese momento, el aviso sale tarde en vez de perderse (D3). Si la
persona mueve la entrada, el nuevo momento vuelve a avisar.
- (a) WHEN llega o ya pasó el momento de una entrada de calendario activa que aún no tiene recordatorio, the system shall crear una notificación no leída de tipo "irrigation_reminder" para su dueño.
- (b) The system shall crear como máximo un recordatorio por entrada y por momento programado.
- (c) WHEN el dueño cambia la fecha o la hora de una entrada, the system shall permitir un recordatorio nuevo para el nuevo momento de esa entrada.
- (d) IF una entrada está inactiva, THEN the system shall no crear su recordatorio.
- (e) The system shall redactar cada recordatorio en español con la fecha y la hora de la entrada, con la forma "Es hora de regar las orquídeas (20-11-2026 08:00)".

### FR-2 — Alerta por lectura fuera de rango (RF4)
Una lectura fuera de los límites del sensor avisa a su dueño/a, pero solo cuando el sensor *pasa* a estar
fuera de rango: si ya lo estaba, repetir el aviso en cada lectura inundaría la lista (D2). La lectura se
guarda aunque el aviso falle: el historial vale más que el aviso.
- (a) WHEN se guarda una lectura fuera de los límites de su sensor y la lectura anterior de ese sensor estaba dentro de ellos o no existe, the system shall crear una notificación no leída de tipo "reading_alert" para el dueño del sensor.
- (b) IF se guarda una lectura fuera de los límites de un sensor cuya lectura anterior también estaba fuera de ellos, THEN the system shall no crear una notificación nueva.
- (c) WHILE un límite del sensor está vacío, the system shall tratar ese lado como sin tope.
- (d) The system shall redactar cada alerta en español con el nombre del sensor, el valor con su unidad y los límites que tenga el sensor, con la forma "Humedad invernadero 1: 65 % fuera de rango (mín 70 %, máx 90 %)".
- (e) IF crear la alerta falla, THEN the system shall conservar la lectura ya guardada.

### FR-3 — Ver mis notificaciones (RF2, RF4)
La persona ve sus avisos más recientes primero y puede ocultar los ya leídos.
- (a) WHEN un usuario autenticado pide sus notificaciones, the system shall responder con sus 100 notificaciones más recientes, de la más reciente a la más antigua, cada una con su id, tipo, mensaje, estado de lectura y fecha.
- (b) WHERE el usuario pide solo las no leídas, the system shall omitir las notificaciones leídas.
- (c) The system shall omitir las notificaciones de otros usuarios en las respuestas de cada usuario.

### FR-4 — Marcar como leída (RF2, RF4)
- (a) WHEN un usuario autenticado marca como leída una notificación suya, the system shall guardarla como leída y responder con ella.
- (b) IF la notificación no existe o es de otro usuario, THEN the system shall responder "Notificación no encontrada" y no modificar ninguna notificación.

## 5. Non-functional requirements

- **Security:** ver y marcar notificaciones exige token (001 FR-3); los recordatorios y las alertas los crea el sistema, ninguna operación pública los crea.
- **Isolation:** toda lectura y cambio filtra por la cuenta dueña; una notificación ajena responde "no encontrada" (regla 1).
- **Language:** los mensajes de las notificaciones y de error están en español, tal como se citan arriba; los tipos "irrigation_reminder" y "reading_alert" son identificadores.
- **Traceability:** FR-1 sirve a RF2; FR-2 a RF4; FR-3 y FR-4 a RF2 y RF4.
- **Timeliness:** con el sistema en marcha, un recordatorio se crea a más tardar 60 segundos después del momento de su entrada; una alerta se crea durante la misma petición que guarda la lectura.
- **Data retention:** ninguna operación borra notificaciones.

## 6. Edge cases

| Situación | Comportamiento esperado |
|---|---|
| Sistema apagado en el momento de la entrada | Al volver a funcionar crea el recordatorio tardío (FR-1.a). |
| Entrada ya recordada que se desactiva y se reactiva sin cambiar fecha ni hora | No se recuerda otra vez (FR-1.b). |
| Entrada vencida que nunca tuvo recordatorio y se reactiva | Recuerda en la siguiente revisión (FR-1.a). |
| Entrada ya recordada que se reprograma | Un recordatorio nuevo para el nuevo momento (FR-1.c). |
| Varias instancias del sistema en marcha | Un solo recordatorio por entrada y momento (FR-1.b). |
| Primera lectura de un sensor ya fuera de rango | Alerta (no hay lectura anterior, FR-2.a). |
| Lectura que vuelve al rango y luego sale otra vez | Una alerta nueva por cada salida (FR-2.a). |
| Lectura exactamente igual a un límite | Está dentro del rango; los límites son inclusivos (D5). |
| Límites cambiados entre dos lecturas | Se evalúa con los límites vigentes al guardar cada lectura. |
| Sensor sin ningún límite | Nunca alerta (FR-2.c). |
| Más de 100 notificaciones acumuladas | Se ven las 100 más recientes; el filtro de no leídas ayuda a no perder las pendientes (D4). |
| Marcar como leída una ya leída | La misma respuesta, sin error (FR-4.a). |

## 7. Out of scope

- Avisos fuera de la aplicación (push, correo, mensajes): `specs/backlog.md`.
- Actualización en vivo de la lista: `specs/backlog.md`.
- Marcar todas como leídas, borrar o paginar notificaciones: `specs/backlog.md`.
- Aviso de "volvió al rango" y aviso de sensor sin señal: `specs/backlog.md`.
- La pantalla con la lista: interfaz web, `specs/backlog.md`.

## 8. Completion criteria

El spec se cumple cuando:
- una entrada activa cuyo momento llegó genera exactamente una notificación para su dueño, también si el sistema estuvo apagado, y reprogramarla genera otra;
- una entrada inactiva no genera nada;
- una lectura que saca al sensor de su rango genera una alerta, una segunda lectura fuera de rango consecutiva no genera otra, y volver a entrar y salir sí;
- si falla la alerta, la lectura queda guardada;
- la lista sale del más reciente al más antiguo con tope de 100, filtra no leídas y no muestra avisos ajenos;
- marcar como leída funciona y una notificación ajena responde "no encontrada";
- las rutas sin token se rechazan.

## 9. Open questions

None.

## 10. Decisions taken

- **D1 — Las notificaciones son una lista dentro de la aplicación.** *Por qué:* el brief pide que la aplicación avise, el prototipo es web y la tabla de notificaciones ya existe; push y correo piden permisos y cuentas externas que el brief no menciona. *Descartado:* push y correo (backlog).
- **D2 — Se avisa al pasar de dentro a fuera de rango, no en cada lectura fuera de rango.** *Por qué:* un sensor que lee cada hora y queda fuera de rango un día generaría 24 avisos iguales; el primero ya dice lo que hay que saber. *Descartado:* un aviso por lectura; un aviso cada N horas (necesita un reloj de silencio por sensor).
- **D3 — Un recordatorio vencido sale tarde, no se pierde.** *Por qué:* con el sistema apagado a la hora de riego, un aviso tardío sigue siendo útil; perderlo en silencio no. *Costo:* una entrada vencida que se reactiva por primera vez avisa de inmediato.
- **D4 — La lista es fija de 100 notificaciones, sin paginar.** *Por qué:* basta para un prototipo; el filtro de no leídas cubre la necesidad real. *Descartado:* paginación (backlog).
- **D5 — Los límites son inclusivos:** un valor igual al límite está dentro del rango. *Por qué:* "fuera de rango" debe significar estrictamente por debajo o por encima.
- **D6 — Un recordatorio por momento programado:** cambiar la fecha o la hora reinicia el control, no lo hace desactivar y reactivar. *Por qué:* mover el riego es una nueva cita; reactivar la misma no lo es.
