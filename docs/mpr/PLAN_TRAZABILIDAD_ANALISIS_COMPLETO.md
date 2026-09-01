# Plan: Trazabilidad artículo — análisis completo (paridad chat 610)

**Fecha:** 01/09/2026  
**Change SDD:** `mpr-trazabilidad-analisis-completo`  
**Producto:** Informe en hub MPR Trazabilidad que reproduzca el análisis operativo hecho a mano (caso 610 T6: demanda PED + OPA/remitos/inventario + saldo corrido Terminado + brecha Pedido vs PED Urgente).  
**Goal:** agregar *todo* lo acordado; este documento es el contrato de alcance antes de apply.

---

## 1. Problema

Hoy coexisten dos piezas incompletas:

| Informe actual | Qué hace | Qué falta vs análisis del chat |
|----------------|----------|--------------------------------|
| **Línea de tiempo** | Eventos MPR (envío/parte/clasificación) + OPP/OPA MSTOCK | Remitos/FA, inventario físico, demanda PED, saldo corrido, BOM, KPIs de brecha |
| **Kardex artículo** | OPP/OPA MSTOCK + BOM + saldo corrido (ventana) | Remitos/FA/inventario; demanda PED; explicación Pedido vs PED Urgente; puente Semi |

El usuario necesita **un solo informe** que explique, para un artículo y período:

1. Qué demanda comercial vive (PED).
2. Qué movimientos movieron stock (OPA, REM/FA, inventario, OPP, MPR).
3. Cómo quedó el saldo (incl. negativos visibles).
4. Por qué **PED Urgente ≠ Pedido** (Terminado negativo o insuficiente).
5. Si es pack: BOM y efecto en Semi de los armados.

Referencia empírica: `exports/_gen_kardex_610_t6.py` + Excel `exports/kardex_610_t6_terminado.xlsx` (hojas Resumen | OPA y Remitos | Kardex por pack).

---

## 2. Objetivo de producto

Transformar el hub **Producción → Reportes → Trazabilidad** en el **análisis de trazabilidad artículo** canónico:

- Entrada: búsqueda predictiva (código/descripción) + Desde/Hasta + Docenas|Pares.
- Salida en pantalla (y export CSV/Excel): bloques alineados al Excel del chat.
- Misma semántica de fórmulas que Tablero Pack (`Pedido`, `Terminado`, `PED Urgente`, `TOT Urgente`).

### 2.1 Nombre / navegación (decisión de plan)

| Opción | Pros | Contras |
|--------|------|---------|
| **A — Unificar en Kardex artículo** (recomendado) | Ya tiene BOM + saldo; nombre cercano al análisis | Hay que ampliar mucho el partial/servicio |
| **B — Ampliar Línea de tiempo** | Usuario ya está ahí | Nombre “timeline” queda corto; duplica Kardex |
| **C — Nuevo reporte “Análisis trazabilidad”** | Separación clara | Tercer entry point; más chrome |

**Decisión de plan:** **Opción A** — el reporte `kardex_articulo` pasa a ser el análisis completo; la **Línea de tiempo** redirige o se convierte en vista/ancla del mismo servicio (misma URL o deep-link `reporte=kardex_articulo` con ancla `#timeline`). Evita dos fuentes de verdad.

Si en design se prefiere B, el servicio único sigue siendo el mismo; solo cambia el slug UI.

---

## 3. Alcance funcional (MUST)

### 3.1 Cabecera artículo

- MUST mostrar: `id_articulo`, código manual, descripción, `tipo_art_fab` (Terminado / Fabricado / …).
- MUST indicar si es **pack** (tiene `id_en_abm` + BOM) o **componente**.
- MUST conservar búsqueda predictiva (`reportes_articulo_buscar_api`).

### 3.2 Bloque DEMAND A (PED)

- MUST listar renglones de pedidos PED **no anulados** con estado comercial **no** en `Facturado` / `Cerrado` (paridad tablero / `listar_demanda_pack_desde_pedidos` o extracto equivalente por artículo).
- MUST mostrar por fila: nro pedido, cliente, fecha, cantidad pedida / pendiente (saldo comercial), estado OPT si existe.
- MUST agregar **Pedido (P_ped)** = suma pendiente comercial del artículo en el filtro vigente.
- SHOULD mostrar pedidos cerrados/cutover solo si chip “Incluir cerrados” (default off) — opcional v1; **fuera de MUST** salvo que design lo pida.

### 3.3 Bloque STOCK actual

- MUST mostrar **Terminado** = saldo real en depósitos `suma_stock='Si'` (o depósito Terminado MPR según contrato vigente del tablero pack).
- MUST **mostrar negativos** (sin clamp a 0), estilo alerta.
- SHOULD mostrar Semi / 2da / Producción si el artículo es componente o si el pack tiene BOM (saldos de componentes en Semi para “capacidad de armado”).

### 3.4 Bloque BRECHA (paridad Tablero Pack)

Fórmulas (pares; UI Docenas|Pares como hub):

- `PED Urgente = max(0, P_ped − Terminado)`
- `TOT Urgente = max(0, P_ped + Reserva − Terminado)` donde `Reserva = articulo.stock_reserva`
- MUST explicar en texto corto cuando Terminado &lt; 0: “PED Urgente = Pedido + |Terminado|”.

### 3.5 Bloque BOM (solo pack)

- MUST listar componentes: código, descripción, cantidad BOM, link a trazabilidad del componente.
- SHOULD indicar `max_packs` armables desde Semi (ya parcialmente en kardex).

### 3.6 Bloque MOVIMIENTOS / timeline con saldo corrido

Unión cronológica en el período, filtrable por tipo:

| Tipo | Fuente | Efecto típico en pack Terminado |
|------|--------|----------------------------------|
| **OPA / ARMADO** | `movimiento_stock` MSTOCK | Entrada pack; (detalle) salida componentes Semi |
| **OPP / Parte producción** | MSTOCK +/o `mpr_parte_*` | Entrada Semi (componente) |
| **REM** | `movimiento_stock` tipo_comprobante remito | Salida Terminado |
| **FA** (y egresos factura relevantes al stock) | idem | Según depósito; documentar si FA no afecta depósito Terminado |
| **Inventario / faltante / ajuste** | MSTOCK motivo inventario | Entrada/salida |
| **Envío / clasificación MPR** | `mpr_envio_produccion`, `mpr_transicion_lote` | Pipeline componente |

Reglas:

- MUST calcular **saldo corrido** del artículo en el eje Terminado (pack) o depósito relevante (componente Semi), partiendo de saldo al inicio del período **o** documentar explícitamente “saldo inicial de ventana = 0” vs “saldo anterior” (stretch: checkbox saldo anterior — pendiente SDD kardex previo).
- **Decisión de plan v1:** saldo inicial de ventana = stock al *inicio* del `desde` (movimientos previos al período), no 0. Si el costo SQL es alto, design puede proponer saldo_inicial=0 + aviso; el Excel del chat reconstruyó desde movimientos — preferir **saldo real al corte**.
- MUST colorear/etiquetar OPA / REM / FA / INV / MPR (paridad Excel).
- MUST para cada OPA de pack: mostrar en detalle o subfilas la **salida de componentes Semi** (qty BOM × packs).

### 3.7 Bloque A PRODUCIR / capacidad (pack)

- MUST mostrar: a fabricar/armar ≈ TOT Urgente (o PED Urgente según toggle docenas).
- SHOULD: capacidad desde Semi = `floor(min(saldo_semi_i / bom_i))`.
- SHOULD: alerta si PED Urgente &gt; 0 y Semi = 0.

### 3.8 Presentación y export

- MUST Docenas|Pares (hub existente).
- MUST export CSV del análisis (columnas por bloque o hoja lógica).
- SHOULD export Excel multi-hoja (Resumen | Movimientos | Kardex) — paridad `_gen_kardex_610_t6.py`; si excede presupuesto de PR, CSV en v1 y Excel en tarea stretch.

### 3.9 UX / permisos

- MUST UI español; fechas dd/MM/yyyy; sin `alert`/`confirm`.
- MUST permiso reportes MPR existente (`mpr.reportes` / mixin vigente).
- MUST canon UI reportes MPR (partials hub).

---

## 4. Fuera de alcance (v1)

- Corregir datos cutover PED cerrados en `lista_produccion` (dato, no UI).
- Remitos en otras bases / multi-empresa batch.
- NL / asistente IA (reutilizar informe después).
- Rediseño completo del grupo Producción/Demanda.
- Cambiar fórmulas del Tablero (solo **leer** las mismas).

---

## 5. Arquitectura técnica propuesta

```
UI hub (kardex_articulo partial enriquecido)
    │
    ▼
construir_analisis_trazabilidad_articulo(base, id_art, desde, hasta)
    │
    ├── identidad + BOM          (existente kardex / get_bom_detalle)
    ├── demanda_ped              (reusar listar_demanda… o query PED por id_art)
    ├── stock_actual             (stock_deposito / suma_stock; Semi por BOM)
    ├── brechas                  (mismas fórmulas tablero pack)
    └── movimientos_unificados   (nuevo collector)
            ├── mstock: OPA/OPP/REM/FA/INV (clasificador por tipo_mov + tipo_comprobante + motivo)
            ├── mpr_*: envío / parte / transición
            └── saldo_corrido + detalle componentes OPA
```

### 5.1 Archivos tocados (previsto)

| Área | Paths |
|------|--------|
| Servicio | `mpr/services_kardex_articulo.py` (ampliar o split `services_trazabilidad_articulo.py`) |
| Vista hub | `mpr/views.py` (rama `kardex_articulo` / timeline) |
| Hub registry | `mpr/reportes_hub.py` (labels, CSV columns) |
| UI | `mpr/templates/mpr/reportes/partials/kardex_articulo.html` (+ includes bloques) |
| Timeline | `trazabilidad_timeline.html` → thin wrapper / redirect |
| Tests | `mpr/tests/test_kardex_articulo.py`, nuevo `test_analisis_trazabilidad_articulo.py` |
| Docs | `docs/mpr/REPORTES_MPR.md`, este plan, `docs/mpr/TRAZABILIDAD_ARTICULO.md` (nuevo) |

### 5.2 Clasificación de movimientos MSTOCK (borrador)

| Señal | Clase UI |
|-------|----------|
| `tipo_mov ∈ {OPA, ARMADO}` | `opa` |
| `tipo_mov = OPP` o motivo Parte producción | `opp` |
| `tipo_comprobante` remito (REM…) | `rem` |
| `tipo_comprobante` FA (y política de afectación depósito) | `fa` |
| motivo inventario / faltante / sobrante | `inventario` |
| resto con Entrada/Salida en depósito objetivo | `ajuste` o ignorar |

Reutilizar y extender `_clasificar_movimiento_kardex` / `_normalizar_fila_kardex` (ya corrige OPA pack con Entrada).

### 5.3 Demanda PED

Reutilizar la misma exclusión de estados y semántica de `cantidad_pendiente` que el tablero. No inventar otra definición de Pedido.

---

## 6. Criterios de aceptación (verificación)

1. Artículo pack 610 Mix (IDArt 1398, Bestsox) período jul–sep/2026: aparecen **≥4 OPA** con cantidades 42/68/30/120 y saldo corrido coherente.
2. Si hay REM/FA/inventario en el período, aparecen etiquetados (inventario faltante campaña #3 incluido si está en rango).
3. Bloque Pedido coincide con tablero Pack (docenas/pares) para el mismo artículo.
4. PED Urgente = `max(0, Pedido − Terminado)` con Terminado negativo mostrado.
5. BOM lista los 3 componentes del Mix; link abre análisis del componente.
6. Tests unitarios del collector + fórmulas; `docker exec Synap_app python manage.py test …`.
7. Docs `REPORTES_MPR.md` + `TRAZABILIDAD_ARTICULO.md` actualizados.
8. Sin diálogos nativos; UI en español.

---

## 7. Plan de entrega SDD

| Fase | Artefacto | Notas |
|------|-----------|--------|
| Explore | `exploration.md` | Gap vs kardex/timeline; inventario código; riesgos FA/REM |
| Propose | `proposal.md` | Intent, scope, non-goals (este plan §3–4) |
| Spec | delta `mpr-reporte-trazabilidad` + posiblemente `mpr-kardex-articulo` | Escenarios MUST en español |
| Design | `design.md` | Servicio único, clasificación MSTOCK, UI bloques, saldo inicial |
| Tasks | `tasks.md` | TDD estricto; oleadas: collector → KPIs/PED → UI → export → timeline thin |
| Apply | implementación | Workers Composer; UI polish Opus si hace falta |
| Verify | `verify-report.md` | Aceptación §6 |

**Strict TDD:** sí (`openspec/config.yaml`).

**Presupuesto líneas:** alto (estimado 800–1200). Preferir PRs encadenados:

1. Collector + fórmulas + tests (sin UI grande)  
2. UI bloques + búsqueda  
3. Export + unificación timeline  

---

## 8. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| FA no baja `stock_deposito` igual que REM | Documentar en UI; no inventar movimiento fantasma |
| Remitos con naming heterogéneo de `tipo_comprobante` | Inventario SQL en explore; whitelist + tests |
| Saldo inicial ventana costoso | Cache por artículo+desde; o saldo_inicial=0 con banner |
| Tres códigos “610” en búsqueda | Predictivo ya lista; UI muestra descripción completa |
| Duplicar OPP (MSTOCK + mpr_parte) | Deduplicar por código_movimiento / fecha+qty o marcar fuente |

---

## 9. Estado

- [x] Entendimiento producto acordado (chat 01/09/2026)  
- [x] Plan detallado (este documento)  
- [x] SDD explore → propose → spec → design → tasks  
- [x] Apply PR1 (servicio/collector) + PR2 (UI bloques) + PR3 (export CSV, timeline wrapper, docs)  
- [ ] Verify — checklist §6 con evidencia pack 610  

**Manual operativo:** [TRAZABILIDAD_ARTICULO.md](TRAZABILIDAD_ARTICULO.md)
