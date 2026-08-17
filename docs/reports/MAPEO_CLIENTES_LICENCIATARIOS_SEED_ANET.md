# Mapeo clientes seed → AdministraNET (VML)

**Informe:** Ventas Mensuales Licenciatarios (`ventas-mensuales-licenciatarios`)  
**Modelo:** `MonthlyReportingClientMatch`  
**Base canónica:** `administranet` @ `181.174.198.194:30804`  
**Fuente negocio:** `Libro1.xlsx` (17/08/2026) + confirmaciones manuales (Ghiano/Nolasco 17/08/2026)  
**Alcance:** el mismo vínculo seed→ANET alimenta el **pack de licenciatarios** (merger híbrido + panel de pendientes). No aplica a VMM (ese informe no usa seed).

---

## 1. Confirmados (aplicar vía modal/API match)

| Nombre en planilla (seed) | CUIT ANET | Código ANET | Nombre ANET | Notas |
|---------------------------|-----------|-------------|-------------|--------|
| AGALMA | 30-71175431-4 | 1091 | AGALMA | |
| MC PIE SRL | 30-71000570-9 | 1092 | MC PIE S.R.L. | |
| ML FULL | 27-34230002-8 | 348 | TREACY JENNIFER | Confirmado negocio 10/08/2026 |
| RADA TILLY | 30-55822868-3 | 1099 | LOMPAS SRL | Fantasía «RADA TILLY» |
| ALONSO JUAN JOSE | 20-16162791-8 | 1093 | JUAN JOSE ALONSO | |
| BELLETTINI JOSE | 20-23637940-0 | 1094 | JOSE GUSTAVO BELLETTINI | Planilla a veces «… GUSTAVO» |
| BRAVA MARKET | 30-71876976-7 | 1095 | BRAVAMARKET ARGENTINA S.A. | |
| DE GRUTTOLA JAVIER E HIJAS | 30-71654904-2 | **615** | DE GRUTTOLA JAVIER E HIJAS | CUIT también en 614 (`DE GRUTOLLA DOMINGO`); usar **615** |
| DELGADO JULIA MARCELA | 27-27561823-9 | 1096 | JULIA MARCELA DELGADO | |
| FALCON ESTEBAN LECINA | 20-27167406-7 | 303 | FALCO ESTEBAN LECINA | Typo planilla/ANET |
| FRALFE SPORT | 30-71901315-1 | 1097 | FRALFE SPORT S.A.S. | |
| JOSE MARIA BRUNO | 20-35292124-7 | 309 | MAURO BRUNO | Mismo CUIT |
| PARENTI KARINA VERONICA | 27-23628344-0 | 1098 | KARINA VERONICA PARENTI | |
| MARTIN GHIANO | 20-41618536-1 | **876** | SOTO GASTON NICOLAS | Alias comercial confirmado negocio 17/08/2026 |
| NOLASCO ARIEL | 30-71740107-3 | **1026** | ANORAK S.A. | Alias comercial confirmado negocio 17/08/2026 |

**Total:** 15/15 — sin pendientes de este listado.  
**Estado Postgres (17/08/2026):** seed ene–jul importado desde `Best Sox/Julio/reportesjul`; los 15 vínculos Libro1 aplicados (`estado=matched`, `base_empresa=administranet`). Quedan otros clientes seed en `pending` (no listados en Libro1) para match operativo vía UI.

Catálogo máquina: [`reports/data/monthly_reporting_client_matches_libro1.json`](../../reports/data/monthly_reporting_client_matches_libro1.json).

---

## 2. Operación

1. Importar seed Monthly Reporting (crea filas `MonthlyReportingClientMatch` en `pending`).  
2. Para cada fila de §1: API/modal de match del dashboard VML → vincular `anet_cliente_id` y `base_empresa=administranet`.
