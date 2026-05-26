# Tareas — resumen gerencial margen bruto

**Cambio:** `resumen-gerencial-margen-bruto`  
**Estado:** implementación aplicada (11/05/2026)

## 1. Backend — agregados

- [x] **1.1** En `executive_sales_summary.py`, extraer o reutilizar expresiones SQL de signo FA/NC para `PrecioNetoxR` y **`PrecioCostoxR`** (misma paridad que Top 10).
- [x] **1.2** Implementar función interna **totales margen** (venta neta líneas, costo neto líneas) para `fecha` + `cod_sucursal` opcional.
- [x] **1.3** Implementar agregación **por rubro** (`articulo` → `rubro`), bucket «Sin clasificar».
- [x] **1.4** Implementar agregación **por subrubro** (`articulo` → `subrubro`, incluir nombre rubro padre).
- [x] **1.5** Integrar resultados en `run_executive_summary`: objeto `margen_bruto`, listas `margen_por_rubro`, `margen_por_subrubro`, claves `meta` (`margen_costo_criterio`, `margen_venta_criterio`, bump `definicion` si aplica).
- [x] **1.6** Redondeo: importes a 2 decimales; porcentajes a 2 decimales; `null` cuando no aplique división.

## 2. Contrato y permisos

- [x] **2.1** Sin cambio de ruta ni permiso: sigue **`ManagerialReportsPermission`** y mismos query params (`fecha`, `sucursal`, `top_orden`).
- [x] **2.2** Documentar en respuesta que **`ventas_netas_dia`** (cuentacliente) puede no coincidir con **`margen_bruto.venta_neta_lineas`** (`meta.nota_venta_neta_lineas_vs_comprobante`).

## 3. Frontend

- [x] **3.1** `executive_summary.js`: parsear nuevas claves; renderizar KPIs de rentabilidad y tablas rubro/subrubro.
- [x] **3.2** `executive_summary.html`: contenedor semántico y clases alineadas al panel existente (ver `FUENTE_VERDAD_UI_REPORTES_MPR.md`).
- [x] **3.3** Manejo de listas vacías y `pct` nulo en UI (guion o «N/D»).

## 4. Pruebas

- [x] **4.1** Extender `test_executive_summary_contract.py`: presencia y tipos de `margen_bruto`, listas (o mocks con cursor fake si el patrón actual lo permite).
- [x] **4.2** Caso borde: venta neta líneas 0 → `pct_sobre_venta_lineas` nulo.

## 5. Documentación

- [x] **5.1** Mantener al día `docs/reports/SPEC_DASHBOARD_RESUMEN_EJECUTIVO_VENTAS.md` (KPIs y API).
- [x] **5.2** Spec principal `openspec/specs/reports-ejecutivo-ventas/spec.md` ya incorporaba REQ-MARG; contrato alineado a `executive-sales-v2`.

## 6. Verificación manual

- [ ] **6.1** Panel con sucursal «todas» y con sucursal filtrada: totales y tablas coherentes.
- [ ] **6.2** Día solo NC: signos y márgenes razonables.
