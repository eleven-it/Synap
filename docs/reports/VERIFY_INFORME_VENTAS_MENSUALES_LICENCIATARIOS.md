# Verificación: Informe «Ventas Mensuales Licenciatarios»

**Fecha:** 08/08/2026  
**Change SDD:** `historial-licenciatarios-hibrido`  
**Spec:** [SPEC_INFORME_VENTAS_MENSUALES_LICENCIATARIOS.md](SPEC_INFORME_VENTAS_MENSUALES_LICENCIATARIOS.md)  
**Plan:** [PLAN_INFORME_VENTAS_MENSUALES_LICENCIATARIOS.md](PLAN_INFORME_VENTAS_MENSUALES_LICENCIATARIOS.md)

---

## Matriz requisitos

| Req. | Criterio | Estado |
|------|----------|--------|
| R1 | Modelos seed PostgreSQL + constraints `(pack,match,month)` | OK (tests Ph1) |
| R2 | Import idempotente SHA-256 + `--replace` auditable | OK (tests Ph2) |
| R3 | Merger cutover 21/22 julio sin doble conteo YTD | OK (tests Ph3) |
| R4 | Match cliente auditable + pendientes visibles | OK (tests Ph4) |
| R5 | Runner híbrido + export 6 packs + hoja QA | OK (tests Ph5) |
| R6 | API permisos + modal Synap + rango mismo año | OK (tests Ph6) |
| R7 | Conciliación planilla vs seed (dry-run) | OK (tests Ph7) |
| R8 | Paridad signos FA/NC vía reglas VMM compartidas | OK (tests Ph3 + VMM) |

---

## Tests automatizados

```bash
docker exec Synap_app python manage.py test \
  reports.tests.test_ventas_mensuales_licenciatarios \
  reports.tests.test_ventas_marcas_mensual \
  --keepdb
```

**Resultado 08/08/2026:** **105/105 OK** (65 licenciatarios + 40 VMM).

Desglose licenciatarios:

| Fase | Tests | Ámbito |
|------|-------|--------|
| Ph1 | constraints, fixtures 6 packs | modelos + plantillas |
| Ph2 | import hash/replace/rollback | importer xlsx |
| Ph3 | reglas VMM, cutover YTD, NC signos | merger + rules |
| Ph4 | match pending/matched, DZ/PK | match + SuperArt |
| Ph5 | runner híbrido, export openpyxl | runner + export |
| Ph6 | API permisos, modal Synap, dd/MM/yyyy | API + UI contract |
| Ph7 | conciliación seed vs planilla | reconciliation service |

---

## Conciliación operativa (Ph7)

Comando dry-run (solo lectura):

```bash
docker exec Synap_app python manage.py reconcile_monthly_reporting_seed \
  --source-dir "/Users/sebastian/Documents/Best Sox/fwdreportesjun"
```

Por pack:

```bash
docker exec Synap_app python manage.py import_monthly_reporting_seed \
  --seed-packs --pack levis_bw \
  --file "/Users/sebastian/Documents/Best Sox/fwdreportesjun/Monthly Reporting Best Sox_LEVIS BW 26.xlsx"

docker exec Synap_app python manage.py reconcile_monthly_reporting_seed \
  --pack levis_bw \
  --source-dir "/Users/sebastian/Documents/Best Sox/fwdreportesjun"
```

**Nota:** montar la carpeta fuente en el contenedor si la ruta host no es visible desde `Synap_app`.

**FA/NC:** la conciliación seed cubre ene–jun; la porción ANET (≥22/07/2026) se valida con `ventas_marcas_mensual_rules` (whitelist FA/NC, anulados) — no paridad binaria xlsx.

---

## Smoke manual sugerido

1. Abrir `/reports/dashboard/ventas-mensuales-licenciatarios/`
2. Elegir pack + rango 01/01/2026–31/12/2026 (mismo año) → Actualizar
3. Verificar **matriz cliente × mes** (unidades + monto) debajo del resumen; no solo KPIs
4. Verificar que al recorrer clientes **no se mueve** el menú, el título ni el resumen: solo scrollea la tabla (cabeceras de mes y columna Cliente quedan visibles)
5. Verificar panel QA / clientes pendientes de match
6. En el banner, **Exportar Excel** → `input Licensee sales` con encabezados en inglés (`Customer`, `City / Province`, `Store Type`, `Product group`), valores de city/store/group del seed, **totales en fila 2** (`=SUM(...)`); `monthly` sigue enlazando a esa fila 2. Conservar `ooh`/`minimum agreed` en LW/Puma. Sin pack seleccionado debe avisar, no descargar.
7. Supervisor: vincular cliente pendiente vía modal Synap (sin `alert`/`confirm`)
8. Tras import seed: ejecutar conciliación dry-run → 0 discrepancias ene–jun

---

## Pendientes fuera de alcance VERIFY

- Planillas actualizadas post-junio con seed jul 1–21 (recepción negocio)
- Filtros ANET exactos por pack (§10.2 análisis) — confirmación negocio
- Paridad pixel-perfect `.xlsb` Puma (export usa `.xlsx` equivalente)
