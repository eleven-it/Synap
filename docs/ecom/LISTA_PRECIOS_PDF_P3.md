# Export lista de precios PDF — Fase P3 (item 2)

Change SDD: `openspec/changes/catalogo-carrito-checkout-mayorista/` · Fase **P3**.
Migra `administraNET-ecom/mayoristapp/exporta_lista_pdf.php` (mPDF) a Synap con **reportlab**.

## Alcance

- Genera un PDF de **lista de precios mayorista** (A3 landscape) para los filtros del catálogo.
- Reutiliza el **catálogo P0** (`obtener_filas_catalogo` / `contar_articulos_catalogo`,
  mismos filtros y **motor de precios** `price_rules_engine`) — sin paginar.
- Muestra **una lista de precios** por PDF (la de la sesión/cliente), como el legacy.

**Fuera de alcance (gaps documentados):**

- Imágenes de producto embebidas (el flag `imagenProducto` solo ajusta los umbrales; el
  render con imágenes es un follow-up).
- Columnas de desglose por renglón (Desc% / IVA / Final c/dcto separados) y listas 1–5 en
  paralelo: el motor devuelve el **precio final ya calculado** (con descuento/reglas/promos);
  el PDF muestra Rubro, Sub Rubro, Cód, Artículo, Precio (neto o final según IVA) y Promo.
- Categoría como columna (el catálogo P0 no la trae).

## Arquitectura

| Componente | Rol |
|---|---|
| `ecom/services/lista_precio_pdf.py` | `exportar_lista_precios_pdf(...)` → `(ok, error, pdf_bytes)` |
| `ecom/services/catalogo_producto.py` | `contar_articulos_catalogo`, `obtener_filas_catalogo` (WHERE compartido con el listado P0) |
| `ecom/lista_precio_pdf_relay_views.py` | Vista GET + página HTML amigable de límite |
| `core/report_pdf.py` | `get_empresa_para_reporte` (razón social/CUIT/logo) |

## Guardrails (runbook `docs/general/RUNBOOK_EXPORTACION_PDF.md`)

1. **Volumen (pre-render):** `COUNT(*)` antes de generar. Si supera `LP_PDF_MAX_ITEMS`
   (o `LP_PDF_MAX_ITEMS_CON_IMAGEN` con imágenes) → página amigable, no se genera.
2. **Tiempo (durante el armado):** presupuesto `LP_PDF_MAX_SECONDS[_CON_IMAGEN]`, revisado
   **cada 50 filas**. El costo real en Synap es el cálculo de precio por fila (reglas/promos
   con consultas), por eso el presupuesto envuelve el armado de datos, no el render.
3. Sin cola/worker (Celery está deshabilitado): generación **síncrona** acotada por los
   dos cortes anteriores (paridad legacy, que también era síncrono).

Umbrales en `settings` (env, defaults = paridad legacy):
`LP_PDF_MAX_ITEMS=2500`, `LP_PDF_MAX_ITEMS_CON_IMAGEN=1800`,
`LP_PDF_MAX_SECONDS=90`, `LP_PDF_MAX_SECONDS_CON_IMAGEN=180`.
> Los `*_SECONDS` deben **re-medirse** en el entorno objetivo (reportlab ≠ mPDF).

## API

`GET /ecom/api/mayoristapp/catalogo/lista-precios.pdf`

Query params (filtros del catálogo): `rubro`, `subrubro`, `marca`, `laboratorio`,
`proveedor`, `q` (o `queArticulo`), `promo`, `imagenProducto` (ajusta umbrales), y los
`*Text` (`categoriaText`, `rubroText`, …, `clienteTexto`) para el encabezado.
Lista/cliente/IVA/depósito se toman de la sesión mayoristapp (igual que el listado P0).

Respuestas: `200 application/pdf` (descarga) · `200 text/html` (página amigable de
límite por volumen/tiempo) · `400/500` errores.

## Tests

`ecom/tests/test_lista_precio_pdf.py` (mocks de MySQL/precio/empresa; reportlab en memoria):
formato de moneda es-AR, happy path (bytes `%PDF`), guardrail de volumen y de tiempo.

```bash
docker exec Synap_app python manage.py test ecom.tests.test_lista_precio_pdf --keepdb
```
