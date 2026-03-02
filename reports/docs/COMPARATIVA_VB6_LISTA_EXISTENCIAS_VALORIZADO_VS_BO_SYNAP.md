# Comparativa: VB6 «Lista de existencias valorizado» vs reporte BO Synap

**Fecha:** 2026-03-02  
**Objetivo:** Ingeniería inversa del reporte BO de Synap que involucra stock, comparación con el informe VB6 «Lista de existencias valorizado», y diferencias en consultas y filtros.

---

## 1. Conclusión principal

**En Synap no existe un reporte BO equivalente a «Lista de existencias valorizado».**

El único reporte BO que utiliza tablas de stock es **bo-stock-facturacion** («BO vs Stock vs Facturación»), cuyo propósito es otro: análisis de facturación, remitos no facturados, backorder (pedidos pendientes) y cobertura con stock/OC. No es un listado de existencias por artículo/depósito valorizado.

Por tanto la comparación se hace entre:
- **VB6:** Informe «Lista de existencias valorizado» (id_reporte = 27, `Listado_Existencia_Valorizado` en Info_Stock.frm).
- **Synap BO:** Reporte **bo-stock-facturacion** (slug `bo-stock-facturacion`, `_run_backorder_vs_stock_vs_facturacion` en `reports/services/query_runner.py`).

---

## 2. Ingeniería inversa del reporte BO Synap (bo-stock-facturacion)

### 2.1 Ubicación y propósito

| Elemento | Valor |
|----------|--------|
| Slug | `bo-stock-facturacion` |
| Nombre típico | BO vs Stock vs Facturación |
| Código | `reports/services/query_runner.py` → `_run_backorder_vs_stock_vs_facturacion` (aprox. líneas 2847–3600+) |
| Propósito | Dashboard que combina: (1) Facturación neta (ventas − NC), (2) Remitos no facturados, (3) Backorder por producto con stock actual, reservado, disponible, OC pendiente y clasificación CON STOCK / CON INGRESO / SIN STOCK. |

### 2.2 Tablas y consultas del reporte BO

- **Facturación:** `cuentacliente` (FA/FB/FC/FE/FM, NCA/NCB/NCC/NCE/NCM). Filtros: `Fecha` en rango, `Anulado = 'No'`, `TipoComprobante IN (...)`.
- **Facturación por cliente:** `cuentacliente` + `cliente` + `viajantes` + `erp_zona`. Mismo rango de fechas.
- **Remitos no facturados:** `comp_ped` (TipoComprobante = 'REM', Estado = 'Pendiente') + `sucursales` + `punto_venta`.
- **Backorder (detalle por producto):**
  - Origen: `stockp` + `comp_ped` (TipoComprobante = 'PED', Estado = 'Pendiente', Anulado = 'No').
  - Stock: subconsulta sobre `stock_deposito` → `SUM(saldo)` por `id_articulo` (opcional: excluir depósitos).
  - Reservado: subconsulta `stockp` + `comp_ped` (PED, Estado IN ('En preparación','Preparado','Parcial')).
  - OC pendiente: subconsulta `stockp` + `cuentaproveedor` (TipoComprobante = 'OC', Estado = 'Pendiente').
  - Maestros: `articulo`, `rubro` (LEFT JOIN).
- **Detalle BO por comprobante/cliente:** `stockp` + `comp_ped` + `cliente`.
- **Detalle OC pendiente:** `stockp` + `cuentaproveedor` + `proveedor`.

No se usan en este reporte: `stock` (tabla de movimientos), `subrubro`, `marca`, `modelo`, `deposito` (solo para excluir depósitos del sumatorio de saldo).

### 2.3 Filtros del reporte BO

| Filtro | Origen | Efecto |
|--------|--------|--------|
| **base_empresa** | payload / usuario | Base MySQL sobre la que se ejecutan todas las consultas. |
| **fecha_inicio / fecha_fin** | payload (período) | Facturación y remitos: `Fecha` en rango. Backorder: **solo** renglones con `stockp.Fecha` en ese rango. |
| **clientes_excluidos** | payload | Excluye `cp.Codigo` / `cc.Codigo` en facturación, remitos y backorder (y en subconsulta de reservado). |
| **depositos_incluidos** | payload | Opcional: en la subconsulta de stock `stock_deposito.id_deposito IN (...)`; solo se suman esos depósitos al stock_actual. Si vacío, todos. |
| **sucursales / punto_venta** | payload | No se usan en la lógica actual del backorder ni en el sumatorio de stock; pueden afectar solo a vistas o futuras variantes. |

No hay en el BO: filtro por un solo depósito (solo exclusión de depósitos), filtro por artículo/rubro/subrubro/proveedor/marca/modelo, opción “solo con saldo > 0”, lista de precios, fecha determinada sobre tabla `stock` para “existencias a fecha”.

---

## 3. Resumen del informe VB6 «Lista de existencias valorizado»

(Resumen del plan de ingeniería inversa ya realizado.)

- **Objetivo:** Listado de **existencias** (stock por artículo y opcionalmente por depósito) con **valorización** (saldo × precio según lista de precios). Agrupaciones: por artículo, por rubro, por rubro/subrubro, por proveedor, por marca, por marca/modelo.
- **Tablas:** `articulo`, `stock_deposito`, `stock` (solo variante “fecha determinada”), `rubro`, `subrubro`, `proveedor`, `marca`, `modelo`, `deposito`.
- **Filtros fijos:** `articulo.tipo_art <> 'Gasto'`.
- **Filtros opcionales:** depósito (todos o uno), saldo > 0, artículo (uno o por id_manual), rubro, subrubro, proveedor, marca, modelo, rango de fechas en `stock.Fecha` (variante a fecha).
- **Parámetros:** empresa, depósito (texto), lista_precio (índice), TipoPres (Venta/Compra).

---

## 4. Diferencias en consultas y filtros

### 4.1 Propósito y alcance

| Aspecto | VB6 Lista existencias valorizado | Synap BO (bo-stock-facturacion) |
|---------|----------------------------------|----------------------------------|
| **Propósito** | Listado de existencias (saldo) por artículo/depósito, valorizado por lista de precios. | Análisis facturación + remitos no facturados + backorder con cobertura (stock, reservado, disponible, OC pendiente). |
| **Alcance de filas** | Todos los artículos (no Gasto) que cumplan filtros de depósito/rubro/proveedor/marca/modelo y opción “con/sin saldo cero”. | Solo artículos con **backorder > 0** en el período (PED Pendiente con `stockp.Fecha` en rango). |
| **Valorización** | Saldo × precio según **lista de precios** (parámetro). | Importes de backorder desde **PrecioNetoxR** en `stockp` (no lista de precios de artículo). |

### 4.2 Tablas utilizadas

| Tabla | VB6 Lista existencias valorizado | Synap BO |
|-------|----------------------------------|----------|
| **articulo** | Sí (tipo_art, IDArt, id_manual, relaciones rubro/subrubro/proveedor/marca/modelo). | Sí (id_manual, NombreArticulo; join a rubro). Filtro tipo_art <> 'Gasto' aplicado en detalle BO y detalle por renglón. |
| **stock_deposito** | Sí (saldo, id_deposito; filtro por depósito y opcional saldo > 0). | Sí (SUM(saldo) por id_articulo; opcional exclusión de depósitos). No filtro por un solo depósito. |
| **stock** | Sí en variante “fecha determinada” (filtro por Fecha). | No. |
| **rubro** | Sí (filtro/agrupación CodigoRubro). | Sí (solo nombre para categoría en detalle BO). |
| **subrubro** | Sí (filtro/agrupación IDSubRubro). | No. |
| **proveedor** | Sí (filtro Codigo). | Sí solo en detalle OC (proveedor de la OC). |
| **marca / modelo** | Sí (filtro/agrupación CodMarca, CodModelo). | No. |
| **deposito** | Sí (parámetro/nombre). | No (solo lista de id_deposito para excluir). |
| **comp_ped** | No. | Sí (PED para backorder, REM para remitos). |
| **stockp** | No. | Sí (renglones PED y OC). |
| **cuentacliente** | No. | Sí (facturación). |
| **cuentaproveedor** | No. | Sí (OC pendiente). |

### 4.3 Filtros comparados

| Filtro | VB6 Lista existencias valorizado | Synap BO |
|--------|----------------------------------|----------|
| **tipo_art <> 'Gasto'** | Siempre aplicado. | Sí aplicado (detalle BO y detalle por renglón; alineado con VB6). |
| **Depósito** | Todos o un depósito (id_deposito). | Opcional: solo los depósitos seleccionados suman al stock; si ninguno, todos. |
| **Saldo > 0** | Opcional (ComboValCero). | No (se muestra stock_actual aunque sea 0). |
| **Artículo / id_manual** | Opcional: un artículo o consulta por id_manual. | Implícito: solo artículos con BO en período. |
| **Rubro / subrubro** | Opcional (agrupación y filtro). | No (solo rubro como categoría en salida). |
| **Proveedor** | Opcional (agrupación y filtro). | No como filtro de existencias. |
| **Marca / modelo** | Opcional (agrupación y filtro). | No. |
| **Rango de fechas** | Solo en variante “fecha determinada” sobre **stock.Fecha**. | Facturación/remitos: `Fecha` en rango; backorder: **stockp.Fecha** en rango. |
| **Lista de precios** | Parámetro para valorización. | No (no hay valorización por lista). |
| **Clientes excluidos** | No. | Sí (payload). |

### 4.4 Consultas: diferencias clave

- **VB6:** La “consulta” de datos del listado de existencias valorizado está en los .rpt (Crystal); el VB6 solo aplica `RecordSelectionFormula` sobre tablas ya vinculadas en el .rpt. Típicamente: JOIN articulo + stock_deposito + deposito (+ stock si es a fecha) y joins a rubro, subrubro, proveedor, marca, modelo; filtro tipo_art <> 'Gasto'; valorización por lista de precios (Precio1V..Precio5V o equivalente según lista_precio).
- **Synap BO:** Varias consultas independientes (facturación, remitos, backorder con subconsultas). El “stock” entra solo como **stock_actual** = SUM(stock_deposito.saldo) por artículo, con opción de excluir depósitos. No hay consulta que liste “todos los artículos con su saldo y valorización”; solo artículos con backorder en el período, con columnas de cobertura (stock, reservado, disponible, OC pendiente) e importes derivados de PrecioNetoxR.

---

## 5. Qué habría que tener en Synap para equivaler a «Lista de existencias valorizado»

Para un reporte BO equivalente al VB6 «Lista de existencias valorizado» haría falta (resumen):

1. **Consulta principal:** Listado por artículo (y opcionalmente por depósito) desde `articulo` + `stock_deposito` (+ `stock` si se ofrece “a fecha”), con JOIN a rubro, subrubro, proveedor, marca, modelo, deposito.
2. **Filtros:** tipo_art <> 'Gasto'; depósito (todos / uno); opcional “solo con saldo > 0”; opcional artículo (uno o por id_manual); opcionales rubro, subrubro, proveedor, marca, modelo; si “a fecha”, rango sobre `stock.Fecha`.
3. **Valorización:** Campo calculado saldo × precio según **lista de precios** (mapeo lista_precio → Precio1V..Precio5V o tabla de precios) y parámetro TipoPres si aplica.
4. **Parámetros de salida:** empresa, depósito (texto), lista_precio, TipoPres.

Nada de esto está implementado en el reporte actual **bo-stock-facturacion**, que es un reporte distinto (backorder + facturación + remitos).

---

## 6. Referencias

- VB6: `administranet_vb6/Formularios/Info_Stock.frm` (subrutina `Listado_Existencia_Valorizado`, `ReporteC`).
- Reporte Crystal actual en uso (fuera del repo): `stock_listado_existencia_valorizado.rpt` (p. ej. en `/Users/sebastian/Downloads/Jesels/`). Formato binario; para consulta SQL/tablas abrir en Crystal Reports. Ver también [INFORME_VB6_PEDIDOS_POR_CLIENTE_GENERAL_Y_EXCEL_BBDDCALCULOCONSTOCK.md](INFORME_VB6_PEDIDOS_POR_CLIENTE_GENERAL_Y_EXCEL_BBDDCALCULOCONSTOCK.md) (sección 5).
- Synap BO: `reports/services/query_runner.py` (`_run_backorder_vs_stock_vs_facturacion`).
- Plan de ingeniería inversa VB6: `.cursor/plans/` (informe Lista existencias valorizado).
- Comparativa BO vs “Stock disponible/backorder” VB6: [INFORME_VB6_STOCK_DISPONIBLE_BACKORDER_VS_BO.md](INFORME_VB6_STOCK_DISPONIBLE_BACKORDER_VS_BO.md).
- Tablas: [docs/general/tablas/](../general/tablas/) (articulo, stock_deposito, stock, rubro, subrubro, proveedor, marca, modelo, deposito).
