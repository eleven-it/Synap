# Restricciones de catálogo por punto de venta — Fase P3 (item 3)

Change SDD: `openspec/changes/catalogo-carrito-checkout-mayorista/` · Fase **P3**.
Reemplaza el "baneo de productos" legacy (ex-AMICO) por una **configuración genérica en BD**.

## Origen legacy

`control.php` cargaba en sesión dos listas de IDs de artículo **hardcodeadas**:

```php
$_SESSION["lista_baneo_productos_fiscal"]    = array(5002, 4351, 3999, 4004, 3165, 4006);
$_SESSION["lista_baneo_productos_no_fiscal"] = array(60, 93, 94, ...);
```

y `ajax-articulos.php` las aplicaba al listado según el tipo contable del PV activo
(`punto_venta.cont`: `Si` = fiscal / `No` = no fiscal):

```php
if ($tipoPuntoVentaCont === 'Si') $listaBaneoActiva = $_SESSION['lista_baneo_productos_fiscal'];
if ($tipoPuntoVentaCont === 'No') $listaBaneoActiva = $_SESSION['lista_baneo_productos_no_fiscal'];
if (!empty($listaBaneoActiva)) $filtro .= " AND articulo.IDArt NOT IN(...)";
```

**Problemas:** IDs hardcodeados en código, atados a un cliente (AMICO) y a fiscal/no-fiscal.

## Diseño en Synap (genérico, config en BD)

Modelo `EcomCatalogoRestriccionPV` (Postgres `synap`):

| Campo | Descripción |
|---|---|
| `base_empresa` | Base de la empresa |
| `id_punto_venta` | PV concreto al que aplica la restricción |
| `tipo` | `articulo` \| `rubro` \| `subrubro` \| `categoria` |
| `valor_id` | ID a excluir del catálogo |
| `activo` | Habilita/deshabilita sin borrar |
| `nota` | Motivo (auditoría) |

- **Sin IDs en código** ni acoplado a AMICO/fiscal: cada empresa configura, por PV, qué
  artículos/rubros/subrubros ocultar. Gestionable desde **Django admin**.
- Cubre el caso legacy: a los PV fiscales se les cargan los artículos de la lista fiscal,
  a los no-fiscales la no-fiscal (pero ahora por PV y editable).

## Aplicación

1. `ecom/services/catalogo_restricciones.py`
   - `restricciones_para_pv(base_empresa, id_punto_venta)` → `{excluir_articulos, excluir_rubros, excluir_subrubros}`.
   - `aplicar_restricciones_a_filtros(filtros, base_empresa, id_punto_venta)` → filtros combinados.
2. `_construir_where_catalogo` traduce `excluir_*` a `AND <col> NOT IN (%s, ...)` (parametrizado).
3. Se aplica en:
   - **Listado**: `POST /ecom/api/mayoristapp/catalogo/articulos/listado/`.
   - **Export PDF**: `GET /ecom/api/mayoristapp/catalogo/lista-precios.pdf`.
   - El **PV activo** se toma de la sesión (`id_punto_venta_activo`).

> `categoria` está reservado (el catálogo P0 no trae la categoría todavía).
> **Ficha de detalle** y carrito no filtran por restricción (paridad legacy: solo filtraba
> listados; el vendedor no puede encontrar el artículo restringido por búsqueda/listado).

## Tests

`ecom/tests/test_catalogo_restricciones.py`: WHERE con/ sin exclusiones e IDs inválidos,
resolución por PV (activas/inactivas/otros PV), y merge de filtros sin mutar el original.

```bash
docker exec Synap_app python manage.py test ecom.tests.test_catalogo_restricciones --keepdb
```
