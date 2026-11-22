# 001 — Cuentas y autenticación

Status: as-built · Depends on: `002-database-foundation`

## 1. Context and objective

Todo lo que el sistema guarda (sensores, calendario, notificaciones) pertenece a una persona
cultivadora; sin saber quién pide, no hay forma de mostrarle solo lo suyo. Este spec documenta lo que
hoy existe en el árbol de trabajo: crear una cuenta, iniciar sesión para obtener un token de acceso y
resolver ese token a una cuenta en cada operación protegida. Hoy esa cadena **no corre de punta a punta**
(§10, *Known deviations*): el spec fija la regla que el sistema pretende, no el estado roto.

**Objective:** que una persona pueda registrarse, iniciar sesión y que cada operación protegida actúe
siempre en nombre de la cuenta correcta y de ninguna otra.

## 2. Users

| Usuario | Relación con esta capacidad |
|---|---|
| Visitante | Aún sin cuenta o sin sesión: puede registrarse e iniciar sesión, nada más. |
| Cultivador/a | Titular de una cuenta: se identifica con su token en cada operación protegida. |
| Operaciones de otros specs | Piden "la cuenta actual" para filtrar y asignar propiedad (001 FR-3). |

## 3. User stories

- Como visitante, quiero crear una cuenta con mi correo y una contraseña, para tener mi propio invernadero en el sistema.
- Como cultivador/a, quiero iniciar sesión con mi correo y contraseña, para recibir un token que me identifique.
- Como cultivador/a, quiero que el sistema rechace un token vencido o ajeno, para que nadie actúe en mi nombre.

## 4. Functional requirements

### FR-1 — Registro de cuenta
Una cuenta es un nombre, un correo único y una contraseña. El correo es el identificador de acceso, así
que no puede repetirse. La contraseña nunca se guarda ni se devuelve en claro: una filtración de la base
no debe revelar contraseñas.
- (a) WHEN un visitante envía un nombre, un correo sin cuenta y una contraseña, the system shall crear la cuenta.
- (b) WHEN se crea una cuenta, the system shall responder con su id, nombre, correo y fecha de creación.
- (c) The system shall omitir la contraseña y su hash en toda respuesta.
- (d) The system shall guardar la contraseña únicamente como hash de un solo sentido con sal.
- (e) IF ya existe una cuenta con el mismo correo, THEN the system shall rechazar el registro con el mensaje "El email ya está registrado" y dejar las cuentas guardadas sin cambios.
- (f) IF el correo enviado no es una dirección válida, THEN the system shall rechazar el registro y no crear ninguna cuenta.
- (g) IF ya existe una cuenta cuyo correo coincide con el enviado sin distinguir mayúsculas de minúsculas, THEN the system shall rechazar el registro con el mensaje "El email ya está registrado".

### FR-2 — Inicio de sesión
Iniciar sesión cambia correo y contraseña por un token con vencimiento. Cuando falla, el mensaje no
distingue "correo desconocido" de "contraseña errónea", para no revelar qué correos tienen cuenta.
- (a) WHEN un visitante envía el correo y la contraseña de una cuenta existente, the system shall responder con un token de acceso de tipo bearer.
- (b) The system shall hacer que cada token de acceso identifique a su cuenta y venza tras los minutos definidos en la configuración.
- (c) IF el correo enviado no corresponde a ninguna cuenta, THEN the system shall rechazar el inicio de sesión con el mensaje "Email o contraseña incorrectos".
- (d) IF la contraseña enviada no coincide con la de la cuenta, THEN the system shall rechazar el inicio de sesión con el mensaje "Email o contraseña incorrectos".

### FR-3 — Cuenta actual en operaciones protegidas
Toda operación protegida (001 no define ninguna; 101–104 sí) pide la cuenta actual al mismo lugar, para
que ninguna operación decida por su cuenta qué token acepta.
- (a) WHEN una petición a una operación protegida trae un token vigente de una cuenta existente, the system shall ejecutar la operación en nombre de esa cuenta.
- (b) IF una petición a una operación protegida no trae token, THEN the system shall rechazarla como no autenticada.
- (c) IF el token está mal formado, vencido, firmado con otra clave o no lleva id de cuenta, THEN the system shall rechazar la petición con el mensaje "No se pudo validar las credenciales".
- (d) IF la cuenta que nombra el token ya no existe, THEN the system shall rechazar la petición con el mensaje "No se pudo validar las credenciales".

### FR-4 — Ver mi cuenta
La interfaz necesita saber quién inició sesión (la cabecera muestra la inicial del nombre) y el inicio de
sesión solo devuelve el token. La persona consulta su propia cuenta con el token; sin token o con uno
inválido rige FR-3, y la contraseña nunca sale (FR-1.c). Agregado después del as-built (D6). Sirve a
ningún RF directamente: apoya la interfaz de RF1–RF7.
- (a) WHEN un usuario autenticado pide su cuenta, the system shall responder con su id, nombre, correo y fecha de creación.

## 5. Non-functional requirements

- **Security:** contraseñas con hash de un solo sentido con sal; tokens firmados con una clave de la configuración; ningún secreto en respuestas, registros ni specs; mismo mensaje para correo desconocido y contraseña errónea.
- **Isolation:** este spec solo entrega la identidad; el filtro por dueño lo aplica cada operación (regla 1 del perfil).
- **Language:** los mensajes de error visibles para la persona están en español, tal como se citan arriba.
- **Traceability:** el brief no tiene un RF de cuentas; este spec sostiene los RF1–RF7 al dar dueño a cada registro (regla 4 del perfil: sin RF propio).
- **Data retention:** registrarse nunca modifica ni borra cuentas existentes.

## 6. Edge cases

| Situación | Comportamiento esperado |
|---|---|
| Dos registros simultáneos con el mismo correo | Uno crea la cuenta; el otro recibe "El email ya está registrado" (hoy falla: §10 desviación 5). |
| Correo con otras mayúsculas ("Ana@example.com" vs "ana@example.com") | Se trata como el mismo correo (FR-1.g; hoy no se cumple). |
| Contraseña vacía o muy corta | Hoy se acepta; sin regla definida (backlog: política de contraseñas). |
| Token con id de cuenta que no es numérico | Rechazado con "No se pudo validar las credenciales". |
| Token de una cuenta recién borrada | Rechazado (FR-3.d). Hoy no hay forma de borrar cuentas. |
| Correo y contraseña correctos, pero cuenta en otra base | No aplica: una sola base (002). |

## 7. Out of scope

- Recuperación de contraseña, verificación de correo, política de contraseñas, edición de perfil, cierre de sesión con revocación, refresco de token — `specs/backlog.md`.
- Roles y administración — sin dueño.
- Listado de todas las cuentas: existe a medias en el código y viola las reglas 1 y 2; no es requisito (§10 desviación 2).
- El filtro por dueño de cada recurso — specs 101–104.

## 8. Completion criteria

El spec se cumple cuando:
- un visitante se registra y recibe id, nombre, correo y fecha, sin contraseña ni hash;
- el mismo correo (con cualquier combinación de mayúsculas) no se registra dos veces, ni siquiera en peticiones simultáneas;
- un correo inválido no crea cuenta;
- iniciar sesión devuelve un token que vence, y los fallos usan un único mensaje;
- cada fallo de token de FR-3 se rechaza con el mensaje indicado;
- las desviaciones de §10 están cerradas o aceptadas por la persona dueña.

## 9. Open questions

None.

## 10. Decisions taken

- **D1 — Token sin estado.** El token lleva la cuenta y el vencimiento; no hay sesiones en el servidor. *Por qué:* la API es de un prototipo con una sola instancia y no necesita revocar. *Costo:* no hay cierre de sesión real hasta que venza (backlog).
- **D2 — El correo es el identificador de acceso** y es único. *Por qué:* el brief habla de "el usuario" sin más datos; el correo evita inventar nombres de usuario.
- **D3 — Un solo mensaje para correo desconocido y contraseña errónea.** *Por qué:* decir cuál falló permite averiguar qué correos están registrados.
- **D4 — Rechazo por correo duplicado con código 400 y mensaje en español, tal como está hoy.** *Descartado:* 409 (más convencional); se mantiene el comportamiento existente para no cambiar a quien ya lo consume.
- **D5 — Los correos se comparan sin distinguir mayúsculas** (FR-1.g). *Por qué:* es lo que cualquier persona espera de un correo; hoy la base distingue y es una desviación, no una decisión de producto.

- **D6 — Consulta de la cuenta propia (FR-4), agregada el 2026-11-19 a pedido de la sesión del frontend (CalendarioOrquideas), que informó la aprobación de la persona dueña.** *Por qué:* la cabecera del rediseño muestra la inicial del nombre y ninguna ruta decía quién inició sesión. *Descartado:* meter el nombre en el token (cambiaría FR-2.b y quedaría viejo si el nombre cambiara).

### Known deviations

El código actual no cumple estas reglas; ninguna se corrige en este spec (tasks §C):

1. **Falta el módulo de configuración** del que dependen la emisión y la validación de tokens: ni el inicio de sesión ni FR-3 pueden cargarse. Rompe FR-2.a, FR-2.b, FR-3.a–d. → T08.
2. **El router de auth no se puede importar** (usa nombres que no define) y expone un listado de todas las cuentas sin autenticar, contra las reglas 1 y 2. Sin FR: es código a medias. → T09.
3. **Ninguna ruta de auth está montada** en la aplicación: registro e inicio de sesión no son alcanzables. Rompe FR-1, FR-2. → T10.
4. **El correo no se valida** al registrar (se acepta cualquier texto) y la librería de validación no está instalada; además el esquema de login y el de datos del token usan nombres sin importar y nadie los usa. Rompe FR-1.f. → T11.
5. **La unicidad del correo distingue mayúsculas** y un registro simultáneo duplicado termina en error no controlado en vez del mensaje. Rompe FR-1.e (en carrera), FR-1.g. → T12.
6. **Sin pruebas.** Ningún bullet tiene prueba citada. → T14.
