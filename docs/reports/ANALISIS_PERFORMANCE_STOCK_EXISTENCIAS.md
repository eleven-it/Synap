# Análisis de rendimiento — informe Stock y existencias (`stock-existencias`)

**Fecha:** 29/06/2026  
**Alcance:** flujo optimizado (`reports/services/stock_existencias_query.py`, `query_runner._run_stock_existencias`, `dashboard.js`).

## 1. Resumen

Se aplicaron cuatro mejoras:

| Mejora | Implementación |
|--------|----------------|
| Pool MySQL | `get_mysql_pool().get_connection()` en lugar de `MySQLdb.connect` por request |
| Join invertido | `FROM stock_deposito sd STRAIGHT_JOIN articulo a` (filtra saldo antes de artículo) |
| Paginación + búsqueda/orden en SQL | `limit`/`offset`, `filters.busqueda`, `filters.sort_col`/`sort_dir` |
| Virtual scroll cliente | Ventana deslizante en tabla plana (≥40 filas cargadas); scroll infinito al fondo |

**Modo agrupación:** si el usuario activa «Agrupar por», el cliente pide el universo completo (`agrupacion_activa`) y agrupa en navegador (comportamiento previo).

## 2. Mediciones (base `administranet93`, 29/06/2026)

### Antes (universo completo, ~4.461 filas)

| Métrica | Valor |
|---------|------:|
| Tiempo runner | ~1,0–1,1 s |
| Payload JSON | ~1,5 MB |
| Conexión MySQL nueva | ~240 ms |

### Después (primera página, 150 filas)

| Métrica | Valor esperado |
|---------|---------------:|
| Tiempo SQL + pool | < 500 ms (sin sort filesort masivo en cliente) |
| Payload JSON | ~50–60 KB |
| Filas DOM (virtual) | ~70 nodos visibles + buffer |

Con **stock cero** (~22k filas): la carga inicial sigue siendo 150 filas; el resto se obtiene al desplazar.

## 3. API

### Request POST `/api/reports/query/`

| Campo | Descripción |
|-------|-------------|
| `limit` | Default **150**; con `filters.agrupacion_activa` → universo completo |
| `offset` | Desplazamiento para páginas siguientes |
| `filters.busqueda` | Mín. 2 caracteres; LIKE en servidor |
| `filters.sort_col` | `id_manual`, `codigo_barras`, `nombre`, `rubro_nombre`, `subrubro_nombre`, `deposito_nombre` |
| `filters.sort_dir` | `asc` / `desc` |
| `filters.agrupacion_activa` | `true` si hay agrupación en UI |

### Response `meta`

- `row_count`: filas en la página actual  
- `total_registros`: total que cumple filtros  
- `has_more`: hay más páginas  
- `offset`, `limit`

## 4. Frontend

- Búsqueda (debounce 400 ms) → refetch servidor.  
- Orden por cabecera → refetch servidor.  
- Scroll al fondo de `#stock-existencias-scroll` → carga silenciosa de la siguiente página.  
- Virtual scroll: solo renderiza filas visibles + buffer (40 px alto × filas).

## 5. Referencias de código

- SQL: `reports/services/stock_existencias_query.py`
- Runner: `QueryRunnerService._run_stock_existencias`
- UI: `reports/static/reports/js/dashboard.js` (`fetchStockExistenciasData`, virtual scroll)
- Especificación funcional: `docs/reports/SPEC_STOCK_EXISTENCIAS.md`
