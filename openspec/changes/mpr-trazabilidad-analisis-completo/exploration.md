# Exploración: Trazabilidad artículo — análisis completo

**Change:** `mpr-trazabilidad-analisis-completo`  
**Fecha:** 01/09/2026  
**Plan autoritativo:** `docs/mpr/PLAN_TRAZABILIDAD_ANALISIS_COMPLETO.md`  
**Referencia empírica:** `exports/_gen_kardex_610_t6.py`, `exports/kardex_610_t6_terminado.xlsx`

---

## Estado actual

Hoy el hub **Producción → Reportes → Trazabilidad** expone dos informes parciales que no reproducen el análisis operativo del chat (pack 610 T6):

| Informe | Slug hub | Servicio | Qué cubre hoy | Qué falta vs análisis chat |
|---------|----------|----------|---------------|------------------------------|
| **Línea de tiempo** | `timeline` | `reporte_mpr_trazabilidad_componente` | Ledgers MPR (`mpr_envio_produccion`, `mpr_parte_linea`, `mpr_transicion_lote`) + OPP/OPA MSTOCK fusionados cronológicamente | REM/FA, inventario/ajustes, demanda PED, saldo corrido Terminado, KPIs Pedido vs PED Urgente, BOM como puente Semi |
| **Kardex artículo** | `kardex_articulo` | `construir_kardex_articulo` | OPP/OPA MSTOCK por artículo/depósito, BOM, saldo corrido en ventana, modal renglones OPA | REM/FA/inventario; bloque demanda PED; stock actual Terminado negativo; brecha tablero pack; saldo inicial real al corte `desde` |

### Detalle técnico relevante

**Kardex (`mpr/services_kardex_articulo.py`):**

- `_consultar_movimientos_kardex_articulo` solo trae `movimiento_stock` con `tipo_comprobante = MSTOCK` y `tipo_mov ∈ {OPP, OPA, ARMADO}` (+ motivo «Parte producción»).
- `_normalizar_fila_kardex` ya corrige OPA pack con **Entrada** (no queda en cero) — bugfix validado en tests.
- `construir_kardex_articulo` documenta explícitamente **`saldo_inicial = 0`** (línea 233–234, 294): el saldo corrido no refleja stock previo al período.
- `_clasificar_movimiento_kardex` marca OPA/ARMADO como «salida» (perspectiva componente Semi); la normalización usa el sentido real del renglón `stock` para packs.

**Timeline (`mpr/services.py` ~14825):**

- Reutiliza `_consultar_movimientos_kardex_articulo` + `_normalizar_fila_kardex` para OPP/OPA.
- No calcula saldo corrido ni une con tabla `stock` para REM/FA.
- UI vertical (`trazabilidad_timeline.html`); KPI strip solo cuenta eventos.

**Demanda y fórmulas tablero (ya existentes, no cableadas al informe trazabilidad):**

- `listar_demanda_pack_desde_pedidos` — agrega P_ped, stock terminado (`suma_stock='Si'`), reserva, `cantidad_urgente_abs` = max(0, P_ped − Terminado), `cantidad_a_fabricar` = max(0, P_ped + R − Terminado).
- `_listar_demanda_ped_vivo_fifo` — líneas PED **por artículo** con pendiente comercial (resta imputación vía `_cantidad_imputada_pedido_pack`); más adecuado que el agregado pack para el bloque DEMANDA del informe.
- `reporte_mpr_brecha_demanda` — reporte hub «Brecha pack» reutiliza el agregado; no filtra por un solo artículo.

**Referencia chat (`exports/_gen_kardex_610_t6.py`):**

- PED: `stockp` + `comp_ped`, filtros comerciales (no Facturado/Cerrado, estado OPT Pendiente/Parcial).
- OPA: `movimiento_stock` + `stock`, filtro por detalle pack.
- REM/FA: consulta directa a **`stock`** (`Comprobante IN ('REM','FA')`), no MSTOCK.
- Saldo corrido Terminado: depósito fijo `CodDeposito=6`; **FA no afecta** saldo (`afecta_deposito`: comp ≠ 'FA').
- Excel multi-hoja: Resumen | OPA y Remitos | Kardex por pack.

**UI actual kardex:**

- Búsqueda predictiva, selector depósito, tabla OPP/OPA, BOM con links a **timeline** del componente (no kardex).
- KPI strip: saldo final, max packs, conteo movimientos (`_kpi_strip.html`).
- Modal comprobante vía `_build_renglones_modal_map` + `obtener_renglones_movimiento_bulk` (detalle componentes OPA ya disponible para UI).

**Spec vigente:** `openspec/specs/mpr-reporte-trazabilidad/spec.md` cubre solo timeline MPR (REQ-TRAZ-01…05); no exige PED, REM/FA ni saldo corrido.

---

## Áreas afectadas

| Path | Motivo |
|------|--------|
| `mpr/services_kardex_articulo.py` | Ampliar o extraer `construir_analisis_trazabilidad_articulo`; collector REM/FA/INV; saldo inicial; clasificación unificada |
| `mpr/services.py` | Reexport; posible `listar_demanda_ped_por_articulo` wrapper sobre `_listar_demanda_ped_vivo_fifo`; fórmulas brecha reutilizando `_ventana_pack_stock_maps` |
| `mpr/views.py` | Rama `kardex_articulo`: payload enriquecido; timeline redirect/deep-link |
| `mpr/reportes_hub.py` | Labels («Análisis trazabilidad»), columnas CSV/Excel, posible redirect timeline → kardex |
| `mpr/templates/mpr/reportes/partials/kardex_articulo.html` | Bloques UI: DEMANDA, STOCK, BRECHA, BOM, MOVIMIENTOS, A PRODUCIR |
| `mpr/templates/mpr/reportes/partials/trazabilidad_timeline.html` | Thin wrapper, redirect o ancla `#timeline` |
| `mpr/templates/mpr/reportes/_kpi_strip.html` | KPIs Pedido, Terminado, PED Urgente, TOT Urgente |
| `mpr/tests/test_kardex_articulo.py` | Extender; nuevo `test_analisis_trazabilidad_articulo.py` |
| `mpr/tests/test_reportes_trazabilidad.py` | Ajuste si timeline delega en servicio único |
| `openspec/specs/mpr-reporte-trazabilidad/spec.md` | Delta: requisitos análisis completo |
| `docs/mpr/REPORTES_MPR.md`, `docs/mpr/TRAZABILIDAD_ARTICULO.md` (nuevo) | Documentación operativa |

---

## Enfoques comparados

| Enfoque | Descripción | Pros | Contras | Esfuerzo |
|---------|-------------|------|---------|----------|
| **A — Unificar en Kardex artículo** (recomendado en plan) | `kardex_articulo` pasa a ser el informe canónico; servicio único `construir_analisis_trazabilidad_articulo`; timeline redirige o muestra sub-sección | Reutiliza BOM, saldo corrido, modal OPA, tests kardex, búsqueda y depósito ya implementados; una fuente de verdad; alineado al Excel del chat | Partial HTML crece; refactor servicio grande (~800–1200 líneas totales) | **Alto** |
| **B — Ampliar Línea de tiempo** | Mantener slug `timeline`; añadir bloques PED/stock/brecha + tabla movimientos | Usuario puede seguir en pantalla familiar | Nombre «timeline» no describe análisis completo; duplica lógica kardex; BOM/saldo ya viven en otro partial | **Alto** (misma lógica, peor UX naming) |
| **C — Nuevo reporte «Análisis trazabilidad»** | Tercer entry en grupo trazabilidad | Separación conceptual clara | Tercer punto de entrada; duplicación filtros/búsqueda; más chrome hub | **Medio-alto** |

---

## Recomendación

**Enfoque A:** unificar en **`kardex_articulo`** con servicio **`construir_analisis_trazabilidad_articulo`** (extensión o split desde `services_kardex_articulo.py`).

Arquitectura propuesta (paridad plan §5):

```
UI hub (kardex_articulo enriquecido)
    │
    ▼
construir_analisis_trazabilidad_articulo(base, id_art, desde, hasta, id_deposito?)
    ├── identidad + BOM          (existente)
    ├── demanda_ped              (_listar_demanda_ped_vivo_fifo + totales P_ped)
    ├── stock_actual             (_ventana_pack_stock_maps / stock_deposito; Semi vía BOM)
    ├── brechas                  (cantidad_urgente_abs, cantidad_a_fabricar — mismas fórmulas tablero)
    └── movimientos_unificados
            ├── MSTOCK: OPP/OPA (existente)
            ├── stock: REM/FA/INV (nuevo; FA marcado sin efecto saldo)
            ├── mpr_*: envío/parte/clasificación (desde timeline, dedupe OPP)
            └── saldo_corrido + subfilas componentes OPA (modal existente)
```

**Timeline:** no duplicar servicio — redirect GET a `kardex_articulo` con `#timeline` o partial mínimo que incluya el mismo payload filtrado a eventos MPR.

**Entrega:** 3 PRs encadenados (collector + tests → UI bloques → export + unificación timeline), coherente con presupuesto 400 líneas/revisión.

---

## Riesgos

| Riesgo | Evidencia | Mitigación propuesta |
|--------|-----------|----------------------|
| **FA no mueve `stock_deposito`** | Script chat: `afecta_deposito(comp) = comp.upper() != 'FA'` | Listar FA en movimientos; columna «Afecta depósito»; no sumar al saldo corrido; texto explicativo en UI |
| **Naming heterogéneo REM/FA** | En MPR no hay queries REM; en reports usan `comp_ped.TipoComprobante` y `stock.Comprobante` | Inventario SQL en design; whitelist `Comprobante IN ('REM','FA')` + tests con fixtures |
| **Saldo inicial ventana** | Kardex actual usa 0; plan prefiere stock al inicio de `desde` | Query saldo acumulado movimientos anteriores o `stock_deposito` − delta ventana; fallback banner si costoso |
| **Duplicar OPP** | Timeline mezcla `mpr_parte` y MSTOCK OPP | Dedupe por `codigo_movimiento` o fecha+cantidad; preferir MSTOCK cuando exista comprobante |
| **Perspectiva OPA pack vs componente** | Clasificador kardex es «salida» para OPA | Mantener `_normalizar_fila_kardex`; en análisis Terminado usar depósito objetivo y sentido Entrada/Salida real |
| **Tres códigos «610»** | Búsqueda predictiva ya desambigua | Cabecera MUST mostrar descripción completa + IDArt |
| **Alcance PR** | Plan estima 800–1200 líneas | PR1 servicio/tests sin UI grande; PR2 UI; PR3 export/timeline |

---

## Preguntas abiertas (para propose / design)

1. **Depósito Terminado:** ¿forzar depósito MPR tipo Terminado cuando el artículo es pack, o respetar selector actual «Todos» con default inteligente?
2. **Saldo inicial v1:** ¿obligatorio stock real al corte `desde` o aceptable saldo_inicial=0 + banner hasta optimizar SQL?
3. **Timeline:** ¿redirect 302 permanente a kardex, o convivencia con tab/ancla en la misma URL?
4. **Demanda PED:** ¿`_listar_demanda_ped_vivo_fifo` (imputación-aware) o extracto SQL del script chat (`qty_comercial` GREATEST)?
5. **Export Excel multi-hoja:** ¿MUST v1 o stretch post-MVP (CSV por bloques en v1)?
6. **Chip «Incluir pedidos cerrados»:** ¿v1 o fuera de alcance?
7. **Clasificación inventario:** ¿reglas por `motivo_movimiento`, `TipoComp` Armado, u otro catálogo MSTOCK?

---

## Listo para propuesta

**Sí.** El gap está acotado, hay referencia ejecutable (`_gen_kardex_610_t6.py`), piezas reutilizables identificadas y decisión de producto (Opción A) alineada al plan. La fase **propose** debe fijar alcance v1, respuestas a preguntas abiertas y estrategia de PRs encadenados.
