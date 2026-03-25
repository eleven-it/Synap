# Especificación: Reporte MPR — Desperdicio / Scrap (tabla en Reportes MPR)

**Estado: PENDIENTE**  
**Prioridad: Media**  
**Módulos afectados:** mpr (views, services, templates)  
**Ubicación UI:** Menú MPR → Reportes → pestaña "Desperdicio"

---

## 1. Resumen

Tabla de solo lectura en la sección **Reportes** del menú MPR. Muestra movimientos OPP (o equivalentes) con **destino depósito desperdicio** (tipo_mpr = Scrap). Incluye filtro opcional por **fecha_desde** y **fecha_hasta**. No es reporte del módulo Reports (no aparece en catálogo/dashboard Reports).

---

## 2. Data sources

| Origen | Uso |
|--------|-----|
| `movimiento_stock` / `stock` | Movimientos con destino = depósito desperdicio (obtenido vía `get_deposito_desperdicio_mpr` o equivalente) |
| `articulo` | Código/descripción |
| OPT / lista_produccion_agrupada | OPT asociada al movimiento |

**Servicio MPR:** `reporte_mpr_desperdicio(base_empresa, fecha_desde=None, fecha_hasta=None, limit=200)`.

---

## 3. Entradas

| Parámetro | Origen | Obligatorio | Descripción |
|-----------|--------|-------------|-------------|
| `tipo` | GET `?tipo=desperdicio` | Sí | Fija el reporte en la vista Reportes MPR |
| `base_empresa` | Sesión (vista) | Sí | Para ejecutar el servicio |
| `fecha_desde` | GET | No | Filtro inicio período (YYYY-MM-DD) |
| `fecha_hasta` | GET | No | Filtro fin período (YYYY-MM-DD) |

---

## 4. Salidas (contexto vista)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `filas` | list[dict] | Una fila por registro: artículo, cantidad_desperdicio, opt_asociada, fecha (u otras columnas acordadas) |
| `titulo_reporte` | str | `"Desperdicio / Scrap"` |
| `tipo_reporte` | str | `"desperdicio"` |

---

## 5. Reglas de negocio

- Solo movimientos OPP (o equivalentes) cuyo destino sea el depósito configurado como desperdicio (tipo_mpr Scrap).
- Si no se envían `fecha_desde`/`fecha_hasta`: sin filtro de fecha (todo el histórico) o según política (ej. último año).
- Fechas en formato YYYY-MM-DD; validar en servidor.
- Sin `base_empresa` en sesión: redirect a dashboard con mensaje de error (comportamiento actual de ReportesMPRView).

---

## 6. Criterios de aceptación

| ID | Descripción |
|----|-------------|
| CA-DE-01 | GET `/mpr/reportes/?tipo=desperdicio` con usuario logueado y base_empresa → HTTP 200, `context["filas"]` presente, `context["titulo_reporte"]` = "Desperdicio / Scrap". |
| CA-DE-02 | Con `fecha_desde` y `fecha_hasta` en GET → filas filtradas por ese rango. |
| CA-DE-03 | Sin base_empresa en sesión → redirect o mensaje de error (comportamiento actual ReportesMPRView). |

---

## 7. Casos borde

- Sin depósito desperdicio configurado: filas vacías o note en contexto.
- Sin movimientos a desperdicio: `filas = []`.
- Fechas inválidas: ignorar o devolver error suave (mensaje en template).
