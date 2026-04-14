# Tabla `logi_motivo_no_entrega`

Catálogo **por base de datos de empresa** (misma convención que el resto de tablas AdministraNET en esa instancia MySQL). Alimenta los desplegables de motivo en:

- Informe **Reports** `/reports/dashboard/comprobantes-rutas/` (API `GET …/motivos-no-entrega/`).
- Módulo **Logística → Entregas** (`GET /logistica/api/entregas/motivos-no-entrega/`).

El valor guardado en `comp_ped.motivo_no_entrega` es el texto de **`descripcion`** (paridad con legado).

| Campo | Tipo | Uso |
|-------|------|-----|
| `id` | INT PK | Identificador estable (útil para API futura / portal). |
| `descripcion` | VARCHAR(255) | Texto mostrado y persistido en `comp_ped`. |
| `activo` | `Si` / `No` | Si no está activo, no se ofrece en UI. |
| `orden` | INT | Orden de aparición. |
| `requiere_detalle` | `Si` / `No` | Si el formulario debe exigir comentario en `detalle_no_entrega`. |
| `visible_portal` | `Si` / `No` | Reservado para **Portal de cliente** (solo motivos que el cliente pueda ver o usar en consultas públicas). |

**DDL:** `docs/general/sql/logi_motivo_no_entrega.sql`

Si la tabla no existe, Synap usa la lista fija en código (`MOTIVOS_NO_ENTREGA`) como respaldo.
