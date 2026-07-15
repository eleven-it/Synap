# Vendedor → Cliente → Sucursal → Marca (territorio comercial)

**Change:** `ecom-pedidos-hub-kanban-masivo-sucursales` (+ extensión cuaterna)  
**Ruta config:** `/ecom/mayoristapp/config/vendedor-cliente-marca/`  
**Fecha:** 14/07/2026

## Regla de negocio

Cuaterna `(CodViajante, id_cliente, id_cliente_domicilio, CodMarca)`.  
**Unique activo:** `(id_cliente, id_cliente_domicilio, CodMarca)` → un solo vendedor por sucursal.  
La misma marca en el mismo cliente puede ir a **distinto vendedor** si es **otra sucursal**.

Ejemplo válido:

- Vendedor 1 → Cliente 1 → Sucursal A → Marca X  
- Vendedor 2 → Cliente 1 → Sucursal B → Marca X  

Inválido: Vendedor 2 → Cliente 1 → Sucursal A → Marca X (conflicto; informar dueño).

**Visibilidad de cliente** para un vendedor: tiene ≥1 cuaterna activa (EXISTS sin filtrar sucursal).

## Tabla MySQL (legacy por empresa)

`ecom_vendedor_cliente_marca` — DDL:

- Instalación nueva: `ecom/sql/001_ecom_vendedor_cliente_marca.sql`
- Upgrade bases existentes: `ecom/sql/002_ecom_vendedor_cliente_marca_sucursal.sql` (vía catálogo idempotente)

Proveedor catálogo: `ecom_vendedor_cliente_marca`.

Columna clave: `id_cliente_domicilio` (`cliente_domicilio.id_cliente_domicilio`; `0` = edge case sin domicilios).

### Migración de ternas existentes (bases ya pobladas)

Al ejecutar el proveedor en **Archivo → Migración esquema MySQL**:

1. Añade `id_cliente_domicilio` si falta.
2. Reemplaza unique `uk_evcm_cliente_marca_activo` por `uk_evcm_cliente_sucursal_marca_activo`.
3. Por cada fila activa con `id_cliente_domicilio=0`:
   - Si el cliente tiene domicilios activos (`anulado='No'`): inserta una fila por domicilio y **anula** la fila sin sucursal.
   - Si el cliente **no** tiene domicilios: conserva una fila con `id_cliente_domicilio=0` (documentado como edge case).

## Feature flag

`ecom_usa_vcm_ternas`: `Si` | `No` | `auto` (default). Semántica sin cambios.

## Permisos

| Key | Uso |
|-----|-----|
| `ecom.config_vendedor_cliente_marca` | ABM cuaternas (supervisor ventas) |

## Endpoints API

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/ecom/api/mayoristapp/vendedor-cliente-marca/ternas/` | Lista (filtros `CodViajante`, `id_cliente`, `id_cliente_domicilio`, `solo_activas`) |
| POST | `/ecom/api/mayoristapp/vendedor-cliente-marca/crear/` | Alta con `id_cliente_domicilio` obligatorio; **409** `code=conflicto_marca` + `dueno` |
| POST | `/ecom/api/mayoristapp/vendedor-cliente-marca/anular/` | Soft-delete `{id}` |
| GET | `.../vendedores/`, `.../clientes/`, `.../sucursales/?id_cliente=`, `.../marcas/` | Búsqueda predictiva `?q=` |

UI: `/ecom/mayoristapp/config/vendedor-cliente-marca/` — formulario con 4 combobox: Vendedor, Cliente, **Sucursal** (depende de cliente), Marca.

## Filtros operativos

| Flujo | Comportamiento |
|-------|----------------|
| Pedido masivo — clientes | ≥1 cuaterna activa con viajante efectivo |
| Pedido masivo — sucursales | Solo domicilios con ≥1 cuaterna (vendedor, cliente) si VCM activo |
| Pedido masivo / simple — marcas | Con `id_cliente_domicilio`: marcas de esa sucursal; sin domicilio: **unión** de todas las sucursales del par vendedor-cliente |
| Carrito simple `agregar_item` | Valida marca contra cuaternas; sin domicilio en sesión usa unión |

Ver también `docs/ecom/PEDIDO_MASIVO_SUCURSALES.md`.
