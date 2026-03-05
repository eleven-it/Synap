# Configuración Automática de Permisos SIA

## Resumen

Este documento describe cómo los permisos de SIA se crean y sincronizan automáticamente al levantar los contenedores, sin intervención manual.

## Arquitectura de Sincronización

### PostgreSQL (ANALYTICS)

Los permisos SIA se crean automáticamente en PostgreSQL mediante una **migración de datos**:

- **Migración**: `sia/migrations/0002_auto_create_sia_permissions.py`
- **Función helper**: `core/permissions_utils.py::ensure_sia_permissions_in_postgres()`
- **Ejecución**: Automática al ejecutar `python manage.py migrate`

### MySQL (administraNET)

Los permisos SIA se sincronizan automáticamente a MySQL mediante el **entrypoint del contenedor**:

- **Comando**: `python manage.py sync_sia_permissions_to_adminet --auto`
- **Ejecución**: Automática en `docker-entrypoint.sh` después de las migraciones
- **Modo**: Tolerante a errores (no falla si MySQL no está disponible)

## Flujo Automático Completo

```
1. Contenedor inicia
   ↓
2. docker-entrypoint.sh ejecuta:
   ├── python manage.py migrate --noinput
   │   └── Ejecuta migración 0002_auto_create_sia_permissions.py
   │       └── Crea permisos SIA en PostgreSQL ✅
   ↓
3. docker-entrypoint.sh ejecuta:
   └── python manage.py sync_sia_permissions_to_adminet --auto
       └── Sincroniza permisos SIA a MySQL de administraNET ✅
           └── (Tolerante a errores de conexión)
   ↓
4. Sistema listo para usar
```

## Archivos Creados/Modificados

### Nuevos Archivos

1. **`core/permissions_utils.py`**
   - Helper centralizado para gestión de permisos SIA
   - Función `ensure_sia_permissions_in_postgres()`: Idempotente y reutilizable
   - Función `get_sia_permissions_data()`: Retorna definiciones de permisos

2. **`sia/migrations/0002_auto_create_sia_permissions.py`**
   - Migración de datos que crea permisos SIA en PostgreSQL
   - Se ejecuta automáticamente con `migrate`
   - Idempotente y segura

3. **`SIA_AUTO_SYNC_SETUP.md`** (este archivo)
   - Documentación completa del sistema

### Archivos Modificados

1. **`sia/management/commands/create_sia_permissions.py`**
   - Refactorizado para usar `core/permissions_utils.py`
   - Ahora solo llama al helper

2. **`sia/management/commands/sync_sia_permissions_to_adminet.py`**
   - Agregado flag `--auto` para modo automático
   - Mejorado manejo de errores (tolerante a fallos de conexión MySQL)
   - Mejora de idempotencia (maneja IntegrityError por colisiones concurrentes)
   - Logging resumido en modo auto

3. **`core/constantes_permisos.py`**
   - Agregados permisos SIA al diccionario `PERMISOS_POR_MODULO`

4. **`docker-entrypoint.sh`**
   - Agregado comando de sincronización automática después de migraciones

## Modo Automático del Comando de Sincronización

El comando `sync_sia_permissions_to_adminet` tiene un modo especial `--auto` diseñado para entrypoints:

### Características del Modo `--auto`:

1. **Logging Resumido**
   - No imprime detalles de cada permiso procesado
   - Solo loguea resúmenes y errores importantes

2. **Tolerante a Errores**
   - Si MySQL no está disponible: Loguea warning y sale con código 0
   - Si hay errores en empresas individuales: Continúa con las siguientes
   - No falla el arranque del contenedor por problemas de sincronización

3. **Idempotente**
   - Maneja colisiones concurrentes (IntegrityError)
   - Si el permiso ya existe, lo actualiza
   - Seguro para ejecutar múltiples veces

4. **Código de Salida Configurable**
   - Por defecto: Sale con código 0 (éxito) incluso si hay errores
   - Con `--exit-on-error`: Sale con código 1 si hay errores (útil para monitoreo)

### Ejemplo de Uso en Entrypoint

```bash
# En docker-entrypoint.sh (YA IMPLEMENTADO)
python manage.py sync_sia_permissions_to_adminet --auto || {
    echo "⚠️  Advertencia: No se pudieron sincronizar permisos SIA a MySQL"
    # Continúa el arranque aunque falle
}
```

## Verificación Manual

### Verificar Permisos en PostgreSQL

```bash
docker exec Synap_app python manage.py shell
>>> from core.models import Permiso
>>> Permiso.objects.filter(modulo='sia').values_list('codigo', 'nombre')
<QuerySet [('sia.manage_cycles', 'Gestionar Ciclos de Evaluación'), ...]>
```

### Verificar Permisos en MySQL

```bash
docker exec Synap_app python manage.py shell
>>> from django.db import connections
>>> cursor = connections['mysql'].cursor()
>>> cursor.execute("SELECT key_permiso, nombre_permiso FROM permiso_sistema WHERE grupo_permiso = 'SIA'")
>>> cursor.fetchall()
[('sia.manage_cycles', 'Gestionar Ciclos de Evaluación'), ...]
```

### Ejecutar Sincronización Manualmente

```bash
# Modo manual (output detallado)
docker exec Synap_app python manage.py sync_sia_permissions_to_adminet

# Modo automático (logging resumido)
docker exec Synap_app python manage.py sync_sia_permissions_to_adminet --auto

# Sincronizar solo una empresa
docker exec Synap_app python manage.py sync_sia_permissions_to_adminet --base-empresa nombre_base

# Dry-run (simular sin cambios)
docker exec Synap_app python manage.py sync_sia_permissions_to_adminet --dry-run
```

## Troubleshooting

### Si los permisos no se crean en PostgreSQL

1. Verificar que la migración se ejecutó:
   ```bash
   docker exec Synap_app python manage.py showmigrations sia
   ```
   Debe mostrar `[X] 0002_auto_create_sia_permissions`

2. Si la migración no se aplicó, ejecutar manualmente:
   ```bash
   docker exec Synap_app python manage.py migrate sia 0002_auto_create_sia_permissions
   ```

3. Si necesitas recrear los permisos:
   ```bash
   docker exec Synap_app python manage.py create_sia_permissions
   ```

### Si los permisos no se sincronizan a MySQL

1. Verificar conexión MySQL:
   ```bash
   docker exec Synap_app python manage.py shell
   >>> from django.db import connections
   >>> connections['mysql'].ensure_connection()
   ```

2. Verificar configuración en `settings.py`:
   - `DATABASES['mysql']['HOST']`
   - `DATABASES['mysql']['PORT']`
   - `DATABASES['mysql']['USER']`
   - `DATABASES['mysql']['PASSWORD']`

3. Verificar que la base 'empresas' existe:
   ```bash
   docker exec Synap_app python manage.py shell
   >>> from django.db import connections
   >>> cursor = connections['mysql'].cursor()
   >>> cursor.execute("SHOW DATABASES LIKE 'empresas'")
   >>> cursor.fetchall()
   ```

4. Ejecutar sincronización manualmente para ver errores detallados:
   ```bash
   docker exec Synap_app python manage.py sync_sia_permissions_to_adminet
   ```

### Si el contenedor no arranca

El modo `--auto` está diseñado para **NO bloquear** el arranque. Si el contenedor no arranca:

1. Verificar logs del contenedor:
   ```bash
   docker logs Synap_app
   ```

2. Buscar errores en la sincronización:
   ```bash
   docker logs Synap_app | grep -i "sia\|permiso\|mysql"
   ```

3. Si MySQL no está disponible, el modo `--auto` solo loguea un warning y continúa.

## Personalización

### Cambiar Comportamiento en Modo Auto

Si necesitas que el modo `--auto` falle el arranque cuando hay errores, modifica `docker-entrypoint.sh`:

```bash
# Cambiar de:
python manage.py sync_sia_permissions_to_adminet --auto || { ... }

# A:
python manage.py sync_sia_permissions_to_adminet --auto --exit-on-error || {
    echo "❌ Error crítico al sincronizar permisos SIA"
    exit 1
}
```

### Agregar Más Permisos SIA

1. Agregar definición a `core/permissions_utils.py::SIA_PERMISSIONS_DATA`
2. Agregar a `core/constantes_permisos.py::PERMISOS_POR_MODULO["SIA"]`
3. Los permisos se crearán automáticamente en la próxima migración/sincronización

## Notas Importantes

1. **Idempotencia**: Todos los comandos son idempotentes y seguros de ejecutar múltiples veces

2. **Orden de Ejecución**: 
   - Primero se crean en PostgreSQL (migración)
   - Luego se sincronizan a MySQL (entrypoint)

3. **Tolerancia a Errores**: El modo `--auto` está diseñado para no bloquear el arranque

4. **Asignación de Permisos**: Después de sincronizar, los permisos deben asignarse a puestos en administraNET Gestión (tabla `permiso_sistema_puesto`)

5. **Sincronización Bidireccional**: Actualmente solo sincroniza desde PostgreSQL a MySQL. Si se modifican permisos en MySQL, no se reflejan automáticamente en PostgreSQL (requiere ejecución manual del comando).













