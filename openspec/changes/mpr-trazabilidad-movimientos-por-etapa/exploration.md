# Exploración: mpr-trazabilidad-movimientos-por-etapa

**Change:** `mpr-trazabilidad-movimientos-por-etapa`  
**Fecha:** 17/09/2026  
**Modo:** Paridad funcional (historial kardex ↔ inventario por etapa Fabricados)  
**Fuente funcional:** `docs/mpr/AF_TRAZABILIDAD_MOVIMIENTOS_POR_ETAPA.md`

---

## Resumen ejecutivo

El análisis trazabilidad (`kardex_articulo`) ya reconoce componentes fabricados con eje `pipeline_fabricados` y calcula **un** saldo consolidado sobre los tres depósitos MPR (Producción, Semi elaborado, 2.ª selección). Ese consolidado puede conciliar con la suma del inventario por etapa, pero **no** expone movimientos ni saldos corrido **por etapa**, porque las consultas agregan entradas/salidas por `codigo_movimiento` sin `CodDeposito` y el acumulador es escalar. El gap principal es de **modelo de filas + corrido multi-etapa + UI/CSV**, no de descubrimiento del eje pipeline.

---

## Estado actual (as-is en código)

### Inventario por etapa — contrato de referencia

| Aspecto | Implementación |
|---------|----------------|
| Ámbito Fabricados | Columnas fijas `Produccion`, `SemiElaborado`, `2daSeleccion` + **Consolidado** = suma de las tres (`ETAPAS_FABRICADOS`, `_sql_consolidado_expr`) |
| Fuente instantánea | `stock_deposito` JOIN `deposito.tipo_mpr` |
| Módulo | `stock/services/inventario_tabla.py` (`consultar_inventario_tabla`, filtros `ambito=fabricados`) |
| UI | Stock / MPR inventario (no histórico) |

### Análisis trazabilidad — pipeline consolidado

| Pieza | Comportamiento relevante |
|-------|---------------------------|
| Entrada | `construir_analisis_trazabilidad_articulo` en `mpr/services_kardex_articulo.py` |
| Eje componente | Si no es pack y hay ≥2 depósitos pipeline → `tipo_eje: pipeline_fabricados`, `ids_deposito` vía `get_depositos_pipeline_fabricados_mpr` (`mpr/services.py`, `TIPOS_MPR_PIPELINE_FABRICADOS`) |
| Stock KPI | `_fetch_stock_terminado_analisis(..., ids_deposito=dep_ids)` → **SUM** saldo en pipeline |
| Movimientos | `_recolectar_movimientos_analisis` filtra `CodDeposito IN (...)` pero **agrupa** en SQL por movimiento sin depósito |
| Normalización | `_normalizar_fila_kardex` documenta transferencias OPP (salida origen + entrada destino) pero recibe ya **totales neteados** por movimiento |
| Corrido | `_calcular_saldo_corrido_analisis` → un solo `saldo_corrido` |
| Conciliación | Solo consolidado: si `Hasta ≥ hoy` y `saldo_final ≠ stock_terminado` → advertencia |
| Hub / vista | `mpr/views.py` (`ReportesMPRView`, grupo `trazabilidad`, reporte `kardex_articulo`); enriquece `subfilas_opa` con depósito **solo** en detalle de armado pack, no en corrido del componente |
| UI | `mpr/templates/mpr/reportes/partials/kardex_articulo.html`: tabla Fecha \| Tipo \| … \| **Saldo** único; badge «Stock consolidado pipeline» |
| CSV | `mpr/reportes_hub.py` `CSV_COLUMNAS[("trazabilidad","kardex_articulo")]`: sin depósito/etapa ni saldos por etapa |
| Presentación | `mpr/reportes_presentacion.py` (Pares/Docenas) sobre campos cantidad existentes |

### Consulta MSTOCK — raíz del neteo

En `_consultar_movimientos_kardex_articulo` (y análogos REM/inventario):

- Filtro: `s.CodDeposito IN (pipeline)` cuando `ids_deposito` está activo.
- `SELECT`: `COALESCE(SUM(s.Entrada), 0)`, `COALESCE(SUM(s.Salida), 0)`.
- `GROUP BY`: `codigo_movimiento`, fecha, tipo, … **sin** `CodDeposito`.

Un OPP Producción → Semi en el mismo movimiento produce entrada y salida en depósitos distintos pero **una fila** con ambos totales; el corrido consolidado aplica `entrada − salida` y la transferencia interna **desaparece** del saldo total (correcto para consolidado, incorrecto para auditoría por etapa).

### Tests existentes (cobertura del gap)

| Archivo | Qué cubre hoy | Qué **no** cubre |
|---------|---------------|------------------|
| `mpr/tests/test_analisis_trazabilidad_articulo.py` | Eje `pipeline_fabricados`, paso de `ids_deposito` al collector, saldo inicial/corrido escalar, FA excluida | Saldos por `tipo_mpr`, transferencias OPP dual-etapa, paridad vs `inventario_tabla` |
| `mpr/tests/test_kardex_articulo.py` | Hub, CSV columnas actuales, UI parcial, golden pack Terminado | Desglose etapas fabricados |
| `mpr/tests/test_reportes_trazabilidad.py` | Delegación timeline, CSV análisis | Paridad inventario |

No hay tests de contrato «cierre 79/28/0 vs inventario» del AF (art. 1115).

---

## Mapa AF → gaps verificados

| Requisito AF | Estado as-is | Gap |
|--------------|--------------|-----|
| RF-01 Etapa/depósito por movimiento | No hay campo en fila normalizada | **Alto** — requiere filas por impacto de depósito |
| RF-02 Saldos corrido por etapa | Solo `saldo_corrido` | **Alto** — acumulador 3+1 dimensiones |
| RF-03 Consolidado = suma etapas | Consolidado sí (un número); no desglosado | **Medio** — falta desglose en payload y UI |
| RF-04 Transferencias pipeline visibles | Neteadas en SQL GROUP BY | **Alto** — cambio de consulta o explosión post-query |
| RF-05 Conciliación cierre vs inventario | Solo total pipeline vs `stock_terminado` sum | **Alto** — falta comparar por `tipo_mpr` |
| RF-06 UI dimensión etapa | Sin columna etapa en grilla principal | **Medio/Alto** (UX en design) |
| RF-07 CSV etapa | Columnas fijas sin etapa | **Medio** |
| RF-10 Packs Terminado sin regresión | Camino `tipo_eje: terminado` intacto | **Riesgo** si se generaliza multi-eje sin bifurcar |
| RF-11 No cambiar inventario | Inventario no tocado en código actual | OK — consumir como referencia |

---

## Áreas afectadas (implementación futura)

| Archivo | Motivo |
|---------|--------|
| `mpr/services_kardex_articulo.py` | Consultas por depósito, normalización multi-fila, corrido por etapa, saldo inicial por etapa, conciliación extendida |
| `mpr/services.py` | Reutilizar `TIPOS_MPR_PIPELINE_FABRICADOS`, mapeo `CodDeposito` ↔ `tipo_mpr`, posible helper compartido con inventario |
| `stock/services/inventario_tabla.py` | **Lectura** para tests de paridad y/o helper de saldos actuales por etapa (no cambiar semántica columnas) |
| `mpr/reportes_hub.py` | Columnas CSV |
| `mpr/templates/mpr/reportes/partials/kardex_articulo.html` | Columnas saldo/etapa, KPIs cabecera (RF-08/09) |
| `mpr/views.py` | Contexto presentación si nuevos campos; export CSV |
| `mpr/export.py` (`analisis_trazabilidad_a_csv`) | Serialización campos nuevos |
| `mpr/reportes_presentacion.py` | Factores Pares/Docenas sobre nuevos campos numéricos |
| `mpr/tests/test_analisis_trazabilidad_articulo.py`, `test_kardex_articulo.py` | Contratos paridad + transferencia OPP |
| `docs/mpr/` | Documentación post-diseño (política repo) |

**Fuera de alcance (AF):** timeline OPT, inventario físico, cambio reglas OPP/OPA/REM/FA de negocio, rediseño inventario por etapa.

---

## Enfoques

### 1. Explosión por depósito en SQL (GROUP BY `codigo_movimiento` + `CodDeposito`)

Reescribir consultas kardex/stock para devolver una fila por `(movimiento, depósito)` con entrada/salida **de ese depósito**; calcular en Python tres corridos paralelos keyed por `tipo_mpr`.

| Pros | Contras | Esfuerzo |
|------|---------|----------|
| Alineado a datos fuente AdministraNET (`stock` por renglón depósito) | Toca 3 consultas + deduplicación; más filas en UI | **Alto** |
| Transferencias OPP naturales (salida origen, entrada destino) | Límite 2000 movimientos puede truncar más filas | |
| Paridad clara con inventario por `tipo_mpr` | | |

### 2. Post-proceso: segunda consulta de renglones `stock` por `codigo_movimiento`

Mantener cabecera movimiento; para pipeline, cargar detalle `stock` del movimiento y emitir sub-impactos por depósito antes del corrido.

| Pros | Contras | Esfuerzo |
|------|---------|----------|
| Diff más acotado en GROUP BY principal | N+1 o batch adicional; orden intra-movimiento a definir | **Medio-Alto** |
| Reutiliza clasificación actual por movimiento | Dos fuentes deben coincidir con MSTOCK | |

### 3. MVP oleada 1: etapa en fila + KPI cierre por etapa (sin corrido multi-columna completo)

Atributo `etapa`/`deposito` en cada fila donde sea unívoco; saldos iniciales/finales por etapa vía reconstrucción o delta desde inventario al cierre; grilla con una columna Etapa + saldo consolidado legacy.

| Pros | Contras | Esfuerzo |
|------|---------|----------|
| Entrega RF-05/06/07 parcial rápido | RF-02/04 incompletos en histórico intermedio | **Medio** |
| Menor riesgo UI | Usuario no ve evolución 79→28 en Semi fila a fila | |

### 4. Vista «estilo inventario»: columnas fijas Producción / Semi / 2da + Consolidado en cada fila

Backend calcula vector `saldos_etapa` tras cada movimiento (4 números); UI replica pivot inventario.

| Pros | Contras | Esfuerzo |
|------|---------|----------|
| Paridad visual directa con Stock Fabricados | Tabla ancha; sticky header más complejo | **Alto** (UI + backend) |
| RF-02 satisfecho de forma verificable | Presentación docenas en 4 columnas | |

---

## Recomendación

**Enfoque 1 (explosión por depósito en SQL)** como diseño objetivo, con posible **oleada 1 = Enfoque 3** solo si producto acota MVP (preguntas abiertas AF § UI y filas transferencia).

Secuencia sugerida para propose/design:

1. **Contrato de fila:** cada impacto con `id_deposito`, `tipo_mpr`, `entrada`, `salida`, `afecta_deposito`; transferencia interna = dos impactos mismo `codigo_movimiento`.
2. **Corrido:** dict `saldo_por_tipo_mpr` + `saldo_consolidado` derivado (RF-03); reutilizar orden `ETAPAS_FABRICADOS` de `inventario_tabla.py` para etiquetas/orden.
3. **Saldo inicial:** replay pre-período **por depósito** (misma explosión), no solo escalar consolidado.
4. **Conciliación RF-05:** helper que compare cierre vs `consultar_inventario_tabla(ambito=fabricados, id_articulo=…)` cuando `Hasta ≥ hoy`.
5. **Bifurcación:** `tipo_eje != pipeline_fabricados` mantiene camino actual (pack Terminado, semi único).
6. **Tests:** fixture OPP cross-depósito + assert 79/28/0 vs mock inventario; no debilitar golden pack Terminado.

Decisión pendiente producto/UX (AF): una fila con origen→destino vs dos renglones; no bloquea exploración.

---

## Riesgos

1. **Truncamiento `limit=2000`:** más filas por explosión → más advertencias de historial incompleto.
2. **Regresión pack Terminado:** cambios en `_normalizar_fila_kardex` compartida; exigir tests golden existentes.
3. **Movimientos multi-depósito no-OPP:** REM/INV/AJU pueden tocar un solo depósito; validar que no dupliquen filas.
4. **FA / `afecta_deposito=False`:** mantener exclusión del corrido; definir si aparece en columna etapa sin mover saldo.
5. **Presentación docenas:** redondeo por etapa puede diferir ±1 del inventario; documentar tolerancia AF.
6. **Sin snapshot histórico de etapas:** paridad estricta solo con `Hasta ≥ hoy` (AF pregunta 5).
7. **Componente con un solo depósito pipeline:** hoy cae a `tipo_eje: semi` (un depósito); AF apunta a `pipeline_fabricados` con ≥2 — no confundir casos en tests.
8. **Acoplamiento `subfilas_opa`:** depósito ya visible en armado pack; evitar duplicar semántica con nueva columna etapa del componente analizado.

---

## Tests que habrá que añadir o extender

| Área | Tipo |
|------|------|
| OPP transferencia Producción → Semi | Unit: dos impactos, consolidado invariante, Semi sube / Producción baja |
| Saldo inicial por etapa | Unit: pre-período por depósito |
| Cierre vs inventario | Integration/mock: `consultar_inventario_tabla` fabricados |
| CSV | Assert columnas etapa + saldos |
| Regresión pack | Re-ejecutar `TestGoldenSampleKardex610Blanco` y hub CSV |

---

## Listo para propuesta

**Sí.** El AF está alineado con el código; el gap está localizado en agregación SQL y modelo de corrido. Siguiente fase: **sdd-propose** (alcance oleadas MVP vs completo, criterios de aceptación enlazados a RF-01–07, forecast de líneas ~400–900 según enfoque 1 vs 3).

---

## Referencias cruzadas

| Documento / código | Uso |
|--------------------|-----|
| `docs/mpr/AF_TRAZABILIDAD_MOVIMIENTOS_POR_ETAPA.md` | MUST/SHOULD, criterios aceptación |
| `openspec/changes/command-center-paridad-consultas-vb6/exploration.md` | Plantilla estilo exploración |
| `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` | Canon UI reportes MPR (design) |
