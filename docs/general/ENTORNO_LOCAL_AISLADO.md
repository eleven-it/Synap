# Synap local aislado de Odoo

Este entorno utiliza el checkout `synap-local`, el proyecto Compose
`synap-local-codex`, el puerto `127.0.0.1:18080` y volúmenes exclusivos.
Odoo conserva su proyecto, su base, su bind mount y `127.0.0.1:8069`.
El archivo Compose de Synap no publica PostgreSQL, MySQL ni Redis al host
y no se conecta a la red `synap_net` de otras instalaciones.

## Primera configuración

Crear `.env` a partir de `.env.example` y usar valores locales:
`ENVIRONMENT=development`, `SITE_URL=http://127.0.0.1:18080`,
`POSTGRES_HOST=db`, `DB_HOST=mysql`, `REDIS_URL=redis://redis:6379/0`.
Definir contraseñas aleatorias distintas para `SECRET_KEY`,
`POSTGRES_PASSWORD`, `DB_PASSWORD` y `LOCAL_MYSQL_ROOT_PASSWORD`.
Para una base MySQL vacía, `ADMINISTRANET_MYSQL_AES_KEY=localdev` es solo
un valor de prueba; si más adelante se importa una base de administraNET,
usar la clave compatible con esos datos. Verificar la configuración con
`docker compose --env-file .env -f compose.local.yml config --quiet`.

## Arranque en Windows PowerShell

```powershell
Set-Location C:\odoo19\codex\synap-local
docker compose --env-file .env -f compose.local.yml up -d --build
docker compose --env-file .env -f compose.local.yml ps
docker inspect Synap_app --format '{{.State.Health.Status}}'
```

Abrir <http://127.0.0.1:18080/>. `.env` se crea localmente, contiene
credenciales aleatorias y nunca se commitea. Para detener el entorno:

```powershell
docker compose --env-file .env -f compose.local.yml down
```

No agregar `-v` a `down`: borraría las bases locales. En este checkout de
Windows se excluye `theme/templates/admin/` mediante sparse checkout porque
el repositorio incluye un archivo con espacio final incompatible con NTFS.
El resto del código permanece en el commit de `origin/Desarrollo`.

La base MySQL local se crea vacía. Para probar datos de Best Sox se necesita
una importación separada y autorizada a esta base local, siguiendo
`docs/general/MYSQL_LOCAL_IMPORTACIONES.md`; no usar credenciales ni bases
de producción por defecto. Sin datos importados, las pantallas de login o
reportes dependientes de administraNET pueden carecer de usuarios y datos.

Las comprobaciones Django se ejecutan dentro del contenedor:

```powershell
docker exec Synap_app python manage.py check
```

Si en el host ya existe otro contenedor llamado `Synap_app`, detener la
instalación y elegir otra instancia Docker. Este Compose nunca usa la
configuración de Odoo.
