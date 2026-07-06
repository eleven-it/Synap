# Migración AdministraNET → Odoo 19

Módulo Django `odoo_migracion` en Synap para ETL/sincronización hacia Odoo 19 (JSON-2, Argentina AFIP).

## Documentos

| Documento | Contenido |
|-----------|-----------|
| [MODULO_SYNAP_ACCESO.md](MODULO_SYNAP_ACCESO.md) | Module Management, navbar, supervisor |
| [API_KEYS_ODOO.md](API_KEYS_ODOO.md) | Generación y rotación de API keys |
| [ANALISIS_COMPLEJIDAD.md](ANALISIS_COMPLEJIDAD.md) | Matriz de complejidad |
| [INVENTARIO_MIGRACION_ODOO.md](INVENTARIO_MIGRACION_ODOO.md) | F0 discovery |
| [MAPEO_CAMPOS_RESUMEN.md](MAPEO_CAMPOS_RESUMEN.md) | Mapeos por dominio |
| [REGLAS_CONVIVENCIA.md](REGLAS_CONVIVENCIA.md) | Convivencia temporal |

## Fases implementadas

| Fase | Descripción |
|------|-------------|
| F0 | Inventario cuantitativo (`odoo_discovery`, UI `/inventario/`) |
| F1 | App, conexiones, cliente JSON-2, API keys |
| F2 | Documentación de mapeos |
| F3 | Extractores + loaders maestros y partners |
| F4 | Artículos; stock en mapping pendiente (wizard Odoo) |
| F5 | Facturas CC históricas (mapping pendiente manual) |
| F6 | Wizard migración, validación/cuadre, reglas convivencia |

## Comandos

```bash
# F0 — inventario
docker exec Synap_app python manage.py odoo_discovery --base-empresa=MI_BASE

# Migrar dominio
docker exec Synap_app python manage.py odoo_migrate_domain --connection-id=1 --dominio=rubro

# Migrar todos (orden DAG)
docker exec Synap_app python manage.py odoo_migrate_domain --connection-id=1 --dominio=all

# Cuadre
docker exec Synap_app python manage.py odoo_validate_migration --connection-id=1
```

## UI (supervisor)

Patrón visual alineado a MPR/reportes: hero slate, acentos violeta, subnav persistente, KPIs y barras de progreso por dominio/fase.

| Ruta | Función |
|------|---------|
| `/odoo-migracion/` | Panel |
| `/odoo-migracion/inventario/` | F0 |
| `/odoo-migracion/wizard/` | Lanzar jobs |
| `/odoo-migracion/validacion/` | Cuadre |
| `/odoo-migracion/mapeos/` | Correlaciones |

## Estructura código

```
odoo_migracion/
  extractors/     # Lectura MySQL
  mappers/        # Adminet → payload Odoo
  loaders/        # Escritura JSON-2 + MigrationEntityMapping
  services/       # Orquestador, discovery, validación, convivencia
```
