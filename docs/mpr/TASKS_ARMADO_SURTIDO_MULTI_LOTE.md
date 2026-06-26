# Tareas — Armado surtido multi-pack (lote / carrito)

**Change:** `mpr-armado-surtido-multi-lote`  
**Especificación:** [SPEC_ARMADO_SURTIDO_MULTI_LOTE.md](SPEC_ARMADO_SURTIDO_MULTI_LOTE.md)  
**Diseño:** [DESIGN_ARMADO_SURTIDO_MULTI_LOTE.md](DESIGN_ARMADO_SURTIDO_MULTI_LOTE.md)  
**Código principal:** `mpr/services.py`, `mpr/views.py`, `mpr/templates/mpr/armado_surtido.html`

**Estado:** Fases 1–9 (documentación) implementadas. Pendiente QA manual Fase 8 (AC-M1…M10) y accesibilidad modal 6.3.

---

## Fase 1 — Servicios núcleo (sin UI)

- [x] **1.1** Implementar `calcular_demanda_agregada_lote` y `calcular_demanda_item_lote` en `mpr/services.py`.

- [x] **1.2** Implementar `validar_reglas_lote_armado_surtido`:
  - límite 20 ítems;
  - packs duplicados;
  - cruce pack ↔ componente;
  - delegar `validar_datos_armado_surtido` por ítem.

- [x] **1.3** Implementar `parse_lote_armado_surtido_post(request)`:
  - parse `lote_json` UTF-8;
  - normalizar con `to_int_or_none`, enteros ≥ 1;
  - cabecera desde campos formulario;
  - mensajes de error en español.

- [x] **1.4** Tests unitarios Fase 1 en `mpr/tests/test_armado_surtido_lote.py`:
  - demanda agregada (AC-M2 escenario numérico);
  - reglas duplicado / cruce / límite 20;
  - parse JSON válido e inválido.

---

## Fase 2 — Refactor transaccional MVP

- [x] **2.1** Extraer `_ejecutar_armado_surtido_tx(cursor, conn, …)` desde `ejecutar_armado_surtido` (~8809+):
  - misma validación stock, codmov, talonario, stock, lotes FIFO, PrecioCosto;
  - retornar `lineas_enriquecidas` para composición Synap.

- [x] **2.2** Adaptar `ejecutar_armado_surtido` público como wrapper (open → tx → commit → `guardar_composicion_armado_surtido`).

- [x] **2.3** Ejecutar tests existentes `mpr.tests.test_armado_surtido` — **sin regresión**.

- [x] **2.4** Test smoke: wrapper delega correctamente (mock `_ejecutar_armado_surtido_tx`).

---

## Fase 3 — Orquestador lote (parcial D5)

- [x] **3.1** Implementar `ejecutar_lote_armado_surtido(base, id_usuario, cabecera, armados)`:
  - loop FIFO;
  - commit por ítem exitoso;
  - acumular `exitosos` / `fallidos` según §4.5 spec;
  - enriquecer respuesta con código/descripción pack desde `_fetch_articulos_map`.

- [x] **3.2** Implementar `validar_stock_agregado_lote` (lectura MySQL) para API y reutilizar criterio en documentación.

- [x] **3.3** Tests unitarios con mock connection/cursor:
  - AC-M3: 3 ítems, falla el 2.º → 1.º y 3.º en exitosos;
  - ítem fallido no incrementa contador si rollback;
  - orden FIFO respeta consumo acumulado (mock saldos decrecientes).

---

## Fase 4 — Vista POST/GET y sesión

- [x] **4.1** Modificar `ArmadoSurtidoView.post`:
  - usar `parse_lote_armado_surtido_post` / `_resolver_post_armado_surtido` (fallback single-pack);
  - `validar_reglas_lote_armado_surtido`;
  - `opt_puede_armado_surtido` si `id_lista`;
  - `ejecutar_lote_armado_surtido`;
  - guardar `armado_surtido_resultado_lote` y `armado_surtido_lote_fallidos` en sesión;
  - mensajes flash resumen (N grabados, M no grabados);
  - redirect a misma pantalla (RF12).

- [x] **4.2** Modificar `ArmadoSurtidoView.get_context_data`:
  - pop sesión → `resultado_lote_json`, `lote_fallidos_json`, `mostrar_modal_resultado_lote`.

- [x] **4.3** POST unificado vía `lote_json` (`syncLoteHidden`); fallback legacy en `_resolver_post_armado_surtido` hasta carrito Fase 5.

---

## Fase 5 — UI carrito (Alpine)

- [x] **5.1** Reorganizar `armado_surtido.html`:
  - **Cabecera lote** arriba (operario, origen, destino, detalle);
  - **Zona armar pack** (existente);
  - botones **Agregar al lote** / **Limpiar formulario**;
  - **Tabla lote pendiente** + acciones editar/quitar;
  - **Resumen consumo agregado** (componente → total u., saldo origen).

- [x] **5.2** Extender `armadoSurtidoForm()`:
  - estado `lote`, `editandoUid`, `resumenConsumo`;
  - `agregarAlLote`, `editarItemLote`, `quitarItemLote`, `recalcularResumen`;
  - validación cliente RF2–RF4 antes de agregar;
  - `syncLoteHidden()` → input hidden `lote_json`;
  - submit solo con `lote.length >= 1` (RF11).

- [x] **5.3** Cambiar botón principal a **Ejecutar lote (N)** con contador.

- [x] **5.4** Rehidratar `lote` desde `lote_fallidos_json` en init si post-ejecución parcial (AC-M10).

- [x] **5.5** Deshabilitar «Agregar al lote» con 20 ítems (RF10).

---

## Fase 6 — Modal resultado

- [x] **6.1** Crear `mpr/templates/mpr/includes/armado_surtido_modal_resultado_lote.html`:
  - tablas Grabados / No grabados;
  - comprobante + código movimiento;
  - motivo error;
  - botón Cerrar;
  - UI canon MPR (dark/light).

- [x] **6.2** Incluir en `armado_surtido.html`; abrir automáticamente si `mostrar_modal_resultado_lote`.

- [ ] **6.3** Verificar accesibilidad: focus trap básico, `aria-modal`, cerrar con Escape.

---

## Fase 7 — API validación (P1)

- [x] **7.1** `ArmadoSurtidoValidarItemLoteAPIView` + ruta en `mpr/urls.py`.

- [x] **7.2** Wire opcional en `agregarAlLote()` (fetch antes de push); fallback validación solo cliente si API falla.

- [x] **7.3** Test view/API con mock `validar_stock_agregado_lote`.

---

## Fase 8 — Pruebas y verificación

- [x] **8.1** `docker exec Synap_app python manage.py test mpr.tests.test_armado_surtido mpr.tests.test_armado_surtido_lote mpr.tests.test_armado_surtido_view -v 2`

- [ ] **8.2** Verificación manual AC-M1 … AC-M10 en `/mpr/armado-surtido/` (base prueba).

- [ ] **8.3** Verificar AC-M6 con `?id_lista=` desde detalle OPT.

- [ ] **8.4** Verificar PrecioCostoxU/R en renglones de cada MSTOCK del lote (herencia RF9).

---

## Fase 9 — Documentación

- [x] **9.1** Actualizar [MANUAL_USUARIO_MPR.md](MANUAL_USUARIO_MPR.md) §7.1 con flujo carrito + modal.

- [x] **9.2** Actualizar [SPEC_ARMADO_SURTIDO_MULTI_LOTE.md](SPEC_ARMADO_SURTIDO_MULTI_LOTE.md) §12 (estado apply/verify).

- [x] **9.3** Marcar [SDD_ARMADO_SURTIDO_MULTI_LOTE.md](SDD_ARMADO_SURTIDO_MULTI_LOTE.md) como implementado cuando aplique.

---

## Orden de dependencias

```text
1.* → 2.* → 3.* → 4.* → 5.* → 6.*
                    ↘ 7.* (paralelo tras 1.2 + 3.2)
8.* → 9.*
```

**Camino crítico:** 1 → 2 → 3 → 4 → 5 → 6 → 8.

---

## Criterio de done

- Todos los AC-M1 … AC-M10 pasan (auto o manual documentado).
- Tests Fase 1–3 y regresión `test_armado_surtido` en verde.
- Sin regresión flujo `?id_lista=` y PrecioCosto en stock.
- Documentación §9 actualizada.

---

## Estimación orientativa

| Fase | Esfuerzo |
|------|----------|
| 1–3 Backend | 1–2 días |
| 4–6 UI + modal | 1–2 días |
| 7 API | 0.5 día |
| 8–9 QA + docs | 0.5–1 día |

**Total:** ~3–5 días desarrollo + QA.
