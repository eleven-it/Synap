# Propuesta: resumen gerencial — margen bruto total y por rubro/subrubro

**Fecha:** 11/05/2026

## Intención

Ampliar el panel **Resumen ejecutivo (ventas)** con indicadores de **rentabilidad** alineados a la facturación del día: **margen bruto** agregado y **desglose por rubro y subrubro**, usando la misma ventana de datos (fecha contable, comprobantes FA/NC, `stock` por renglón, filtro sucursal opcional).

## Alcance

- Extender **`GET /api/reports/executive-summary/`** y **`run_executive_summary`** con agregados de venta neta y costo por renglón (`PrecioNetoxR`, `PrecioCostoxR`) y agrupación por **`rubro`** / **`subrubro`** vía **`articulo`**.
- UI: bloque gerencial (KPIs y/o tabla jerárquica o dos tablas) en **`executive_summary.html`** + **`executive_summary.js`**, coherente con la fuente de verdad UI de reportes/MPR.
- Tests de contrato en **`test_executive_summary_contract.py`**.
- Documentación: **`docs/reports/SPEC_DASHBOARD_RESUMEN_EJECUTIVO_VENTAS.md`**, spec OpenSpec **`reports-ejecutivo-ventas`**, delta en esta carpeta.

## Fuera de alcance (v1)

- Series históricas de margen (solo día de referencia como el resto del panel).
- Margen por PV, vendedor o cliente.
- Recalcular costo con **`articulo.PrecioCosto`** actual (la v1 usa **costo de renglón** del comprobante).

## Riesgos

- **Conciliación:** el KPI **`ventas_netas_dia`** proviene de **`cuentacliente.SubtotalDesc`**; la suma de **`stock.PrecioNetoxR`** puede diferir por redondeos, descuentos a nivel comprobante o líneas especiales. La spec documenta que el **% de margen** se calcula sobre **venta neta de líneas** incluidas en el universo `stock`, no forzando igualdad con `ventas_netas_dia`.
- **Renglones sin artículo:** se agrupan como «Sin clasificar».
- **Rendimiento:** dos consultas agregadas adicionales (total + por categoría); monitorizar en empresas con alto volumen.
