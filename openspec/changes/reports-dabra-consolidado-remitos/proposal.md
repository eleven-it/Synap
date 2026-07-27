# Proposal: Informe DABRA consolidado remitos (Excel + preview)

## Intent

Best Sox (DABRA) necesita mensualmente un Excel de líneas de factura con remito, fiel a `DABRA MMYYYY.xlsx`. Synap lo generará para FA completas en AdministraNET/Synap, con preview y alarmas de integridad sin bloquear export.

## Scope

### In Scope
- Slug `dabra-consolidado-remitos`: preview tabs REPORTE + TOTAL FACTURAS; export `DABRA MMYYYY.xlsx`.
- Cliente fijo DABRA (`Codigo=368`); filtros Mes | Año (fecha factura).
- FA no anuladas, sin NC/ND; granularidad línea; desfasajes remito/FA alarmados, no bloquean.
- Columnas A–AW y TOTAL FACTURAS según sample; valores calculados; preview B,D,E,F,NombreArticulo,G–N,Q,R,S,U,V,X.
- Permiso nuevo; `base_empresa` sesión; Σ líneas vs cabecera obligatorio.

### Out of Scope
- Otro cliente; NC/ND; FA importadas/incompletas BEST anterior; UnidMed; O/P vacías; Y–AW cero.

## Capabilities

### New Capabilities
- `reports-dabra-consolidado-remitos`: servicio, relay, export openpyxl, dashboard, permiso, tests.

### Modified Capabilities
- None

## Approach

Patrón `reports-cobranzas-vendedor`: `reports/services/dabra_consolidado_remitos.py`, `ReportDefinition`, relay, dashboard UI canónica, export openpyxl.

Join `cuentacliente`+`stock`+`rem_fact`→`comp_ped`. PV/legal desde `NroComprobante`. CAE `fe_cae`/`fe_vto_cae`. NroCUIT empresa. Item/talle `CodArtProv`; categoría default ACCESORIOS. Entrega=Suc=`NroCalle` (domicilio remito; multi-remito→design). Precio bruto pre-bonif; bonif % línea; IVA alícuota artículo; importes validados, no recalculados ciegamente. Un pedido por remito; CompRef/NumeroRef del remito.

**Validación dev:** sin tocar `.env` repo; override sesión a LAN `192.168.0.2:30804`/`administranet` (BEST SOX). Prueba: FA 24/07/2026 PV 0008.

## Affected Areas

| Area | Impact |
|------|--------|
| `reports/services/dabra_consolidado_remitos.py` | New |
| `reports/views/`, relay, migrations | New |
| `core/constantes_permisos.py` | Modified |
| `reports/tests/`, `docs/reports/` | New |

## Risks

| Risk | Mitigation |
|------|------------|
| Multi-remito por FA | Design: fila por remito |
| Σ ≠ cabecera | Error export; debug Desarrollo |
| Paridad Excel | Tests vs sample |

## Rollback Plan

Quitar `ReportDefinition`, permiso, servicio, relay y tests. Sin DDL MySQL.

## Dependencies

MySQL legacy, openpyxl, sample `DABRA MMYYYY.xlsx`.

## Success Criteria

- [ ] Export/preview coinciden sample para mes DABRA.
- [ ] Alarmas visibles; export no bloqueado.
- [ ] Permiso y validación totales OK.
- [ ] Tests contenedor con FA 24/07/2026 PV 0008.
