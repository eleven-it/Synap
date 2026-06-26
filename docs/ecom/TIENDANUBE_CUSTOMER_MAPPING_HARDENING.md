# Endurecimiento mapeo manual de clientes Tienda Nube

Change SDD: `openspec/changes/tiendanube-customer-mapping-hardening/`

## Objetivo

Reducir riesgos del flujo **New Customer** (`CustomerMapping` manual).

## Cambios implementados

| Mitigación | Implementación |
|------------|----------------|
| Validar IDs existen | `services/customer_mapping_validation.py` + `CustomerMappingForm.clean()` |
| Email cruzado TN/Adminet | Warning/error si ambos IDs informados y emails difieren |
| Unicidad `adminet_codigo` | Migración `0023` + constraint Django |
| Anti-duplicado MySQL | `AdministraNETService._reject_duplicate_adminet_customer()` |
| Listado incompletos | Filtros Todos / Completo / Incompleto + badge |
| Sync explícito | Botón lista + «Guardar y sincronizar ahora» en formulario |
| Defaults seguros | `sync_enabled=False`, `sync_direction=tiendanube_to_adminet` |

## Migración 0023

```bash
docker exec Synap_app python manage.py migrate tiendanube_administranet 0023
```

Si falla por `adminet_codigo` duplicados en datos existentes, resolver duplicados en BD Synap antes de aplicar.

## Tests

```bash
docker exec Synap_app python manage.py test tiendanube_administranet.tests
```

## Consulta de IDs al crear mapeo

Los IDs los genera cada sistema. En **New Customer**:

- **Consultar**: valida un ID numérico contra Tienda Nube (API) o AdministraNET (MySQL sesión).
- **Buscar**: modal por email, nombre o documento; al elegir fila se completa el ID y vista previa.
- Al **guardar**, el servidor vuelve a consultar origen y completa email/nombre en el mapeo.

APIs:

- `GET .../api/customers/tiendanube/<id>/`
- `GET .../api/customers/search/?q=...` (Tienda Nube)
- `GET .../api/customers/adminet/<codigo>/`
- `GET .../api/customers/adminet/search/?q=...`

Errores de validación se muestran en el formulario (campo o banner superior). Sync en listado usa toast, no `alert()`.

## Paginación del listado

El listado pagina 20 clientes por página. La variable de contexto de filas es `customers`;
`page_obj` es el objeto `Page` de Django (controles Anterior/Siguiente). No usar
`context_object_name = 'page_obj'` en la vista: pisa el paginador y oculta la navegación.

## Columna Customer y nombres en listado

El listado (`/tiendanube_administranet/customers/`) usa la propiedad `CustomerMapping.display_name`:

1. `tiendanube_first_name` + `tiendanube_last_name`
2. `tiendanube_name`
3. `adminet_nombre`
4. `tiendanube_email` o «Sin nombre»

La sync masiva desde Tienda Nube normaliza con `tiendanube_customer_to_form_fields()` (API
`first_name`/`last_name` o `name`). La sync desde AdministraNET usa
`nombre_completo_a_campos_tiendanube()` al crear o completar campos TN vacíos.

## Status vs Sync en listado

| Columna | Campo | Significado |
|---------|-------|-------------|
| **Status** | `sync_status` | Resultado de la última sincronización (`pending`, `synced`, `error`, `conflict`) |
| **Sync** | `sync_enabled` | Si el mapeo participa en sync automática/periódica (default `False` en clientes) |

Un mapeo puede estar **Sincronizado** y **Disabled**: hubo sync manual o masiva con `force`, pero
no quedó habilitado para tareas automáticas. Activar sync en el formulario o usar
**Guardar y sincronizar ahora**.

El botón **Sync now** del listado envía `force=1` y **sí sincroniza** aunque `sync_enabled` sea
`False`. Ese flag solo bloquea tareas automáticas/Celery (`sync_enabled=True` requerido sin
`force`).

### TN → AdministraNET (sync manual)

1. Si el mapeo no tiene `adminet_codigo`, se busca en MySQL por `id_tiendanube` antes de crear.
2. `create_customer` usa `cursor.lastrowid` (y fallback por `id_tiendanube`) para obtener `Codigo`.
3. `ListaPrecio` debe ser VARCHAR (`Lista 1`); no normalizar como entero en
   `normalize_adminet_customer_payload`.

## Uso recomendado

1. Buscar o consultar clientes en cada sistema y seleccionar IDs autogenerados.
2. Crear mapeo con al menos un ID (idealmente ambos tras verificar emails).
2. Revisar badge **Incompleto** en listado si falta un lado.
3. Activar sync manualmente o usar **Guardar y sincronizar ahora**.
4. Evitar bidireccional hasta confirmar vínculo.

## Sync AdministraNET → Tienda Nube (`cliente_ecommerce`)

Análogo a productos con `articulo.ecommerce='Si'`:

| Campo MySQL | Valor | Efecto |
|-------------|-------|--------|
| `cliente.cliente_ecommerce` | `'Si'` | El cliente entra en la sync masiva Adminet → TN |
| `cliente.id_tiendanube` | vacío | Se **crea** en Tienda Nube y se persiste el ID en MySQL |
| `cliente.id_tiendanube` | numérico | Se **actualiza** en Tienda Nube |

Implementación: `TiendanubeAdministraNETSyncService.sync_customers_from_adminet()` y
`_push_adminet_customer_to_tiendanube()`.

Si el cliente no tiene email en AdministraNET, se usa fallback `adminet_{Codigo}@noemail.local`
para la API de Tienda Nube.

Clientes con `cliente_ecommerce='No'` no se publican desde AdministraNET; el flujo TN → Adminet
(webhook) sigue creando clientes con `cliente_ecommerce='Si'` e `id_tiendanube`.

## Sync inicial por lotes (Adminet → TN)

Para catálogos grandes, la sync masiva inicial se ejecuta en **lotes resumibles** sin saturar
la API de Tienda Nube. El progreso se persiste en `InitialSyncCheckpoint` (migración `0024`).

### Comando de gestión

```bash
# Primer lote de clientes (30 ítems)
docker exec Synap_app python manage.py tiendanube_initial_sync --tipo customer --batch-size 30

# Continuar desde el último checkpoint
docker exec Synap_app python manage.py tiendanube_initial_sync --tipo customer --resume

# Productos ecommerce
docker exec Synap_app python manage.py tiendanube_initial_sync --tipo product --batch-size 30 --resume

# Ambos tipos en secuencia
docker exec Synap_app python manage.py tiendanube_initial_sync --tipo both --resume

# Reiniciar progreso y volver a offset 0
docker exec Synap_app python manage.py tiendanube_initial_sync --tipo customer --reset --offset 0
```

Parámetros:

| Flag | Descripción |
|------|-------------|
| `--tipo` | `customer`, `product` o `both` |
| `--batch-size` | Ítems por lote (default 30) |
| `--offset` | Offset manual (ignorado con `--resume`) |
| `--resume` | Lee offset desde checkpoint |
| `--reset` | Reinicia checkpoint antes de ejecutar |

### Celery (background)

```python
from tiendanube_administranet.tasks.sync_tasks import initial_sync_batch_task

initial_sync_batch_task.delay(sync_type='customer', limit=30)
initial_sync_batch_task.delay(sync_type='product', limit=30)
```

### Servicio

`InitialSyncService` (`services/initial_sync_service.py`) delega en
`TiendanubeAdministraNETSyncService.sync_*_from_adminet(limit=..., offset=...)`, que aplica
el slice **después** del fetch completo en AdministraNET.
