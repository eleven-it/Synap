# Diseño: trazabilidad kardex por etapa (pipeline fabricados)

**Change:** `mpr-trazabilidad-movimientos-por-etapa` · **Fecha:** 17/09/2026 · **Modo:** evolution  
**AF:** `docs/mpr/AF_TRAZABILIDAD_MOVIMIENTOS_POR_ETAPA.md` · **Propuesta:** `proposal.md` · **Exploración:** `exploration.md`

---

## Enfoque técnico

Se explota cada movimiento por `stock.CodDeposito` **en SQL** (enfoque 1 de exploración) y se reemplaza el acumulador escalar por un **vector de saldos por `tipo_mpr`** con consolidado derivado. Todo el cambio queda **bifurcado** por `tipo_eje == "pipeline_fabricados"`: pack Terminado y componente de depósito único conservan el camino actual byte a byte (RF-10). El payload crece de forma **aditiva**; `saldo_corrido` sigue existiendo con el mismo significado (consolidado), de modo que `construir_kardex_articulo` y su proyección legacy no cambian.

---

## Decisiones de arquitectura (ADR)

### ADR-01 · Explosión por depósito en SQL, `tipo_mpr` resuelto en Python

**Elección:** añadir `s.CodDeposito` al `SELECT`/`GROUP BY`/`ORDER BY` de las tres consultas (`_consultar_movimientos_kardex_articulo`, `_consultar_movimientos_stock_rem_fa`, `_consultar_movimientos_inventario_mstock`) detrás de un flag `desglosar_por_deposito: bool = False`; el mapeo `CodDeposito → tipo_mpr` se resuelve con un mapa cargado una vez por request.

**Alternativas rechazadas:** (a) segunda consulta de renglones `stock` por movimiento (enfoque 2) — N+1 y dos fuentes que pueden divergir de MSTOCK; (b) `JOIN deposito` dentro de cada consulta — obliga a replicar los filtros `anulado`/`suma_stock` en tres SQL y dificulta el test unitario del SQL.

**Racional:** el dato ya existe por renglón en `stock`; el flag por defecto en `False` garantiza que packs y ejes de depósito único ejecuten el SQL actual. Un solo mapa sirve además para etiquetas, orden y conciliación.

### ADR-02 · Eje pipeline con los mismos filtros de depósito que inventario

**Elección:** nuevo helper en `mpr/services.py`:

```python
def get_etapas_pipeline_fabricados_mpr(base_empresa: str) -> List[Dict[str, Any]]:
    """[{id_deposito, tipo_mpr, label, orden}] en orden Produccion → SemiElaborado → 2daSeleccion,
    filtrando anulado='No' AND suma_stock='Si' (paridad inventario_tabla)."""
```

`construir_analisis_trazabilidad_articulo` toma de aquí `dep_ids` y el mapa; si devuelve `[]`, cae al legacy `get_depositos_pipeline_fabricados_mpr` (sin desglose) y emite advertencia.

**Alternativas rechazadas:** seguir usando `get_depositos_pipeline_fabricados_mpr` (no filtra `suma_stock`) — un depósito de pipeline con `suma_stock='No'` entraría en el kardex pero **no** en el inventario, produciendo un descuadre permanente e inexplicable en RF-05.

**Racional:** la conciliación exige que ambos lados definan el universo de depósitos igual. Se agrega helper nuevo en vez de cambiar el existente para no alterar los demás consumidores.

### ADR-03 · Clave de deduplicación `(codigo_movimiento, cod_deposito)`

**Elección:** `_deduplicar_movimientos` pasa a indexar por tupla; con `cod_deposito=None` (todos los ejes no-pipeline) el comportamiento es idéntico al actual. La clave de orden pasa a `(fecha_sort, codigo_movimiento, orden_impacto, orden_etapa, cod_deposito)`.

**Alternativas rechazadas:** deduplicar antes de explotar — reintroduce el neteo que el change viene a eliminar.

**Racional:** es el punto exacto donde hoy se perdería el segundo renglón de una transferencia; sin este cambio la regla de dos renglones (ADR-04) es inefectiva.

### ADR-04 · Transferencias internas: dos renglones, salida primero

**Elección:** la explosión ya produce dos impactos del mismo `codigo_movimiento`. Un post-proceso los marca: `es_transferencia_interna=True`, `contraparte={tipo_mpr,label,sentido}`, `orden_impacto=0` para el lado **salida** y `1` para el lado **entrada**, `es_primer_impacto=True` solo en el primero del movimiento.

**Alternativas rechazadas:** una fila con `origen → destino` — obliga a dos saldos en la misma fila y rompe la lectura columna a columna del corrido.

**Racional:** decisión de producto cerrada en propose; además hace visible el invariante «consolidado no cambia en transferencia pura» (RF-03/RF-04).

### ADR-05 · Corrido multi-etapa en backend, consolidado derivado

**Elección:** cada fila expone `saldos_por_etapa: {tipo_mpr: int}` (snapshot posterior al impacto, con **todas** las etapas del eje presentes) y `saldo_corrido = sum(saldos_por_etapa.values())`.

**Alternativas rechazadas:** derivar el vector en el cliente (Alpine) — el saldo inicial histórico y el orden intra-movimiento no son reconstruibles en UI; también rompería CSV.

**Racional:** RF-02/RF-03 verificables por test unitario; `saldo_corrido` conserva su semántica y contrato.

### ADR-06 · Stock actual por etapa: consulta propia en MPR, `inventario_tabla` solo como oráculo de test

**Elección:** nuevo `_fetch_stock_por_etapa_pipeline(base_empresa, id_articulo, etapas)` sobre `stock_deposito` agrupando por `tipo_mpr`, con los mismos filtros del `_sql_agg_subquery` de inventario. `consultar_inventario_tabla` **no** se invoca en el camino de request.

**Alternativas rechazadas:** llamar a `consultar_inventario_tabla(id_articulo=…, ambito=fabricados)` — filtra `tipo_art_fab IN ('Fabricado','Fabricado 2da')`, por lo que un componente con otro `tipo_art_fab` devolvería 0 filas y generaría un descuadre falso; además arrastra joins de catálogo y CE innecesarios.

**Racional:** paridad por **misma regla**, no por misma función. En tests sí se compara contra `consultar_inventario_tabla` como oráculo independiente.

### ADR-07 · Conciliación estricta por etapa solo con `Hasta >= hoy`, una sola advertencia

**Elección:** para eje pipeline, la advertencia consolidada actual se **reemplaza** por una advertencia por etapas que enumera solo las que difieren. Comparación siempre en pares (unidades), nunca en docenas.

**Alternativas rechazadas:** una advertencia por etapa (ruido) o mantener ambas (mensaje duplicado).

**Racional:** no existe snapshot histórico de etapas; fuera de «hoy» la comparación no tiene fuente de verdad (riesgo 6 de exploración).

### ADR-08 · UI: columna Etapa + tres columnas de saldo, **una sola fila de encabezado**

**Elección:** en `kardex_articulo.html`, solo cuando `meta.deposito.tipo_eje == "pipeline_fabricados"`: columna **Etapa** (badge) después de Tipo, y columnas `Producción | Semi | 2da | Consolidado` en lugar de la única `Saldo`. Sin fila de encabezado agrupador.

**Alternativas rechazadas:** `thead` de dos niveles con `colspan` — el sticky actual depende de un hack de `shadow-[0_-16px_0_0_#f8fafc,…]` como cortina opaca; una segunda fila exige recalcular `top` y reproducir la máscara, con riesgo alto de regresión visual.

**Racional:** paridad visual con inventario Fabricados al costo mínimo de fragilidad. Sin diálogos nativos (RF-12); el modal de comprobante existente se conserva.

### ADR-09 · Presentación docenas con el mismo helper que inventario

**Elección:** nuevo `preparar_saldos_etapa_kardex(...)` en `mpr/reportes_presentacion.py` que produce `saldos_por_etapa_celdas` usando `_celda_stock_deposito(saldo, modo, clamp_negativos=False)` — exactamente el helper que usa `preparar_filas_inventario_presentacion`.

**Alternativas rechazadas:** agregar `entrada`/`salida`/`saldo_corrido` a `CAMPOS_CANTIDAD` — ese set se aplica por coincidencia de clave a **todos** los reportes MPR y cambiaría reportes fuera de alcance.

**Racional:** misma descomposición docenas/pares en ambas pantallas ⇒ el redondeo no puede divergir (riesgo 5 de exploración queda cerrado, no solo documentado).

### ADR-10 · CSV con columnas dinámicas (packs byte-idénticos)

**Elección:** `analisis_trazabilidad_a_csv` recibe `etapas` y **solo** para eje pipeline añade, al final de la sección MOVIMIENTOS, `Etapa`, `Cód. depósito`, `Saldo Producción`, `Saldo Semi elaborado`, `Saldo 2da Selección`, y una sección `SALDOS POR ETAPA` (inicial / cierre / stock actual / diferencia). `CSV_COLUMNAS[("trazabilidad","kardex_articulo")]` **no se toca**: este reporte se exporta por `analisis_trazabilidad_a_csv` (`mpr/views.py`), ese dict es legacy.

**Racional:** RF-10 es restricción dura; con columnas dinámicas el CSV de pack no cambia ni un byte y el golden existente sigue verde sin editarse.

### ADR-11 · Límite y truncado en unidades de impacto

**Elección:** para eje pipeline, el `limit` efectivo se multiplica por la cantidad de etapas (tope duro 5000 ya presente) y la advertencia de truncado se evalúa sobre **movimientos distintos**, no sobre filas.

**Racional:** conservar el mismo horizonte histórico que hoy pese a que la explosión multiplica filas (riesgo 1 de exploración).

### ADR-12 · `conteo` de inventario pasa a ser por etapa

**Elección:** en eje pipeline, `conteo` de una fila `clase_ui == "inventario"` es `saldos_por_etapa[etapa]`, no el consolidado. Otros ejes sin cambio.

**Racional:** un conteo físico reconcilia un depósito; mostrar el consolidado en esa celda sería una lectura falsa.

---

## Flujo de datos

```
GET /mpr/reportes/?grupo=trazabilidad&reporte=kardex_articulo&id_articulo=…
        │
        ▼
mpr/views.py ReportesMPRView
        │  construir_analisis_trazabilidad_articulo(base, id_art, desde, hasta)
        ▼
mpr/services_kardex_articulo.py
  1. get_etapas_pipeline_fabricados_mpr ──→ etapas[] + mapa dep→tipo_mpr   (mpr/services.py)
  2. _fetch_stock_por_etapa_pipeline    ──→ stock_actual{tipo_mpr}         (stock_deposito)
  3. _recolectar_movimientos_analisis(solo_pre_periodo=True, desglosar=True)
                                        ──→ impactos previos → saldo_inicial{tipo_mpr}
  4. _recolectar_movimientos_analisis(rango, desglosar=True)
       ├─ _consultar_movimientos_kardex_articulo   (OPP/OPA, GROUP BY … , s.CodDeposito)
       ├─ _consultar_movimientos_stock_rem_fa      (REM/FA)
       └─ _consultar_movimientos_inventario_mstock (INV/INI/AJU)
                                        ──→ _normalizar_* → impactos con cod_deposito
  5. _marcar_transferencias_internas   ──→ es_transferencia_interna / contraparte / orden_impacto
  6. _deduplicar_movimientos           ──→ clave (codigo_movimiento, cod_deposito)
  7. _calcular_saldo_corrido_por_etapa ──→ fila.saldos_por_etapa + saldo_corrido
  8. _conciliar_cierre_por_etapa       ──→ kpis.conciliacion_por_etapa + advertencias
        │
        ▼
mpr/reportes_presentacion.preparar_saldos_etapa_kardex (docenas/pares)
        │                                   │
        ▼                                   ▼
partials/kardex_articulo.html        mpr/export.analisis_trazabilidad_a_csv
```

### Secuencia de una transferencia OPP Producción → Semi

```mermaid
sequenceDiagram
    participant SQL as MySQL (stock)
    participant N as _normalizar_fila_kardex
    participant T as _marcar_transferencias_internas
    participant A as _calcular_saldo_corrido_por_etapa
    SQL->>N: (mov 8801, dep 3 Produccion) Entrada 0 / Salida 12
    SQL->>N: (mov 8801, dep 5 SemiElaborado) Entrada 12 / Salida 0
    N->>T: 2 impactos, mismo codigo_movimiento
    T->>A: impacto A orden 0 (salida, contraparte Semi elaborado)
    T->>A: impacto B orden 1 (entrada, contraparte Producción)
    A->>A: Produccion 91-12=79 ; consolidado 107
    A->>A: SemiElaborado 16+12=28 ; consolidado 107 (invariante)
```

---

## Contrato de payload (aditivo)

```python
# fila de `movimientos[]` — campos NUEVOS (los actuales se conservan)
{
  "cod_deposito": 3,                     # int | None (None = eje sin desglose)
  "etapa": {"tipo_mpr": "Produccion", "label": "Producción", "orden": 0},   # dict | None
  "etapa_label": "Producción",           # atajo para UI/CSV; "" si no aplica
  "es_transferencia_interna": True,
  "contraparte": {"tipo_mpr": "SemiElaborado", "label": "Semi elaborado", "sentido": "entrada"},
  "es_primer_impacto": True,             # gobierna botón expandir y subfilas_opa
  "orden_impacto": 0,                    # 0 = salida (origen), 1 = entrada (destino)
  "saldos_por_etapa": {"Produccion": 79, "SemiElaborado": 28, "2daSeleccion": 0},
  "saldo_corrido": 107,                  # EXISTENTE = suma de saldos_por_etapa
  "conteo": 79,                          # por etapa en eje pipeline (ADR-12)
}

# saldo_inicial
{"valor": 107, "calculado_ok": True, "origen": "historico_pre_periodo",
 "por_etapa": {"Produccion": 91, "SemiElaborado": 16, "2daSeleccion": 0}}   # NUEVO

# deposito
{"id": None, "ids": [3, 5, 7], "nombre": "…", "tipo_eje": "pipeline_fabricados",
 "etapas": [{"id_deposito": 3, "tipo_mpr": "Produccion", "label": "Producción", "orden": 0}, …]}  # NUEVO

# stock
{"terminado": 107, "negativo": False, "semi_componentes": [],
 "por_etapa": {"Produccion": 79, "SemiElaborado": 28, "2daSeleccion": 0}}   # NUEVO

# kpis — campos NUEVOS
{"saldo_final_por_etapa": {...}, "stock_por_etapa": {...},
 "etapas": [{"tipo_mpr": "...", "label": "..."}, ...],
 "conciliacion_estricta": True,          # Hasta >= hoy y eje pipeline
 "conciliacion_por_etapa": {"Produccion": {"kardex": 79, "inventario": 79, "diferencia": 0}, ...}}
```

**Invariantes del contrato:** (1) `saldo_corrido == sum(saldos_por_etapa.values())` en toda fila de eje pipeline; (2) `saldos_por_etapa` contiene siempre las tres claves del eje; (3) en eje no-pipeline los campos nuevos son `None`/`{}` y `_proyectar_movimientos_kardex_compat` los descarta sin cambios.

---

## Algoritmos

### Explosión por depósito

```sql
SELECT m.codigo_movimiento, m.fecha, …, s.CodDeposito AS cod_deposito,
       COALESCE(SUM(s.Entrada), 0) AS total_entrada,
       COALESCE(SUM(s.Salida),  0) AS total_salida
FROM movimiento_stock m INNER JOIN stock s ON s.CodigoMovimiento = m.codigo_movimiento
WHERE s.IDArt = %s AND … AND s.CodDeposito IN (%s, %s, %s)
GROUP BY m.codigo_movimiento, m.fecha, …, s.CodDeposito      -- + s.CodDeposito
ORDER BY m.fecha ASC, m.codigo_movimiento ASC, s.CodDeposito ASC
LIMIT %s
```

`_normalizar_fila_kardex` **no cambia de lógica**: sobre una fila ya explotada, la rama OPP (`entrada`) recibe el renglón de un solo depósito, por lo que el origen queda `(0, 12)` y el destino `(12, 0)` de forma natural. Impacto cuyo `cod_deposito` no esté en el mapa (no debería ocurrir por el `IN`) se descarta y suma advertencia.

### Saldo multi-etapa

```python
saldos = dict(saldo_inicial_por_etapa)          # todas las etapas del eje
for imp in ordenados:                            # (fecha, cod_mov, orden_impacto, orden_etapa, dep)
    tipo = (imp.get("etapa") or {}).get("tipo_mpr")
    if imp.get("afecta_deposito", True) and tipo in saldos:
        saldos[tipo] += imp["entrada"] - imp["salida"]
    imp["saldos_por_etapa"] = dict(saldos)       # copia = snapshot
    imp["saldo_corrido"] = sum(saldos.values())
```

FA (`afecta_deposito=False`) sigue fuera del acumulado y del listado (regla preservada del AF).

### Saldo inicial por etapa

1. **Primario:** replay pre-período con la misma explosión → `inicial[tipo] = Σ(entrada − salida)` por etapa.
2. **Fallback** (replay no disponible): `inicial[tipo] = stock_actual[tipo] − neto_periodo[tipo]`, usando `_fetch_stock_por_etapa_pipeline`. El fallback es por etapa, nunca por consolidado repartido.

### Conciliación (`Hasta >= hoy`)

```python
if eje_pipeline and hasta >= hoy and calculado_ok:
    difs = [(label, kardex, inv) for etapa … if kardex != inv]     # comparación en pares
    if difs:
        advertencias.append("El saldo reconstruido al cierre no coincide con el inventario "
                            "por etapa: " + "; ".join(f"{l}: kardex {k} vs inventario {i}" for …))
```
Sustituye (no acumula) la advertencia consolidada actual para este eje. El consolidado se valida por construcción (suma).

---

## Cambios de archivos

| Archivo | Acción | Descripción |
|---|---|---|
| `mpr/services.py` | Modificar | `get_etapas_pipeline_fabricados_mpr` (id + `tipo_mpr` + label + orden, filtros `anulado`/`suma_stock`) |
| `mpr/services_kardex_articulo.py` | Modificar | flag `desglosar_por_deposito` en 3 consultas; `cod_deposito`/`etapa` en normalizadores; `_marcar_transferencias_internas`; clave dedupe; `_calcular_saldo_corrido_por_etapa`; `_calcular_saldo_inicial_por_etapa`; `_fetch_stock_por_etapa_pipeline`; `_conciliar_cierre_por_etapa`; payload |
| `mpr/reportes_presentacion.py` | Modificar | `preparar_saldos_etapa_kardex` reutilizando `_celda_stock_deposito` |
| `mpr/views.py` | Modificar | pasar etapas a presentación; `subfilas_opa`/botón expandir solo si `es_primer_impacto`; `etapas` a CSV |
| `mpr/templates/mpr/reportes/partials/kardex_articulo.html` | Modificar | columna Etapa + 3 columnas de saldo + Consolidado (condicional); desglose por etapa en cards de saldo inicial/cierre y en badge de stock de cabecera |
| `mpr/export.py` | Modificar | columnas dinámicas en MOVIMIENTOS + sección `SALDOS POR ETAPA` |
| `mpr/tests/test_analisis_trazabilidad_articulo.py` | Modificar | contratos backend (ver plan de pruebas) |
| `mpr/tests/test_kardex_articulo.py` | Modificar | UI condicional + CSV pipeline; golden pack sin editar |
| `mpr/tests/test_paridad_kardex_inventario_etapa.py` | Crear | paridad cierre vs `consultar_inventario_tabla` (oráculo) |
| `docs/mpr/AF_TRAZABILIDAD_MOVIMIENTOS_POR_ETAPA.md` | Modificar | cerrar preguntas abiertas 1–5 con las decisiones de este diseño |
| `docs/mpr/README.md` | Modificar | índice / nota de contrato nuevo |
| `stock/services/inventario_tabla.py` | Solo lectura | **MUST NOT** modificar (RF-11); consumido en tests |

---

## No-regresión de packs (RF-10)

| Vector | Garantía |
|---|---|
| SQL | `desglosar_por_deposito=False` por defecto ⇒ mismo `GROUP BY`, mismos params |
| Dedupe | `cod_deposito=None` ⇒ clave equivalente a la actual |
| Corrido | eje no-pipeline usa `_calcular_saldo_corrido_analisis` sin tocar |
| Payload | `_proyectar_movimientos_kardex_compat` inalterado ⇒ `construir_kardex_articulo` idéntico |
| UI | bloque nuevo bajo `{% if meta.deposito.tipo_eje == "pipeline_fabricados" %}` |
| CSV | columnas dinámicas ⇒ export de pack byte-idéntico |
| Test | `TestGoldenSampleKardex610Blanco` y `TestArticulo340StockInicialRemSobrante` deben pasar **sin editarse** |

---

## Plan de pruebas

| Capa | Qué se prueba | Cómo |
|---|---|---|
| Unit | SQL explotado incluye `s.CodDeposito` en SELECT/GROUP BY/ORDER BY y orden de params | mock cursor, assert sobre SQL y `params` (patrón `TestConsultarInventarioMstockParams`) |
| Unit | Flag apagado ⇒ SQL sin `CodDeposito` (no-regresión) | mismo patrón |
| Unit | OPP Producción→Semi: dos impactos sobreviven al dedupe, salida antes que entrada | `_deduplicar_movimientos` + orden |
| Unit | Transferencia pura: Producción baja, Semi sube, **consolidado invariante** | `_calcular_saldo_corrido_por_etapa` |
| Unit | `saldo_corrido == sum(saldos_por_etapa)` en todas las filas | invariante sobre fixture |
| Unit | Saldo inicial por etapa vía replay pre-período y vía fallback `stock_actual − neto` | `_calcular_saldo_inicial_por_etapa` |
| Unit | FA no mueve ninguna etapa ni el consolidado | fixture con FA |
| Unit | `conteo` de fila INV = saldo de su etapa (ADR-12) | fixture inventario |
| Unit | Impacto en depósito fuera del mapa ⇒ descartado + advertencia | fixture borde |
| Integración | Cierre 79 / 28 / 0 / 107 con `Hasta >= hoy` cuadra con oráculo `consultar_inventario_tabla(ambito=fabricados)` | `test_paridad_kardex_inventario_etapa.py` con mocks de `stock_deposito` compartidos |
| Integración | `Hasta < hoy` ⇒ `conciliacion_estricta=False`, sin advertencia de descuadre | payload |
| Integración | Descuadre en una etapa ⇒ una sola advertencia que nombra solo esa etapa | payload |
| Contrato UI | Eje pipeline renderiza columna Etapa + 4 columnas de saldo; eje Terminado no las renderiza | `assertContains`/`assertNotContains` |
| Contrato UI | Botón expandir OPA aparece una sola vez por movimiento | conteo en HTML |
| Contrato CSV | Sección MOVIMIENTOS con columnas de etapa + sección `SALDOS POR ETAPA` en pipeline | `analisis_trazabilidad_a_csv` |
| Regresión | Golden pack Terminado y CSV de pack, **sin editar el test** | suites existentes |
| Presentación | Docenas: celda de etapa usa la misma descomposición que inventario (mismo input ⇒ mismo output) | comparación directa con `_celda_stock_deposito` |

Comando: `docker exec Synap_app python manage.py test mpr.tests.test_analisis_trazabilidad_articulo mpr.tests.test_kardex_articulo mpr.tests.test_paridad_kardex_inventario_etapa mpr.tests.test_reportes_trazabilidad`

---

## Matriz de amenazas

**N/A** — el change no toca routing, comandos de shell, subprocesos, automatización VCS/PR, clasificación de archivos ejecutables ni integración de procesos. Nota de seguridad fuera de matriz: todo filtro de depósito y fecha se mantiene **parametrizado** (`%s`); los valores `tipo_mpr` provienen de constantes del código, nunca de la query string.

---

## Migración / rollout

Sin DDL, sin migraciones Django, sin feature flag: el cambio es de lectura y su alcance está acotado por `tipo_eje`. Rollback = revertir el merge (`proposal.md` § Rollback Plan).

**Costura de PR encadenado** (presupuesto 400 líneas, estrategia `ask-on-risk`): el payload es aditivo, por lo que el corte natural es
- **PR1 — backend + tests:** `mpr/services.py`, `mpr/services_kardex_articulo.py`, tests unitarios y de paridad. Entrega verificable RF-01–05 sin tocar UI.
- **PR2 — UI + CSV + docs:** template, `reportes_presentacion.py`, `views.py`, `export.py`, tests de contrato UI/CSV, docs. Entrega RF-06/07/09.

---

## Riesgos

| # | Riesgo | Mitigación |
|---|---|---|
| 1 | `_deduplicar_movimientos` colapsa los dos renglones de la transferencia (regresión silenciosa del objetivo) | ADR-03 + test dedicado que falla antes del fix |
| 2 | Depósito de pipeline con `suma_stock='No'` cambia el consolidado actual del kardex | ADR-02 explícito + advertencia cuando se excluye un depósito; documentar en AF |
| 3 | Explosión multiplica filas y dispara truncado por `limit` | ADR-11 (límite por impacto, truncado por movimientos distintos) |
| 4 | Regresión visual del `thead` sticky al ampliar columnas | ADR-08 (una sola fila de encabezado); test de contrato UI |
| 5 | Redondeo docenas divergente vs inventario | ADR-09 (mismo helper) |
| 6 | `subfilas_opa` duplicadas por impacto | `es_primer_impacto` + test de conteo en HTML |
| 7 | Tests que hoy parchean `get_depositos_pipeline_fabricados_mpr` dejan de cubrir el camino real | actualizar `TestComponenteUsaPipelineFabricadosPorDefecto` para el helper nuevo, manteniendo el fallback probado |
| 8 | Sin snapshot histórico, paridad solo con `Hasta >= hoy` | ADR-07; `conciliacion_estricta` explícito en el payload |

---

## Preguntas abiertas

- [ ] ¿La advertencia por descuadre debe además exponerse como bloque de conciliación visible (no solo aviso ámbar)? — no bloquea; el payload ya lo permite (`kpis.conciliacion_por_etapa`).
- [ ] RF-08 (filtro/pestaña por etapa) queda fuera del MVP; confirmar con producto si entra en oleada 2 junto con packs.
