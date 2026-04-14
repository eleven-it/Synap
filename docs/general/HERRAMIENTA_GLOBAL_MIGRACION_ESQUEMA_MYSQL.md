# Herramienta global: migración de esquema MySQL (AdministraNET legacy)

## Alcance

**Solo bases MySQL** compartidas con AdministraNET (VB6): el mismo criterio que `core.mysql_pool.get_connection(base_empresa)` y `docs/general/TIPOS_DATOS_ADMINISTRANET.md`.

- **No** sustituye a `manage.py migrate` de Django (eso actúa sobre **PostgreSQL** / `default`).
- **Sí** alinea tablas/columnas en el **esquema por empresa** (`base_empresa`) cuando Synap o un módulo necesitan campos que el ERP aún no tiene en esa instalación.

## Estado actual (referencia)

| Origen | Mecanismo | Ejemplo |
|--------|-----------|---------|
| Catálogo único | `core/services/legacy_mysql_schema/catalog.py` + `PROVIDER_REGISTRY` | Tienda Nube, MPR depósito/artículo, trazabilidad lista producción |
| `core` | Comandos `manage.py` (`apply_schema_mpr`, `apply_alter_detalle_trazabilidad`) delegan en el catálogo | Misma lógica que la herramienta web |
| `tiendanube_administranet` | `AdministraNETService.verify_and_migrate_schema()` → `run_tiendanube_integration_mysql` | `id_tiendanube` en `cliente` / `articulo` |
| UI supervisor | **Archivo → Parámetros → Migración esquema MySQL (legacy)** (`core:legacy_mysql_schema`) | Ejecutar proveedores sobre `base_empresa` de sesión |

La conexión es siempre pool Synap (`get_connection`) + `base_empresa` de sesión o argumento CLI.

## Objetivo de producto

Una **herramienta global** (una pantalla o entrada en menú de administración) que permita:

1. Elegir **qué conjunto de comprobaciones/aplicaciones** ejecutar (por módulo o por “paquete” documentado).
2. Ver **resultado** por paso (aplicado / omitido / error) sobre la empresa activa.
3. Opcional: modo **solo simulación** (dry-run) donde el diseño lo permita.

Los módulos **registran** sus necesidades de esquema; el núcleo **orquesta** permisos, sesión y ejecución.

## Diseño propuesto (registro + orquestador)

1. **`core.services.legacy_mysql_schema`** (nombre tentativo):
   - Registro de **proveedores**: `app_label`, título visible, descripción, función `run(connection|base_empresa, request) -> dict` con lista de cambios.
   - Validación común: `resolve_mysql_base_empresa` / sesión (misma política que hoy en integración TN).

2. **Vista única** en `core`:
   - **Visibilidad:** solo el usuario técnico **supervisor** (`cod_usuario == 'supervisor'`), mismo criterio que Archivo / Module Management / Settings en `apps_visibles_para_usuario` (no basta con el puesto «Supervisor» en AdministraNET).
   - Lista de proveedores activos.
   - Botón “Ejecutar” por proveedor o “Ejecutar todos” con confirmación.

### Ubicación del acceso en la UI (recomendado)

| Opción | Pros | Contras |
|--------|------|--------|
| **Archivo → Parámetros** (nuevo ítem, p. ej. «Migración esquema MySQL») | Misma barra que el resto de tareas de sistema; el menú Archivo ya es solo supervisor. | Hay que añadir fila en `APPS_MENU` + `menu_item_id` único. |
| **Solo Module Management** | Todo lo “de instalación” junto. | Module Management es **activar/desactivar módulos** (`ModuleConfig`), no mantenimiento DBA por empresa; mezcla conceptos. |
| **Ambos** | Enlace secundario desde Module Management (“Herramientas”) hacia la vista en `core`. | Dos entradas a mantener. |

**Recomendación:** pantalla canónica bajo **Archivo** (sección Parámetros o bloque «Herramientas» solo supervisor). Opcional: en **Module Management** un enlace breve *«Migración esquema MySQL (legacy)»* que apunte a la misma URL, para quien busca desde ahí, **sin** sustituir el menú principal de Module Management.

3. **Migración desde módulos existentes**:
   - `tiendanube_administranet`: envolver `verify_and_migrate_schema` como proveedor registrado; el botón en la pantalla del módulo puede **redirigir** a la herramienta global o mostrarse como atajo que llama al mismo backend.
   - Comandos `core` tipo `apply_schema_mpr`: encapsular la lógica en funciones importables y registrarlas como proveedores (el comando CLI seguiría llamando a la misma función).

4. **Seguridad y auditoría**:
   - Siempre HTTPS, CSRF en POST.
   - Log estructurado (usuario, `base_empresa`, proveedor, resultado).
   - En producción, activar según `ENVIRONMENT=production` las mismas barreras que el plan general (cookies, sesión).

## Qué no es esta herramienta

- No gestiona índices PostgreSQL ni modelos Django.
- No reemplaza scripts SQL manuales de una sola vez en entornos sin Synap (se pueden seguir documentando en `docs/*/sql/`).

## Próximos pasos sugeridos

1. ~~Entrada en **Archivo** (supervisor)~~ — ítem `archivo_param_mysql_schema` en `APPS_MENU`.
2. ~~Vista `core:legacy_mysql_schema`~~ con lista de proveedores y ejecución por ítem o todos.
3. Enlace opcional desde **Module Management** hacia la misma URL (si se desea).
4. Añadir nuevos proveedores solo en `catalog.py` + documentación breve del caso de uso.

---

*Documento orientativo para alinear equipos; la implementación debe seguir el flujo de ramas en `docs/general/FLUJO_RAMAS_Y_PLAN.md`.*
