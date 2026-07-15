# Comandos de gestión Django (Synap)

Este documento inventaria los **comandos personalizados** (`manage.py <nombre>`) del repositorio Synap: **objetivo**, **cuándo usarlos** y **cómo ejecutarlos**.

## Cómo ejecutarlos

En desarrollo con Docker (recomendado en el proyecto):

```bash
docker exec Synap_app python manage.py <comando> [opciones]
```

Sin Docker (entorno local con dependencias instaladas):

```bash
python manage.py <comando> [opciones]
```

Muchos comandos que tocan **MySQL por empresa** piden el nombre de la base (`base_empresa`), por ejemplo `administranet92`. Ese valor debe coincidir con la empresa activa en sesión / configuración MySQL del entorno.

Para ver la ayuda integrada de un comando:

```bash
docker exec Synap_app python manage.py <comando> --help
```

---

## Nota sobre archivos duplicados

En algunas carpetas existen archivos cuyo nombre termina en **` 2.py`** (copias accidentales). **No** deben usarse como referencia: el comando válido es el que tiene el nombre **sin** ese sufijo. Si aparecen dos definiciones del mismo nombre, revisar y eliminar el duplicado.

---

## Core (`core`)

| Comando | Objetivo | Ejemplo / notas |
|--------|-----------|-----------------|
| `initial_setup` | Puesta en marcha inicial completa del sistema (migraciones, datos, módulos, etc.). | `python manage.py initial_setup --help` (muchas flags: `--skip-migrations`, `--dry-run`, nombre empresa, etc.). |
| `bootstrap_instalacion` | **Primera instalación / staging:** activa `core`, `login`, `dashboard`, `reports`, permisos Postgres y tablas `synap_*` en MySQL (best-effort). Idempotente; lo invoca `docker-entrypoint.sh` en DB nueva. | `--force`, `--skip-permisos-mysql`, `--base-empresa`. |
| `load_initial_data` | Carga datos iniciales (geografía, unidades, medios de pago, categorías, impuestos, etc.). | Opciones `--skip-*` por bloque. |
| `load_geographic_data` | Carga datos geográficos (AR, CL, UY, PY, BR, US, ES). | |
| `populate_countries_states` | Puebla países y provincias/estados. | |
| `populate_fiscal_responsibilities` | Responsabilidades fiscales por país. | `--pais AR`, `--force`, `--dry-run`. |
| `create_default_empresa` | Crea empresa y sucursal por defecto (p. ej. staging). | `--nombre`, `--cuit`, `--sucursal`, `--codigo`, `--dry-run`. |
| `crear_roles_base` | Crea permisos y roles base desde `core/constantes_permisos.py`. | `--solo-permisos`, `--solo-roles`, `--force`. |
| `crear_usuario` | Crea usuario (autenticación AdministraNET; ver ayuda del comando). | |
| `sincronizar_permisos` | Sincroniza permisos definidos en constantes con la tabla `Permiso` en PostgreSQL/Django. | Tras añadir códigos en `PERMISOS_POR_MODULO`. |
| `apply_synap_permisos_tables` | Crea tablas `synap_*` y siembra catálogo `synap_permiso` en MySQL (no escribe en VB6). | `<base_empresa>`, `--dry-run`. |
| `backfill_synap_permisos_from_legacy` | Migra asignaciones de `permiso_sistema_puesto` → `synap_*` (rol dedicado por puesto). | `<base_empresa>`, `--dry-run`, `--force`. |
| `purge_synap_legacy_permisos` | Elimina filas `grupo_permiso='Synap'` en `permiso_sistema*` (dry-run por defecto). | `<base_empresa>`, `--ejecutar`. |
| `init_adminet_permissions` | Inicializa grupo y permisos para integración AdministraNET. | |
| `asignar_rol` | Gestión de usuarios: roles, alta/baja, sincronización con Firebase (ver `--help`). | |
| `asignar_roles_predeterminados` | Crea o actualiza roles predeterminados y sus permisos. | |
| `asignar_sucursales_admins` | Asigna todas las sucursales a usuarios con rol administrador. | |
| `sincronizar_usuarios_firebase` | Sincroniza usuarios desde Firebase a la base local (incluye múltiples roles). | Ver `--help`. |
| `setup_modules` | Module Management: inicializar, listar, activar/desactivar módulos, validar dependencias, menús, hooks, plugins, extensiones. | Ver subsección **setup_modules** más abajo. |
| `add_administraNET_module` | Registra/actualiza el módulo AdministraNET en `ModuleConfig`. | |
| `add_reports_ai_module` | Registra/actualiza el módulo Reports AI en `ModuleConfig`. | |
| `add_tiendanube_administranet_module` | Registra/actualiza el módulo Tiendanube AdministraNET en `ModuleConfig`. | |
| `cleanup_removed_modules` | Elimina filas de `ModuleConfig` para nombres de módulos ya retirados del código. | `--dry-run`. |
| `cleanup_sales_module` | Elimina el registro del módulo `sales` de `ModuleConfig`. | `--dry-run`. |
| `activate_reports` | Activa el módulo `reports` en base de datos. | |
| `setup_reports_installation` | Configura instalación de Reports (migraciones, módulo activo, etc.). | `--force`, `--skip-migrations`. |
| `fix_reports_migrations` | Corrige estado de migraciones de `reports` en Django. | `--force`. |
| `apply_schema_mpr` | Aplica columnas MPR en MySQL: `deposito.suma_stock`, `deposito.tipo_mpr`, `articulo.stock_reserva`. | `apply_schema_mpr administranet89 [--dry-run]` |
| `apply_alter_detalle_trazabilidad` | Aplica ALTER de trazabilidad `lista_produccion_detalle` (script SQL de MPR). | `base_empresa` + `--dry-run` opcional. |
| `inspect_lista_produccion_tables` | Muestra estructura de tablas de lista de producción y relaciones. | `[base_empresa]` (default en código). |
| `diagnostico_empresa_adminet` | Comprueba tabla `DatosEmpresa` y existencia de tablas en MySQL. | `--database` o similar (ver `--help`). |
| `mantenimiento_sistema` | Tareas de mantenimiento: caché, logs, optimización DB, integridad. | `--limpiar-cache`, `--limpiar-logs`, `--optimizar-db`, `--verificar-integridad`, `--todo`, `--dias-logs N`. |
| `migrate_products_to_empresa` | Migra productos Tiendanube a la empresa activa del usuario. | `--user-email`, `--empresa-id`, `--dry-run`. |
| `fix_cross_company_stock` | Corrige stock que cruza límites de empresa. | `--dry-run`, `--empresa-id`. |
| `sync_tiendanube` | Sincroniza productos/stock con Tienda Nube. | `--tipo`, `--limite`, `--forzar`, `--config-id`, `--auto-config`. |
| `update_cdn_domain` | Actualiza dominio del CDN en configuración. | `--dominio`, `--proveedor`. |
| `show_azure_clients` | Lista clientes de Azure SQL (consulta/demo). | `--limit`, `--detailed`. |
| `show_azure_clients_detailed` | Detalle de clientes Azure SQL. | `--limit`, `--client-id`. |
| `show_azure_client_addresses` | Busca direcciones/datos de clientes en Azure. | `--client-id`, `--search`. |
| `export_azure_schema` | Exporta esquema Azure SQL a Markdown. | `--output`, `--include-samples`. |
| `analyze_best_processes` | Análisis de procesos del sistema BEST. | `--output`, `--include-details`. |
| `cleanup_clientes_app` | Limpia la app `clientes` (destructivo; ver confirmaciones). | `--force`, `--dry-run`. |

### `setup_modules` (detalle)

Puede combinarse varias acciones en una sola invocación (el comando ejecuta cada bloque activado en orden).

| Opción | Objetivo |
|--------|-----------|
| `--init` | Inicializa la configuración por defecto de módulos (cuando aún no existe `ModuleConfig` o se requiere bootstrap). |
| `--reset` | Resetea todas las configuraciones de módulos. |
| `--list` | Lista módulos y estado. |
| `--info <m1> [m2 ...]` | Información detallada de módulos concretos. |
| `--activate <m1> [m2 ...]` | Activa módulos. |
| `--deactivate <m1> [m2 ...]` | Desactiva módulos. |
| `--validate` | Valida dependencias entre módulos. |
| `--menus` | Muestra información de menús por módulo. |
| `--validate-menus` | Valida configuración de menús. |
| `--reload-menus` | Recarga configuración de menús. |
| `--hooks` | Muestra información de hooks. |
| `--validate-hooks` | Valida hooks. |
| `--reload-hooks` | Recarga hooks. |
| `--events` | Muestra información de eventos. |
| `--test-hooks` | Prueba el sistema de hooks con eventos de ejemplo. |
| `--plugins` | Muestra información de plugins. |
| `--validate-plugins` | Valida plugins. |
| `--reload-plugins` | Recarga plugins. |
| `--extensions` | Muestra información de extensiones. |
| `--validate-extensions` | Valida extensiones. |
| `--reload-extensions` | Recarga extensiones. |
| `--test-plugins` | Prueba el sistema de plugins. |
| `--test-extensions` | Prueba el sistema de extensiones. |

Ejemplos:

```bash
docker exec Synap_app python manage.py setup_modules --list
docker exec Synap_app python manage.py setup_modules --init
docker exec Synap_app python manage.py setup_modules --activate reports mpr --reload-menus
```

Nota técnica: las opciones de **plugins** y **extensiones** están declaradas en el parser (aparecen en `--help`). Si al usar solo esas banderas el comando avisa que no hay acción, revisar el `handle` actual de `setup_modules.py` (el flujo principal puede no estar invocándolas aún).

---

## MPR (`mpr`)

| Comando | Objetivo | Ejemplo |
|--------|-----------|---------|
| `diagnosticar_demanda_mpr` | Diagnóstico de demanda OPT: query de pedidos pendientes y estado de `lista_produccion_detalle` / agrupada. | `diagnosticar_demanda_mpr --base-empresa=administranet92 [--fecha-desde ...] [--fecha-hasta ...] [--busqueda ...]` |
| `inspeccionar_pedidos_pendientes_mpr` | Lista pedidos Pendiente + artículos en `stockp` y si son terminados para producción. | `--base-empresa` obligatorio; fechas opcionales. |
| `inspeccionar_opt` | Inspecciona cómo quedó registrada una OPT en MySQL. | `--base-empresa`, argumento o flag para `id_lista_produccion` (ver `--help`). |
| `inspeccionar_armado_opt` | Inspecciona líneas de armado de una OPT (componentes, stock semi, máx. armable). | `--base-empresa`, id OPT. |
| `analizar_trazabilidad_opt` | Analiza trazabilidad OPT en varias tablas legacy. | `analizar_trazabilidad_opt <id_lista> --base-empresa=...` |

---

## Reports (`reports`)

| Comando | Objetivo | Ejemplo |
|--------|-----------|---------|
| `diagnostico_bo_comprobantes` | Diagnóstico de comprobantes en reporte backorder (BO). | `--base-empresa`, lista de NroComprobante. |
| `documentar_tablas_db` | Genera documentación de tablas MySQL (schema, relaciones, uso). | `--base-empresa`, `--solo-schema`, rutas VB6/docs. |
| `inspect_articulos_schema` | Inspecciona tabla `articulos` y relacionadas en MySQL. | `--base-empresa`, `--tabla`, `--all-related`. |
| `investigar_factura_stock` | Investiga factura de compra vs movimientos de stock y remito. | Nro comprobante, `--base-empresa`, fecha opcional. |
| `verify_reservado_por_deposito` | Verifica reservado por depósito (`stock_deposito` vs `stockp`). | `--base-empresa`. |
| `reconcile_saldo_pedido_proveedor` | Reconciliación de `saldo_pedido_proveedor` vs movimientos OC/remito/factura. | `--base-empresa`, ejercicio, fechas, `--max-diff`. |
| `create_report_templates` | Crea plantillas de reportes del sistema. | |
| `assign_builder_permission_to_supervisor` | Asigna `reports.builder` al rol o usuario Supervisor. | Flags `--rol`, `--usuario`, `--ambos`, `--listar-usuarios`, `--email`. |
| `fix_migration_0017` | Marca migración 0017 como aplicada (fake) si las tablas ya existen. | |
| `fix_show_in_catalog_column` | Añade columna `show_in_catalog` en `reports_reportdefinition` si falta. | |

---

## Self-checkout (`self_checkout`)

| Comando | Objetivo | Ejemplo |
|--------|-----------|---------|
| `create_self_checkout_tables` | Crea tablas `self_checkout_*` en MySQL de la empresa. | `--base-empresa` obligatorio en multi-tenant; `--dry-run`. |
| `seed_self_checkout_kiosk` | Registra kiosco en `self_checkout_kiosk` y valida IDs sucursal/PV/deposito. | `--skip-validate` opcional. |
| `add_cod_viajante_kiosk` | Añade columna `cod_viajante` en `self_checkout_kiosk`. | `--base-empresa`. |
| `sync_self_checkout_permissions` | Sincroniza permisos self-checkout → `permiso_sistema` (MySQL). | `--base-empresa`, `--dry-run`. |
| `update_cuentacliente_cod_viajante` | Actualiza `CodViajante` en facturas self-checkout (`cuentacliente` TPV). | `--base-empresa`, `--cod-viajante`, `--dry-run`. |
| `diagnostico_cart_estado` | Carritos con factura pero estado distinto de confirmado. | `--base-empresa`, `--cart-id`. |
| `self_checkout_confirm_pending` | Reintenta confirmación de carritos en `pago_aprobado`. | `--base-empresa`, `--limit`, `--days`, `--dry-run`. |
| `self_checkout_retry_fe` | Reintenta facturación electrónica para estados pendientes/error. | `--base-empresa`, `--limit`, `--dry-run`. |
| `self_checkout_apply_migration_004` … `_008` | Aplica migraciones SQL incrementales 004–008 en la base empresa. | `--base-empresa` (cada comando). |
| `self_checkout_apply_migrations_promociones_voucher` | Aplica migraciones 006 y 007 (promociones + voucher). | `--base-empresa` o `--all` (según implementación). |

---

## Stock (`stock`)

| Comando | Objetivo | Ejemplo |
|--------|-----------|---------|
| `limpiar_temporales_stock` | Elimina registros temporales en `cuerpostock_mstock` (y series temp) por antigüedad. | Bases empresa como argumentos; `--horas N` (0 = todos). |

---

## Facturación AFIP (`fe_afip`)

| Comando | Objetivo | Ejemplo |
|--------|-----------|---------|
| `request_caea_auto` | Obtiene/renueva CAEA para períodos en ventana (tarea diaria típica). | `--base-empresa` opcional (todas si no se pasa); `--dry-run`. |

---

## E-com (`ecom`)

| Comando | Objetivo | Ejemplo |
|--------|-----------|---------|
| `process_ecom_mail_queue` | Procesa cola asíncrona de mails e-com. | `--retries`, `--max-attempts`. |

---

## IA (`ia`)

| Comando | Objetivo | Ejemplo |
|--------|-----------|---------|
| `export_ia_learning_jsonl` | Exporta ejemplos de aprendizaje a JSONL para fine-tuning. | `--agent-slug`, `--status`, `--output`, `--mark-exported`, `--limit`. |

---

## Mercado Pago (`mercadopago`)

| Comando | Objetivo | Ejemplo |
|--------|-----------|---------|
| `create_mercadopago_tables` | Crea tablas `mercadopago_*` en MySQL de la empresa. | `--base-empresa`, `--dry-run`. |

---

## Tiendanube AdministraNET (`tiendanube_administranet`)

| Comando | Objetivo | Ejemplo |
|--------|-----------|---------|
| `initialize_field_mappings` | Inicializa mapeos de campos Tiendanube ↔ AdministraNET. | `--tipo`, `--force`, `--dry-run`. |
| `sync_customers_from_adminet` | Sincroniza clientes desde AdministraNET hacia Synap. | `--limit`, `--offset`, `--force`. |
| `sync_customer_updates` | Sincroniza actualizaciones de clientes Tiendanube → AdministraNET. | Horas hacia atrás, flags validar/corregir (ver `--help`). |
| `migrate_to_new_app` | Migra datos de app `tiendanube` a `tiendanube_administranet`. | `--dry-run`, `--force`, skips por bloque. |

---

## Soporte / conocimiento RAG (`support` — app `knowledge`)

| Comando | Objetivo | Ejemplo |
|--------|-----------|---------|
| `sync_rag_from_synap` | Obtiene conocimiento desde la API Synap e ingesta en base RAG del backend Support. | `--company-id` opcional. |

**Nota:** Este comando vive bajo `support/backend/apps/knowledge/`; debe ejecutarse desde el proyecto Django donde esa app esté en `INSTALLED_APPS` (si aplica en vuestro despliegue).

---

## Mantenimiento del inventario

La lista anterior se obtiene de los archivos `**/management/commands/*.py` **excluyendo** `__init__.py` y nombres terminados en **` 2.py`**. Si se añade un comando nuevo en el repositorio, conviene actualizar esta tabla en el mismo commit o en uno inmediato (política de documentación del proyecto).

---

## Referencias

- Herramienta global de migración MySQL legacy: `docs/general/HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md`
- Module Management: `docs/general/ANALISIS_MODULE_MANAGEMENT.md`
- Política de documentación: `docs/general/POLITICA_DOCUMENTACION.md`
