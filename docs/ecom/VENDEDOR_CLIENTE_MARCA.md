# Vendedor → Cliente → Marca (territorio comercial)

**Change:** `ecom-pedidos-hub-kanban-masivo-sucursales`  
**Ruta config (Phase 2):** `/ecom/mayoristapp/config/vendedor-cliente-marca/`  
**Fecha:** 13/07/2026

## Regla de negocio

Terna `(CodViajante, id_cliente, CodMarca)`.  
**Unique activo:** `(id_cliente, CodMarca)` → un solo vendedor.  
Mismo cliente puede tener varios vendedores si las **marcas no se solapan**.

Ejemplo válido:

- Vendedor 1 → Cliente 1 → Marca A  
- Vendedor 2 → Cliente 1 → Marca B  

Inválido: Vendedor 2 → Cliente 1 → Marca A (conflicto; informar dueño).

## Tabla MySQL (legacy por empresa)

`ecom_vendedor_cliente_marca` — DDL en `ecom/sql/001_ecom_vendedor_cliente_marca.sql`, proveedor catálogo `ecom_vendedor_cliente_marca`.

**No confundir** con `vendedores_clientes_asignacion` / `vendedores_marcas_asignacion` (`docs/general/SPEC_VENDEDOR_ASIGNACION_VENTAS.md`): esas tablas asignan cliente **o** marca en exclusiva global al vendedor. Esta terna es **marca por cliente** para el pedido masivo / filtro de catálogo.

## Mapeo usuario ↔ viajante

Tabla opcional `ecom_usuario_viajante` (1 usuario → 1 `CodViajante`), patrón MPR operario. Complementa `cod_viajante` de sesión si falta.

## Permisos

| Key | Uso |
|-----|-----|
| `ecom.config_vendedor_cliente_marca` | ABM ternas (supervisor ventas) |

## Endpoints API

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/ecom/api/mayoristapp/vendedor-cliente-marca/ternas/` | Lista (filtros `CodViajante`, `id_cliente`, `solo_activas`) |
| POST | `/ecom/api/mayoristapp/vendedor-cliente-marca/crear/` | Alta; **409** `code=conflicto_marca` + `dueno` |
| POST | `/ecom/api/mayoristapp/vendedor-cliente-marca/anular/` | Soft-delete `{id}` |
| GET | `.../vendedores/`, `.../clientes/`, `.../marcas/` | Búsqueda predictiva `?q=` |

UI: `/ecom/mayoristapp/config/vendedor-cliente-marca/` (canon tablero slate-800).
