# Especificación: asignación vendedor ↔ cliente / marca (Ventas Synap)

Estado: **propuesta acordada** (iteración 2026-06-29).

## Alcance

- Tablas MySQL legacy por `base_empresa` (cualquier empresa; no solo Best Sox).
- Pantalla unificada en **Ventas** con toggle Cliente / Marca.
- Consumo del flag vía **relays Synap** (`ecom/` en este repositorio) según `configuracion_ecom`.
- **Sin** sincronización con `cliente.CodViajante`.
- **`administraNET-ecom/`** (repo externo, mayoristapp PHP): **solo lectura** para paridad e integración; **no modificar** desde Synap (no es propiedad del equipo Synap). Cualquier cambio en PHP legacy debe coordinarse con el dueño de ese repositorio.

## Modelo de datos

```sql
CREATE TABLE vendedores_clientes_asignacion (
  id BIGINT NOT NULL AUTO_INCREMENT,
  id_vendedor INT NOT NULL COMMENT 'viajantes.CodViajante',
  id_cliente INT NOT NULL COMMENT 'cliente.Codigo',
  fecha_alta DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_mod DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
  usuario_mod VARCHAR(60) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_vca_cliente (id_cliente),
  INDEX idx_vca_vendedor (id_vendedor)
) ENGINE=InnoDB ...;

CREATE TABLE vendedores_marcas_asignacion (
  id BIGINT NOT NULL AUTO_INCREMENT,
  id_vendedor INT NOT NULL,
  id_marca INT NOT NULL COMMENT 'marca.CodMarca',
  ...
  UNIQUE KEY uk_vma_marca (id_marca),
  INDEX idx_vma_vendedor (id_vendedor)
) ENGINE=InnoDB ...;
```

- **Integridad:** UNIQUE por cliente/marca; índice por vendedor; **sin FK física** (paridad legacy).
- **Datos iniciales:** tablas **vacías** (no sembrar desde `cliente.CodViajante`).
- **Desasignar:** `DELETE` de la fila (cliente/marca sin vendedor permitido).
- **Elegibles:** solo clientes `Estado = 'Activo'`, marcas `anulado = 'No'`, vendedores `anulado = 'No'`.

## Configuración ecom (fuente legacy vs tabla)

| key_permiso | Valores | Default |
|-------------|---------|---------|
| `ecom_fuente_vendedor_cliente` | `legacy` \| `tabla` | `legacy` |
| `ecom_fuente_vendedor_marca` | `legacy` \| `tabla` | `legacy` |

- Catálogo en `configuracion_ecom_conf` + fila operativa en `configuracion_ecom`.
- Editable desde AdministraNET (Configuración adicional ecom) o directamente en MySQL.
- Migración: proveedor **`vendedores_asignacion`** en `core/services/legacy_mysql_schema/catalog.py` → **Archivo → Migración esquema MySQL**.

### Comportamiento (integración Synap)

| Modo | Filtro clientes (relay Synap `ecom`) |
|------|--------------------------------------|
| `legacy` | `cliente.CodViajante` (paridad PHP `relay-clientes.php`) |
| `tabla` | `EXISTS` en `vendedores_clientes_asignacion` |

Implementado en **este repositorio** (Synap):

- `ecom/services/ecom_config_mysql.py` — lectura de `configuracion_ecom`
- `ecom/services/vendedor_asignacion_sql.py` — fragmentos SQL legacy vs tabla
- `ecom/services/cliente_relay.py` — filtro en búsqueda/selección de clientes

**Referencia de lectura (no editar):** `administraNET-ecom/mayoristapp/relay-clientes.php`, `control.php`, `control-cliente.php`.

**Nota:** `usa_viajante_cliente` (sesión PHP) es independiente del flag de fuente; ver código PHP solo como referencia de paridad.

## UI MVP (escala: 10+ vendedores, 1000+ clientes)

**No** usar Kanban multi-columna. Layout **master-detail + tabla paginada server-side**:

1. **Sidebar:** lista de vendedores activos (búsqueda predictiva, scroll).
2. **Panel principal:** clientes/marcas del vendedor seleccionado (o filtro «sin asignar»), paginación 25/50/100.
3. **Búsqueda global** de ítem (cliente/marca) con columna «vendedor actual».
4. **Reasignación masiva:** checkboxes + combo vendedor destino + «Aplicar».
5. **Drag & Drop (MVP):** arrastrar filas seleccionadas a la **fila del vendedor en sidebar** (un solo drop target), no entre columnas de clientes.

Toggle **Asignar: Cliente | Marca** reutiliza el mismo shell; cambia APIs y etiquetas.

## Implementado (Synap ventas)

- Servicio: `ventas/services/vendedor_asignacion_mysql.py`
- Vistas/API: `ventas/views_vendedor_asignacion.py`
- UI: `/ventas/asignacion-vendedor/?modo=cliente|marca` — sidebar + tabla paginada + DnD + masivo
- Menú Ventas → Gestión → Asignación vendedor
- Permisos: lectura `ventas.ver`; mutaciones `ventas.editar`
- Migración MySQL: proveedor `vendedores_asignacion` en herramienta legacy

## Pendiente opcional

- Relay ecom marca cuando un flujo Synap filtre por marca
- Tests de integración con MySQL real en contenedor
