# Reportes MPR — catálogo y fuentes

**Ruta:** `/mpr/reportes/`  
**Change:** `mpr-reportes-trazabilidad-produccion`  
**Fecha:** 04/07/2026 — **actualizado 08/07/2026** (Fabricando, control de calidad, componentes vs pack)

---

## Propósito

Centro de **analítica y trazabilidad** del flujo MPR diario:

```text
Envío tablero → Parte de producción → Control de calidad (clasificación) → Armado pack (terminado)
```

Los reportes leen **ledgers Synap** (`mpr_envio_produccion`, `mpr_parte_linea`, `mpr_transicion_lote`) y el **tablero consolidado** en vivo para demanda/stock de **componentes**.

---

## Modelo conceptual (sincronizado con operación)

### Pack vs componente

| Nivel | Rol en reportes | Depósito Terminado |
|-------|-----------------|--------------------|
| **Componente** (semi elaborado) | Tablero, parte, clasificación CC, cadena pipeline, pendientes | **No** — el componente no va a PT; el terminado es del pack |
| **Pack** (artículo armado) | Demanda pack, brecha pack, armado, stock terminado | **Sí** — saldo PT tras armado 1ra/2da |

Los reportes de **Producción** en este hub miden el pipeline de **componentes**, salvo los de **Demanda** (pack).

### Cadena ledger (embudo)

| Etapa operativa | Pantalla | Tabla / fuente | Qué mide el reporte |
|-----------------|----------|----------------|---------------------|
| 1. Compromiso de fabricación | Tablero → Enviar | `mpr_envio_produccion` | **Enviado** (resumen, cadena) |
| 2. Registro en planta | Parte de producción | `mpr_parte` / `mpr_parte_linea` | **Parte** (resumen, cadena, por operario) |
| 3. Control de calidad | Clasificación producción | `mpr_transicion_lote` (`tipo_origen = Produccion`) | **Clasificado**, **Scrap**, rendimiento por operario fabricante |
| 4. Armado | Armado 1ra / 2da | `movimiento_stock` Armado, stock PT pack | Fuera del hub Producción; ver demanda pack / stock |

**Clasificado** en reportes = suma de salidas desde **Producción** hacia Semi / 2da / Scrap (no incluye movimientos de armado ni terminado de pack).

### Fabricando (cupo operativo, no es columna de reporte)

Concepto compartido por **tablero de producción** y **parte de producción**:

```text
Fabricando(comp) = max(0, Σ envíos_tablero(comp) − acreditado(comp))

acreditado(comp) = max(
  stock_fisico_pipeline,            # Semi + 2da + Scrap (Producción NO acredita)
  clasificado_desde_Producción,   # SUM(mpr_transicion_lote WHERE tipo_origen = 'Produccion')
  partes_acumulados                 # SUM(mpr_parte_linea + ajustes)
)
```

- **No** usa depósito **Terminado** del componente.
- Tras CC + armado del pack, el semi del componente puede quedar en **0** físico; la trazabilidad en `mpr_transicion_lote` evita que Fabricando repunte.
- **No** usa depósito **Producción** en el acreditado (destino del parte / cola CC). Stock preexistente ahí no anula Fabricando tras Enviar.
- Si **Fabricando = 0**, el componente **no aparece** habilitado en la grilla de parte. Primero Enviar desde el Tablero.

Ver: [TABLERO_CONSOLIDADO.md](TABLERO_CONSOLIDADO.md), [PARTE_PRODUCCION.md](PARTE_PRODUCCION.md), [ENVIO_PRODUCCION_TABLERO.md](ENVIO_PRODUCCION_TABLERO.md).

### Control de calidad (clasificación por operario)

Documento de referencia: [DOCENAS_CLASIFICACION_OPERARIO_MPR.md](DOCENAS_CLASIFICACION_OPERARIO_MPR.md).

| Concepto | Regla |
|----------|-------|
| Fila CC | Artículo × **operario fabricante** (el que registró el parte) |
| Pendiente CC | Solo unidades en **Producido** sin clasificar para fecha+turno del clasificador |
| Bloqueo falso positivo | No bloquea si la fila ya está 100 % clasificada o sin cantidad sin operario |
| Ledger | `mpr_transicion_lote.id_operario` = fabricante; `id_usuario` = quien guardó la clasificación |
| Destinos | Semi elaborado, 2da selección, Scrap (desde Producción) |

El reporte **Por operario** cruza **parte** (`mpr_parte_linea`) con **clasificación por fabricante** (`sumar_clasificado_rendimiento_operario`) para semi / 2da / scrap y % apto / % scrap.

### Presentación docenas | pares

Toggle en tablero, parte, clasificación y reportes. Persistencia siempre en **pares** (unidades). Divisor componentes: **12 pares = 1 docena**. Ver `mpr/reportes_presentacion.py` y `mpr/presentacion_operativa.py`.

---

## Navegación

| Grupo | Reportes | Fuente principal |
|-------|----------|------------------|
| **Producción** | Resumen diario, Por operario, Por operario (mensual), Por operario y máquina, Cadena pipeline, Pendiente componentes | `mpr_envio_produccion`, `mpr_parte_linea`, `mpr_transicion_lote`, `listar_tablero_por_articulo` |
| **Demanda** | Brecha pack, Pedidos por estado, Stock, Bajo mínimo | PED en vivo, `comp_ped`, stock pack |
| **Trazabilidad** | Línea de tiempo, Movimientos, Conciliación envíos↔producción | Ledgers `mpr_envio_produccion`, `mpr_parte_linea`, `mpr_transicion_lote` |

### Reportes de trazabilidad máquina/línea (Fase 8 — change `mpr-trazabilidad-maquina-linea-operario`)

- **Por operario y máquina** (`produccion/operario_maquina`): `reporte_mpr_operario_maquina` agrupa por operario × máquina (con la línea vigente) y suma `cantidad_declarada`, `cantidad_aprobada` y `gap`. Los partes históricos sin máquina se agrupan como "Sin máquina".
- **Conciliación envíos↔producción** (`trazabilidad/conciliacion`): `reporte_mpr_conciliacion_envios_produccion` compara, por componente, lo **enviado** a fabricación (`mpr_envio_produccion`) contra lo **producido aprobado** (`mpr_parte_linea` de partes `estado='aprobado'`) y marca lo **no respaldado** (`producido − enviado > 0`), es decir, stock generado sin envío que lo respalde.

**Default:** Producción → Resumen diario, últimos 7 días.

**Sin `lista_produccion_*`:** el hub de reportes no consulta tablas OPT legacy. Para **eliminar físicamente** las tablas en MySQL:

```bash
docker exec Synap_app python manage.py drop_mpr_lista_produccion_legacy administranet96 --confirm
```

También disponible en **Archivo → Parámetros → Migración esquema MySQL** (`mpr_drop_lista_produccion_legacy`, riesgo alto).

---

## Reportes de Producción — definición por informe

### Resumen diario

Consolidado de **producción registrada por día** en el período filtrado. Réplica de la
hoja **«Produccion Diario»** del Excel de fábrica (`Best Sox/Produccion.xlsx`, pivote
`Origen = Producción` → *Docenas Producidas*): una sola cantidad por día, agrupada por
**Año/Mes** con **subtotal por mes** y **Total general**. Solo se listan los días con
producción registrada (los días sin partes se omiten, igual que el pivote).

| Columna / KPI | Fuente SQL | Interpretación |
|---------------|------------|----------------|
| **Producción registrada** (por día) | `SUM(mpr_parte_linea.cantidad)` por `fecha_produccion` | Cantidad consolidada de partes registrados ese día (= *Docenas Producidas*, Origen=Producción en BEST) |
| **Subtotal por mes / Total general** | suma de la producción diaria | Paridad con «Total {mes}» y total del pivote Excel |
| KPI **Producción registrada** | `SUM(parte)` del período | Total producido |
| KPI **Días con producción** | conteo de días con `parte > 0` | Días efectivos |

**Agrupación (estilo BO):** filas de grupo por **mes colapsables** (chevron que rota, subtotal
en la propia fila de grupo, filas de día indentadas) replicando el patrón de las tablas de los
reportes de Back Office (`renderGroupedTableRowsBO`). Paleta slate/sky.

**Gráfico:** barras verticales de producción registrada por día (solo días con datos).

**Nota paridad BEST/PCP:** la serie comparable a *producción diaria de planta* es **Parte**
(producción registrada), no Enviado. Las métricas de pipeline (Enviado, Clasificado, Scrap,
Gap envío→parte) siguen disponibles en **Cadena pipeline** y **Por operario**.
Ver [BEST_SOX_ITERACION1_VALIDACION.md](BEST_SOX_ITERACION1_VALIDACION.md).

### Por operario

Ranking de **productividad** (parte) y **rendimiento de clasificación** (CC).

| Campo | Fuente |
|-------|--------|
| Unidades / partes / componentes | `mpr_parte_linea` agrupado por `id_operario` |
| Semi / 2da / Scrap | `mpr_transicion_lote` con `id_operario` fabricante (`sumar_clasificado_rendimiento_operario`) |
| % apto (semi) | `semi / unidades_parte × 100` |
| % scrap | `scrap / unidades_parte × 100` |

**Gráfico:** barras horizontales top 12 por unidades; variante apilada semi · 2da · scrap.

**Prerrequisito MySQL:** columnas operario en `mpr_transicion_lote` (`apply_mpr_core_tables <base>`).

### Por operario (mensual)

Réplica de la tabla dinámica **«Producción x Tejedor»** del Excel de fábrica: pivote con
grano **Año → Mes** en filas y **operario (tejedor)** en columnas, con subtotales por año
y **Total general** (Fase B del plan `PLAN_REPORTE_POR_OPERARIO_TEJEDOR_Y_CONTINUIDAD_HISTORICA.md`).

- **Selector predictivo con tags:** permite elegir **1** operario (filtrar) o **2** (comparar).
  Con 2 seleccionados aparece la columna **Δ** (diferencia col1 − col2, con color verde/rojo).
  Sin selección se muestran **todos** los operarios del período (ordenados por producción).
- **Parámetro URL:** `?...&op=<id1>,<id2>` (se preserva al cambiar período/presentación).
- **Servicio:** `reporte_mpr_operario_mensual` (`mpr/services.py`), fuente nativa
  `mpr_parte_linea` × `mpr_parte.fecha_produccion` (`SUM(cantidad)` en pares; presentación docenas/pares).
- **CSV:** filas planas `operario · Año · Mes · Cantidad`.

> Sugerencia: ampliar el período (p. ej. «Este mes» → rango anual con el selector de fechas)
> para ver la evolución mensual completa. El histórico previo al corte (BEST) se integra en la Fase C.

### Cadena pipeline

Snapshot **por componente** en el período. El embudo muestra las 4 etapas del pipeline:
**En fabricación** (enviado) → **Producido** (parte) → **Semi elaborado** → **2da selección**.

- **En fabricación** = `mpr_envio_produccion` (compromiso de fabricación / enviado a planta).
- **Producido** = `mpr_parte_linea` (producción registrada en parte).
- **Semi elaborado** = `mpr_transicion_lote` (`tipo_origen = Produccion`, `tipo_destino = SemiElaborado`).
- **2da selección** = `mpr_transicion_lote` (`tipo_origen = Produccion`, `tipo_destino = 2daSeleccion`).

`Clasificado` (interno) = Semi + 2da + Scrap; se conserva para el cálculo del **Estado**.

| Estado | Condición |
|--------|-----------|
| Sin envío | `enviado = 0` |
| Falta parte | `enviado > parte` |
| Falta clasificar | `parte > clasificado` |
| Completo | `enviado ≤ parte` y `parte ≤ clasificado` |

**Importante:** estado **Completo** significa que el flujo **envío → parte → CC** cerró en el período para ese componente. **No** implica armado de pack ni stock terminado. Un componente puede estar «Completo» en CC y tener **Fabricando = 0** en tablero aunque el semi ya se haya consumido en armado.

**Gráficos:** barras embudo planta (4 etapas); dona por estado; brechas en fabricación → producido (top componentes).

### Pendiente componentes

**Instantánea** del tablero consolidado (`listar_tablero_por_articulo`) — **el filtro de fechas del hub no aplica**.

| Campo reporte | Campo tablero | Notas |
|---------------|---------------|-------|
| Demanda / resta urgente / resta total | PCP pack explotado por BOM | Paridad Excel PCP |
| Fabricando | `enviado` en servicio | Cupo ledger − acreditado (ver fórmula arriba) |
| Stock pipeline | Producido, 2da, Semi | **Sin Terminado** en componentes |
| Pendiente | `resta_total` | Brecha demanda − stock en proceso |

**Gráfico:** barras horizontales top 12 por `pendiente` (crítico ≥ 50 u.).

---

## Reportes de Demanda y Trazabilidad

| Reporte | Alcance |
|---------|---------|
| **Brecha pack** | Demanda pack vs stock terminado (PT) |
| **Pedidos por estado** | PED / `comp_ped` en vivo |
| **Stock / Bajo mínimo** | Saldos por depósito (`suma_stock`) |
| **Línea de tiempo** | Eventos ledgers por `id_articulo` |
| **Movimientos** | Unión cronológica envíos, partes, transiciones |

---

## Filtros

- **Desde / Hasta** (visualización dd/MM/yyyy)
- Presets: Hoy, 7 días, Mes
- **Presentación:** Pares (entero) o Docenas (`docenas · pares`, divisor 12 en componentes). Parámetro: `?presentacion=unidades|pares|docenas` (`pares` es alias de `unidades`). Se conserva al navegar y al exportar CSV.
- **Marcas** (pantallas operativas; pendiente de extensión uniforme en todos los reportes): `marcas_incluidos` en tablero, parte y CC.

### Exportar CSV

UTF-8 BOM en reportes principales de Producción y Demanda; en modo docenas exporta columnas `*_display`.

### UI compacta (chrome denso alineado al Tablero — 26/07/2026)

El hub usa el **chrome denso slate-800** del Tablero de producción ([TABLERO_PRODUCCION_CHROME_DENSIDAD.md](TABLERO_PRODUCCION_CHROME_DENSIDAD.md) §3.1), **sin migas de pan**:

- Barra `sticky top-14 md:top-16 z-40` bajo el navbar, `rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 shadow-md`, en **dos filas densas**.
- Fila 1: `h1` blanco con el título del reporte + subtítulo `dd/MM/yyyy — dd/MM/yyyy · presentación`; Desde/Hasta (`h-9` oscuros) + presets Hoy / 7 días / Mes; toggle **Docenas | Pares** (`includes/toggle_docenas_pares.html` con `variant="dark"`, activo sky); **Actualizar** secundario `slate-700` y **Exportar CSV** secundario slate (solo ícono + tooltip por debajo de `2xl`); a la derecha CTA **Tablero de producción** (emerald → `mpr:tablero_produccion`), `chrome_nav_flujo.html` (`current="tablero_prod"`) y ayuda `help_outline` → manual MPR.
- Fila 2: grupos (Producción / Demanda / Trazabilidad, activo púrpura) + pills de reporte (activo slate-600) y chips KPI densos sobre fondo oscuro.
- Zona de datos: tarjeta `rounded-lg border-slate-200` con scroll interno dentro del viewport (`h-[calc(100dvh-4.5rem)]`); fondo de página `bg-slate-50`.

El **Tablero KPI** (`mpr:tablero`) ya no es CTA primario: queda como ícono ámbar dentro de `chrome_nav_flujo`.

### Infraestructura gráficos

| Archivo | Rol |
|---------|-----|
| `mpr/reportes_charts.py` | `build_charts_produccion(reporte, ctx)` |
| `mpr/static/mpr/js/mpr_reportes_charts.js` | Init Chart.js |
| `mpr/templates/mpr/reportes/partials/_mpr_charts.html` | Shell de bloques |

### Módulo de presentación

| Archivo | Rol |
|---------|-----|
| `mpr/reportes_presentacion.py` | `parse_modo_presentacion`, `aplicar_presentacion_reporte`, campos `*_display` |
| `ReportesMPRView` | Aplica presentación tras cargar datos del reporte |

---

## Compatibilidad URLs antiguas (sin OPT)

| URL legacy | Destino |
|------------|---------|
| `?tipo=produccion_operario` | Producción → Por operario |
| `?tipo=stock` | Demanda → Stock |
| `?tipo=bajo_minimo` | Demanda → Bajo mínimo |
| `?tipo=pendiente`, `wip`, `desperdicio`, `opt_cerradas` | Default: Resumen diario |

Los reportes basados en `lista_produccion_*` / OPT **no están disponibles** en este hub.

---

## Servicios (backend)

| Servicio | Archivo |
|----------|---------|
| `reporte_mpr_resumen_diario` | `mpr/services.py` |
| `reporte_mpr_operario_parte` | `mpr/services.py` |
| `reporte_mpr_cadena_pipeline` | `mpr/services.py` |
| `reporte_mpr_pendiente_componentes` | `mpr/services.py` |
| `reporte_mpr_trazabilidad_componente` | `mpr/services.py` |
| `reporte_mpr_movimientos` | `mpr/services.py` (ledgers `mpr_*`, respeta período) |
| Hub vista / routing | `mpr/reportes_hub.py`, `mpr/views.py` `ReportesMPRView` |
| Tablero / Fabricando | `listar_tablero_por_articulo`, `_fabricando_por_componentes` |
| CC / clasificación | `construir_grilla_clasificacion_produccion`, `mpr/repositories/transicion_lote.py` (incl. `cantidad_extra` extra producción) |

---

## Lectura cruzada (operación ↔ reporte)

| Pregunta de planta | Dónde operar | Dónde reportar |
|--------------------|--------------|----------------|
| ¿Qué falta enviar a fabricar? | Tablero — Resta urgente / Enviar | Pendiente componentes |
| ¿Qué está en curso sin parte? | Tablero — Fabricando | Cadena pipeline (Falta parte) |
| ¿Qué falta clasificar en CC? | Control de calidad | Cadena pipeline (Falta clasificar) |
| ¿Cuánto hizo cada operario? | Parte de producción | Por operario |
| ¿Calidad por operario (semi/2da/scrap)? | Control de calidad | Por operario (columnas clasificación) |
| ¿Cuánto pack falta armar? | Armado tablero PCP | Brecha pack (demanda) |

---

## Tests

```bash
docker exec Synap_app python manage.py test \
  mpr.tests.test_reportes_shell_legacy_map \
  mpr.tests.test_reportes_resumen_diario \
  mpr.tests.test_reportes_operario_parte \
  mpr.tests.test_reportes_cadena_pipeline \
  mpr.tests.test_reportes_trazabilidad \
  mpr.tests.test_reportes_mpr_view \
  mpr.tests.test_reportes_presentacion \
  mpr.tests.test_tablero_consolidado \
  mpr.tests.test_etapa8_parte_por_componente \
  mpr.tests.test_docenas_clasificacion_operario \
  --keepdb
```

---

## Referencias

- [DOCENAS_CLASIFICACION_OPERARIO_MPR.md](DOCENAS_CLASIFICACION_OPERARIO_MPR.md) — CC por operario fabricante y docenas operativas
- [TABLERO_CONSOLIDADO.md](TABLERO_CONSOLIDADO.md) — columnas tablero y Fabricando
- [PARTE_PRODUCCION.md](PARTE_PRODUCCION.md) — grilla parte y validaciones
- [TRANSICIONES_LOTE.md](TRANSICIONES_LOTE.md) — ledger `mpr_transicion_lote`
- [DISENO_ARMADO_TABLERO_PCP.md](DISENO_ARMADO_TABLERO_PCP.md) — armado pack (terminado)
  stock_fisico_post_CC,             # Semi + 2da + Scrap (NO Producción)
