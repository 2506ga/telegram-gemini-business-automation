# MVP — Gestión por Telegram + Gemini + SQLite

Primera versión funcional para demostrar un sistema de gestión conversacional.

## Qué hace

Un empleado puede escribir en Telegram:

- `Vendimos $185.000 en el bar`
- `Compré bebidas para el bar por 90 mil`
- `Evento López: cobré 850 mil y gasté 510 mil`
- `Reserva de Juan Pérez para 8 personas, confirmada, seña 120 mil`

Gemini interpreta el mensaje y el bot muestra una confirmación antes de guardar.

Después se puede preguntar:

- `¿Cuánto vendimos hoy?`
- `¿Cuál fue el margen del evento López?`
- `¿Cuánto gastamos hoy en el bar?`
- `¿Cuántas reservas confirmadas tenemos hoy?`

Los números se calculan desde SQLite; Gemini no "recuerda" los importes ni inventa la respuesta.

---

## Arquitectura

Telegram
↓
Python / python-telegram-bot
↓
Gemini API (interpretación)
↓
SQLite (fuente real de datos)
↓
Python calcula los resultados
↓
Gemini redacta la respuesta
↓
Telegram

---

## 1. Requisitos

- Windows 10/11
- Python 3.11 o superior recomendado
- Telegram
- Token de BotFather
- API key de Google AI Studio

---

## 2. Crear el bot de Telegram

En Telegram:

1. Buscar `@BotFather`.
2. Enviar `/newbot`.
3. Elegir un nombre.
4. Elegir un username terminado en `bot`.
5. BotFather entrega un token.

Ejemplo:

`123456789:AA...`

No publiques ese token.

---

## 3. Obtener la API Key de Gemini

Entrar a Google AI Studio y generar una Gemini API key.

La variable se llama:

`GEMINI_API_KEY`

El proyecto usa por defecto:

`gemini-3.8-flash`

El modelo se puede cambiar sin tocar código desde `.env`.

---

## 4. Abrir en VS Code

Abrí la carpeta completa:

`gestion_telegram_gemini_mvp`

Después abrí una terminal en VS Code.

### Crear entorno virtual

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

CMD:

```bat
python -m venv .venv
.venv\Scripts\activate
```

### Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## 5. Configurar `.env`

Copiar:

`.env.example`

y renombrarlo a:

`.env`

Completar:

```env
TELEGRAM_BOT_TOKEN=TOKEN_DE_BOTFATHER
GEMINI_API_KEY=API_KEY_DE_GOOGLE
GEMINI_MODEL=gemini-3.8-flash
ALLOWED_TELEGRAM_USERS=
```

Para la primera prueba podés dejar `ALLOWED_TELEGRAM_USERS` vacío.

Después conviene limitarlo a IDs autorizados.

---

## 6. Ejecutar

```bash
python bot.py
```

Deberías ver:

```text
ASISTENTE DE GESTIÓN - MVP
Modelo Gemini: gemini-3.8-flash
Base de datos: gestion.db
Bot iniciado.
```

Abrí Telegram y enviá al bot:

`/start`

---

## 7. Demo rápida

Mandá:

`/demo`

Carga tres registros ficticios.

Después preguntá:

`¿Cuál fue el margen del evento López?`

Con los datos de prueba:

- Facturación: $850.000
- Costos: $510.000
- Resultado: $340.000
- Margen: 40%

También:

`¿Cuánto vendimos hoy?`

---

## 8. Seguridad básica

En Telegram mandá:

`/id`

El bot devuelve tu Telegram ID.

En `.env` podés configurar:

```env
ALLOWED_TELEGRAM_USERS=123456789,987654321
```

Solo esas personas podrán operar.

---

## 9. Base de datos

Se crea automáticamente:

`gestion.db`

Tabla principal:

`operations`

Campos principales:

- fecha
- tipo de operación
- unidad de negocio
- categoría
- importe
- costo
- evento
- cliente
- cantidad de personas
- estado de reserva
- medio de pago
- notas
- usuario de Telegram

---

## 10. Próximas etapas recomendadas para Codex

### Etapa 2
- Roles: empleado / encargado / administrador.
- Corrección de operaciones.
- Eliminar/anular registros.
- Auditoría.
- Reportes diarios automáticos.
- Mejores filtros por fecha.
- Categorías configurables.

### Etapa 3
- Dashboard web.
- FastAPI.
- PostgreSQL.
- Login.
- Gráficos.
- Gestión de caja.
- Proveedores.
- Inventario.
- Reservas.
- Eventos.

### Etapa 4
- Deploy permanente.
- Backups.
- HTTPS.
- Logs.
- Monitoreo.
- Integraciones externas.
- Eventualmente WhatsApp Business API.

---

## Diseño importante

Gemini NO es la base de datos.

Gemini interpreta:

`"Compré bebidas para el bar por 185 mil"`

y lo transforma en datos.

SQLite almacena esos datos.

Cuando alguien pregunta:

`"¿Cuál fue el margen del evento López?"`

Python consulta SQLite y calcula el resultado.

Gemini solamente presenta esos resultados en lenguaje natural.

Esto evita que la IA invente números financieros.

---

# V2 — Dashboard web de gestión

Esta versión incorpora un dashboard profesional que utiliza exactamente la misma base `gestion.db` que el bot de Telegram.

## Ejecutar solo el dashboard

```bash
python dashboard.py
```

Abrir:

```text
http://127.0.0.1:5050
```

El dashboard puede iniciarse incluso antes de configurar Telegram o Gemini.

## Ejecutar bot + dashboard juntos

Una vez configurado `.env`:

```bash
python run_all.py
```

Esto levanta:

- Dashboard web: `http://127.0.0.1:5050`
- Bot de Telegram en polling

## Qué incluye el dashboard

### Resumen ejecutivo

- Ingresos del período.
- Costos del período.
- Resultado y margen.
- Reservas y reservas confirmadas.
- Comparación contra el período anterior equivalente.
- Evolución diaria de ingresos y costos.
- Rentabilidad por Bar, Salón y Catering.
- Rentabilidad por evento.
- Últimos movimientos.

### Filtros globales

- Desde / hasta.
- Unidad de negocio.
- Tipo de movimiento.

### Operaciones

La pantalla `Operaciones` permite:

- Consultar hasta 250 movimientos.
- Buscar por evento, cliente, categoría o notas.
- Filtrar por período, unidad y tipo.
- Cargar manualmente una operación.
- Eliminar una operación.
- Identificar si el registro provino de Telegram o del dashboard.

## Criterio de diseño

El panel está deliberadamente construido con pocas superficies visuales grandes en lugar de una pared de tarjetas.

Principios utilizados:

- navegación lateral contenida;
- una sola banda de KPIs;
- un gráfico principal;
- tablas como interfaz operativa principal;
- filtros globales y consistentes;
- jerarquía tipográfica fuerte;
- color usado principalmente para estados y significado;
- responsive para notebook, tablet y celular.

## Estructura V2

```text
gestion_telegram_gemini_mvp/
│
├── bot.py
├── dashboard.py
├── run_all.py
├── database.py
├── gemini_service.py
├── config.py
├── requirements.txt
├── .env.example
│
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   └── operations.html
│
└── static/
    ├── app.css
    └── app.js
```

## Nota sobre gráficos

El dashboard utiliza Chart.js desde CDN para la gráfica de evolución. El resto de la interfaz funciona sin ese recurso; si después querés un despliegue completamente offline, Codex puede descargar y servir Chart.js localmente desde `/static/vendor/`.

## Próxima evolución sugerida

Para una versión comercial/producción:

1. autenticación;
2. roles y permisos;
3. edición y anulación con auditoría en vez de borrado físico;
4. cajas y cierres;
5. cuentas por cobrar;
6. proveedores e inventario;
7. PostgreSQL;
8. backups;
9. API FastAPI o Flask modular;
10. dashboard de rentabilidad avanzada y conciliación.

## Acceso y publicación

El dashboard ahora requiere inicio de sesión y usa la identidad visual de Ponte Pilar. Las credenciales se configuran con `DASHBOARD_USERNAME` y `DASHBOARD_PASSWORD_HASH` (recomendado) o `DASHBOARD_PASSWORD` para pruebas locales.

La guía completa para publicar el dashboard y el bot está en `../GUIA_PRODUCCION.md`. El archivo `../render.yaml` deja preparado un servicio de Render con HTTPS, health check y disco persistente para SQLite.
