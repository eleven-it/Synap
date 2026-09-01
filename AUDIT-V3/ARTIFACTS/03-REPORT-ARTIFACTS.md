# 03 — Report Artifacts

**Estado:** COMPLETE

| Type | Mechanism | Format |
|------|-----------|--------|
| Interactive dashboard | Browser render | HTML + JSON widgets |
| Dashboard export | `/api/reports/export/?type=xlsx` | XLSX |
| Monthly reporting pack | `ventas_mensuales_licenciatarios_export.py` | XLSX templates |
| Builder export/import | `export_import_service.py` | JSON config |
| MPR reportes | `mpr/export.py` | CSV, XLSX |
| Contabilidad export | `contabilidad_audit/export.py` | CSV, XLSX |
| Executive PDF | **Not in reports module** — PDF via reportlab in other modules only |

## Distinction

- **Interactive:** stays in browser, queries live MySQL
- **Export snapshot:** file download, point-in-time
- **Scheduled:** **NOT implemented** (`reports.programar` perm exists, no worker)

## Relation to Reports Engine

Export uses `ExportService` + `ReportDefinition` config — same data as dashboard, different delivery channel.
