# Herramienta global: migración de esquema MySQL (AdministraNET legacy)

## Alcance

**Solo bases MySQL** compartidas con AdministraNET (VB6): el mismo criterio que `core.mysql_pool.get_connection(base_empresa)` y `docs/general/TIPOS_DATOS_ADMINISTRANET.md`.

- **No** sustituye a `manage.py migrate` de Django (eso actúa sobre **PostgreSQL** / `default`).
- **Sí** alinea tablas/columnas en el **esquema por empresa** (`base_empresa`) cuando Synap o un módulo necesitan campos que el ERP aún no tiene en esa instalación.

## Estado actual (referencia)

| Origen | Mecanismo | Ejemplo |
|--------|-----------|---------|
| Catálogo único | `core/services/legacy_mysql_schema/catalog.py` + `PROVIDER_REGISTRY` | Tienda Nube, MPR (depósito, **tablas core `mpr_*`**), Self-checkout tablas MySQL, objetivos ventas, asignación vendedores |
| `core` | Comandos `manage.py` (`apply_schema_mpr`, `apply_mpr_core_tables`, `apply_mpr_maquina_linea`, …) delegan en el catálogo | Misma lógica que la herramienta web |
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

## Proveedores MPR (estado 04/07/2026)

| Proveedor (UI) | id | Notas |
|----------------|-----|--------|
| MPR — depósito y artículo | `mpr_deposito_articulo` | Columnas en `deposito` / `articulo` |
| **MPR — tablas core Synap (ledgers MySQL)** | `mpr_core_tables` | 13 tablas `mpr_*` (`001_mpr_core_tables.sql`); **usar en instalaciones nuevas** |
| **MPR — máquina/línea/trazabilidad** | `mpr_maquina_linea_trazabilidad` | Tablas nuevas de trazabilidad por máquina/línea/operario (`003_mpr_maquina_linea_tables.sql`: `mpr_linea`, `mpr_maquina` con `observacion_planilla`, `mpr_maquina_linea`, `mpr_maquina_articulo`, `mpr_operario_linea`, `mpr_operario_usuario`) + ALTER idempotente de `observacion_planilla` en instalaciones existentes + extensión idempotente del ledger de partes (estado/origen/gap/máquina) y del roster (override de línea), equivalente a `004_mpr_parte_maquina_gap.sql`. Función `run_mpr_maquina_linea_mysql`. CLI: `apply_mpr_maquina_linea <base>`. Ver `docs/mpr/TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md` |
| **MPR — eliminar OPT legacy** | `mpr_drop_lista_produccion_legacy` | DROP `lista_produccion_*` (irreversible). CLI: `drop_mpr_lista_produccion_legacy <base> --confirm` |
| *(retirados de la herramienta)* | `mpr_lista_produccion_*` | ~~Creación~~ de tablas OPT legacy. Solo funciones de emergencia en código; **no** recrear tras el DROP |

---

## Si la migración «no termina» y no hay error en el log

La herramienta web (`core:legacy_mysql_schema`) responve **solo cuando MySQL termina** toda la cadena de la petición (un POST = uno o todos los proveedores). Mientras tanto:

- **No** se escribe en log el resultado final (éxito o fallo); es normal que `docker logs` parezca «mudo» hasta que termine el ALTER más lento.
- Los `ALTER TABLE` (p. ej. `CHANGE COLUMN` en **MPR — trazabilidad lista producción (detalle)**) pueden tardar **minutos** en tablas grandes o quedar **esperando bloqueo** si otra sesión (VB6, otro Synap, backup) mantiene la tabla abierta.

**Qué hacer**

1. Tras actualizar Synap, vigilar el log de la app: deberían aparecer líneas `legacy_mysql_schema:` (inicio/fin por proveedor y duración) y, para ese proveedor, `MPR trazabilidad detalle:` antes de cada paso pesado.
2. En MySQL, revisar `SHOW PROCESSLIST` (o `performance_schema.metadata_locks` en 8.0) para ver si la sesión está en «Waiting for table metadata lock».
3. Para evitar timeout del **navegador o del proxy** delante de DDL largos, ejecutar el mismo cambio por **CLI** en el contenedor, por ejemplo:
   - `docker exec Synap_app python manage.py apply_mpr_core_tables administranet92`
   - (u otro `manage.py` que delegue en el mismo catálogo).

### Pocas filas y, aun así, «Waiting for table metadata lock»

El tiempo del `ALTER` **no** depende solo del número de filas visibles: si en `SHOW PROCESSLIST` aparece **Waiting for table metadata lock**, hay **cola de bloqueos de metadatos** sobre `lista_produccion_detalle` / `lista_produccion_agrupada` (u otras tablas tocadas en el mismo lote).

Causas típicas:

- Sesiones en **Sleep** muy largas desde clientes (192.168.x, ERP, herramientas SQL) que mantienen **transacción abierta** o dejaron de usar la tabla pero otra sesión sigue con consultas concurrentes.
- **Varios** `ALTER` o migraciones lanzados a la vez (pestañas duplicadas, Synap + script manual): todos compiten y se encadenan en espera.
- Algún proceso que **aún no** aparece como «waiting» pero **retiene** el modo de bloqueo compatible (hay que localizar al «dueño» con `performance_schema.metadata_locks` / `metadata_locks_waits` en MySQL 8 o con la vista `sys` de bloqueos, según instalación).

En la **herramienta web** Synap se usa un **candado lógico** `GET_LOCK('synap_mysql_schema:<base_empresa>', …)` para que **no** se solapen dos ejecuciones de migración desde Synap sobre la misma base (reduce duplicar ALTER por doble clic). **No** sustituye a cerrar clientes externos que bloquean el servidor MySQL.

### Cómo liberar el bloqueo (DBA): localizar y `KILL`

**No** hay un comando mágico tipo “UNLOCK TABLE” para MDL: hay que **terminar la sesión que retiene** el bloqueo (o la que está mal encolada) con criterio, preferiblemente tras identificarla.

1. **MySQL 8.0** — ver quién bloquea a quién (si existe el esquema `sys`):

```sql
SELECT * FROM sys.schema_table_lock_waits;
```

O inspección directa (sustituir esquema y tablas):

```sql
SELECT * FROM performance_schema.metadata_locks
WHERE OBJECT_TYPE = 'TABLE'
  AND OBJECT_SCHEMA = 'administranet92'
  AND OBJECT_NAME IN ('lista_produccion_detalle', 'lista_produccion_agrupada');
```

En `metadata_locks`, interesa la fila cuyo `LOCK_STATUS` sea **granted** con `OWNER_THREAD_ID` del proceso que **impide** el `ALTER` (y las demás en *pending*).

2. **Cortar la sesión bloqueadora** (sustituir `N` por el **Id** de `SHOW PROCESSLIST` o el hilo equivalente):

```sql
KILL N;
```

En entornos con roles, a veces hace falta `KILL QUERY N` (solo la consulta actual) frente a `KILL N` (toda la conexión). Para sesiones **Sleep** muy largas que sospechan de transacción colgada, suele usarse `KILL N` sobre esa conexión.

3. **Varios ALTER duplicados en espera**  
   Tras liberar al **primer bloqueador**, muchas sesiones en *Waiting for table metadata lock* pueden seguir o despejarse solas. Si quedaron migraciones **duplicadas** lanzadas por error, el DBA puede **matar** las sesiones que solo esperan el mismo `ALTER` (dejando **una** que ejecutará el cambio), siempre coordinado con el equipo.

4. **MySQL 5.7**  
   No hay `metadata_locks` tan cómodo; suele usarse `SHOW FULL PROCESSLIST`, revisar sesiones **no** en espera de MDL que toquen el mismo esquema, o herramientas (`pt-deadlock-logger`, etc.). La lógica es la misma: **identificar conexión** → **`KILL`**.

**Riesgo:** `KILL` a una sesión de producción puede dejar transacciones a medias en el cliente (ERP). Coordinar ventana de mantenimiento, cerrar VB6/Heidi antes de migrar y **no** matar a ciegas el hilo del servidor si no está claro qué es.

---

*Documento orientativo para alinear equipos; la implementación debe seguir el flujo de ramas en `docs/general/FLUJO_RAMAS_Y_PLAN.md`.*
