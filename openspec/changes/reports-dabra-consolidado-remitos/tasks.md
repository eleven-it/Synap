# Tasks: Informe DABRA consolidado remitos

**Change:** `reports-dabra-consolidado-remitos` · **TDD:** strict · **Runner:** `docker exec Synap_app python manage.py test reports.tests.test_dabra_consolidado_remitos`

**Cierres producto (v1):** PV col D zero-pad **5**; string `Comprobante` TOTAL con PV **4** (`A000400020777`). `CompRef`=PV remito pad 5; `NumeroRef`=nº remito (máscara 8). Bonif=`pordesc_bonif`≠0 else `PorDesc`; no usar `cliente.Descuento` si ambos 0. Layout A–AW fiel a sample `DABRA 052026.xlsx` (headers exactos, espacios trailing P904/P908/P912/P916/P920). **CAE v1:** incluir fila con CAE vacío + alarma (`alarmas[]`); *nota:* diverge escenario REQ-DABRA-003 (excluir) — ajustar spec en apply si aplica.

---

## Phase 1: Foundation

- [x] 1.1 Añadir `("reports.dabra_consolidado_remitos", "Informe DABRA consolidado remitos")` en `core/constantes_permisos.py`
- [x] 1.2 Crear `DabraConsolidadoRemitosPermission` en `reports/permissions.py` (patrón cobranzas-vendedor)
- [x] 1.3 Crear migration `reports/migrations/0032_add_dabra_consolidado_remitos_report.py` (`ReportDefinition` slug `dabra-consolidado-remitos`, guarda tabla + reverse, patrón `0030`)
- [x] 1.4 Crear stubs vacíos: `reports/services/dabra_consolidado_remitos.py`, `..._export.py`, `reports/dabra_consolidado_remitos_relay_views.py`
- [x] 1.5 Registrar rutas en `reports/api_urls.py`: `dabra-consolidado-remitos/relay/` y `.../relay/export/`

## Phase 2: Tests RED

- [x] 2.1 Crear `reports/tests/test_dabra_consolidado_remitos.py` — parse `NroComprobante` → PV pad-5 col D, legal máscara 8, letra+PV4+legal8 (`REQ-DABRA-006`)
- [x] 2.2 RED: `CompRef`/NumeroRef remito (PV pad-5 / nº máscara 8), letra REM `R` (`REQ-DABRA-005`)
- [x] 2.3 RED: bonif fallback `pordesc_bonif`→`PorDesc`; ambos 0 ⇒ 0 (no `cliente.Descuento`)
- [x] 2.4 RED: `CodArtProv`→item/talle; categoría default `ACCESORIOS` (`REQ-DABRA-008`)
- [x] 2.5 RED: tolerancia Σ `max(0.05, 0.01×n_lineas)` neto/bruto; mismatch ⇒ `errores[]` (`REQ-DABRA-016`)
- [x] 2.6 RED: servicio mock cursor — filtros mes/año, `Codigo=368`, `TipoComprobante='FA'`, `Anulado='No'`, `base_empresa` sesión (`REQ-DABRA-001/002/004`)
- [x] 2.7 RED: expansión multi-remito (2 filas/línea); 0 remitos ⇒ refs vacías + alarma; Σ antes de expandir
- [x] 2.8 RED: FA sin `fe_cae` ⇒ fila incluida, CAE vacío, alarma en payload (cierre producto #5)
- [x] 2.9 RED: relay 403 sin permiso, 400 sin mes/año, 409 con errores Σ, 200 preview OK (`REQ-DABRA-018`)
- [x] 2.10 RED: exporter — 2 hojas, `DABRA MMYYYY.xlsx`, O/P vacías, Y–AW=0, sin `NombreArticulo`, headers sample (`REQ-DABRA-011/012/013`)

## Phase 3: Core Implementation (GREEN)

- [x] 3.1 Implementar helpers puros en `dabra_consolidado_remitos.py`: parse PV/legal, letra tipo, `CodArtProv`, bonif, tolerancia Σ
- [x] 3.2 Implementar SQL parametrizado + materialización línea×remito: joins `cuentacliente`/`stock`/`articulo`/`rem_fact`/`comp_ped`/`cda`/`cliente_domicilio`; Entrega=Suc=`NroCalle` por REM
- [x] 3.3 Implementar `get_dabra_consolidado_remitos(...)`: validación Σ pre-expansión, `totales_facturas` (1 fila/FA, Comprobante PV4), alarmas, `COLUMNS_PREVIEW`, normalización `administranet_types`
- [x] 3.4 Implementar `exportar_dabra_xlsx(...)` en `dabra_consolidado_remitos_export.py`: hoja REPORTE A–AW + TOTAL FACTURAS; CUIT `datosempresa.CUIT` 11 dígitos
- [x] 3.5 Implementar relay GET preview + export en `dabra_consolidado_remitos_relay_views.py` (409 si `errores`, mensajes español)

## Phase 4: Integration / UI

- [x] 4.1 En `reports/views.py`: slug `dabra-consolidado-remitos` → template dedicado + `dabra_api_url`/`dabra_export_url`
- [x] 4.2 Crear `reports/templates/reports/includes/filters_mes_anio.html` (Mes 1–12 + Año)
- [x] 4.3 Crear `dashboard_dabra_consolidado_remitos.html`: canon reportes, tabs REPORTE/TOTAL FACTURAS, panel alarmas/errores, export, `SynapMessages` (sin diálogos nativos) (`REQ-DABRA-017`)

## Phase 5: Verification

- [x] 5.1 Ejecutar suite completa en contenedor; todos los tests GREEN
- [ ] 5.2 Validación manual LAN: sesión `base_empresa` → BEST SOX; Mes=7 Año=2026; comparar export vs sample con FA 24/07/2026 PV 0008

## Phase 6: Documentation

- [x] 6.1 Crear `docs/reports/INFORME_DABRA_CONSOLIDADO_REMITOS.md`: mapeo A–AW↔legacy, alarmas, formatos PV/CompRef, override dev sin `.env`, nota CAE v1 vs spec
