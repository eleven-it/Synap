# 04 — Export / Import Artifacts

**Estado:** COMPLETE

| Format | Import | Export |
|--------|--------|--------|
| **XLSX** | pedido masivo plantilla/import | reports, mpr, stock, contabilidad, sia |
| **XLSM** | pedido masivo (macros) | — |
| **CSV** | — | mpr reportes, contabilidad, TN clientes |
| **JSON** | reports builder import | reports builder export |
| **PDF** | OCR captura (read) | pedidos, OPT, stock, lista precios |
| **TXT** | — | legacy scripts |

## Validation

- Pedido masivo: extension check + `pedido_masivo_import.py` schema validation
- Monthly reporting: importer with row validation
- TN CSV export: AJAX generated

## Encoding

- CSV contabilidad: UTF-8
- Legacy scripts: `;` separator

## Business usage

| Artifact | Criticality |
|----------|:-------------:|
| Pedido masivo xlsx | HIGH — daily ops |
| Reports xlsx export | HIGH — management |
| Builder JSON | MEDIUM — admin |
| TN CSV export | LOW |
