# Verificación UAT — Command Center financiero

**Fecha:** 19/05/2026  
**Base:** `administranet` (MySQL local contenedor)  
**Período:** 01/05/2026 – 19/05/2026  

## Comando

```bash
docker exec Synap_app python manage.py uat_tesoreria_cashflow \
  --fecha-inicio=2026-05-01 --fecha-fin=2026-05-19
```

## Paridad tesorería vs `cash_flow_waterfall`

| Métrica | Command Center | Waterfall | Diff | Estado |
|---------|----------------|-----------|------|--------|
| saldo_inicial | 4.662.293.269,59 | 4.662.293.269,59 | 0,00 | OK |
| saldo_final | 4.703.072.829,09 | 4.703.072.829,06 | 0,03 | OK |
| ingresos_operativos | 40.779.559,47 | 40.779.559,47 | 0,00 | OK |
| egresos_operativos | 0,00 | 0,00 | 0,00 | OK |

Tolerancia: 1,00 ARS. La diferencia de saldo final (0,03) es redondeo al sumar últimos `caja.Saldo` por caja.

## Contexto del período (dato de negocio)

- 19 movimientos en `caja` (solo cheques `CHEQ`, ingresos).
- `ingresos_cobranzas` = total operativo; `ingresos_ventas` = 0 (coherente: no hay FA/FB en el período).
- **Ventas cobros:** facturado 0 (sin filas `resumen_venta_cv` en el período); cobrado en caja 40.779.559,47 (= ingresos caja).

## Specs

- REQ-ED-TES saldos y flujos: cubierto por paridad waterfall.
- REQ-ED-COB dos series: responden; facturado 0 es dato real del período, no bug.
- Sin `areas.impuestos`: OK.

## Conclusión

**P0 aprobado para despliegue** en entorno con misma semántica que informe cash-flow. Recomendación: repetir UAT en empresa piloto con período que incluya FA + REC + `resumen_venta_cv`.
