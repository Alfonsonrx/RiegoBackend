# Backlog — trabajo conocido y aún sin especificar

Cuando se escribe la spec de un ítem, se borra de aquí. Cada ítem dice de dónde viene y qué spec lo
tocaría. Las specs 001–002 (as-built) y 101–104 (nuevas, `draft`) ya cubren RF1–RF7 del brief; esto es
lo que **no** cubren.

## Entregables del brief que no son código de este repo
- **Pruebas de funcionamiento documentadas** (brief: "diseñar, ejecutar y documentar pruebas") — se
  derivan de las tablas de casos de plan §5 de cada spec; falta redactar el documento. Dueño: sin dueño.
- **Evaluación de complejidad y viabilidad técnica** (Industria 4.0: sensores y microcontroladores) —
  documento de la entrega, no una spec. Dueño: sin dueño.

## Fuera del backend
- **Interfaz web** (calendario, "Datos en tiempo real", lista de notificaciones, "Conectar sensores" con
  instrucciones si la conexión falla — RF1, RF3, RF7 del brief): otro repo/entrega. Las specs 101–104
  fijan lo que la API le ofrece.
- **Firmware del microcontrolador y emparejamiento Bluetooth/Wi-Fi** (RF3): el backend solo registra el
  sensor y recibe lecturas con su clave (102, 103). Un spec de protocolo del dispositivo (formato,
  reintentos, lecturas acumuladas sin conexión con hora propia) se escribe cuando exista el firmware.

## Backend, diferido a propósito
- **Calendario recurrente** (días de la semana + hora; brief RF1 dice "días y horas"): hoy 101 define
  entradas de fecha y hora únicas (101 D1). Tocaría 101 y 104.
- **Borrar entradas de calendario y sensores**: hoy se desactivan (101 D2, 102 D5).
- **Más tipos de sensor y de conexión** (humedad del sustrato, LoRa — los comentarios del modelo los
  mencionan, el brief no): hoy 102 D1 acepta humedad y temperatura por Wi-Fi o Bluetooth.
- **Canales de notificación fuera de la app** (push, correo): hoy solo lista dentro de la app (104 D1).
- **Actualización en vivo** (WebSocket/SSE) para "tiempo real" (RF7): hoy es la última lectura por
  consulta (103 D3).
- **Marcar todas las notificaciones leídas / borrarlas / paginarlas** (104 D4).
- **Aviso de "volvió al rango"** y **aviso de sensor sin señal** (104 §7).
- **Política de contraseñas, recuperación de contraseña, verificación de correo, cierre de sesión con
  revocación, refresco de token, edición de perfil** (001 §7).
- **Roles / administración**: sin dueño.
- **Zona horaria por usuario / varios invernaderos** (101 D4).
- **Agregados para gráficos** (promedio por hora/día) y **política de retención/purga** de lecturas (103 §7).
- **CORS y despliegue** (la interfaz web vive en otro origen): sin dueño.
- **CI** (no hay workflow): sin dueño.
- **passlib con bcrypt 4.x registra `module 'bcrypt' has no attribute '__about__'`** al hashear (funciona, pero ensucia el registro; passlib no tiene mantenimiento) · source: 101 review · target: → 001 (usar `bcrypt` directo o fijar una versión compatible).
