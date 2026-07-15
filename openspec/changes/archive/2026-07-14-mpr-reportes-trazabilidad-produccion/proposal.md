# Propuesta — Reportes MPR: trazabilidad y producción visual

**Change:** `mpr-reportes-trazabilidad-produccion`  
**Fecha:** 04/07/2026  
**Modo:** Product Mode (experiencia de usuario + analítica operativa)  
**Depende de:** `mpr-mysql-fuente-unica`, tablero consolidado desacoplado de OPT  
**Exploración:** [exploration.md](./exploration.md)  
**Diseño UX:** [design.md](./design.md)

---

## 1. Intención

Transformar **`/mpr/reportes/`** en un **centro de analítica y trazabilidad** de producción MPR: pantallas **claras, visuales y accionables** para supervisores y gerencia, alimentadas por ledgers **`mpr_*`** y demanda PED en vivo — no por listas OPT legacy como fuente principal.

El usuario MUST poder, en segundos:

- Elegir un **período** y ver qué pasó en planta.
- Identificar **gaps** (enviado sin parte, parte sin clasificar, demanda sin stock).
- **Rastrear** un componente desde envío hasta stock.
- Ver **productividad por operario** con datos reales de parte.

---

## 2. Problema

| Hoy | Dolor |
|-----|-------|
| Reportes OPT-centric | No reflejan flujo diario post-E11 |
| Tablas sin filtros ni KPIs | Supervisores exportan a Excel manualmente |
| Servicios útiles sin UI | Brecha, movimientos, pedidos ocultos |
| UX genérica | No transmite prioridad ni estado del pipeline |

---

## 3. Alcance

### Incluido (P0 — MVP)

| # | Entrega | Descripción breve |
|---|---------|-------------------|
| R1 | **Shell reportes** | Filtro período sticky, grupos de navegación, KPI strip, export CSV, empty states |
| R2 | **Resumen diario planta** | KPIs + tabla por día: enviado, parte, clasificado, scrap % |
| R3 | **Producción por operario** | Ranking desde `mpr_parte_linea`; barras proporcionales |
| R4 | **Cadena envío→parte→clasificación** | Tabla componente con mini-barras de pipeline |
| R5 | **Pendiente componentes** | Reemplazo visual de «Pendiente» legacy; demanda vs pipeline |
| R6 | **Brecha demanda pack** | UI para `reporte_mpr_brecha_demanda` con PED en vivo |
| R7 | **Línea de tiempo componente** | Trazabilidad ad hoc (filtro artículo + período) |

### Incluido (P1 — iteración)

| # | Entrega |
|---|---------|
| R8 | Movimientos MSTOCK filtrados MPR |
| R9 | Cumplimiento demanda por cliente/pedido |
| R10 | Eficiencia clasificación (scrap % por componente) |
| R11 | WIP pipeline (estado actual sin OPT) |

### Legacy (P2 — sin borrar)

- OPT cerradas, WIP OPT, desperdicio con columna OPT → sección **«Histórico OPT»** colapsada, etiquetada «Solo consulta legacy».

### Fuera de alcance v1

- Widgets embebidos en dashboard gerencial (`/reports/dashboard/`) — spec aparte si producto lo pide.
- Tabla `mpr_evento` unificada (P4 fuente única).
- PDF / impresión formal (CSV suficiente en v1).
- Alertas push / email.

---

## 4. Capabilities (contrato para specs)

### New Capabilities

| Capability | Spec path | Descripción |
|------------|-----------|-------------|
| `mpr-reportes-shell` | `specs/mpr-reportes-shell/spec.md` | Shell UX, filtros, navegación, export |
| `mpr-reporte-resumen-diario` | `specs/mpr-reporte-resumen-diario/spec.md` | Agregación diaria planta |
| `mpr-reporte-operario` | `specs/mpr-reporte-operario/spec.md` | Productividad operario desde parte |
| `mpr-reporte-cadena-pipeline` | `specs/mpr-reporte-cadena-pipeline/spec.md` | Envío→parte→clasificación |
| `mpr-reporte-pendiente-componentes` | `specs/mpr-reporte-pendiente-componentes/spec.md` | Pendientes vs demanda |
| `mpr-reporte-brecha-pack` | `specs/mpr-reporte-brecha-pack/spec.md` | Brecha pack PED |
| `mpr-reporte-trazabilidad` | `specs/mpr-reporte-trazabilidad/spec.md` | Timeline componente |

### Modified Capabilities

| Capability | Cambio |
|------------|--------|
| `mpr-reportes-legacy` | Reagrupar OPT bajo histórico; deprecar como default |

---

## 5. Criterios de éxito (aceptación producto)

1. **Claridad:** Un supervisor sin capacitación identifica el componente más crítico en <30 s con filtro «Hoy».
2. **Verdad de datos:** Operario y resumen diario coinciden con `mpr_parte_linea` / `mpr_envio_produccion` (± redondeo).
3. **Visual:** Cada reporte P0 muestra ≥1 elemento no tabular (KPI card, barra pipeline o timeline).
4. **Canon UI:** Cumple `FUENTE_VERDAD_UI_REPORTES_MPR.md` (slate hero, tipografía, fechas dd/MM/yyyy).
5. **Español:** Etiquetas, empty states y errores en español.
6. **Tests:** Suite dedicada `mpr.tests.test_reportes_*` en contenedor.

---

## 6. Fases de implementación (preview tasks)

| Fase | Entregables |
|------|-------------|
| **F1** | Shell + resumen diario + operario |
| **F2** | Cadena pipeline + pendiente + brecha pack |
| **F3** | Trazabilidad timeline + legacy colapsado |
| **F4** | P1 movimientos + cumplimiento + docs `docs/mpr/REPORTES_MPR.md` |

---

## 7. Documentación

- `docs/mpr/REPORTES_MPR.md` — catálogo usuario + fuentes datos
- Actualizar `docs/mpr/NAVIGACION_MPR_ETAPA11.md` — enlace reportes
- Specs en `docs/reports/mpr/` alineadas con OpenSpec delta

---

## 8. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Scope creep visual | Design tokens reutilizados de tablero; no gráficos custom sin librería existente |
| Datos legacy mezclados | Badges «Legacy OPT» visibles |
| Performance | Agregaciones SQL; paginación 50 filas default |

---

## 9. Enfoque técnico (resumen)

- Refactor **hub único** `/mpr/reportes/` con query params `grupo`, `reporte`, `desde`, `hasta`.
- **Servicios nuevos** sobre `mpr_envio_produccion`, `mpr_parte*`, `mpr_transicion_lote`; reutilizar tablero consolidado y demanda PED.
- **Plantillas fragmentadas** + Alpine.js para presets; export CSV en misma vista.
- Detalle en [design.md](./design.md).

---

## 10. Rollback

Revert del commit de apply restaura vista monolítica actual. Servicios legacy (`reporte_mpr_pendiente`, etc.) permanecen sin eliminar; cambio es aditivo en capa presentación + agregadores nuevos.
