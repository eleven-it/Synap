# Tasks: Descuento al pie en facturación VMM

**Change:** `vmm-dto-pie-facturacion`  
**Capability:** `reports-ventas-marcas-mensual`  
**Orden:** T1 → T2 → T3 → T4/T5 (paralelo posible) → T6 → T7 → T8

---

## Fase 1 — Módulo compartido (T1)

**Depende de:** —  
**REQ:** REQ-VMM-PIE-02, REQ-VMM-PIE-06

- [x] **T1.1** Crear `reports/services/comprobante_descuento_cabecera.py` con `factor_descuento_cabecera(subtotal1, subtotal_desc)` movida desde `dabra_consolidado_remitos.py` (líneas ~203–218), normalizando con `to_decimal_or_none` / `_dec` sin cambiar semántica.  
  **Done:** función idéntica a DABRA; `SubTotal1==0` → `Decimal("1")`; `SubtotalDesc is None` → factor 1.

- [x] **T1.2** En el mismo módulo, mover `porcentaje_descuento_cabecera` (líneas ~131–155 DABRA) y añadir `sql_factor_descuento_cabecera_expr(subtotal1_col="cc.SubTotal1", subtotal_desc_col="cc.SubtotalDesc")` con `CASE WHEN ABS(COALESCE(SubTotal1,0)) < 0.0001 THEN 1 ELSE COALESCE(SubtotalDesc, SubTotal1) / SubTotal1 END`.  
  **Done:** expr SQL parametrizable; ε=0.0001 documentado en docstring.

- [x] **T1.3** Crear `reports/tests/test_comprobante_descuento_cabecera.py`: casos factor 1 (sin pie), 0,8 (20 %), `SubTotal1=0`, `SubtotalDesc` null; assert substrings en SQL (`CASE`, `COALESCE(SubtotalDesc`, `0.0001`).  
  **Done:** `docker exec Synap_app python manage.py test reports.tests.test_comprobante_descuento_cabecera` verde.

---

## Fase 2 — Refactor DABRA (T2)

**Depende de:** T1  
**REQ:** REQ-VMM-PIE-06

- [x] **T2.1** En `reports/services/dabra_consolidado_remitos.py`, eliminar defs locales de `factor_descuento_cabecera` y `porcentaje_descuento_cabecera`; importar desde `comprobante_descuento_cabecera` y **re-exportar** ambos símbolos (mantener `from reports.services.dabra_consolidado_remitos import factor_descuento_cabecera` válido).  
  **Done:** sin cambio funcional; grep confirma cero defs duplicadas.

- [x] **T2.2** Ejecutar regresión DABRA: `docker exec Synap_app python manage.py test reports.tests.test_dabra_consolidado_remitos`.  
  **Done:** suite completa verde sin modificar tests DABRA.

---

## Fase 3 — Expresión post-pie en rules (T3)

**Depende de:** T1  
**REQ:** REQ-VMM-PIE-01, REQ-VMM-PIE-02, REQ-VMM-PIE-05

- [x] **T3.1** En `reports/services/ventas_marcas_mensual_rules.py`, importar `sql_factor_descuento_cabecera_expr` y añadir `sql_signo_imp_post_pie_expr()` que compone signo FAC/NC × `PrecioNetoxR` × factor cabecera (mismos `TIPOS_FAC`/`TIPOS_NC` que `sql_signo_imp_expr`).  
  **Done:** nueva función exportada; **`sql_signo_imp_expr()` intacta** (licenciatarios sin cambio).

- [x] **T3.2** Test en `test_ventas_marcas_mensual.py` o `test_comprobante_descuento_cabecera.py`: `sql_signo_imp_expr()` **no** contiene `SubTotal1`/`SubtotalDesc`; `sql_signo_imp_post_pie_expr()` sí incluye factor cabecera.  
  **Done:** assert substring; licenciatarios no afectados (grep `ventas_mensuales_licenciatarios_query.py` sigue con expr vieja).

---

## Fase 4 — Runner VMM (T4)

**Depende de:** T3  
**REQ:** REQ-VMM-PIE-01, REQ-VMM-PIE-03, REQ-VMM-PIE-04, REQ-VMM-PIE-05

- [x] **T4.1** En `reports/services/ventas_marcas_mensual_runner.py` (~700), sustituir import y uso de `sql_signo_imp_expr()` por `sql_signo_imp_post_pie_expr()` en agregación matriz única y modo comparar.  
  **Done:** SQL emitido usa expr post-pie; `sql_signo_qty_expr` / factor docenas **sin** factor pie.

- [x] **T4.2** Verificar KPIs downstream sin cambio de firma: `_compute_kpis_licencia` recibe `facturacion` post-pie; regalías = fact × tasa; precio_medio = fact/unidades; proyección `pf` sobre `f` post-pie, `pu` sin factor.  
  **Done:** no se añade lógica KPI nueva; solo base SQL corregida.

- [x] **T4.3** Test integrado runner (mock cursor): FA `SubTotal1=1000`, `SubtotalDesc=800`, Σ `PrecioNetoxR`=1000 → `facturacion=800`; NC mismo factor → −800; sin pie (`SubtotalDesc≈SubTotal1`) → factor 1.  
  **Done:** `assertAlmostEqual(..., places=2)`; escenarios REQ-VMM-PIE-01 y REQ-VMM-PIE-04 regalías.

- [x] **T4.4** Test modo comparar: marcas A/B usan importe post-pie; delta % coherente (REQ-VMM-PIE-03).  
  **Done:** KPIs y celdas `a`/`b` con misma base post-pie.

---

## Fase 5 — Export VMM (T5)

**Depende de:** T3  
**REQ:** REQ-VMM-PIE-03

- [x] **T5.1** En `reports/services/ventas_marcas_mensual_export.py`, eliminar `_signo_imp_sql()` duplicado (~55–62); importar `sql_signo_imp_post_pie_expr` en `fetch_detalle_renglones` (~92).  
  **Done:** matriz y detalle comparten la misma expr; cero duplicación local.

- [x] **T5.2** Test paridad export: suma montos Detalle coherente con KPI `facturacion` y `data[]` con FA dto pie (REQ-VMM-PIE-03 escenario paridad pantalla vs export).  
  **Done:** mock con mismos filtros; Σ detalle ≈ KPI (places=2).

---

## Fase 6 — Tests consolidados (T6)

**Depende de:** T2, T4, T5  
**REQ:** REQ-VMM-PIE-01…06

- [x] **T6.1** Ampliar `reports/tests/test_ventas_marcas_mensual.py`: unidades invariantes con dto pie 20 % (REQ-VMM-PIE-05); filtro marca parcial mantiene factor cabecera completo por `CodigoMovimiento` (REQ-VMM-PIE-03 / ADR-4).  
  **Done:** KPI/matriz `u` sin ×0,8; factor no recalculado por subset de marca.

- [x] **T6.2** Ejecutar suite completa en contenedor:  
  `docker exec Synap_app python manage.py test reports.tests.test_comprobante_descuento_cabecera reports.tests.test_ventas_marcas_mensual reports.tests.test_dabra_consolidado_remitos`  
  **Done:** las tres suites verdes.

---

## Fase 7 — Documentación (T7)

**Depende de:** T4, T5  
**REQ:** REQ-VMM-PIE-03, REQ-VMM-PIE-06

- [x] **T7.1** Actualizar `docs/reports/SPEC_INFORME_VENTAS_MARCAS_MENSUAL.md`: motor importe post-pie (`signo × PrecioNetoxR × factor`), KPIs/regalías/proyección sobre base post-pie, nota filtro marca parcial (factor cabecera total).  
  **Done:** § motor y KPIs alineados con spec OpenSpec.

- [x] **T7.2** Añadir nota en `docs/reports/MAPEO_PUW_PUM_ADMINISTRANET.md`: factor cabecera compartido VMM/DABRA (`comprobante_descuento_cabecera.py`).  
  **Done:** referencia cruzada al helper y criterio AdministraNET.

- [x] **T7.3** Una frase en `docs/reports/MANUAL_USUARIO_REPORTES.md`: la facturación del informe Ventas marcas mensual incluye descuento al pie de factura.  
  **Done:** texto visible para usuario final en español.

---

## Fase 8 — Verificación rápida (T8)

**Depende de:** T6, T7

- [x] **T8.1** Grep de regresión: ningún call site VMM usa `sql_signo_imp_expr()` ni `_signo_imp_sql()`; licenciatarios (`ventas_mensuales_licenciatarios_query.py`) **sigue** con expr pre-pie.  
  **Done:** solo VMM migrado; DABRA importa helper compartido.

- [x] **T8.2** Checklist manual contra criterios de éxito del proposal: FA pie 20 % → fact=800; sin pie → paridad previa; regalías/TC/proyección coherentes; export Matriz/Detalle/comparar misma base.  
  **Done:** todos los ítems del proposal § Success Criteria marcables.

---

## Mapa de dependencias

```
T1 ─┬─→ T2 (DABRA)
    └─→ T3 (rules) ─┬─→ T4 (runner)
                    └─→ T5 (export)
T4,T5 ─→ T6 (tests) ─→ T8
T4,T5 ─→ T7 (docs) ─→ T8
```

## Riesgos a vigilar en apply

| Tarea | Riesgo |
|-------|--------|
| T4.3 / T6 | Filtro marca parcial: Σ filtradas × factor ≠ `SubtotalDesc` del subset (aceptado ADR-4) |
| T5 | Divergencia matriz/detalle si queda expr duplicada |
| T3 | Mutar accidentalmente `sql_signo_imp_expr()` rompe licenciatarios |
| T2 | Olvidar re-export rompe imports DABRA externos |
