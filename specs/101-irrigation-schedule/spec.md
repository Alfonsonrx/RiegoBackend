# 101 — Calendario de riego

Status: draft · Depends on: `001-accounts-auth`, `002-database-foundation`

## 1. Context and objective

El brief pide que "el usuario pueda establecer un calendario de riego para las orquídeas" (RF1: el
usuario "configura los días y horas para el riego" y guarda). Esta capacidad solo guarda y muestra el
calendario; avisar cuando llega la hora es de 104 (RF2). El calendario de este spec es una lista de
entradas de fecha y hora únicas, por decisión de la persona dueña (D1); la repetición semanal queda en el
backlog.

**Objective:** que cada cultivador/a cree, vea, cambie y desactive sus propias entradas de riego (fecha y hora), sin ver ni tocar las de otras personas.

## 2. Users

| Usuario | Relación con esta capacidad |
|---|---|
| Cultivador/a | Dueño/a de sus entradas: las crea, las ve, las cambia o las desactiva. |
| 104 (recordatorios) | Lee las entradas activas para avisar cuando llega su momento. |

## 3. User stories

- Como cultivador/a, quiero anotar cuándo regar mis orquídeas, para que el sistema me lo recuerde.
- Como cultivador/a, quiero ver mi calendario ordenado, para saber cuál es el próximo riego.
- Como cultivador/a, quiero cambiar o desactivar una entrada, para corregir un error o saltarme un riego sin perder el registro.
- Como cultivador/a, quiero que nadie más vea mi calendario, para que mi invernadero sea solo mío.

## 4. Functional requirements

### FR-1 — Crear una entrada de calendario (RF1)
Una entrada es una fecha y una hora de pared del invernadero, activa desde que se crea y propiedad de quien
la crea. Una entrada que ya pasó no sirve: su recordatorio saldría de inmediato y no avisaría de nada.
- (a) WHEN un usuario autenticado envía una fecha y una hora posteriores al momento actual, the system shall crear una entrada activa de su propiedad.
- (b) WHEN se crea una entrada, the system shall responder con su id, fecha, hora y estado activo.
- (c) IF la fecha o la hora faltan o no son una fecha o una hora válidas, THEN the system shall rechazar la petición y no crear ninguna entrada.
- (d) IF la fecha y la hora enviadas no son posteriores al momento actual, THEN the system shall rechazar la petición con el mensaje "La fecha y hora de riego deben ser futuras" y no crear ninguna entrada.

### FR-2 — Ver el calendario (RF1)
La persona ve solo sus entradas, de la más próxima a la más lejana, con la opción de ocultar las que
desactivó.
- (a) WHEN un usuario autenticado pide su calendario, the system shall responder con sus entradas ordenadas por fecha y hora, de la más próxima a la más lejana.
- (b) The system shall omitir las entradas de otros usuarios en el calendario de cada usuario.
- (c) WHERE el usuario pide solo las entradas activas, the system shall omitir las entradas inactivas.

### FR-3 — Cambiar una entrada (RF1)
La persona corrige la fecha o la hora, o desactiva la entrada sin borrarla (D2). Cambiar solo el estado de
una entrada no revalida su fecha, para poder desactivar una entrada que ya venció.
- (a) WHEN un usuario autenticado cambia la fecha, la hora o el estado activo de una entrada suya, the system shall guardar el cambio y responder con la entrada actualizada.
- (b) IF un cambio modifica la fecha o la hora de la entrada y la deja en un momento no posterior al actual, THEN the system shall rechazar el cambio con el mensaje "La fecha y hora de riego deben ser futuras" y dejar la entrada como estaba.
- (c) IF la entrada no existe o pertenece a otro usuario, THEN the system shall responder "Entrada de riego no encontrada" y no modificar ninguna entrada.
- (d) IF un cambio trae una fecha, una hora o un estado vacíos o inválidos, THEN the system shall rechazar el cambio y dejar la entrada como estaba.

## 5. Non-functional requirements

- **Security:** todas las operaciones exigen un token válido (001 FR-3); sin token se rechazan.
- **Isolation:** toda lectura y cambio filtra por la cuenta dueña; una entrada ajena responde "no encontrada", igual que una inexistente (regla 1 del perfil).
- **Language:** los mensajes visibles están en español, tal como se citan arriba.
- **Traceability:** FR-1, FR-2 y FR-3 sirven a RF1.
- **Data retention:** el sistema no borra entradas; desactivar las conserva (D2).

## 6. Edge cases

| Situación | Comportamiento esperado |
|---|---|
| Fecha y hora exactamente iguales al momento actual | Rechazada: no es posterior (FR-1.d). |
| Dos entradas con la misma fecha y hora | Permitidas, ambas se guardan (D5). |
| Cambiar solo el estado de una entrada vencida | Permitido; no se revalida la fecha (FR-3). |
| Reenviar la entrada completa con la misma fecha y hora y otro estado | Solo cambia el estado: no se revalida la fecha (FR-3.b). |
| Cambiar solo la hora | La fecha ya guardada y la hora nueva deben ser posteriores al momento actual (FR-3.b). |
| Id de entrada de otra persona o inexistente | La misma respuesta "Entrada de riego no encontrada" (FR-3.c). |
| Petición sin token o con token inválido | Rechazada por 001 FR-3, sin llegar a esta capacidad. |
| Reactivar una entrada vencida cuyo recordatorio nunca salió | La atiende 104 (recordatorio tardío). |

## 7. Out of scope

- Avisar cuando llega la hora: 104.
- Calendario recurrente (días de la semana + hora): `specs/backlog.md`.
- Borrar entradas: `specs/backlog.md`.
- Pantalla del calendario: interfaz web, `specs/backlog.md`.
- Varios invernaderos o una zona horaria por persona: `specs/backlog.md`.

## 8. Completion criteria

El spec se cumple cuando:
- una persona autenticada crea una entrada futura y la ve en su calendario con id, fecha, hora y estado;
- las entradas con fecha pasada, igual a la actual, o con datos faltantes o inválidos se rechazan sin crear nada;
- el calendario sale ordenado y el filtro de activas oculta las inactivas;
- una persona no puede ver ni cambiar las entradas de otra, y la respuesta no distingue "ajena" de "inexistente";
- cambiar la fecha o la hora a un momento pasado se rechaza y desactivar una entrada vencida funciona;
- cada operación sin token se rechaza.

## 9. Open questions

None.

## 10. Decisions taken

- **D1 — Entradas de fecha y hora únicas** (respuesta de la persona dueña, 2026-11-13), no repetición semanal. *Por qué:* es lo que ya modela la base y basta para RF1; "días y horas" del brief se cubre creando una entrada por día. *Descartado:* días de la semana + hora (cambia el esquema; backlog).
- **D2 — No se borran entradas, se desactivan.** *Por qué:* RF1 solo pide "establecer"; desactivar cubre "saltarme un riego" y no deja huérfanos a 104. *Descartado:* borrado (backlog si se pide).
- **D3 — Una entrada no puede quedar en el pasado al crearla ni al cambiar su fecha u hora.** *Por qué:* su recordatorio saldría al instante y no avisaría de nada. *Descartado:* aceptarlas y recordarlas tarde (queda para entradas que vencen con el sistema apagado, 104).
- **D4 — Una sola zona horaria para todo el sistema, configurable: la hora local del invernadero.** *Por qué:* la base guarda fecha y hora sin zona (002 D3) y el brief describe un solo invernadero. *Costo:* personas en otra zona verían horas corridas (backlog).
- **D5 — Se permiten entradas repetidas** (misma fecha y hora). *Por qué:* no hay riesgo, y prohibirlas obligaría a decidir qué hacer con las inactivas.
- **D6 — Los RF se numeran como la tabla de requerimientos del brief (RF1–RF7).** *Por qué:* las fichas de detalle del brief saltan de RF4 a RF6 y numeran RF6–RF8 lo que la tabla llama RF5–RF7 (registro histórico, crear base, tiempo real); además la ficha RF8 repite por error la descripción de RF7 de la base de datos. Se sigue la tabla. Esta decisión rige para todos los specs 1xx.

### Taken while building

- **D7 — FR-3.d: un cambio con fecha, hora o estado vacíos o inválidos se rechaza** (round 1; aceptado por la persona dueña, 2026-11-17). *Por qué:* FR-1.c lo cubría al crear pero ningún bullet al cambiar; sin el rechazo, un `null` llegaría a una columna obligatoria y respondería con error de servidor.
- **D8 — FR-3.b dice "modifica la fecha o la hora" en vez de "deja la fecha y la hora"** (round 2, T06; la persona dueña aprobó el comportamiento el 2026-11-17). *Por qué:* leída al pie de la letra, la versión anterior rechazaba también desactivar una entrada vencida, que la introducción de FR-3 y D3 permiten; y reenviar la entrada completa sin cambiar fecha ni hora no es cambiarlas.
- **Rechazada (round 1): dependencia `tzdata` y validar `TIMEZONE` al cargar** (era T07; la persona dueña no la quiere, 2026-11-17). *Costo conocido:* en Windows Python no trae base de zonas horarias, y con una zona inexistente crear o cambiar una entrada responde con error de servidor.
