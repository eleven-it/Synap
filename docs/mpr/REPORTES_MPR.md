# Reportes MPR — catálogo y fuentes

**Ruta:** `/mpr/reportes/`  
**Change:** `mpr-reportes-trazabilidad-produccion`  
**Fecha:** 04/07/2026

---

## Propósito

Centro de **analítica y trazabilidad** del flujo MPR diario (envío tablero → parte → clasificación), con demanda pack en vivo.

---

## Navegación

| Grupo | Reportes | Fuente principal |
|-------|----------|------------------|
| **Producción** | Resumen diario, Por operario, Cadena pipeline, Pendiente componentes | `mpr_envio_produccion`, `mpr_parte_linea`, `mpr_transicion_lote`, tablero consolidado |
| **Demanda** | Brecha pack, Pedidos por estado, Stock, Bajo mínimo | PED en vivo, `comp_ped`, stock |
| **Trazabilidad** | Línea de tiempo, Movimientos | Ledgers `mpr_envio_produccion`, `mpr_parte_linea`, `mpr_transicion_lote` |

**Default:** Producción → Resumen diario, últimos 7 días.

**Sin `lista_produccion_*`:** el hub de reportes no consulta tablas OPT legacy. Para **eliminar físicamente** las tablas en MySQL y exponer código pendiente de migración:

```bash
docker exec Synap_app python manage.py drop_mpr_lista_produccion_legacy administranet96 --confirm
```

También disponible en **Archivo → Parámetros → Migración esquema MySQL** (`mpr_drop_lista_produccion_legacy`, riesgo alto). El módulo OPT (`/mpr/opt/`, ventana pack) seguirá referenciando esas tablas en código hasta completar la migración a `mpr_*`.

---

## Filtros

- **Desde / Hasta** (visualización dd/MM/yyyy)
- Presets: Hoy, 7 días, Mes
- **Presentación:** Unidades (entero) o Docenas (`docenas · unidades`, divisor 12 en componentes OPP; `cantidad_promedio_bulto` en packs). Parámetro URL: `?presentacion=unidades|docenas`. Se conserva al navegar entre reportes y al exportar CSV.
- **Exportar CSV** (UTF-8 BOM) en reportes de Producción y Demanda principales; en modo docenas exporta columnas formateadas (`*_display`).

### UI compacta

Panel de control **sticky** en una sola tarjeta con tres zonas: contexto (título del reporte activo + período), filtros con etiquetas visibles, y navegación con KPIs en chips laterales (desktop) o debajo (mobile). El área de datos usa **scroll interno** a altura de viewport (`h-[calc(100dvh-4.5rem)]`) para maximizar filas visibles sin sacrificar legibilidad (texto `sm`, targets táctiles `h-9`).

### Resumen diario — gráfico

- **Tipo:** líneas múltiples (Chart.js) sobre la tabla.
- **Series principales (eje izquierdo):** Enviado, Parte, Clasificado — mismas magnitudes, evolución día a día del pipeline.
- **Scrap:** línea discontinua en **eje derecho** (escala independiente; suele ser mucho menor que clasificado).
- **Gap envío→parte** y **Scrap %** permanecen solo en la tabla (métricas derivadas / porcentajes).

### Por operario — gráfico

- **Tiene sentido:** sí — ranking de productividad (categorías, no tiempo).
- **Tipo:** barras horizontales, top 12 por unidades.
- **No usar líneas:** no hay eje temporal.

### Cadena pipeline — gráficos

- **Tiene sentido:** sí — vista agregada del embudo y del backlog por estado.
- **Tipos:**
  1. Barras verticales — totales planta Enviado / Parte / Clasificado.
  2. Dona — cantidad de componentes por estado (Falta parte, Falta clasificar, etc.).
  3. Barras horizontales agrupadas — top componentes con brecha envío→parte (si hay gap).
- **No usar líneas:** snapshot del período, no serie diaria.

### Pendiente componentes — gráfico

- **Tiene sentido:** sí — priorización visual de faltantes.
- **Tipo:** barras horizontales top 12 por `pendiente` (ámbar; rojo si crítico ≥50 u.).
- **Sin período en datos:** instantánea del tablero; el filtro de fechas no aplica a este reporte.

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
  --keepdb
```
