# Runbook — Exportación PDF de alto volumen

**Ámbito:** guía para exportar listados grandes a PDF en Synap sin agotar memoria/tiempo, con paridad de comportamiento respecto al legacy `administraNET-ecom/mayoristapp/exporta_lista_pdf.php` (lista de precios mayorista).
**Fecha:** 02/07/2026.
**Estado:** guardrails y umbrales **confirmados** contra el legacy. La migración del export de **lista de precios** en sí está **diferida** (depende del catálogo/carrito mayorista, aún no migrado — ver `docs/ecom/DELTA_PHP_2026Q2.md`, decisión abierta #2).

---

## 1. Umbrales confirmados (`LP_PDF_MAX_*`)

Valores tomados de `exporta_lista_pdf.php` (definidos con `define(...)`, sobrescribibles):

| Constante | Valor legacy | Significado |
|---|---|---|
| `LP_PDF_MAX_ITEMS` | **2500** | Máximo de ítems para exportar **sin imágenes**. Si se supera → página "límite" y aborta. |
| `LP_PDF_MAX_ITEMS_CON_IMAGEN` | **1800** | Máximo de ítems **con imágenes** de producto. |
| `LP_PDF_MAX_SECONDS` | **90** | Presupuesto de tiempo (seg) para la generación **sin imágenes**. |
| `LP_PDF_MAX_SECONDS_CON_IMAGEN` | **180** | Presupuesto de tiempo (seg) **con imágenes**. |

**En Synap:** exponer como settings (env), no hardcodear:

```python
# settings.py (valores por defecto = paridad legacy)
LP_PDF_MAX_ITEMS = int(os.getenv("LP_PDF_MAX_ITEMS", "2500"))
LP_PDF_MAX_ITEMS_CON_IMAGEN = int(os.getenv("LP_PDF_MAX_ITEMS_CON_IMAGEN", "1800"))
LP_PDF_MAX_SECONDS = int(os.getenv("LP_PDF_MAX_SECONDS", "90"))
LP_PDF_MAX_SECONDS_CON_IMAGEN = int(os.getenv("LP_PDF_MAX_SECONDS_CON_IMAGEN", "180"))
```

> Nota: estos umbrales están calibrados para mPDF (PHP) en A3-L. Al portar a `reportlab` (Synap) hay que **re-medir** en el entorno objetivo antes de dar por buenos 90/180 s; los valores por defecto son punto de partida, no garantía.

---

## 2. Guardrails de comportamiento (paridad legacy)

El legacy protege el servidor con tres controles. Replicarlos en Synap:

1. **Corte por volumen (pre-generación):** contar resultados **antes** de renderizar. Si `count > LP_PDF_MAX_ITEMS` (o `> LP_PDF_MAX_ITEMS_CON_IMAGEN` cuando hay imágenes) → **no** generar; devolver una página amigable en español ("La lista tiene demasiados productos…") con: cantidad encontrada, límite permitido, filtro/búsqueda activa y acciones (volver / cambiar filtros).

2. **Corte por tiempo (durante la generación):** medir tiempo transcurrido y revisar el presupuesto (`LP_PDF_MAX_SECONDS[_CON_IMAGEN]`) periódicamente (legacy: cada **50 filas** y antes del `Output`). Si se supera → abortar con página "demorada" (cantidad, tiempo máximo, con/sin imágenes, recomendación de reducir filtros o exportar sin imágenes).

3. **Red de seguridad ante fatal (OOM/timeout duro):** el legacy usa `register_shutdown_function` que inspecciona `error_get_last()` y, si es *maximum execution time* o *allowed memory size*, limpia buffers y muestra la página "demorada" en vez de un 500 crudo.
   - **En Synap/Django:** equivalente = un **middleware o try/except** en la vista que capture `MemoryError`/timeouts y devuelva la misma página amigable; y ejecutar el trabajo pesado con límites (worker/cola con timeout) para no colgar el request web.

---

## 3. Optimizaciones de render (para lograr los tiempos)

Del legacy (llevaron la generación de ~600 s a ~30 s):

- **`table-layout: fixed`** + anchos `%` explícitos por columna (evita el cálculo de anchos O(n) de mPDF).
- **Escritura por bloques** (chunking): escribir la tabla en lotes (legacy: bloques de 50 filas) en lugar de un único `WriteHTML` gigante, revisando el presupuesto de tiempo entre bloques.
- **Zebra inline** en `<tr style="background-color:...">` en vez de selectores CSS (más barato para el motor).
- **Compresión** del PDF final; **desactivar** sustitución de fuentes / formularios activos.
- **`memory_limit` alto** (legacy: 1024M) para el proceso de generación.
- **Cerrar la sesión** (`session_write_close`) antes del trabajo pesado para liberar el lock y permitir concurrencia. En Django: no mantener transacciones/locks abiertos durante la generación; leer datos y luego renderizar.

### Mapeo a Synap

- Motor PDF disponible: **`reportlab`** (`requirements.txt`; ya usado en `stock/views.py` con `canvas`/A4 landscape y en export de reportes).
- Export tabular de reportes: **`reports/services/export_service.py`** (patrón de columnas/orden ya establecido para Excel; reutilizar la misma normalización de columnas para el PDF).
- Para alto volumen: preferir **generación en background** (cola/worker) y descarga diferida, o **streaming** por páginas con `reportlab` (dibujar de a lotes) en vez de armar todo en memoria. Los cortes por volumen/tiempo del punto 2 siguen aplicando como primera barrera.

---

## 4. Parámetros de la lista de precios (referencia legacy)

`exporta_lista_pdf.php` recibe por GET los filtros del catálogo (para replicar al migrar): `categoria`, `rubro`, `subrubro`, `marca`, `modelo`, `laboratorio`, `queArticulo`/`idArticulo` (+ `claseBusca` texto|codigo), `promo`, `consumo`, `tacc`, `proveedor`, `listaDePrecios`, `ivaIncluido`, `imagenProducto`, `tipoCliente`, y los `*Text` (nombres para el encabezado del PDF). Encabezado: logo por CUIT, empresa, filtros aplicados, cliente, TACC, búsqueda. Formato: **A3 landscape**, pie con `Página {PAGENO} de {nbpg}`.

> Esta parametrización depende del **motor de precios mayorista** (listas 1–5, descuentos por renglón, `reglas_precio` por cliente, IVA/imp. interno) — mismo prerequisito que "Productos destacados". Por eso el export de lista de precios se implementa **cuando** exista el catálogo mayorista en Synap.

---

## 5. Checklist de aceptación (al implementar en Synap)

**Implementado (Fase P3, 03/07/2026)** — `ecom/services/lista_precio_pdf.py`, ruta `GET /ecom/api/mayoristapp/catalogo/lista-precios.pdf`. Ver `docs/ecom/LISTA_PRECIOS_PDF_P3.md`.

- [x] Umbrales tomados de settings/env (no hardcode) con defaults de §1.
- [x] Corte por volumen con página amigable en español (dd/MM/yyyy).
- [x] Corte por tiempo durante generación (cada 50 filas, envuelve el armado de datos).
- [x] Render con reportlab (A3-L, `Table` con `repeatRows`, zebra); layout fijo por anchos %.
- [ ] Trabajo pesado fuera del request (cola/worker): **N/A por ahora** (Celery deshabilitado); acotado por los cortes de volumen/tiempo, igual que el legacy síncrono.
- [ ] Re-medición de `LP_PDF_MAX_SECONDS*` en el entorno objetivo (pendiente al desplegar).
- [x] Documentado en `docs/ecom/LISTA_PRECIOS_PDF_P3.md`.
- [ ] Imágenes de producto embebidas en el PDF (diferido; el flag ya ajusta umbrales).
