# Tasks: Hub consolidado de cargas masivas

## Phase 1: Fundación (modelo y estado inicial)

- [x] **1.1** Añadir `estado_aprobacion_lote` (`CharField`, choices `-|pendiente|aprobado|rechazado|error`, default `-`, `db_index`) en `EcomPedidoMasivoDraft`. **Archivos:** `ecom/models.py`, `ecom/migrations/00XX_estado_aprobacion_lote.py`. **Done:** migración aplica sin error; campo nullable/ignorable por código previo. **REQ:** APR-07.
- [x] **1.2** Tras `batch_checkout_masivo` exitoso con `ecom_aprobacion_pedidos_activa` ON, persistir `estado_aprobacion_lote='pendiente'`. **Archivos:** servicio checkout masivo (donde confirma draft). **Done:** draft confirmado queda `pendiente`; sin subflag queda `-`. **REQ:** APR-07, MAS-20.

## Phase 2: Pipeline hub

- [x] **2.1** Implementar `_lotes_masivos_confirmados(base, id_u)` → tarjetas `tipo=lote_masivo` con rollup, fechas `dd/MM/yyyy`, URL resumen. **Archivos:** `ecom/services/pedidos_hub_pipeline.py`. **Done:** draft confirmado en alcance aparece en lista; fuera de alcance no. **REQ:** HUB-07, HUB-08.
- [x] **2.2** Implementar `_mapa_reverso_lotes` (`cod_mov → draft_id`) alineado a ventana hub (`dias=60`). **Archivos:** `pedidos_hub_pipeline.py`. **Done:** todos los `codigos_movimiento[]` del draft resuelven al mismo `draft_id`. **REQ:** HUB-09.
- [x] **2.3** Enriquecer `_pedidos_mysql` con `lote_draft_id`, `lote_label`, `lote_indice`, `lote_total`; forzar `meta.puede_aprobar=False` si lote pendiente. **Archivos:** `pedidos_hub_pipeline.py`. **Done:** PED hijo tiene chip meta; PED suelto sin meta lote. **REQ:** HUB-04, HUB-09.
- [x] **2.4** Exponer clave top-level `cargas_masivas[]` en `construir_hub_pedidos` (separada de `columnas[]`). **Archivos:** `pedidos_hub_pipeline.py`. **Done:** payload incluye `cargas_masivas` + `columnas`; tests columnas Kanban intactos. **REQ:** HUB-07.

## Phase 3: UI hub

- [x] **3.1** Lane desktop **Cargas masivas** + estado vacío en español; chip móvil equivalente `<lg`. **Archivos:** `ecom/templates/ecom/pedidos_hub.html`. **Done:** lote visible en lane; sin lotes lane oculto/vacío. **REQ:** HUB-07, HUB-06.
- [x] **3.2** Render tarjeta `lote_masivo`: rollup `k/n`, badge estado, CTA **Ver resumen**. **Archivos:** `pedidos_hub.html`. **Done:** CTA navega a `/ecom/mayoristapp/pedidos/lote/<draft_id>/`. **REQ:** HUB-08, LOT-01.
- [x] **3.3** Chip `Lote · {Cliente} (k/n)` en PED hijos; ocultar CTAs Autorizar/Rechazar si lote pendiente. **Archivos:** `pedidos_hub.html`. **Done:** hijo pendiente sin CTA individual; suelto pendiente sí tiene CTA. **REQ:** HUB-04, HUB-09.
- [x] **3.4** Filtro Lista **Ocultar PED de lotes** (query o sesión); tarjeta padre permanece visible. **Archivos:** `pedidos_hub.html`, bootstrap hub si aplica. **Done:** activo oculta filas con `lote_draft_id`; inactivo las muestra. **REQ:** HUB-10.

## Phase 4: Resumen de lote

- [x] **4.1** Crear `construir_resumen_lote(base, draft_id, sess)` con reconciliación PED: activo, **Anulada**, **No generada**, contador `k/n`. **Archivos:** `ecom/services/lote_resumen.py` (nuevo). **Done:** API/pantalla reciben `sucursales[]` coherentes con `codigos_movimiento[]`. **REQ:** LOT-01, LOT-02, LOT-04.
- [x] **4.2** `LoteResumenView` + `LoteResumenAPIView`; rutas web/API; ownership 403/404; draft no confirmado → 404. **Archivos:** `ecom/pedido_gestion_views.py`, `ecom/urls.py`. **Done:** GET HTML y JSON devuelven payload diseño; fechas `dd/MM/yyyy`. **REQ:** LOT-01, LOT-02.
- [x] **4.3** Template `lote_resumen.html` (canon MPR): pestañas Resumen / **Qué se cargó**; CTAs Autorizar/Rechazar con modales Synap (sin `alert/confirm/prompt`). **Archivos:** `ecom/templates/ecom/lote_resumen.html` (nuevo). **Done:** CTAs visibles solo con permiso y lote pendiente; resuelto muestra badge. **REQ:** LOT-03, LOT-05, LOT-06.
- [x] **4.4** Soporte `readonly=1` en `PedidoMasivoSucursalesView`: sin edición, autoguardado ni confirmar. **Archivos:** `ecom/pedido_masivo_views.py`, bootstrap/JS matriz. **Done:** pestaña embebe matriz sin inputs editables. **REQ:** MAS-21, LOT-03.
- [x] **4.5** Post-confirmación: redirección o pantalla éxito con CTA **Ver resumen del lote** + mensaje autorización a nivel lote. **Archivos:** flujo checkout masivo / template éxito. **Done:** usuario llega al resumen o ve CTA con `draft_id`. **REQ:** MAS-20.

## Phase 5: Autorización de lote

- [x] **5.1** `resolver_lote_masivo(...)`: iterar `codigos_movimiento`, snapshot, llamar `resolver` por PED; escalado válido; compensación ante fallo parcial. **Archivos:** `ecom/services/aprobacion_pedidos.py`. **Done:** fallo PED 2/3 revierte PED 1; `estado_aprobacion_lote='error'` o `pendiente` coherente. **REQ:** APR-05, APR-08.
- [x] **5.2** `puede_aprobar_lote(draft, aprobador, sess)`; sincronizar `estado_aprobacion_lote` al finalizar lote. **Archivos:** `aprobacion_pedidos.py`. **Done:** hub/resumen consumen flag; éxito → `aprobado`/`pendiente`(escalados). **REQ:** APR-05, APR-07, LOT-05.
- [x] **5.3** `AprobacionLoteAprobarAPIView` + `AprobacionLoteRechazarAPIView` (motivo obligatorio); rutas POST diseño; subflag OFF → error español. **Archivos:** `pedido_gestion_views.py`, `urls.py`. **Done:** 200 con `{resueltos, escalados, estado_aprobacion_lote}`; 400 tras compensación con `afectados`. **REQ:** APR-06, LOT-05.
- [x] **5.4** Guard en API aprobar/rechazar individual: rechazar PED hijo de lote `pendiente` con error español. **Archivos:** `aprobacion_pedidos.py`, vista API individual. **Done:** POST `cod_mov` de lote pendiente no modifica estado; suelto sigue operativo. **REQ:** APR-03.

## Phase 6: Tests y documentación

- [x] **6.1** Ampliar `test_pedidos_hub_pipeline`: `cargas_masivas`, mapa reverso, meta hijo, `puede_aprobar=False`. **Archivos:** `ecom/tests/test_pedidos_hub_pipeline.py`. **Done:** `docker exec Synap_app python manage.py test ecom.tests.test_pedidos_hub_pipeline` verde. **REQ:** HUB-07..09, HUB-04.
- [x] **6.2** Crear `test_lote_resumen`: ownership 403/404, reconciliación Anulada/No generada, JSON coherente. **Archivos:** `ecom/tests/test_lote_resumen.py` (nuevo). **Done:** `docker exec Synap_app python manage.py test ecom.tests.test_lote_resumen` verde. **REQ:** LOT-01, LOT-02, LOT-04.
- [x] **6.3** Crear `test_aprobacion_lote`: aprobar/rechazar N PED, escalado no fallo, compensación parcial. **Archivos:** `ecom/tests/test_aprobacion_lote.py` (nuevo). **Done:** `docker exec Synap_app python manage.py test ecom.tests.test_aprobacion_lote` verde. **REQ:** APR-05, APR-08.
- [x] **6.4** Actualizar docs ecom: lane Cargas masivas, resumen lote, autorización lote, matriz readonly, post-confirmación. **Archivos:** `docs/ecom/PEDIDOS_HUB_KANBAN.md`, `docs/ecom/PEDIDO_MASIVO_SUCURSALES.md`, `docs/ecom/JERARQUIA_COMERCIAL_APROBACION.md`. **Done:** documentación alineada a specs y rutas finales. **REQ:** todos los dominios.
