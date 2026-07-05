# Exploración — Reportes MPR: trazabilidad y producción

**Change:** `mpr-reportes-trazabilidad-produccion`  
**Fecha:** 04/07/2026  
**Perspectiva:** Product Design + analista de datos de producción MPR

---

## 1. Situación actual

### 1.1 Pantalla `/mpr/reportes/`

| Aspecto | Hallazgo |
|---------|----------|
| Navegación | 7 pestañas planas sin agrupación ni filtros visibles de fecha |
| Datos | 5 de 7 reportes anclados a **OPT/OPP legacy** (`lista_produccion_*`, `lista_produccion_historico`) |
| UX | Una sola tabla genérica; sin KPIs, gráficos ni estados vacíos orientadores |
| Filtros | Solo desperdicio / operario / OPT cerradas aceptan `fecha_desde`/`fecha_hasta` en query string — **no hay UI de fechas** |
| Canon UI | No sigue el patrón denso de `tablero_produccion.html` ni el shell de reportes `/reports/dashboard/` |

### 1.2 Servicios existentes (implementados vs expuestos)

| Servicio | UI | Fuente datos | Alineado flujo diario |
|----------|-----|--------------|------------------------|
| `reporte_mpr_pendiente` | Sí | `lista_produccion_agrupada` | No |
| `reporte_mpr_wip` | Sí | OPT en proceso | No |
| `reporte_mpr_stock` | Sí | `stock_deposito` | Parcial |
| `reporte_mpr_bajo_minimo` | Sí | stock + mínimos | Sí |
| `reporte_mpr_desperdicio` | Sí | MSTOCK Scrap | Parcial (OPT en columna) |
| `reporte_mpr_produccion_por_operario` | Sí | `lista_produccion_historico` | No — ignora `mpr_parte_linea` |
| `reporte_mpr_opt_cerradas` | Sí | legacy OPT | No |
| `reporte_mpr_brecha_demanda` | **No** | ventana pack / agrupada | Debe usar PED en vivo |
| `reporte_mpr_movimientos` | **No** | MSTOCK | Parcial |
| `reporte_mpr_pedidos_por_estado` | **No** | `comp_ped` | Sí |

### 1.3 Ledgers MySQL (`mpr_*`) — fuente canónica post-cutover

| Tabla | Evento de negocio | Campo fecha para reportes |
|-------|-------------------|---------------------------|
| `mpr_envio_produccion` | Envío tablero → fabricar | `creado_en` |
| `mpr_parte` + `mpr_parte_linea` | Parte de producción (operario × componente) | `fecha_produccion` (parte), `registrado_en` |
| `mpr_parte_ajuste` | Corrección delta | `registrado_en` |
| `mpr_transicion_lote` | Clasificación Semi/2da/Scrap | `creado_en` |
| `mpr_turno` / `mpr_roster_dia` | Contexto turno/operario planificado | `fecha` roster |
| `mpr_armado_lote` + líneas | Armado 1ra/2da | `ejecutado_en` |
| `movimiento_stock` / `stock` | Asiento físico MSTOCK | `fecha` |

**Trazabilidad end-to-end:** envío → parte → clasificación → (opcional) armado, enlazable por `id_articulo` + ventana temporal + `codigo_movimiento` cuando exista.

---

## 2. Personas y jobs-to-be-done

| Persona | Necesita | Frecuencia | Decisión que toma |
|---------|----------|------------|-------------------|
| **Supervisor de planta** | Ver si lo enviado se produjo y clasificó; gaps por turno | Diaria | Reasignar operarios, pedir parte faltante |
| **Jefe de producción** | Ranking operarios, scrap %, pendientes críticos | Semanal | Bonos, capacitación, turnos |
| **Gerencia / dirección** | Resumen planta, cumplimiento demanda vs producido | Mensual | Inversión, metas, clientes prioritarios |
| **Calidad / reclamos** | Línea de tiempo de un componente | Ad hoc | Auditoría, trazabilidad cliente |

---

## 3. Métricas clave (analítica MPR)

### 3.1 Pipeline diario (componente)

```
Demanda (PED→BOM) → Enviado (ledger) → Producido (parte) → Clasificado (Semi+2da+Scrap) → Stock pipeline
```

| KPI | Fórmula | Umbral visual |
|-----|---------|---------------|
| Pendiente | max(0, demanda − enviado − stock_pipeline) | >0 ámbar |
| Gap envío→parte | enviado − producido | >0 rojo suave |
| Gap parte→clasif | producido − (semi+2da+scrap) | >0 ámbar |
| Scrap % | scrap / (semi+2da+scrap) | >5% rojo (configurable) |
| Cumplimiento | producido / demanda | <80% ámbar |

### 3.2 Por operario (periodo)

- Unidades en parte (`SUM mpr_parte_linea.cantidad`)
- Partes registrados (`COUNT DISTINCT mpr_parte`)
- Componentes distintos
- Promedio unidades / parte
- % del total planta (barra proporcional)

### 3.3 Por pack (demanda)

- Brecha desde `listar_demanda_pack_desde_pedidos`
- Urgente: pedido > stock terminado

---

## 4. Brechas UX (Product Design audit)

| Problema | Impacto usuario | Dirección de solución |
|----------|-----------------|------------------------|
| Sin barra de fechas global | No puede responder «¿qué pasó la semana pasada?» | Filtro sticky dd/MM/yyyy + presets (Hoy, 7d, Mes) |
| Tablas sin contexto | Números sueltos, difícil priorizar | Fila de **4 KPI cards** arriba de cada reporte histórico |
| OPT en columnas | Confunde operación nueva | Renombrar/reemplazar; legacy en sección colapsada |
| Sin export | Supervisores usan Excel | Botón «Exportar CSV» en toolbar |
| Sin drill-down | Trazabilidad imposible desde tabla | Clic en componente → panel timeline |
| Inconsistencia visual | MPR operativo vs reportes genéricos | Shell tipo `tablero_produccion` + includes reportes |

---

## 5. Referencias UI canónicas Synap

- **Operación MPR:** `mpr/tablero_produccion.html`, `mpr/tablero.html` (KPI cards, slate hero)
- **Informes densos:** `reports/dashboard_detail.html` + `reports/includes/filters_period.html`
- **Normativa:** `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`, spec `ui-fuente-verdad-reportes-mpr`

**Decisión preliminar:** Reportes MPR viven en `/mpr/reportes/` (módulo operativo), pero adoptan **patrones visuales** de dashboard reportes (filtros período, KPI strip, tablas sticky header). No mover a `/reports/dashboard/` en v1 (evita mezclar permisos y menú gerencial).

---

## 6. Riesgos de datos

| Riesgo | Mitigación |
|--------|------------|
| Ledgers vacíos en empresas recién migradas | Empty state explicativo + enlace a tablero/parte |
| Histórico OPT vs nuevo convive | Sección «Histórico OPT» separada, etiquetada |
| Fechas cruzadas (parte vs creado_en envío) | Documentar en UI: «Parte usa fecha de carga del informe» |
| Performance agregaciones | Índices existentes `idx_mpr_*`; limit + paginación server-side v2 |

---

## 7. Priorización P0 (MVP visual)

1. Shell reportes refactor (filtros + grupos + KPI strip)
2. Resumen diario planta
3. Producción por operario (desde `mpr_parte_linea`)
4. Cadena envío→parte→clasificación
5. Pendiente componentes + brecha pack (reemplazo pendiente OPT)
6. Línea de tiempo componente (trazabilidad)

Legacy OPT → pestaña colapsada «Histórico», sin eliminar en v1.
