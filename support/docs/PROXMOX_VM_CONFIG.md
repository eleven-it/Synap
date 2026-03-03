# Configuración de la VM en Proxmox (Support)

Guía para desplegar Support en una máquina virtual bajo Proxmox: recursos, red y firewall para que el webhook de Telegram (y el resto del sistema) sea accesible por HTTPS.

---

## 1. Recursos de la VM

Para el stack Support (PostgreSQL, Redis, backend Django, opcional frontend estático y reverse proxy en la misma VM):

| Recurso | Mínimo recomendado | Notas |
|---------|--------------------|--------|
| **vCPU** | 2 | 4 si hay Celery worker + beat y tráfico alto |
| **RAM** | 2 GB | 4 GB si se añade MinIO o más workers |
| **Disco** | 20 GB | 32–50 GB si se guardan muchos adjuntos o logs |
| **SO** | Debian 12 / Ubuntu 22.04 LTS | Con soporte Docker y systemd |

---

## 2. Red en Proxmox

- **Interfaz de red:** VM con un único bridge (ej. `vmbr0`) conectado a la red donde está el router/firewall.
- **IP:** Asignar IP fija a la VM (DHCP con reserva o configuración estática en el SO).
- **Acceso desde internet:** El router/firewall debe hacer **NAT (port forwarding)** o la VM puede tener IP pública. Lo importante es que el puerto **443** (HTTPS) llegue a la VM (o al proxy que esté en ella).

Opciones típicas:

- **A) NAT en el router:** Redirigir `IP_router:443` → `IP_VM:443` (o `IP_VM:80` si el proxy escucha en 80 y hace redirect a 443).
- **B) IP pública en la VM:** Asignar la IP pública directamente a la VM (menos habitual en entornos domésticos/pequeños).

---

## 3. Puertos en la VM

En la VM solo deben ser accesibles desde internet los que realmente lo necesiten:

| Puerto | Servicio | ¿Exponer a internet? |
|--------|----------|------------------------|
| **22** | SSH | Sí (recomendado con clave y, si es posible, sin contraseña). |
| **443** | Reverse proxy (HTTPS) | **Sí** — Telegram y usuarios acceden aquí. |
| 80 | HTTP (redirect a 443) | Opcional, solo si el proxy escucha en 80. |
| 8250 | Backend Support | **No** — Solo el proxy en localhost. |
| 5432, 6379, 9000 | Postgres, Redis, MinIO | **No** — Solo red interna / localhost. |

No abrir 5432, 6379 ni 9000 al exterior.

---

## 4. Firewall en la VM (ejemplo con iptables / nftables o ufw)

Si usás **ufw** en Debian/Ubuntu:

```bash
# Permitir SSH y HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 443/tcp
# Opcional: HTTP para redirect
sudo ufw allow 80/tcp
sudo ufw enable
```

Desde Proxmox no hace falta abrir puertos extra si el tráfico entra por la IP de la VM y el firewall lo gestiona la VM.

---

## 5. Reverse proxy (HTTPS) en la VM

El backend Support (puerto 8250) no se expone directamente. Un proxy en la misma VM termina HTTPS y reenvía al backend.

**Ejemplo con Caddy** (certificado automático con Let's Encrypt):

1. Instalar Caddy en la VM.
2. Dominio: por ejemplo `support.tudominio.com` apuntando (DNS) a la IP pública del router o de la VM.
3. Configuración mínima (`/etc/caddy/Caddyfile`):

```text
support.tudominio.com {
    reverse_proxy localhost:8250
}
```

Caddy escucha en 443 (y opcionalmente 80 para redirect) y reenvía todo al backend en `localhost:8250`.

**Ejemplo con Nginx (proxy inverso completo):**

1. Instalar Nginx y (opcional) certbot para Let's Encrypt:

```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

2. Crear el sitio (reemplazá `support.tudominio.com` por tu dominio):

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

# HTTPS: proxy inverso al backend Support (puerto 8250)
server {
    listen 443 ssl http2;
    server_name support.tudominio.com;

    # Certificados (Let's Encrypt con certbot; paths típicos)
    ssl_certificate     /etc/letsencrypt/live/support.tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/support.tudominio.com/privkey.pem;

    # Opcional: parámetros SSL recomendados
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;

    # Tamaño máximo para webhooks (Telegram envía JSON en el body)
    client_max_body_size 1M;

    location / {
        proxy_pass http://127.0.0.1:8250;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

3. Activar el sitio y comprobar la configuración:

```bash
sudo ln -s /etc/nginx/sites-available/support /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

4. **Si usás Let's Encrypt por primera vez** (antes de poner el bloque `listen 443 ssl` con rutas de certbot, podés dejar solo el `server` de 80 temporalmente y ejecutar):

```bash
sudo certbot --nginx -d support.tudominio.com
```

Certbot crea o modifica el server block y añade las rutas a `fullchain.pem` y `privkey.pem`. Luego podés editar el archivo para añadir `client_max_body_size` y los `proxy_*` si no estaban.

**Sin Let's Encrypt** (certificados propios): reemplazá las líneas `ssl_certificate` y `ssl_certificate_key` por las rutas de tu `.crt` y `.key`.

---

## 5. Servir también el frontend (SPA) desde internet

Si querés que la interfaz web (React) sea accesible desde internet en el mismo dominio, Nginx debe:

1. **Servir los estáticos del build del frontend** (HTML, JS, CSS) para las rutas que no son API.
2. **Enviar solo `/api/` al backend** (puerto 8250).

Pasos:

**1. Build del frontend en la VM (o en tu máquina y copiá la carpeta `dist`):**

```bash
cd support/frontend
# La API se llama por la misma origen; no hace falta VITE_API_BASE_URL (queda /api)
npm ci
npm run build
```

Se genera la carpeta `dist/`. Copiala a la VM, por ejemplo en `/var/www/support`:

```bash
sudo mkdir -p /var/www/support
sudo cp -r support/frontend/dist/* /var/www/support/
# O desde la VM si el código está ahí:
# sudo cp -r /ruta/al/repo/support/frontend/dist/* /var/www/support/
sudo chown -R www-data:www-data /var/www/support
```

**2. Nginx: mismo server block, pero `/api` al backend y el resto al SPA:**

Reemplazá el bloque `server` de 443 por este (manteniendo el redirect 80→443 igual):

```nginx
# HTTPS: frontend estático + proxy /api al backend
server {
    listen 443 ssl http2;
    server_name support.tudominio.com;

    ssl_certificate     /etc/letsencrypt/live/support.tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/support.tudominio.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;

    client_max_body_size 1M;

    root /var/www/support;
    index index.html;

    # API y webhooks → backend Django (8250)
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

    # SPA: todo lo demás sirve index.html y los estáticos
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**3. Backend (variables de entorno):** Con frontend y API en el mismo dominio no hay CORS cross-origin. En el `.env` del backend (o en el compose) definí el dominio para que Django acepte el Host y CSRF:

```bash
ALLOWED_HOSTS=support.tudominio.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://support.tudominio.com
CORS_ALLOWED_ORIGINS=https://support.tudominio.com
```

Si usás `config.settings.local` en producción, esos valores pueden estar en el archivo de settings; en producción conviene usar `config.settings.prod` y pasar todo por env.

**4. Rebuild al actualizar:** Cada vez que cambies el frontend, ejecutá `npm run build` y volvé a copiar `dist/*` a `/var/www/support`.

---

## 6. Resumen del flujo

1. **Proxmox:** VM con 2 vCPU, 2–4 GB RAM, disco 20–32 GB, una interfaz en el bridge de la red.
2. **Red:** IP fija en la VM; en el router/firewall, reenvío de **443** (y opcionalmente 80) a esa IP.
3. **Firewall en la VM:** Solo 22 (SSH) y 443 (y 80 si aplica) abiertos al exterior.
4. **Dentro de la VM:** Docker Compose con backend en 8250 (sin mapear 8250 al host si no hace falta); reverse proxy (Caddy/Nginx) en 443/80 que hace `proxy_pass` a `localhost:8250`.
5. **Telegram:** Webhook configurado como `https://support.tudominio.com/api/webhooks/telegram/`.

Con esto la VM en Proxmox queda preparada para que Support sea accesible por HTTPS y el bot de Telegram funcione correctamente.
