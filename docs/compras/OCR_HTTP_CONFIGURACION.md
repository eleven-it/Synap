# OCR de factura compra vía HTTP (opcional)

## Objetivo

Usar un **servicio OCR o parser externo** cuando el parser local (`heuristic`, texto embebido en PDF) no alcanza (imágenes, PDF escaneados, modelos propios).

## Variables de entorno

En `.env` de Synap:

- `FACTURA_COMPRA_OCR_ADAPTER=http`
- `FACTURA_COMPRA_OCR_HTTP_URL=<url del servicio OCR>`
- `FACTURA_COMPRA_OCR_HTTP_BEARER_TOKEN=<token opcional>`
- `FACTURA_COMPRA_OCR_HTTP_TIMEOUT=30`
- `FACTURA_COMPRA_OCR_HTTP_VERIFY_SSL=True`

## Contrato esperado del servicio OCR

`POST` multipart con campo `archivo` (PDF/imagen).  
Respuesta JSON (acepta cualquiera de estos alias):

- Texto: `texto_plano` o `text` o `raw_text`
- Confianza: `confianza_global` o `confidence`
- Cabecera: `campos_cabecera` o `header` o `fields`
- Líneas: `lineas_sugeridas` o `lines` o `items`

Ejemplo mínimo:

```json
{
  "text": "Factura ...",
  "confidence": 0.88,
  "header": {
    "proveedor_texto": "Proveedor SA",
    "nro_comprobante_texto": "0001-00001234",
    "fecha_comprobante_texto": "25/03/2026"
  },
  "lines": [
    {"descripcion": "Item 1", "cantidad": "2", "precio_unitario": "1500.00"}
  ]
}
```

## Nota operativa

El adapter por defecto es **`heuristic`** (local). Configurá `http` solo si tenés un endpoint compatible; ver también [OCR_HEURISTICO_PDF.md](OCR_HEURISTICO_PDF.md).
