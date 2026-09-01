# Propuesta: Trazabilidad artículo — análisis completo

**Change:** `mpr-trazabilidad-analisis-completo`  
**Plan:** `docs/mpr/PLAN_TRAZABILIDAD_ANALISIS_COMPLETO.md`  
**Modo:** hybrid | **Idioma artefacto:** español

---

## Intent

Unificar el hub **Producción → Reportes → Trazabilidad** en un **informe canónico por artículo** que explique demanda PED, stock Terminado (incl. negativos), brecha Pedido vs PED Urgente, BOM pack y movimientos con saldo corrido — paridad operativa del análisis chat 610 T6 y fórmulas del Tablero Pack. Hoy **Línea de tiempo** y **Kardex artículo** son piezas incomplementarias con dos fuentes de verdad.

---

## Proposal question round

Las preguntas de explore quedaron **cerradas por orquestador/plan** (01/09/2026). No se requiere ronda adicional salvo rechazo explícito de producto.

| # | Decisión cerrada |
|---|------------------|
| 1 | **Depósito Terminado:** auto-resolver como tablero pack (`suma_stock` / Terminado MPR); selector depósito opcional en UI (`Todos` = eje Terminado). |
| 2 | **Saldo inicial v1:** MUST saldo real al inicio de `desde`; si falla cálculo, advertencia visible (no 0 silencioso). |
| 3 | **Timeline:** thin wrapper / deep-link a `kardex_articulo#timeline` — una sola fuente de verdad. |
| 4 | **Demanda PED:** `_listar_demanda_ped_vivo_fifo` (o equivalente vigente) por `id_articulo`; exclusión Facturado/Cerrado como tablero. |
| 5 | **Export:** CSV MUST en v1; Excel multi-hoja SHOULD stretch. |
| 6 | **Chip «Incluir cerrados»:** fuera de v1. |
| 7 | **Inventario:** clasificar por motivo (faltante/sobrante/inventario) + `TipoComp` cuando exista; FA en lista pero **no** entra al saldo corrido Terminado si no afecta `stock_deposito` (documentar en UI). |

---

## Scope

### In scope (v1)

- Servicio único `construir_analisis_trazabilidad_articulo` (extensión/split desde kardex).
- Bloques UI: cabecera artículo, DEMANDA PED, STOCK, BRECHA, BOM (pack), MOVIMIENTOS + saldo corrido, A PRODUCIR.
- Collector unificado: MSTOCK OPP/OPA, `stock` REM/FA/INV, eventos MPR; dedupe OPP.
- Saldo corrido Terminado con saldo inicial real; negativos visibles.
- Docenas\|Pares; export CSV; permiso `mpr.reportes`; canon UI MPR/reportes.
- Timeline → wrapper/deep-link sin duplicar servicio.
- Tests unitarios collector + fórmulas; docs `REPORTES_MPR.md` + `TRAZABILIDAD_ARTICULO.md`.

### Out of scope (v1)

- Corregir datos cutover PED cerrados; multi-empresa batch; NL/IA; rediseño grupo Demanda; cambiar fórmulas tablero (solo leer); chip «Incluir cerrados»; Excel multi-hoja (stretch).

---

## Capabilities

### New

- `mpr-analisis-trazabilidad-articulo`: análisis completo por artículo (PED, stock, brecha, BOM, movimientos, saldo corrido, export CSV).

### Modified

- `mpr-reporte-trazabilidad`: timeline delega en kardex (`#timeline`); sin segunda fuente de verdad; REQ timeline existentes se preservan vía ancla/sección.

---

## Approach

**Opción A (plan):** enriquecer slug `kardex_articulo` como informe canónico.

```
UI kardex_articulo → construir_analisis_trazabilidad_articulo
  ├── identidad + BOM (existente)
  ├── demanda_ped (_listar_demanda_ped_vivo_fifo)
  ├── stock_actual (_ventana_pack_stock_maps / suma_stock)
  ├── brechas (fórmulas tablero pack)
  └── movimientos_unificados (MSTOCK + stock REM/FA/INV + mpr_*; saldo corrido)
```

**Entrega:** 3 PRs encadenados — (1) collector + tests, (2) UI bloques, (3) export + timeline thin wrapper. Presupuesto ~800–1200 líneas; riesgo revisión **Alto** → chained PRs.

Paridad datos/negocio con tablero (SPEC presupuesto §1.3–§1.4 aplicable en espíritu); UX canon `ui-fuente-verdad-reportes-mpr`.

---

## Affected Areas

| Área | Impacto | Descripción |
|------|---------|-------------|
| `mpr/services_kardex_articulo.py` | Modified | Servicio análisis + collector REM/FA/INV |
| `mpr/services.py` | Modified | Wrapper demanda; reexport |
| `mpr/views.py` | Modified | Payload kardex; timeline redirect |
| `mpr/reportes_hub.py` | Modified | Labels, columnas CSV |
| `mpr/templates/.../kardex_articulo.html` | Modified | Bloques análisis |
| `mpr/templates/.../trazabilidad_timeline.html` | Modified | Thin wrapper / deep-link |
| `mpr/tests/` | New/Modified | `test_analisis_trazabilidad_articulo.py` |
| `docs/mpr/` | Modified | REPORTES_MPR + TRAZABILIDAD_ARTICULO |

---

## Risks

| Riesgo | Prob. | Mitigación |
|--------|-------|------------|
| FA no afecta `stock_deposito` | Med | Listar FA; columna «Afecta depósito»; excluir del saldo corrido |
| REM/FA naming heterogéneo | Med | Whitelist + tests fixtures |
| Saldo inicial costoso | Med | Query acumulada; fallback advertencia |
| Duplicar OPP MSTOCK/mpr_parte | Med | Dedupe por `codigo_movimiento` |
| Alcance PR | High | 3 PRs encadenados |

---

## Rollback Plan

1. Revertir merge por PR (collector → UI → export/timeline).
2. Restaurar `construir_kardex_articulo` y partial timeline autónomo si wrapper falla.
3. Hub: reactivar entry timeline independiente vía `reportes_hub.py`.
4. Sin migraciones DB; rollback = código + templates.

---

## Dependencies

- Funciones tablero pack: `listar_demanda_pack_desde_pedidos`, `_listar_demanda_ped_vivo_fifo`, `_ventana_pack_stock_maps`.
- Referencia: `exports/_gen_kardex_610_t6.py`.
- Permisos MPR existentes; búsqueda `reportes_articulo_buscar_api`.

---

## Success Criteria

- [ ] Pack 610 jul–sep/2026: ≥4 OPA, saldo corrido coherente, REM/FA/INV etiquetados.
- [ ] Pedido y PED Urgente = paridad tablero Pack (docenas/pares).
- [ ] Terminado negativo visible; texto brecha cuando aplica.
- [ ] BOM 3 componentes con link a análisis componente.
- [ ] Timeline abre misma data vía `#timeline`; sin duplicar servicio.
- [ ] Export CSV v1; tests `docker exec Synap_app python manage.py test …`; docs actualizados.
- [ ] UI español, fechas dd/MM/yyyy, sin diálogos nativos.
