# Guía de implementación — servidor Staging

Pasos para desplegar **Synap** en un servidor remoto (Linux) usando la rama **Staging**, Docker Compose y arranque automático tras reinicio.

**Repositorio:** `git@github.com:eleven-it/Synap.git`  
**Rama de preproducción:** `Staging`  
**Flujo de ramas:** ver [FLUJO_RAMAS_Y_PLAN.md](FLUJO_RAMAS_Y_PLAN.md)

> La rama **Staging** no incluye la carpeta `docs/` ni archivos `.md` de raíz. Esta guía vive en **Desarrollo**.

---

## 1. Requisitos

| Requisito | Detalle |
|-----------|---------|
| SO | Ubuntu 24.04 LTS o superior (servidor Linux recomendado) |
| Usuario | Cuenta con `sudo` (ej. `administranet`) |
| Red | GitHub + MySQL AdministraNET (`DB_HOST`) |
| Puertos | `8000` (app), `5435`→Postgres, `6381`→Redis |

---

## 2. Acceso al repositorio (Deploy Key SSH)

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
ssh-keygen -t ed25519 -C "administranet-synap-staging" \
  -f ~/.ssh/id_ed25519_synap_staging -N ""

cat >> ~/.ssh/config << 'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_synap_staging
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config ~/.ssh/id_ed25519_synap_staging
chmod 644 ~/.ssh/id_ed25519_synap_staging.pub
```

Registrar la clave pública en https://github.com/eleven-it/Synap/settings/keys (Deploy key, solo lectura).

```bash
ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
ssh -T git@github.com

git clone -b Staging git@github.com:eleven-it/Synap.git
cd Synap
```

---

## 3. Instalar Docker y Docker Compose

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

sudo systemctl enable docker
sudo usermod -aG docker administranet
# Cerrar sesión SSH y volver a entrar
```

---

## 4. Configurar `.env`

```bash
cp env.example .env
nano .env
```

PostgreSQL (dentro de Docker):

```env
POSTGRES_DB=synap_db
POSTGRES_USER=synap_user
POSTGRES_PASSWORD=<clave-segura>
POSTGRES_HOST=db
POSTGRES_PORT=5432
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<clave-larga>
ALLOWED_HOSTS=localhost,127.0.0.1,<dominio-o-ip>
```

MySQL AdministraNET:

```env
DB_NAME=administranet
DB_USER=administranet
DB_PASSWORD=<password-mysql>
DB_HOST=<host-mysql>
DB_PORT=3306
```

Definir credenciales **antes** del primer `docker compose up` si el volumen Postgres es nuevo.

---

## 5. Primera instalación automática (DB limpia)

Con volumen Postgres **nuevo**, un solo comando basta:

```bash
docker compose up -d --build
```

El `docker-entrypoint.sh` ejecuta:

1. Espera Postgres y Redis  
2. Detecta si **no existe** `django_migrations` (instalación nueva)  
3. **`migrate`** completo (con `SYNAP_MIGRATIONS_POSTGRES_ONLY=1`)  
4. **`bootstrap_instalacion`**: activa `core`, `login`, `dashboard`, `reports`; permisos Postgres; sync MySQL (best-effort)  
5. En bases **existentes**: `fix_reports_migrations` + `setup_reports_installation`  
6. `collectstatic` e inicia el servidor  

Verificación:

```bash
docker ps
docker logs Synap_app --tail 80
docker exec Synap_app python manage.py setup_modules --list
docker exec Synap_app python manage.py check
curl -I http://localhost:8000
```

Módulos activos esperados tras bootstrap: **core**, **login**, **dashboard**, **reports**.

---

## 6. Bootstrap manual (si falló el automático)

```bash
docker compose run --rm --entrypoint "" \
  -e SYNAP_MIGRATIONS_POSTGRES_ONLY=1 \
  app python manage.py migrate --noinput

docker exec Synap_app python manage.py bootstrap_instalacion --force

docker compose up -d app
```

Opciones:

```bash
docker exec Synap_app python manage.py bootstrap_instalacion --skip-permisos-mysql
docker exec Synap_app python manage.py bootstrap_instalacion --base-empresa administranet
```

---

## 7. Permisos en AdministraNET (puestos)

El bootstrap intenta `sync_synap_permissions_to_adminet`. Si MySQL no estaba listo, repetir:

```bash
docker exec Synap_app python manage.py sync_synap_permissions_to_adminet --base-empresa TU_BASE_EMPRESA
```

Asignar permisos al puesto (ej. `reports.ver`) en AdministraNET o en `/core/permisos-sistema/`.

```bash
docker exec Synap_app python manage.py debug_permissions supervisor
```

---

## 8. Arranque automático tras reinicio

```bash
sudo systemctl enable docker
```

Los servicios `app`, `db` y `redis` usan `restart: unless-stopped`.

Opcional — unidad systemd para el stack:

```ini
# /etc/systemd/system/synap.service
[Unit]
Description=Synap Docker Compose
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/administranet/Synap
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=administranet
Group=docker

[Install]
WantedBy=multi-user.target
```

---

## 9. Actualizar Staging

```bash
cd ~/Synap
git pull origin Staging
docker compose up -d --build
```

---

## 10. Solución de problemas

| Síntoma | Acción |
|---------|--------|
| Loop de reinicio en DB nueva (versiones antiguas) | Actualizar código con entrypoint corregido o `bootstrap_instalacion --force` |
| `django_migrations does not exist` | `migrate` antes de `fix_reports_migrations` |
| `ia.0001_initial is applied before its dependency core.0011_moduleconfig_logistica` | En BD existente el entrypoint ejecuta `fix_inconsistent_migration_history --force` (marca `core.0011` y asegura ModuleConfig logistica). Manual: `python manage.py fix_inconsistent_migration_history --force` y luego `migrate --noinput`. |
| Módulos inactivos | `python manage.py bootstrap_instalacion --force` |
| `--activate reports` falla | Activar cadena: `core login dashboard reports` (lo hace `bootstrap_instalacion`) |
| Menú MPR u otros sin activar módulo | Controlado por permisos MySQL (`mpr.ver`), no por Module Management |

---

## 11. Referencias

- [FLUJO_RAMAS_Y_PLAN.md](FLUJO_RAMAS_Y_PLAN.md)  
- [SEGURIDAD_CAMBIOS_SYNAP.md](SEGURIDAD_CAMBIOS_SYNAP.md)  
- [SYNC_PERMISOS_SYNAP.md](SYNC_PERMISOS_SYNAP.md)  
- [comandos.md](../core/management/commands/comandos.md) — `bootstrap_instalacion`  
- [README_INSTALLATION.md](../../README_INSTALLATION.md)
