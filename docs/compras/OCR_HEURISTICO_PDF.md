# Parser heurístico y OCR Tesseract (PDF / imagen) — Compras

## Objetivo

1. **PDF con texto embebido:** `pypdf` + patrones regex (Argentina / español) → cabecera e ítems sugeridos.
2. **Fotos JPEG/PNG** (p. ej. desde la **PWA / cámara móvil**): **Tesseract** en el servidor sobre la imagen, luego **las mismas regex** sobre el texto reconocido.

Así se cubre el flujo “sacar foto a la factura” sin depender de un servicio HTTP externo. El adapter **`http`** sigue disponible para otros motores.

## Visor PDF en «Revisión de factura»

El iframe **no** usa `/media/…` directamente: carga la ruta dedicada `…/compras/captura/revision/<uuid>/documento/<id_doc>/` (`DocumentoFuenteServeView`), que devuelve el PDF o la imagen con `Content-Disposition: inline`. Así el visor comparte la misma cookie de sesión que la página sin depender de la política de media genérica.

En `django_project/settings.py`, `X_FRAME_OPTIONS` debe ser **`SAMEORIGIN`** (no el valor por defecto `DENY` de Django): con `DENY`, el navegador no muestra el PDF en el iframe y en consola aparece `Refused to display '…' in a frame because it set 'X-Frame-Options' to 'deny'`.

**Autorización:** debe existir sesión **administraNET** (`request.session["user"]`) y la empresa activa de sesión (`empresa_activa_id` o `user.id_empresa`, función `empresa_synap_id_desde_sesion` en `factura_compra_captura/session_empresa.py`) debe coincidir con `expediente.empresa_id`.

En el formulario, la cabecera se rellena combinando `metadata.posting_v1` / `proveedor_synap` con `resultado_ocr.campos_cabecera`: si la razón social guardada parece una etiqueta de factura (p. ej. «Fecha de Emisión:»), se descarta y se prioriza el texto del OCR cuando corresponde.

- **Razón social (emisor):** se intenta primero el bloque AFIP `Razón Social:` con valor en la misma línea o en la siguiente (saltando líneas como «ORIGINAL» / «DUPLICADO»). No se usa la línea del receptor (`Apellido y Nombre / Razón Social`).
- **Letra fiscal (FA/FB/FC/FM):** el heurístico rellena `campos_cabecera.tipo_factura` desde: texto «Factura A/B/C/M»; **COD. 011** / **Cód. 006** (impreso ARCA debajo de la letra en caja; 011→Factura C); «Tipo de Comprobante» / «Tipo Cmp» con código numérico AFIP (1→FA, 6→FB, 11→FC, 51→FM); o una línea que sea solo **A**, **B** o **C** cerca de la palabra **FACTURA** (layout electrónico sin «Factura C» en una sola línea). En revisión se prioriza la sugerencia del PDF frente al borrador guardado cuando difieren (aviso ámbar) y conviene **Guardar** para persistir. El botón **Resolver proveedor** puede sugerir FA/FB desde el padrón AFIP; no reemplaza la letra del comprobante recibido (p. ej. FC).
- **Revisión de líneas:** la pantalla muestra una tabla tipo carrito (descripción, cantidad, precio unitario, subtotal, códigos legacy); el JSON sigue disponible con «Ver JSON» para casos excepcionales.
- **PDF multipágina (copias Original / Duplicado / Triplicado):** el texto se concatena por página; el mismo renglón puede aparecer varias veces. El parser **deduplica** ítems con la misma descripción, cantidad y precio unitario y expone `campos_cabecera.lineas_repetidas_omitidas` (y un aviso en la revisión). No sustituye la comparación humana si una copia tuviera diferencias reales en renglones.
- **Tipo de comprobante:** además del texto multilínea, se evalúa una versión **compactada** (espacios/saltos unificados) para captar `COD. 011` o `Factura C` cuando pypdf parte las palabras en líneas distintas.
- **Código proveedor legacy:** **no** se extrae del PDF. Viene de la tabla `proveedor` de AdministraNET cuando existe un proveedor con ese CUIT (**Resolver proveedor**), o se asigna al **aprobar** el expediente si el flujo crea/vincula proveedor en legacy. El usuario puede cargarlo manualmente en el campo numérico si ya lo conoce.

## Listado de expedientes (rutas)

- **Listado:** `/compras/captura/expedientes/` (filtra por la misma empresa que la API al crear el borrador).
- **`/compras/captura/revision/`** sin UUID redirige a ese listado; la pantalla de un expediente es **`/compras/captura/revision/<uuid>/`**.

## PWA / cámara

La pantalla `/compras/captura/movil/` ofrece:

- **Cámara:** `input type=file` con `accept="image/*"` y `capture="environment"` (cámara trasera donde el SO lo permite).
- **Archivo o PDF:** segundo `input` con `accept="image/*,application/pdf"` (galería o PDF).

La subida sigue siendo **multipart al backend**; el OCR corre **en Synap**, no en el navegador.

## Configuración (`.env`)

| Variable | Descripción |
|----------|-------------|
| `FACTURA_COMPRA_OCR_ADAPTER` | `heuristic` (default) u `http`. |
| `FACTURA_COMPRA_OCR_TESSERACT_ENABLED` | `True` / `False`. Si `False`, las imágenes no pasan por Tesseract (útil en dev sin binario). Los tests de API usan `False` con un JPEG mínimo. |
| `FACTURA_COMPRA_OCR_TESSERACT_LANG` | Por defecto `spa+eng` (requiere paquetes de idioma instalados). |
| `FACTURA_COMPRA_OCR_TESSERACT_CMD` | Ruta al ejecutable `tesseract` si no está en `PATH`. |

## Docker

En el `Dockerfile` principal se instalan `tesseract-ocr`, `tesseract-ocr-spa` y `tesseract-ocr-eng`. Tras rebuild de la imagen, las fotos se procesan sin pasos extra.

## Detalles técnicos

- **Preprocesado imagen:** conversión a RGB, escalado si el lado mayor es &lt; 1400 px (mejora lectura en fotos chicas) o reducción si &gt; 4200 px.
- **Tesseract:** `--oem 1 --psm 3` (LSTM, segmentación automática).
- **Confianza:** tras OCR, la confianza heurística se **limita a 0,88** (el texto OCR es más ruidoso que el PDF nativo).
- **`resultado_ocr.raw`:** `extraccion` = `pypdf` | `tesseract` | `deshabilitada`.

## Códigos de error

- `OCR_PDF_ILEGIBLE`: PDF corrupto o no legible por `pypdf`.
- `OCR_TESSERACT_NO_INSTALADO`: falta el binario Tesseract (mensaje orienta a instalar o `FACTURA_COMPRA_OCR_TESSERACT_CMD`).
- `OCR_IMAGEN_NO_VALIDA`: archivo no es una imagen legible.

## Archivos

- `factura_compra_captura/ocr/heuristic_pdf.py` — pypdf, Tesseract, regex.
- `factura_compra_captura/ocr/heuristic_adapter.py` — lee settings y traduce excepciones.
- `factura_compra_captura/templates/.../captura_movil.html` — flujo cámara / archivo.

## Evolución futura

- PDF **solo imagen** (escaneo): rasterizar páginas (p. ej. `pdf2image` + Poppler) y pasar por Tesseract.
- Afinar PSM/OCR por plantilla de proveedor.
- Mapeo validado hacia `posting_v1`.
