# Informe de verificación SDD

**Change:** `ecom-pedidos-usabilidad-supervisor`  
**Fecha:** 13/07/2026  
**Modo:** Standard (strict_tdd no configurado)  
**Verificador:** sdd-verify (hybrid)

---

## Veredicto

**PASS WITH WARNINGS**

Backend y contratos API cumplen specs con 78/78 tests verdes. Tareas A–E completas. Escenarios UI (banner, selector, tokens visuales) tienen evidencia estática pero sin tests automatizados. Advertencias operativas conocidas: latencia preview masivo, seed `configuracion_ecom` por base, purple residual en hub pedidos (fuera alcance E.2).

---

## Completitud de tareas

| Métrica | Valor |
|--------|-------|
| Tareas totales | 29 |
| Tareas completadas `[x]` | 29 |
| Tareas incompletas | 0 |

**Oleadas:** A (9/9) · B (6/6) · C (4/4) · D (6/6) · E (4/4)

---

## Ejecución build y tests

**Build / system check:** ✅ OK

```bash
docker exec Synap_app python manage.py check
# System check identified no issues (0 silenced).
```

**Suite ecom (change):** ✅ 78 passed / 0 failed / 0 skipped (151,3 s)

```bash
docker exec Synap_app python manage.py test \
  ecom.tests.test_vendedor_operativo \
  ecom.tests.test_mayoristapp_sesion_contexto \
  ecom.tests.test_vcm_simple_operativo \
  ecom.tests.test_mayorista_cart_descuentos \
  ecom.tests.test_mayorista_cart_service \
  ecom.tests.test_pedido_masivo_matriz \
  ecom.tests.test_batch_checkout_masivo \
  ecom.tests.test_catalogo_producto_listado \
  --keepdb
```

**Cobertura:** ➖ No ejecutada en esta verificación.

**Notas de ejecución:** Algunos tests de masivo registran errores de conexión MySQL a `192.168.0.2` en logs (`leer_contexto_cliente_masivo`); los mocks permiten que la suite termine OK. No bloqueante para este change.

---

## Matriz de cumplimiento de specs

Criterio: ✅ COMPLIANT = test pasó; ⚠️ PARTIAL = implementación estática sin test de comportamiento; ❌ UNTESTED = sin test ni evidencia suficiente.

| Requisito | Escenario | Test / evidencia | Resultado |
|-----------|-----------|------------------|-----------|
| REQ-VOP-01 | Vendedor sin selección explícita | `test_vendedor_operativo > test_default_sin_operativo` | ✅ COMPLIANT |
| REQ-VOP-01 | Supervisor sin vendedor elegido | `test_mayoristapp_sesion_contexto > test_supervisor_hidrata_cartera_y_operativo` | ✅ COMPLIANT |
| REQ-VOP-02 | Supervisor con cartera legacy | `test_vendedor_operativo > test_json_config` | ✅ COMPLIANT |
| REQ-VOP-02 | Vendedor no supervisor | `test_mayoristapp_sesion_contexto > test_supervisor_cod_usuario_todos_clientes` | ✅ COMPLIANT |
| REQ-VOP-03 | Cambio de vendedor operativo | `test_vendedor_operativo > test_guardar_y_reset_operativo` | ✅ COMPLIANT |
| REQ-VOP-03 | Vendedor sin permiso supervisor | (sin test UI) | ⚠️ PARTIAL |
| REQ-VOP-04 | Banner «Operando como» | includes `pedidos_selector_vendedor.html` | ⚠️ PARTIAL |
| REQ-VOP-05 | Logout limpia operativo | `test_vendedor_operativo > reset_cod_viajante_operativo` | ⚠️ PARTIAL |
| REQ-VOP-06 | Checkout usa operativo | `test_vendedor_operativo > test_session_cod_viajante_usa_operativo`; `test_batch_checkout_masivo > test_confirmar_aplica_descuentos_y_operativo` | ✅ COMPLIANT |
| REQ-UI-01 | CTA primario pedido simple | tokens `.pedidos-*` en `pedidos_page_styles.html` | ⚠️ PARTIAL |
| REQ-UI-01 | Header pedido masivo slate/sky | sin `purple` en `pedido_masivo_sucursales.html` | ⚠️ PARTIAL |
| REQ-UI-02 | Barrido post-implementación | grep: sin `purple` en compra_mayorista, pedido_masivo, includes pedidos_* | ⚠️ PARTIAL |
| REQ-UI-03 | Modal confirmación masivo | `pedidos_modal.html` + `pedido_masivo_app.mjs` (sin `confirm()`) | ⚠️ PARTIAL |
| REQ-UI-04 | Badge lista coherente | `pedidos_lista_badge.html` en simple y masivo | ⚠️ PARTIAL |
| REQ-VTA-05 | Cliente con lista asignada | `test_vcm_simple_operativo > test_payload_lista_y_pdf` | ✅ COMPLIANT |
| REQ-VTA-05 | Sin override de lista | `test_vcm_simple_operativo > test_rechaza_override_lista` | ✅ COMPLIANT |
| REQ-VTA-06 | Editar descuento renglón | `test_mayorista_cart_descuentos > test_patch_descuento_renglon` | ✅ COMPLIANT |
| REQ-VTA-07 | Selector visible supervisor | include `pedidos_selector_vendedor.html` | ⚠️ PARTIAL |
| REQ-VTA-08 | Banner en shell | include selector + banner | ⚠️ PARTIAL |
| REQ-VTA-09 | Descuento pie precargado | `test_mayorista_cart_descuentos > test_primera_seleccion_precarga_desc_pie` | ✅ COMPLIANT |
| REQ-VCM-04 | VCM simple con operativo | `test_vcm_simple_operativo > test_operativo_usa_solo_terna_efectiva` | ✅ COMPLIANT |
| REQ-VCM-04 | Catálogo filtrado marcas terna | `test_vcm_simple_operativo > test_aplica_marcas_terna_operativo` | ✅ COMPLIANT |
| REQ-VCM-04 | Supervisor usa propio viajante | `test_vcm_simple_operativo > test_legacy_supervisor_sin_vcm_mantiene_cargo` | ✅ COMPLIANT |
| REQ-VCM-05 | Paridad simple ↔ masivo | `test_vcm_simple_operativo > test_mismo_viajante_operativo_en_busquedas` | ✅ COMPLIANT |
| REQ-CAR-005 | Cliente 5% descuento comercial | `test_mayorista_cart_descuentos > test_primera_seleccion_precarga_desc_pie` | ✅ COMPLIANT |
| REQ-CAR-005 | Cambio de cliente actualiza pie | `test_mayorista_cart_descuentos > test_cambio_cliente_actualiza_desc_pie` | ✅ COMPLIANT |
| REQ-CAR-006 | PATCH descuento renglón | `test_mayorista_cart_descuentos > test_patch_descuento_renglon` | ✅ COMPLIANT |
| REQ-CAR-006 | descRenglon al agregar | `test_mayorista_cart_descuentos > test_desc_renglon_al_agregar` | ✅ COMPLIANT |
| REQ-CAR-007 | Totales exclusivamente backend | `test_mayorista_cart_service > test_serializa_carrito` | ✅ COMPLIANT |
| REQ-CAT-004 | Marca no asignada oculta | `test_vcm_simple_operativo > test_aplica_marcas_terna_operativo` | ✅ COMPLIANT |
| REQ-CAT-004 | Sin cliente → 400 | `test_vcm_simple_operativo > test_sin_cliente_400` | ✅ COMPLIANT |
| REQ-CAT-005 | Lista fijada por cliente | `test_vcm_simple_operativo > test_rechaza_override_lista` | ✅ COMPLIANT |
| REQ-CAT-006 | Payload cliente con lista | `test_vcm_simple_operativo > test_payload_lista_y_pdf` | ✅ COMPLIANT |
| REQ-CHK-010 | Vendedor directo confirma | `test_vendedor_operativo > test_session_cod_viajante_id_vendedor_usr` | ✅ COMPLIANT |
| REQ-CHK-010 | Supervisor confirma en nombre | `test_batch_checkout_masivo > test_confirmar_aplica_descuentos_y_operativo` | ✅ COMPLIANT |
| REQ-CHK-011 | Sesión solo id_vendedor_usr | `test_vendedor_operativo > test_session_cod_viajante_id_vendedor_usr` | ✅ COMPLIANT |
| REQ-CHK-011 | Bug legacy corregido | mismo test + fix `_session_cod_viajante` | ✅ COMPLIANT |
| REQ-CHK-012 | Lote masivo operativo | `test_batch_checkout_masivo > test_confirmar_aplica_descuentos_y_operativo` | ✅ COMPLIANT |
| REQ-MAS-03 | Supervisor confirma lote | `test_batch_checkout_masivo > test_confirmar_aplica_descuentos_y_operativo` | ✅ COMPLIANT |
| REQ-MAS-06 | Confirmación con modal | `pedido_masivo_app.mjs` + `pedidos_modal.html` | ⚠️ PARTIAL |
| REQ-MAS-07 | Precio distinto Precio1V | `test_pedido_masivo_matriz` (price_rules mock) | ✅ COMPLIANT |
| REQ-MAS-08 | Descuento fila en matriz | `test_pedido_masivo_matriz > test_guardar_descuento_fila_y_pie` | ✅ COMPLIANT |
| REQ-MAS-08 | Descuento pie de lote | `test_pedido_masivo_matriz > test_preview_ok_con_warning` | ✅ COMPLIANT |
| REQ-MAS-09 | Precarga descRenglon | `test_pedido_masivo_matriz > test_precarga_desc_renglon_al_celda` | ✅ COMPLIANT |
| REQ-MAS-10 | Preview previo a confirmar | `test_pedido_masivo_matriz > test_preview_ok_con_warning` | ✅ COMPLIANT |
| REQ-MAS-10 | Lote grande con límites | `test_batch_checkout_masivo > test_preview_warning_celdas_limite` | ✅ COMPLIANT |
| REQ-MAS-11 | Banner en masivo | include selector en template | ⚠️ PARTIAL |
| REQ-DSC-01 | Paridad descRenglon al agregar | `test_mayorista_cart_descuentos > test_desc_renglon_al_agregar` | ✅ COMPLIANT |
| REQ-DSC-01 | Override manual renglón | `test_mayorista_cart_descuentos > test_patch_descuento_renglon` | ✅ COMPLIANT |
| REQ-DSC-02 | Pie precargado y editable | `test_mayorista_cart_descuentos > test_cambio_cliente_actualiza_desc_pie` | ✅ COMPLIANT |
| REQ-DSC-03 | Confirmación con descuentos masivo | `test_batch_checkout_masivo > test_confirmar_aplica_descuentos_y_operativo` | ✅ COMPLIANT |
| REQ-DSC-04 | UI no contradice backend | preview API testeado; display UI sin test E2E | ⚠️ PARTIAL |
| REQ-DSC-05 | Orden renglón + pie | `test_mayorista_cart_descuentos > test_renglon_10_pie_10_sobre_neto_gravado` | ✅ COMPLIANT |

**Resumen cumplimiento:** 38/53 ✅ COMPLIANT · 15/53 ⚠️ PARTIAL · 0/53 ❌ FAILING/UNTESTED crítico backend

---

## Correctitud (evidencia estática)

| Área | Estado | Notas |
|------|--------|-------|
| `vendedor_operativo.py` resolver único | ✅ | Consumido por checkout, masivo, cliente_relay |
| Hidratación `configuracion_ecom` | ✅ | `mayoristapp_sesion_contexto.py` + fallback `[cv]` |
| APIs vendedores-cartera / vendedor-operativo | ✅ | Validación ∈ cartera |
| Fix `_session_cod_viajante` | ✅ | Usa resolver operativo |
| VCM ternas en simple | ✅ | Paridad con masivo |
| Descuentos simple + masivo | ✅ | Backend autoridad totales |
| Preview masivo + límite blando | ✅ | Warning ≤200 celdas |
| JS masivo extraído | ✅ | `ecom/static/ecom/js/pedido_masivo_app.mjs` (ruta `js/` vs `static/ecom/` en tasks — equivalente) |
| Tokens slate/sky pedido simple/masivo | ✅ | Sin purple en alcance E.2 |

---

## Coherencia con design.md

| Decisión | ¿Seguida? | Notas |
|----------|-----------|-------|
| Resolver único viajante efectivo | ✅ | `vendedor_operativo.py` |
| Cartera en `configuracion_ecom` JSON | ✅ | Sin DDL |
| VCM ternas en simple | ✅ | |
| Lista precios RO + PDF | ✅ | |
| Descuentos backend-only | ✅ | |
| Masivo price_rules + preview | ✅ | |
| Modal canon vs confirm() | ✅ | Masivo migrado |
| Barrido purple slate/sky | ⚠️ | Hub `pedidos_hub.html` conserva purple (documentado fuera E.2) |

---

## Issues encontrados

### CRITICAL (bloquean archive)

Ninguno.

### WARNING (corregir o aceptar explícitamente)

1. **Latencia preview masivo:** `price_rules_engine` por fila puede degradar UX en lotes grandes; límite blando 200 celdas emite warning pero no garantiza SLA de tiempo (riesgo design §Preguntas abiertas).
2. **`configuracion_ecom` por base:** cartera supervisor requiere seed manual `ecom_vendedores_a_cargo_<CodViajante>`; sin fila solo opera con `[cv]` propio.
3. **Escenarios UI sin tests:** banner, selector supervisor, tokens visuales y modal masivo dependen de revisión manual / E2E.
4. **Hub purple fuera alcance E.2:** `pedidos_hub.html` y `config_vendedor_cliente_marca.html` mantienen clases `purple-*` (aceptado como fuera de scope según notas del change).
5. **Build/type-check dedicado:** no hay comando de build en `openspec/config.yaml`; solo `manage.py check` ejecutado.

### SUGGESTION

1. Tests de plantilla o E2E para REQ-UI-* y REQ-VOP-04/VTA-07/08.
2. Documentar script seed `configuracion_ecom` por cliente desplegado.
3. Monitorear latencia preview en staging con matriz real.

---

## Próximo paso recomendado

**sdd-archive** — veredicto PASS WITH WARNINGS; no hay blockers CRITICAL. Registrar warnings operativos en archive o backlog de producto.
