# Ingeniería inversa: «Pedidos por cliente general» (Info_Venta) y Excel bbddcalculoconstock

**Fecha:** 2026-03-02  
**Objetivo:** Ingeniería inversa del informe VB6 «Pedidos por cliente general» en Info_Venta.frm, con filtrado por Todas las Sucursales, Todos los Punto de venta, intervalo 01/01/2026 a hoy y Lista completa; y su uso junto con «Lista de existencias valorizado» para el Excel bbddcalculoconstock.xls que debe replicar el reporte BO.

---

## 1. Identificación del informe en VB6

El informe **«Pedidos por cliente general»** corresponde al **id_reporte 208** («Pedidos por cliente - Todos») en [Info_Venta.frm](administranet_vb6/Formularios/Info_Venta.frm).

| id_reporte | Nombre en formulario | .rpt | Uso |
|------------|----------------------|------|-----|
| **208** | Pedidos por cliente - Todos | ventas_pedidos_cliente_todos.rpt | **Informe de referencia:** lista completa de clientes, sin filtro por estado de comprobante. |
| 233 | Lista de pedidos resumen / detalle | ventas_pedidos_resumen_cliente.rpt (Combo_Filtro_PR = 1) | Variante resumen/detalle por cliente. |
| 6 | Pedidos por cliente | ventas_pedidos_cliente.rpt | Incluye filtro por Estado del comprobante (estado_comp). |

Para **Todas las Sucursales, Todos los Punto de venta, 01/01/2026 a hoy, Lista completa** el informe a replicar en el BO es **id 208** (ventas_pedidos_cliente_todos.rpt).

---

## 2. Reporte 208 – Pedidos por cliente - Todos (informe de referencia)

### 2.1 Ubicación

- **Formulario:** [administranet_vb6/Formularios/Info_Venta.frm](administranet_vb6/Formularios/Info_Venta.frm)
- **Disparo:** `If reporte.BoundText = 208 Then` (bloque aprox. líneas 8762–8836)
- **Archivo Crystal:** ventas_pedidos_cliente_todos.rpt

### 2.2 Filtros para «Pedidos por cliente general»

- **Todas las sucursales:** selec_sucursal.ListIndex = 0 → filtro_sucursal_comp_ped = `" AND ({comp_ped.CodSucursal} <> 0)"`
- **Todos los Punto de venta:** selec_pv.ListIndex = 0 (no se agrega condición sobre id_pv).
- **Lista completa:** opcion_cliente_completo.Value = True (todos los clientes).

RecordSelectionFormula en ese caso (línea ~8801):

```text
"({comp_ped.Anulado} = 'No') And ({comp_ped.Fecha} >= " & F1 & " and {comp_ped.Fecha} <= " & F2 & ") and
 ({comp_ped.TipoComprobante} = 'PED') And ({comp_ped.CodigoMovimiento} <> 0) " & filtro_sucursal_comp_ped
```

- **F1, F2:** fechas Crystal (Desde, Hasta). Para el caso: 01/01/2026 a hoy.
- No se filtra por estado de comprobante (a diferencia del id 6).

### 2.3 Parámetros del reporte

- **empresa:** Principal.nombre_empresa  
- **sucursal:** "Todas" si selec_sucursal.ListIndex = 0, si no Sucursal.Text  

### 2.4 Tablas involucradas (inferidas)

- **comp_ped:** cabecera de pedidos (Fecha, TipoComprobante, Anulado, CodSucursal, CodigoMovimiento, Codigo cliente, id_pv, etc.).
- **cliente:** datos del cliente (join por comp_ped.Codigo).
- **stockp:** renglones del pedido (habitual en reportes de PED).
- Posibles en el .rpt: articulo, rubro, etc. La consulta SQL exacta está en el .rpt.

---

## 3. Resumen: consulta equivalente para «Pedidos por cliente general» (id 208)

Para replicar en el BO el informe «Pedidos por cliente general» con:

- Todas las Sucursales  
- Todos los Punto de venta  
- Fechas: 01/01/2026 a hoy  
- Lista completa (todos los clientes)  

la lógica de filtrado debe ser:

- **Tabla principal:** comp_ped (y renglones en stockp u otra tabla de detalle según el .rpt).
- **Condiciones:**
  - comp_ped.TipoComprobante = 'PED'
  - comp_ped.Anulado = 'No'
  - comp_ped.Fecha >= '2026-01-01' AND comp_ped.Fecha <= &lt;fecha_hoy&gt;
  - comp_ped.CodigoMovimiento <> 0 (o IS NOT NULL)
  - comp_ped.CodSucursal <> 0 (todas las sucursales; no restringir a una).
- **Punto de venta:** no filtrar por id_pv (todos los PV).
- **Cliente:** no filtrar por Codigo (lista completa).

Campos típicos a exponer (según .rpt): cliente (Codigo, nombre), comp_ped (Fecha, NroComprobante, Estado, etc.), renglones (artículo, cantidad, precios), sucursal, punto de venta si existe en comp_ped.

---

## 4. Relación con «Lista de existencias valorizado» y Excel bbddcalculoconstock.xls

- **Lista de existencias valorizado** (Info_Stock, id_reporte 27): listado de stock por artículo/depósito valorizado; tablas: articulo, stock_deposito, stock (a fecha), rubro, subrubro, proveedor, marca, modelo, deposito; filtros tipo_art <> 'Gasto', depósito, lista de precios, etc. (ver [COMPARATIVA_VB6_LISTA_EXISTENCIAS_VALORIZADO_VS_BO_SYNAP.md](COMPARATIVA_VB6_LISTA_EXISTENCIAS_VALORIZADO_VS_BO_SYNAP.md) y plan de ingeniería inversa).
- **Pedidos por cliente general** (Info_Venta, **id 208**): listado de pedidos (comp_ped + detalle) para todos los clientes, todas sucursales, todos PV, en el rango de fechas.

El Excel **bbddcalculoconstock.xls** que se usa como resultado objetivo del reporte BO se armaba a partir de estos dos informes VB6. El archivo .xls es binario y no se puede leer desde el repositorio; para replicar exactamente el BO hace falta:

1. **Estructura del Excel:** columnas, hojas, fórmulas y relaciones entre «pedidos por cliente» y «existencias valorizado» (por ejemplo: demanda por artículo desde pedidos vs stock disponible por artículo). Conviene exportar bbddcalculoconstock.xls a CSV o describir en un documento las hojas y columnas.
2. **Reglas de negocio:** cómo se cruzan pedidos y stock (por artículo, por depósito, por lista de precios, etc.) y qué totales o indicadores se calculan (cobertura, faltantes, valorizado, etc.).

Con eso se puede definir un único reporte BO que:
- Incluya (o reutilice) la lógica de «Lista de existencias valorizado» (stock valorizado).
- Incluya la lógica de «Pedidos por cliente general» (pedidos con filtros indicados).
- Genere una salida (tabla/Excel/descarga) equivalente a bbddcalculoconstock.xls.

---

## 5. Reportes Crystal (.rpt) actualizados en uso

Los reportes que se están usando actualmente para exportar a Excel y armar el reporte (bbddcalculoconstock) son:

| Informe VB6 | Archivo .rpt (referencia actual) |
|-------------|----------------------------------|
| Lista de existencias valorizado (id 27) | `stock_listado_existencia_valorizado.rpt` |
| Pedidos por cliente - Todos (id 208) | `ventas_pedidos_cliente_todos.rpt` |

**Ubicación (fuera del repo):**
- `/Users/sebastian/Downloads/Jesels/stock_listado_existencia_valorizado.rpt`
- `/Users/sebastian/Downloads/Jesels/ventas_pedidos_cliente_todos.rpt`

Los archivos `.rpt` son binarios (formato Crystal Reports). Para obtener la consulta SQL exacta, las tablas y los campos de cada reporte hay que abrirlos en Crystal Reports (o SAP BusinessObjects) y revisar *Database Expert* / *Report Designer* (vínculos de tablas, comandos SQL si existen, fórmulas y campos colocados). Es recomendable documentar en este directorio o en `docs/general/` la estructura extraída (tablas, columnas, filtros del .rpt) para alinear el desarrollo del reporte BO.

---

## 6. Referencias

- VB6 Info_Venta: [administranet_vb6/Formularios/Info_Venta.frm](administranet_vb6/Formularios/Info_Venta.frm) (reporte **208** = Pedidos por cliente - Todos, líneas 8762–8836).
- VB6 Info_Stock – Lista existencias valorizado: [administranet_vb6/Formularios/Info_Stock.frm](administranet_vb6/Formularios/Info_Stock.frm) (Listado_Existencia_Valorizado).
- Comparativa existencias valorizado vs BO: [COMPARATIVA_VB6_LISTA_EXISTENCIAS_VALORIZADO_VS_BO_SYNAP.md](COMPARATIVA_VB6_LISTA_EXISTENCIAS_VALORIZADO_VS_BO_SYNAP.md).
- Excel objetivo: `/Users/sebastian/Downloads/Jesels/bbddcalculoconstock.xls` (revisar estructura y reglas fuera del repo).
- Tablas: comp_ped, stockp, cliente, articulo, stock_deposito; ver [docs/general/tablas/](../general/tablas/).
