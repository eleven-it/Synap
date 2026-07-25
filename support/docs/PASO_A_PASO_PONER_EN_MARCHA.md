# Paso a paso: poner en marcha Support

Guía para tener el backend (Django), el frontend (React) y la **configuración por UI** funcionando.

**Support es independiente de Synap (ERP):** su stack se levanta solo (no comparte Docker con Synap). **Un solo archivo de variables:** `support/.env` (backend, Docker y frontend lo usan). Synap: `docker compose up -d` desde la raíz. Support: `cd support && docker compose -f docker/docker-compose.yml up -d` o desde raíz con `-f docker-compose.support.yml -p support --env-file support/.env`. Ver [§ 7](#7-levantar-todo-con-docker-compose).

**Dos formas de arrancar Support:**

1. **Con Docker** (recomendado): todo el stack desde `support/` usando el único `.env` en `support/.env`; backend en **http://localhost:8250**, frontend opcional en 3000. Ver [§ 7](#7-levantar-todo-con-docker-compose).
2. **Sin Docker**: backend y frontend en local; mismo `support/.env`; backend en **http://localhost:8000**, frontend en 3000. Ver [§ 3](#3-backend-django) y [§ 4](#4-frontend-react).

---

## 1. Requisitos previos

- **Python 3.10+** (backend)
- **Node.js 18+** y **npm** (frontend)
- **PostgreSQL 14+** con extensión **pgvector**
- **Redis** (para Celery y cache; en desarrollo se puede usar sin Celery al principio)

Si usas Docker para el resto del proyecto Synap, puedes tener Postgres y Redis en contenedores; el backend puede correr fuera del contenedor apuntando a esos servicios.

---

## 2. Base de datos PostgreSQL

Crear base de datos y usuario (o usar los que ya tengas):

```bash
# Ejemplo con psql (ajusta usuario/contraseña)
createdb support
# Si hace falta crear el rol:
# createuser -P support   # y elegir contraseña
```

Habilitar la extensión **pgvector** (necesaria para RAG):

```sql
-- Conectar a la base 'support' y ejecutar:
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## 3. Backend (Django)

### 3.1 Entorno e instalación

```bash
cd support/backend
python -m venv .venv
source .venv/bin/activate   # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3.2 Variables de entorno

Support usa **un solo .env** en la raíz de Support (no en backend/ ni en docker/):

```bash
cd support
cp .env.example .env
```

Editar `support/.env` y asegurarse de tener al menos:

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `SECRET_KEY` | Clave Django (producción: string largo aleatorio) | `change-me-in-production-use-long-random-string` |
| `DATABASE_URL` | URL de PostgreSQL | `postgres://support:support@localhost:5432/support` |
| `REDIS_URL` | Redis (Celery/cache) | `redis://localhost:6379/0` |
| `CONFIG_ENCRYPTION_KEY` | **Obligatoria para la configuración por UI**: cifra tokens y API keys en la base de datos | Ver paso siguiente |
| `DJANGO_SETTINGS_MODULE` | Módulo de settings | `config.settings.local` |

### 3.3 Generar CONFIG_ENCRYPTION_KEY

Sin esta clave, la configuración de canales/IA/storage no podrá guardar secretos de forma segura. Generar una y pegarla en `.env`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copiar la línea que imprime (ej. `dGhpc19pc19hX2V4YW1wbGVfa2V5Xz...`) y en `support/.env` poner:

```
CONFIG_ENCRYPTION_KEY=dGhpc19pc19hX2V4YW1wbGVfa2V5Xz...
```

### 3.4 Migraciones

```bash
export DJANGO_SETTINGS_MODULE=config.settings.local
python manage.py migrate
```

Deben aplicarse migraciones de todas las apps, incluidas `audit` (eventos de config) y `system_config`.

### 3.5 Usuario administrador y perfil

Crear un usuario de Django:

```bash
python manage.py createsuperuser
```

Introducir username, email (opcional) y contraseña.

Asignar **rol Admin** para poder usar la sección Configuración:

1. Iniciar el servidor (si no está ya): `python manage.py runserver 0.0.0.0:8000`
2. Ir a **http://localhost:8000/admin/**
3. Iniciar sesión con el superusuario
4. **Agentes** → **Perfiles de agente** → **Añadir**
5. Usuario: elegir el que creaste; **Rol**: **Administrador** → Guardar

### 3.6 Arrancar el backend

```bash
python manage.py runserver 0.0.0.0:8000
```

El API quedará en **http://localhost:8000**. Health: **http://localhost:8000/api/health/**  
*(Si usas Docker, el backend estará en el puerto **8250**; ver [§ 7](#7-levantar-todo-con-docker-compose).)*

*(Opcional más adelante: Celery worker y beat para tareas asíncronas y SLA.)*

---

## 4. Frontend (React)

En **otra terminal**, desde la **raíz del repositorio** (donde está la carpeta `support/`):

### 4.1 Instalación

```bash
cd support/frontend
npm install
```

El frontend lee las variables desde **support/.env** (Vite está configurado con `envDir: ..`). No hace falta `cp .env.example .env` en frontend si ya creaste `support/.env` en [§ 3.2](#32-variables-de-entorno).

### 4.2 Variables de entorno

En **support/.env** (único archivo):

- **Con Docker** (backend en 8250): `VITE_API_BASE_URL=http://localhost:8250`
- **Sin Docker** (backend en 8000): `VITE_API_BASE_URL=http://localhost:8000` o vacío si usas el proxy de Vite (en `vite.config.ts` el proxy apunta por defecto a 8250; para 8000 local, ajústalo).

### 4.3 Arrancar el frontend

```bash
npm run dev
```

La SPA suele quedar en **http://localhost:3000**.

### 4.4 Acceso por dominio (Nginx)

Para que el frontend y la API sean accesibles por un mismo dominio (p. ej. `https://support.tudominio.com`), se usa **Nginx** como reverse proxy: sirve los estáticos del build del frontend y reenvía `/api/` al backend.

**1. Build del frontend**

En la máquina donde esté el código (o en el servidor):

```bash
cd support/frontend
npm ci
npm run build
```

Se genera la carpeta `dist/`. Copiarla al servidor donde corre Nginx, por ejemplo en `/var/www/support`:

```bash
sudo mkdir -p /var/www/support
sudo cp -r dist/* /var/www/support/
sudo chown -R www-data:www-data /var/www/support
```

**2. Instalar Nginx y Certbot (Let's Encrypt)**

```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

**3. Configuración Nginx completa**

Crear el sitio (reemplazá `support.tudominio.com` por tu dominio):

```bash
sudo nano /etc/nginx/sites-available/support
```

Contenido del archivo:

```nginx
# Redirect HTTP → HTTPS
server {
    listen 80;
    server_name support.tudominio.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS: frontend estático + proxy /api al backend
server {
    listen 443 ssl http2;
    server_name support.tudominio.com;

    # Certificados (Let's Encrypt; paths típicos tras certbot)
    ssl_certificate     /etc/letsencrypt/live/support.tudominio.com/fullchain.pem;
    ssl_certificate_key  /etc/letsencrypt/live/support.tudominio.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;

    client_max_body_size 1M;

    root /var/www/support;
    index index.html;

    # API y webhooks → backend Django (puerto 8250)
    location /api/ {
        proxy_pass http://127.0.0.1:8250;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # SPA: el resto sirve index.html y estáticos
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**4. Activar el sitio y certificado**

```bash
sudo ln -s /etc/nginx/sites-available/support /etc/nginx/sites-enabled/
sudo nginx -t
```

Si aún no tenés certificado HTTPS, primero dejá solo el `server` que escucha en 80 (sin el bloque 443), ejecutá `sudo certbot --nginx -d support.tudominio.com` y luego completá el bloque 443 con las rutas que certbot indique (o las de arriba). Después:

```bash
sudo systemctl reload nginx
```

**5. Variables de entorno del backend**

Con frontend y API en el mismo dominio no hay CORS cross-origin. En **support/.env** definí:

```bash
ALLOWED_HOSTS=support.tudominio.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://support.tudominio.com
CORS_ALLOWED_ORIGINS=https://support.tudominio.com
```

El backend debe estar escuchando en **8250** (Docker o gunicorn). No es necesario exponer 8250 al exterior; Nginx hace `proxy_pass` a `127.0.0.1:8250`.

**6. Rebuild al actualizar el frontend**

Cada vez que cambies el frontend: `npm run build` y volvé a copiar `dist/*` a `/var/www/support`.

Documentación ampliada (VM en Proxmox, red, firewall): [PROXMOX_VM_CONFIG.md](PROXMOX_VM_CONFIG.md).

---

## 5. Probar el sistema

1. Abrir **http://localhost:3000** (frontend) en el navegador.
2. **Iniciar sesión** con el usuario al que asignaste rol **Administrador**.
3. **Crear al menos una empresa (ID Synap):** en el menú ir a **Empresas** y añadir una empresa con **ID Synap** (o prefijo) e idioma. Sin esta empresa creada, la configuración (IA, canales, etc.) y los casos pueden no tener ámbito asociado y la activación o los datos guardados no se reflejarán correctamente.
4. En el menú, ir a **Configuración** (solo visible para Admin).
5. Ahí puedes:
   - **Canales**: crear/editar configuración de Telegram, WhatsApp, Email (tokens se guardan cifrados; en pantalla se ven enmascarados).
   - **IA**, **RAG**, **Storage**, **Seguridad**, **Notificaciones**, **Branding**, **SLA**: ver y editar la configuración; los cambios se persisten en el backend.

**URLs de referencia:** Backend API → **http://localhost:8250** (Docker) o **http://localhost:8000** (runserver local). Frontend → **http://localhost:3000**.

Si al guardar o probar un canal no pasa nada, revisar que en **support/.env** esté definida **CONFIG_ENCRYPTION_KEY** y que hayas ejecutado **migrate**.

---

## 6. Resumen de comandos (sin Docker)

```bash
# --- Variables (una sola vez) ---
cd support
cp .env.example .env
# Editar .env: DATABASE_URL, CONFIG_ENCRYPTION_KEY (generar con el comando de abajo)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# --- Backend ---
cd support/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=config.settings.local
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000

# --- Frontend (otra terminal) ---
cd support/frontend
npm install
# VITE_API_BASE_URL y demás se leen de support/.env
npm run dev
```

Luego en **http://localhost:8000/admin/** → Perfiles de agente → asignar **Administrador** al usuario.  
Para **todo con Docker** (backend en 8250), ver [§ 7](#7-levantar-todo-con-docker-compose).

---

## 7. Levantar todo con Docker Compose

**Support es un producto independiente de Synap:** su stack (PostgreSQL, Redis, backend Django, opcional frontend) no comparte servicios ni red con Synap. **Un solo .env:** `support/.env` (backend, frontend y Compose lo usan).

**Opción A – Desde support/ (recomendado):** Compose usa por defecto `support/.env`.

```bash
cd support
cp .env.example .env
# Editar .env: CONFIG_ENCRYPTION_KEY (generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
docker compose -f docker/docker-compose.yml up -d
```

**Opción B – Desde la raíz del repo (solo Support, no levanta Synap):**

```bash
# Crear support/.env si no existe (cp support/.env.example support/.env)
docker compose -f docker-compose.support.yml -p support --env-file support/.env up -d
```

Para parar o bajar desde support/: `docker compose -f docker/docker-compose.yml down`. Desde la raíz: `docker compose -f docker-compose.support.yml -p support stop` o `... down`.

Queda el **backend en http://localhost:8250**. Crear superusuario (el flag `-it` es necesario para poder escribir usuario y contraseña en la terminal):

```bash
docker compose -f docker/docker-compose.yml exec -it backend python manage.py createsuperuser
```

*(Desde la raíz: `docker compose -f docker-compose.support.yml -p support exec -it support_backend python manage.py createsuperuser`.)*

Después: **http://localhost:8250/admin/** → **Agentes** → **Perfiles de agente** → **Añadir** → Usuario elegido, Rol **Administrador** → Guardar.

**Opcional – frontend en http://localhost:3000:**

```bash
docker compose -f docker/docker-compose.yml --profile dev up -d
```

En **support/.env** debe estar `VITE_API_BASE_URL=http://localhost:8250` para que el navegador llame al API correctamente.

Más detalle (perfiles `storage`, MinIO, comandos útiles): **[support/docker/README.md](../docker/README.md)**.

---

## 8. Relación con Synap (ERP)

Support **no** debe ejecutarse dentro del mismo Docker Compose ni contenedor que Synap. Para levantar solo Synap (ERP) usa desde la raíz: `docker compose up -d`. Para levantar solo Support usa `support/docker` (o desde raíz `docker compose -f docker-compose.support.yml -p support up -d`; el `-p support` es necesario para stop/down). Ambos stacks pueden coexistir en la misma máquina (puertos distintos: Synap 8000, Support 8250).

---

## 9. Activar el agente IA (copiloto)

Para que el **copiloto IA** en el detalle de caso responda con un modelo real (OpenAI) en lugar del mensaje stub:

1. Asegúrate de tener **al menos una empresa** creada (menú **Empresas**, con ID Synap / prefijo). Ver [§ 5](#5-probar-el-sistema).
2. Entra como usuario con rol **Administrador** y abre **Configuración** (menú o ruta de admin).
3. En la sección **IA** (o **Configuración** → **IA**):
   - **Proveedor:** `openai`
   - **Modelo:** p. ej. `gpt-4o-mini` o `gpt-4o`
   - **API key:** tu clave de API de OpenAI (se guarda cifrada con `CONFIG_ENCRYPTION_KEY`)
   - **Estado:** **Activo**
4. Guarda. El backend usa la primera configuración IA **activa** (por empresa si existe, si no la global).

El copiloto (panel en el detalle de caso o `POST /api/copiloto/mensaje/`) usará esa config para generar respuestas. Si no hay config activa o no hay API key, se muestra un mensaje indicando que hay que configurar IA en Configuración.

---

## 10. Canales (Telegram, WhatsApp, Email)

Si configurás un canal en **Django Admin** (Configuración del sistema → Configuraciones de canal), esa configuración se refleja en la UI de **Configuración** del frontend (card "Canales"). Ahí podés ver el estado real (No configurado, Validando, Activo, etc.) y usar **Probar** o el switch **Activo**.

**Para que el sistema use el canal**, el estado debe ser **Activo**, no "Validando". Si en Admin dejaste el canal en "Validando":

- Podés pasarlo a **Activo** desde la card **Canales** en Configuración (switch "Activo"), o  
- En Django Admin → editar la configuración del canal → **Estado**: elegir **Activo** → Guardar.

**Configurar el webhook del bot en Telegram:** Telegram debe saber a qué URL enviar las actualizaciones (mensajes). La URL tiene que ser **HTTPS** y **accesible desde internet** (no sirve `localhost`).

1. **Tené la URL pública del backend Support**, por ejemplo: `https://support.tudominio.com` (sin barra final). La ruta del webhook será: `https://support.tudominio.com/api/webhooks/telegram/`
2. **Llamá a la API de Telegram** para registrar esa URL (reemplazá `TU_BOT_TOKEN` y la URL por las tuyas):

   ```text
   https://api.telegram.org/bot<TU_BOT_TOKEN>/setWebhook?url=https://support.tudominio.com/api/webhooks/telegram/
   ```

   Podés abrir ese enlace en el navegador (si el token está en la URL, usá solo vos y no lo compartas) o con `curl`:

   ```bash
   curl "https://api.telegram.org/bot<TU_BOT_TOKEN>/setWebhook?url=https://support.tudominio.com/api/webhooks/telegram/"
   ```

   La respuesta en JSON debería tener `"ok": true`. Si `"ok": false`, revisá el mensaje en `description` (por ejemplo: URL no HTTPS, dominio no accesible, etc.).
3. **Para quitar el webhook** (dejar de recibir mensajes en Support):  
   `https://api.telegram.org/bot<TU_BOT_TOKEN>/deleteWebhook`
4. **Para ver la URL actual:**  
   `https://api.telegram.org/bot<TU_BOT_TOKEN>/getWebhookInfo`

El token del bot es el mismo que configuraste en **Configuración → Canales → Telegram** (token de BotFather). No hace falta configurar nada más en Support para el webhook; solo que el canal esté **Activo** y que la URL apunte a tu backend en producción o staging.

**Flujo del webhook de Telegram (chat conversacional):** cuando el canal Telegram está **Activo** y la **IA** está activa, el endpoint `/api/webhooks/telegram/` hace lo siguiente: (1) recibe el POST de Telegram, (2) extrae `message_id`, `chat.id` y el texto del mensaje (o de `edited_message`), (3) evita duplicados por `(telegram, message_id)`, (4) obtiene la primera config activa de Telegram y la empresa asociada (o la primera empresa si la config es global), (5) obtiene o crea un caso abierto para ese chat (`external_channel_id = chat_id`), (6) guarda el mensaje entrante en el caso, (7) genera la respuesta con el copiloto IA (`copilot_reply`), (8) envía la respuesta al chat con la API de Telegram (`sendMessage`), (9) guarda el mensaje saliente en el caso. Todo en la misma petición; la respuesta a Telegram es siempre 200 OK para no provocar reintentos. Para que el bot responda con IA, además del canal en **Activo** hace falta tener **Configuración → IA** en **Activo** con proveedor (p. ej. OpenAI) y API key.

**Qué hace el botón "Probar" (canales):** comprueba que la configuración del canal sea válida y que las credenciales funcionen. No activa el canal (eso es el switch "Activo").

- **Telegram:** llama a la API de Telegram (`getMe`) con el token del bot. Si el token es correcto, verifica el bot y muestra un mensaje tipo "Bot @nombre verificado". Si falta el token o es inválido, devuelve error.
- **WhatsApp:** valida el token/credenciales contra la API de Meta (Graph).
- **Email:** comprueba conexión SMTP (y opcionalmente IMAP) con host, usuario y contraseña configurados.

El resultado se muestra en un mensaje (éxito o error) y se actualizan "Última comprobación" y "Último error" en el backend; al refrescar la lista de canales esos datos se ven en la UI. Si en el backend está `ALLOW_EXTERNAL_TESTS=False`, la prueba no llama a servicios externos y devuelve "Estructura válida (test externo deshabilitado)".

---

## 11. Problemas frecuentes

| Síntoma | Qué revisar |
|---------|-------------|
| 403 al entrar a Configuración | Usuario debe tener **Perfil de agente** con rol **Administrador**. |
| Error al guardar config (canales, IA, etc.) | `CONFIG_ENCRYPTION_KEY` en **support/.env**; migraciones aplicadas (`system_config`, `audit`). |
| Frontend no conecta con el API | CORS en backend; `VITE_API_BASE_URL` acorde al puerto del backend (**8250** Docker, **8000** runserver local). |
| "Superuser creation skipped due to not running in a TTY" | Usar `docker compose exec -it backend python manage.py createsuperuser` (con `-it`). |
| Backend en Docker no conecta a la base | Variables de entorno: con `overwrite=False` en settings, el `DATABASE_URL` inyectado por el compose (host `db`) tiene prioridad sobre **support/.env**. Ver [support/backend/config/settings/base.py](../backend/config/settings/base.py). |
| La configuración guardada (IA, canales) no se ve al volver a Configuración | Crear **antes** al menos una **empresa** (menú **Empresas**) con su **ID Synap** / prefijo. Sin empresa, el ámbito de la configuración no queda bien definido. |
| `relation "support_company" does not exist` | Ejecutar `python manage.py migrate`. |
| pgvector no existe | En Postgres: `CREATE EXTENSION IF NOT EXISTS vector;` (y volver a ejecutar migrate si falló). |
| Copiloto responde "agente IA no está configurado" | Configuración → IA: proveedor `openai`, modelo, API key y estado **Activo**. Ver [§ 9](#9-activar-el-agente-ia-copiloto). |
| Canales en "Validando" o el bot no responde | El canal debe estar en estado **Activo**. Para que Telegram responda con IA, también **Configuración → IA** debe estar **Activo** (OpenAI u otro con API key). La URL del webhook en Telegram debe ser la de tu backend público: `https://tu-dominio/api/webhooks/telegram/`. Ver [§ 10](#10-canales-telegram-whatsapp-email). |

Documentación adicional: [support/docs/backend/](backend/), [support/docs/frontend/](frontend/), [support/docker/README.md](../docker/README.md), [support/docs/PROXMOX_VM_CONFIG.md](PROXMOX_VM_CONFIG.md) (VM en Proxmox, red y HTTPS).
