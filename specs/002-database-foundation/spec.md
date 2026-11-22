# 002 — Base de datos y fundamentos

Status: as-built · Depends on: ninguno

## 1. Context and objective

El brief exige que el prototipo "esté conectado con una base de datos" para guardar los datos
ambientales históricos (RF6 en la tabla de requerimientos; la ficha de detalle lo numera RF7, "Crear
base de datos"). Este spec documenta lo que ya existe como base de todo lo demás: un almacén relacional
duradero, la estructura de cinco tipos de registro creada por migraciones versionadas, una forma de preguntar si la
base responde y la lectura de su conexión desde el entorno.

Solo las cuentas (001) usan hoy el almacén de punta a punta. Los otros cuatro tipos de registro tienen
estructura pero ningún lector ni escritor (§10); 101–104 los terminan.

**Objective:** que el sistema tenga un almacén duradero, con su estructura creada por migraciones, cuyo estado se pueda consultar y cuyas credenciales no estén en el código.

## 2. Users

| Usuario | Relación con esta capacidad |
|---|---|
| Persona desarrolladora | Aplica las migraciones con un comando, arranca el sistema y espera que la conexión salga del entorno. |
| Persona que opera el sistema | Consulta si la base responde antes de culpar a otra cosa. |
| Cultivador/a | No lo ve, pero depende de que sus datos sobrevivan a un reinicio. |

## 3. User stories

- Como desarrollador/a, quiero crear o actualizar la estructura de la base con un solo comando, para no prepararla a mano.
- Como operador/a, quiero preguntar si la base responde, para distinguir una caída de la base de un fallo del sistema.
- Como cultivador/a, quiero que mis datos sigan ahí tras un reinicio, para que el historial no se pierda.

## 4. Functional requirements

### FR-1 — Almacén duradero (RF6)
Los cinco tipos de registro (cuentas, sensores, lecturas, entradas de calendario y notificaciones) viven
en una base relacional separada del proceso, para que un reinicio no los pierda. La estructura la crean y
la cambian migraciones versionadas que se aplican con un comando; arrancar no la toca.
- (a) The system shall conservar cada registro guardado tras un reinicio del sistema.
- (b) WHEN se aplican las migraciones y falta la estructura de cuentas, sensores, lecturas, entradas de calendario o notificaciones, the system shall crear la estructura que falte.
- (c) WHEN se aplican las migraciones y la estructura ya existe, the system shall dejar sin cambios los registros guardados.
- (d) WHEN el sistema arranca, the system shall dejar sin cambios la estructura de la base.

### FR-2 — Estado de la base de datos
Una consulta pública y mínima dice si la base responde, sin exigir cuenta, para que pueda usarla un
monitor externo.
- (a) WHEN se consulta el estado de la base, the system shall responder que la base está en orden después de ejecutar con éxito una consulta mínima contra el almacén.
- (b) IF el almacén no responde, THEN the system shall no responder que la base está en orden.
- (c) The system shall responder a la consulta de estado sin exigir token.

### FR-3 — Conexión desde el entorno
Servidor, puerto, nombre, usuario y contraseña de la base salen de la configuración del entorno, no del
código ni de los specs.
- (a) The system shall tomar el servidor, el puerto, el nombre, el usuario y la contraseña de la base de la configuración del entorno.

## 5. Non-functional requirements

- **Security:** ninguna credencial de la base aparece en respuestas, registros ni specs; el estado de la base no revela nada más que "en orden".
- **Isolation:** no aplica a este spec (no hay registros de usuario propios).
- **Language:** la respuesta de estado es técnica y no se traduce.
- **Traceability:** FR-1 sirve a RF6 del brief (ficha "RF7 Crear base de datos"); RF5 y RF7 usan el almacén vía 103.
- **Data retention:** aplicar las migraciones no borra registros (FR-1.c); arrancar no toca la estructura (FR-1.d).

## 6. Edge cases

| Situación | Comportamiento esperado |
|---|---|
| La base está caída al arrancar | El sistema arranca igual (arrancar no se conecta); cada operación que usa la base falla con error de servidor y la consulta de estado no dice "en orden". |
| La base se cae con el sistema ya en marcha | La consulta de estado deja de decir "en orden" (FR-2.b); las demás operaciones fallan con error de servidor. |
| Falta el usuario o la contraseña de la base, o están vacíos | El sistema no arranca: el mensaje nombra el ajuste que falta y no muestra ningún valor. Servidor, puerto y nombre tienen valores de desarrollo por defecto. |
| Una tabla existe pero le falta una columna nueva | La migración que trae la columna la añade al aplicar las migraciones. |
| Dos aplicaciones de migraciones a la vez sobre una base vacía | La estructura se crea dentro de una transacción: una termina y la otra falla sin dejar nada a medias. |
| Se arranca sin haber aplicado las migraciones | El sistema arranca; la primera operación que usa una tabla falla con error de servidor; la consulta de estado sigue diciendo "en orden" porque solo prueba la conexión. |

## 7. Out of scope

- Aplicar las migraciones solas al arrancar o al desplegar — sin dueño (hoy es un paso manual del README, D6).
- Copias de seguridad y recuperación — sin dueño.
- Política de retención y purga de lecturas — `specs/backlog.md`.
- Dónde se aloja la base (servicio gestionado) — sin dueño.
- Qué datos guarda cada tipo de registro y cómo se usan: cuentas, 001; calendario, 101; sensores, 102; lecturas, 103; notificaciones, 104.

## 8. Completion criteria

El spec se cumple cuando:
- tras crear una cuenta y reiniciar, la cuenta sigue guardada;
- aplicar las migraciones sobre una base vacía crea las cinco estructuras, aplicarlas de nuevo no cambia ningún registro y arrancar no toca la estructura;
- la consulta de estado responde "en orden" con la base arriba y no lo responde con la base inalcanzable, sin token en ambos casos;
- la conexión se configura solo con el entorno y no queda ninguna contraseña por defecto en el código;
- las desviaciones de §10 están cerradas o aceptadas por la persona dueña.

## 9. Open questions

None.

## 10. Decisions taken

- **D1 — Una sola base relacional para todos los tipos de registro.** *Por qué:* las lecturas, el calendario y las notificaciones se relacionan con la cuenta dueña; separar almacenes obligaría a juntar datos a mano.
- **D2 — La consulta de estado es pública** (regla 2 del perfil). *Por qué:* un monitor externo no tiene cuenta; la respuesta solo dice "en orden".
- **D3 — Los instantes se guardan con zona horaria; la fecha y la hora de riego del calendario no** (se interpretan en la zona del invernadero, 101 D4). *Por qué:* un instante de lectura es un punto en el tiempo; "regar el 20 a las 08:00" es hora de pared.
- **D4 — La base de pruebas es otra base de la misma clase, no una de juguete** (plan 002 D4). *Por qué:* las claves numéricas largas se comportan distinto en bases de juguete y las pruebas dejarían de probar lo que corre.
- **D5 — La estructura de referencia es la de la base real** (creada a mano antes del código, igual al diagrama de la persona dueña): borrar una cuenta o un sensor borra en cascada lo que depende de él, seis índices de apoyo, y la fecha de creación de cuentas y notificaciones nunca vacía. Los modelos y la revisión base de migraciones la reproducen exactamente (2026-11-16, aprobado por la persona dueña). *Por qué:* la base real ya estaba marcada en esa revisión; si el código difería, la siguiente migración generada habría quitado las cascadas y los índices. Ninguna ruta borra cuentas ni sensores (102 D5), así que la cascada solo actúa en borrados manuales.
- **D6 — La estructura la crean y la cambian solo las migraciones; arrancar no la toca, y aplicarlas es un paso manual documentado en el README** (2026-11-16, aprobado por la persona dueña; reescribe FR-1.b y FR-1.c, que decían "WHEN el sistema arranca", y añade FR-1.d). *Por qué:* con la creación al arrancar, una base nueva quedaba sin versión y la primera migración posterior fallaba; migrar al arrancar exigiría al sistema permisos para cambiar la estructura y abriría carreras entre instancias.

### Known deviations

1. ~~**Las tablas se crean al importar la aplicación y no hay migraciones.**~~ Cerrada en T07–T08 (D6). Importar el módulo principal ya toca la base (también en pruebas) y una tabla existente nunca recibe columnas nuevas; el gestor de migraciones está instalado pero sin configurar. Contra la regla 5; afecta FR-1.b, FR-1.c y a 101–104 (que añaden columnas). → T07, T08.
2. **Cuatro tipos de registro sin uso:** sensores, lecturas, entradas de calendario y notificaciones tienen estructura pero nada los lee ni los escribe, y los cuatro módulos de rutas correspondientes están vacíos. Sin FR (no funcionan de punta a punta). → T11 (seguimiento hasta que 101–104 estén construidos).
3. ~~**Credenciales por defecto en el código:**~~ Cerrada en T09. si falta usuario o contraseña, se usan valores de desarrollo; tampoco hay una lista de ajustes de ejemplo. Contra la regla 3; afecta FR-3.a. → T09.
4. **Restos sin uso** en el módulo principal (importaciones y un contexto de hash duplicado). Sin FR. → T10.
5. **Sin pruebas ni CI**, y la herramienta de pruebas no está en las dependencias. → T05, T06.
