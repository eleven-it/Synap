# Verificación — Command Center financiero

**Change:** `adminnet-module-migration-command-center-finance`  
**Modo:** Standard (hybrid)  
**Veredicto:** PASS WITH WARNINGS

---

## Verificación UAT P0

**Fecha:** 19/05/2026  
**Base:** `administranet` (MySQL local contenedor)  
**Período:** 01/05/2026 – 19/05/2026  

### Comando

```bash
docker exec Synap_app python manage.py uat_tesoreria_cashflow \
  --fecha-inicio=2026-05-01 --fecha-fin=2026-05-19
```

### Paridad tesorería vs `cash_flow_waterfall`

| Métrica | Command Center | Waterfall | Diff | Estado |
|---------|----------------|-----------|------|--------|
| saldo_inicial | 4.662.293.269,59 | 4.662.293.269,59 | 0,00 | OK |
| saldo_final | 4.703.072.829,09 | 4.703.072.829,06 | 0,03 | OK |
| ingresos_operativos | 40.779.559,47 | 40.779.559,47 | 0,00 | OK |
| egresos_operativos | 0,00 | 0,00 | 0,00 | OK |

Tolerancia: 1,00 ARS. La diferencia de saldo final (0,03) es redondeo al sumar últimos `caja.Saldo` por caja.

### Contexto del período (dato de negocio)

- 19 movimientos en `caja` (solo cheques `CHEQ`, ingresos).
- `ingresos_cobranzas` = total operativo; `ingresos_ventas` = 0 (coherente: no hay FA/FB en el período).
- **Ventas cobros:** facturado 0 (sin filas `resumen_venta_cv` en el período); cobrado en caja 40.779.559,47 (= ingresos caja).

### Specs P0

- REQ-ED-TES saldos y flujos: cubierto por paridad waterfall.
- REQ-ED-COB dos series: responden; facturado 0 es dato real del período, no bug.
- Sin `areas.impuestos`: OK.

**P0 aprobado para despliegue** en entorno con misma semántica que informe cash-flow.

---

## Verificación P1 — tests de contrato

**Fecha:** 14/07/2026

### Comando

```bash
docker exec Synap_app python manage.py test \
  reports.tests.test_executive_dashboard_contract \
  reports.tests.test_caja_classification --keepdb
```

### Resultado

| Métrica | Valor |
|---------|-------|
| Tests ejecutados | 35 |
| Pasados | 35 |
| Fallidos | 0 |
| Exit code | 0 |

**Estado:** ✅ OK

### Cobertura por spec (matriz resumida)

| Requisito | Escenario | Test | Resultado |
|-----------|-----------|------|-----------|
| REQ-ED-TES P0 | Estructura resumen caja | `test_fetch_tesoreria_resumen_estructura` | ✅ COMPLIANT |
| REQ-ED-TES P1 | Banco `librobanco` | `test_fetch_tesoreria_banco_resumen_estructura` | ✅ COMPLIANT |
| REQ-ED-COB P0 | Dos series facturado/cobrado | `test_fetch_ventas_cobros_resumen_estructura` | ✅ COMPLIANT |
| REQ-ED-ORCH | 7 áreas + banco anidado | `test_run_command_center_estructura` | ✅ COMPLIANT |
| REQ-ED-ORCH | Endpoints P1 en meta | `test_run_command_center_estructura` | ✅ COMPLIANT |
| REQ-ED-ORCH | Degradación tesorería | `test_run_command_center_aisla_fallo_tesoreria` | ✅ COMPLIANT |
| REQ-ED-ORCH | Sin impuestos | `test_run_command_center_estructura` | ✅ COMPLIANT |
| Clasificación caja | REC→cobranzas, FA→ventas | `test_caja_classification` (13 tests) | ✅ COMPLIANT |

---

## Completitud de tareas

| Métrica | Valor |
|---------|-------|
| Tareas totales | 24 (incl. P1.1–P1.3) |
| Completadas | 24 |
| Incompletas | 0 |

---

## Advertencias (no bloqueantes)

1. **P1 sin UAT manual:** banco (`librobanco`), detalle cobros y movimientos caja no tienen paridad documentada contra informes legacy (solo contrato JSON en tests).
2. **Escenarios 403/503 HTTP:** cubiertos parcialmente (degradación orquestador sí; endpoints aislados sin `APIClient` completo).
3. **Timeout MySQL en tests:** escenarios de degradación simulan timeout tesorería (esperado en suite).

---

## Veredicto final

**PASS WITH WARNINGS** — P0 con UAT waterfall OK; P1 con 35/35 tests de contrato OK (14/07/2026). Apto para archive; repetir UAT P1 en empresa piloto con período FA + REC + `resumen_venta_cv`.
