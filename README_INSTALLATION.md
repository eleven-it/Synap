# Guía de Instalación - Synap Reports

Esta guía explica cómo instalar y configurar Synap Reports en una nueva instancia.

## Instalación Automática (Recomendada)

El sistema se configura automáticamente al iniciar el contenedor Docker. El script `docker-entrypoint.sh` ejecuta:

1. ✅ Espera a que PostgreSQL y Redis estén listos
2. ✅ Aplica todas las migraciones pendientes
3. ✅ Configura y activa el módulo Reports
4. ✅ Recolecta archivos estáticos
5. ✅ Inicia el servidor

### Pasos de Instalación

1. **Clonar el repositorio:**
```bash
git clone <repository-url>
cd Synap
git checkout Reports
```

2. **Configurar variables de entorno:**
```bash
cp env.example .env
# Editar .env con tus configuraciones
```

3. **Construir e iniciar contenedores:**
```bash
docker-compose build
docker-compose up -d
```

El sistema se configurará automáticamente al iniciar.

## Instalación Manual

Si prefieres configurar manualmente o si la instalación automática falla:

### 1. Aplicar Migraciones

```bash
docker exec Synap_app python manage.py migrate
```

### 2. Configurar Módulo Reports

```bash
docker exec Synap_app python manage.py setup_reports_installation
```

Este comando:
- ✅ Verifica que las tablas de reports existan
- ✅ Crea y activa el módulo reports en la base de datos
- ✅ Verifica el estado final de la instalación

### 3. Recolectar Archivos Estáticos

```bash
docker exec Synap_app python manage.py collectstatic --noinput
```

## Verificación de Instalación

### Verificar que el módulo esté activo:

```bash
docker exec Synap_app python manage.py shell -c "
from core.module_manager import module_manager
print('Módulo reports activo:', module_manager.is_module_active('reports'))
print('Módulos activos:', module_manager.get_active_modules())
"
```

### Verificar que las tablas existan:

```bash
docker exec Synap_app python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'reports_%' ORDER BY tablename;\")
tables = cursor.fetchall()
print('Tablas de reports:')
for table in tables:
    print(f'  - {table[0]}')
"
```

### Verificar permisos de un usuario:

```bash
docker exec Synap_app python manage.py debug_permissions <usuario>
```

## Comandos Útiles

### Activar módulo Reports manualmente:

```bash
docker exec Synap_app python manage.py activate_reports
```

### Ver estado de migraciones:

```bash
docker exec Synap_app python manage.py showmigrations reports
```

### Aplicar migraciones de reports específicamente:

```bash
docker exec Synap_app python manage.py migrate reports
```

## Solución de Problemas

### Error: "relation reports_reportdefinition does not exist"

**Solución:** Aplicar migraciones:
```bash
docker exec Synap_app python manage.py migrate reports
```

### Error: "Módulo reports NO está activo"

**Solución:** Activar el módulo:
```bash
docker exec Synap_app python manage.py activate_reports
```

### Error: Usuario redirigido al dashboard

**Solución:** Verificar permisos:
```bash
docker exec Synap_app python manage.py debug_permissions <usuario>
```

El usuario debe tener:
- `reports.*` (permiso comodín) O
- Al menos uno de: `reports.ver`, `reports.view_operational`, `reports.view_managerial`

Para usuarios con puesto "Supervisor" o cod_usuario "supervisor", los permisos se agregan automáticamente.

## Estructura de Archivos

- `docker-entrypoint.sh` - Script de inicialización automática
- `core/management/commands/setup_reports_installation.py` - Comando de configuración
- `core/management/commands/activate_reports.py` - Comando para activar módulo
- `core/management/commands/debug_permissions.py` - Comando de diagnóstico

## Notas

- El script de inicialización se ejecuta automáticamente al iniciar el contenedor
- Si necesitas ejecutar el setup manualmente, usa: `python manage.py setup_reports_installation`
- Para forzar la reconfiguración: `python manage.py setup_reports_installation --force`
- Para omitir migraciones: `python manage.py setup_reports_installation --skip-migrations`

