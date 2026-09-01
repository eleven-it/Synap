# 06 — Artifact Lifecycle

**Estado:** COMPLETE

## Generic lifecycle

```text
Generate → Validate → Store → Deliver → View → Download → Archive → Delete
```

## By artifact type

| Artifact | Generate | Validate | Store | Deliver | Retention |
|----------|----------|----------|-------|---------|-----------|
| Report XLSX | ExportService | SQL + permissions | ephemeral HTTP | download | session |
| Pedido PDF | reportlab | business rules | none | HTTP | — |
| OCR documento | upload | MIME + size 15MB | filesystem/PG | web view | empresa-scoped |
| EcomMailQueue | checkout | template | PG queue | SMTP | processed flag |
| Backup | backup_run | checksum | SFTP/local | email notify | policy-driven |
| Builder JSON | export API | schema | download | file | user-managed |
| Ticket print | TPV confirm | stock rules | none | browser print | — |

## Gaps

- No unified artifact registry
- No version history for exports (except ReportDefinitionVersion for config, not output files)
- Expediente files — lifecycle in PG but no archival policy documented
