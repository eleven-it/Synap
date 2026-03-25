# Resultado Fase 2 — Captura de documentos y pipeline OCR (Compras)

**Alcance:** implementación entregada en `factura_compra_captura` (modelo `DocumentoFuente`, servicio de subida, pipeline OCR, API, PWA base móvil, tests).  
**Plan y DoD:** [docs/compras/master_execution_plan.md](compras/master_execution_plan.md), [docs/compras/definition_of_done_by_phase.md](compras/definition_of_done_by_phase.md) (Fase 2).  
**Nota:** D-01 (proveedor OCR real) y D-02 (storage definitivo) no bloquean esta fase: mock + `FileSystemStorage` / `MEDIA_ROOT` en dev.

---

## 1. Flujo de captura (end-to-end)

1. **Expediente** en estado `borrador` (o `ocr_completado` si se vuelve a adjuntar; en ese caso el expediente vuelve a `borrador` antes de guardar el nuevo archivo).
2. **Cliente** envía `POST` multipart con campo `archivo` al endpoint de documentos del expediente.
3. **Validación:** MIME permitido (`image/jpeg`, `image/png`, `application/pdf`) y tamaño ≤ `FACTURA_COMPRA_DOCUMENTO_MAX_BYTES` (por defecto 15 MiB).
4. **Persistencia:** se crea `DocumentoFuente` con `estado_procesamiento = pendiente`, se guarda el archivo vía storage de Django y se calcula SHA-256.
5. **Pipeline OCR** (según configuración, ver §4):
   - En modo **síncrono / inline** (por defecto `FACTURA_COMPRA_OCR_DEFER=False`, o `FACTURA_COMPRA_OCR_SYNC=True`): se ejecuta en el mismo proceso antes de cerrar la transacción del servicio; la respuesta HTTP incluye el estado ya actualizado gracias a `refresh_from_db()` sobre la instancia devuelta.
   - En modo **diferido** (`FACTURA_COMPRA_OCR_DEFER=True`): tras `transaction.on_commit` se lanza un **hilo daemon** que ejecuta el pipeline (no hay Celery en el proyecto principal; sustitución futura documentada en código).
6. **Éxito OCR:** documento `completado`, expediente pasa a `ocr_completado` (si estaba en `borrador`), metadata con referencia al documento y confianza.
7. **Fallo OCR:** documento `fallido` con códigos/detalle; expediente **permanece en `borrador`**; metadata incluye `ocr_ultimo_error`. El expediente no queda bloqueado.
8. **Reintento:** `POST` a `…/documentos/<id>/reintentar-ocr/` para estados `pendiente`, `procesando` o `fallido`; vuelve a programar el job de forma idempotente (el pipeline ignora documentos ya `completado`).

---

## 2. Endpoints

**Prefijo API:** `/api/compras/`

| Método | Ruta | Uso |
|--------|------|-----|
| GET | `/api/compras/expedientes/` | Lista expedientes (filtros opcionales). |
| POST | `/api/compras/expedientes/` | Crea expediente. |
| GET/PATCH | `/api/compras/expedientes/<uuid>/` | Detalle / parche. |
| POST | `/api/compras/expedientes/<uuid>/transiciones/` | Transiciones de workflow. |
| GET | `/api/compras/expedientes/<uuid>/documentos/` | Lista `DocumentoFuente` del expediente. |
| POST | `/api/compras/expedientes/<uuid>/documentos/` | **Subida** multipart (`archivo`). Respuesta incluye `estado_procesamiento`, `resultado_ocr` cuando aplica. |
| GET | `/api/compras/expedientes/<uuid>/documentos/<id>/` | Detalle documento (incluye estado OCR y resultado). |
| POST | `/api/compras/expedientes/<uuid>/documentos/<id>/reintentar-ocr/` | **Reintento** OCR. |

**PWA / captura móvil (HTML):** `/compras/captura/movil/` — shell usable desde navegador móvil; estructura preparada para uso de cámara (input file `capture` / orientación móvil), sin pulido final de UX.

**Consulta de estado OCR:** vía GET del documento o del expediente serializado con `documentos_fuente` (polling sobre el recurso documento).

---

## 3. Decisiones OCR (resumen)

| Tema | Decisión |
|------|----------|
| Proveedor | Interfaz `OcrAdapter` en `factura_compra_captura/ocr/base.py`. Implementación por defecto: **mock** (`MockOcrAdapter`). Valor `http` reservado; sin implementación hasta definir D-01. |
| Motor en CI / tests | Mock; `FACTURA_COMPRA_OCR_MOCK_FAIL=True` fuerza fallo para TC-OCR. |
| Ejecución async | Sin Celery/RQ en el núcleo: **inline** por defecto o **hilo tras commit** si `OCR_DEFER=True`. Comentarios en `jobs.py` indican reemplazo por `shared_task.delay` si se adopta Celery. |
| Prioridad de flags | `FACTURA_COMPRA_OCR_SYNC=True` fuerza ejecución inline **antes** de evaluar `OCR_DEFER` (útil en tests y depuración). |
| Fallos | No bloquean el expediente; eventos y metadata registran el error; reintento explícito vía API. |
| Respuesta API coherente | Tras ejecutar el pipeline en la misma petición, el servicio hace **`refresh_from_db()`** para que el serializer no devuelva estado obsoleto en memoria. |

**Variables de entorno / settings relevantes:** `FACTURA_COMPRA_OCR_ADAPTER`, `FACTURA_COMPRA_OCR_DEFER`, `FACTURA_COMPRA_OCR_SYNC`, `FACTURA_COMPRA_OCR_MOCK_FAIL`, `FACTURA_COMPRA_DOCUMENTO_MAX_BYTES`, `FACTURA_COMPRA_DOCUMENTO_MIME_PERMITIDOS` (lista fija en settings por defecto).

---

## 4. Runbook operativo

- **Worker / hilo caído:** con `OCR_DEFER=True`, si el proceso muere antes de ejecutar el hilo, el documento puede quedarse en `pendiente` o `procesando`. Mitigación: **reintento** con `POST …/reintentar-ocr/` (idempotente respecto de documentos ya completados).
- **Producción recomendada:** `OCR_DEFER=True` para no alargar la respuesta HTTP; monitorizar logs (`Fallo worker OCR` en `jobs.py`) y colas si en el futuro se migra a Celery.
- **Tests:** `factura_compra_captura.tests.test_documento_upload`, `factura_compra_captura.tests.test_ocr_pipeline` (subida, pipeline éxito/fallo, reintento). En tests se usa `FACTURA_COMPRA_OCR_SYNC=True` para ejecutar OCR en línea sin depender de `on_commit`.

---

## 5. Cierre Fase 2 vs DoD

- Subida con MIME/tamaño y storage dev: **sí**.  
- Job async observable: **sí** (hilo + estado en API; inline opcional).  
- Adapter + mock + interfaz para proveedor real: **sí**.  
- API subida + estado: **sí**.  
- PWA base móvil: **sí** (`/compras/captura/movil/`).  
- Tests TC-CAP / TC-OCR mínimos: **sí**.  
- Runbook reintento: **sí** (esta sección + endpoint).

**Próximo paso formal:** cerrar checklist DoD Fase 2 en el PR/MR antes de iniciar Fase 3.
