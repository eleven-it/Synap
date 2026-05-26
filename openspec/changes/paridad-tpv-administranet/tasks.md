# Tasks: Paridad TPV Synap ↔ AdministraNET (`paridad-tpv-administranet`)

Desglose ejecutable alineado con `proposal.md`, `specs/self-checkout-tpv/spec.md` y `design.md`. Regla transversal: **ningún comportamiento nuevo de paridad sin `modo_tpv` activo en el kiosco** (`self_checkout_kiosk.modo_tpv`, ya expuesto en acquire/config).

---

## Fase 1 — Inventario y contrato backend «solo TPV»

- [x] **1.1** Documentar en `docs/general/` (ej. `MATRIZ_PARIDAD_TPV_VB6_SYNAP.md`) tabla **VB6 → Synap**: filas de `Aceptar_Click` / `Validaciones_Factura` / inicio de `Guardar_Factura` (suma medios, medios obligatorios, redondeo, límites desc pie, series, límite caja, `verificar_limites`) vs función/API Synap actual y estado (**OK / parcial / falta**).
- [x] **1.2** En `self_checkout/api_views.py` (vista `cart_confirm` o helper dedicado), obtener **`modo_tpv`** desde **`kiosk_id`** del carrito con `KioskSessionService` / lectura `self_checkout_kiosk` (mismo criterio que `payment_methods_list`). Variable booleana `es_modo_tpv` disponible para validadores posteriores.
- [x] **1.3** Extraer función pura **`calcular_total_medios_tpv(body)`** (o nombre equivalente) en `self_checkout/services/` nuevo módulo pequeño **`tpv_payment_validation.py`** (o dentro de `cart_service.py` si preferís menos archivos): suma `tpv_importe_efectivo`, `tpv_pago_efectivo` solo para cambio, `tpv_importe_tarjeta`, importes cta. cte. / cheque **cuando existan en payload**, más **`tpv_intereses`** si aplica; tolerancia decimal **±0.02** al comparar con `cart.total`. Sin efectos secundarios.

**Verificación:** tests unitarios del helper con casos mixtos y mixtos con intereses (solo números).

---

## Fase 2 — Validación servidor: suma medios = total (solo TPV)

- [x] **2.1** En el flujo POST **`cart/<id>/confirm/`**, si **`es_modo_tpv`** y el body incluye desglose TPV (`payment_method` mixto/efectivo/tarjeta con campos tpv_*), invocar **`calcular_total_medios_tpv`** y comparar con total del carrito; si no coincide → **`400`** con código estable **`E_TPV_MEDIOS_TOTAL`** y mensaje en español (sin tocar DB).
- [x] **2.2** Si **`es_modo_tpv`** y todos los importes de medios son **cero** pero hay intento de confirmar con método que exige desglose → rechazar con **`E_TPV_MEDIOS_VACIOS`** (equivalente funcional a VB6 “al menos un medio”).
- [x] **2.3** Asegurar que cuando **`not es_modo_tpv`**, las nuevas ramas **no** ejecutan validación de suma TPV (contrato autoservicio intacto).

**Verificación:** test integración `manage.py test` con carrito mock/kiosk `modo_tpv=1` vs `0`.

---

## Fase 3 — UI Alpine (`kiosco.html`): espejo cliente

- [x] **3.1** Antes de `confirmarVenta` / `confirmarVentaConMetodo`, si **`this.modoTpv`**, validar suma de totales de efectivo + tarjeta (+ intereses si están en estado) **≈** `this.total` con misma tolerancia que servidor; si falla → `toast` / mensaje y **return** (no llamar API).
- [x] **3.2** Si **`modoTpv`** y ningún medio tiene importe > 0 → mensaje y abort (equivalente mobile/Desktop barra TPV).
- [x] **3.3** No añadir estos bloqueos cuando **`!modoTpv`** (mantener flujo actual checkout).

**Verificación:** prueba manual en kiosco con `modo_tpv` activado en BD y desactivado.

---

## Fase 4 — Series (solo TPV, si aplica catálogo)

- [x] **4.1** Revisar respuesta API al agregar ítem (`requiere_series`): si el modal de series no está completo y **`modoTpv`**, impedir confirmación en cliente (ya puede existir lógica; **unificar** criterio con spec).
- [x] **4.2** (Opcional servidor) Si **`es_modo_tpv`** y líneas tienen `requiere_series`, validar en `confirmar` previo que series cubren cantidad — solo si el diseño actual lo permite sin duplicar VB6 completo.

**Verificación:** escenario ítem seriado en TPV vs mismo flujo autoservicio sin pasos extra innecesarios.

---

## Fase 5 — Límites crédito / caja / PV obligatorio (posterior v1)

- [x] **5.1** Mapear parámetros **`permisos_sistema`** / empresa necesarios para equivalentes a **`limite_efectivo_caja`**, **`verificar_limites`**, **`obliga_selecpv`**, **`obliga_cambvendedor`** (lectura desde servicios existentes o nuevo helper solo lectura).
- [x] **5.2** Implementar validaciones **solo si `es_modo_tpv`**, en orden: después de suma medios, antes de llamar a **`ConfirmationService.confirmar`** (o dentro de un **precheck** dedicado).
- [x] **5.3** Actualizar `MATRIZ_PARIDAD_*` y `PARIDAD_TPV_ADMINISTRANET_ALCANCE.md` con estado «implementado».

**Verificación:** tests con flags simulados / BD fixture si existe patrón en proyecto.

---

## Fase 6 — Observabilidad, docs y cierre SDD

- [x] **6.1** En rechazos **`E_TPV_*`**, registrar **`self_checkout_audit_log`** o log existente con **`codigo`** y **`cart_id`** (sin datos sensibles).
- [x] **6.2** Actualizar `docs/self_checkout/SELF_CHECKOUT_UI.md` con comportamiento “validación medios TPV” en una viñeta.
- [ ] **6.3** Ejecutar **`/sdd-verify`** contra `specs/self-checkout-tpv/spec.md` cuando Fases 2–3 estén merged; abrir tareas Fase 5 solo si producto prioriza.

---

## Dependencias entre fases

```
Fase 1 (1.2 helper modo_tpv + 1.3 cálculo) → Fase 2
Fase 2 → Fase 3 (UI alineada a mismas reglas)
Fase 4 en paralelo tras Fase 3 si hay tiempo
Fase 5 independiente tras Fase 2 (puede ramificar en otro PR)
Fase 6 al cerrar cada oleada mergeada
```

---

## Criterios de “done” por oleada mínima (MVP paridad cobro)

- Oleada A: **1.2, 1.3, 2.1–2.3, 3.1–3.3, 6.2** completadas y tests Fase 2 pasando.
- Oleada B: Fase 4 + tests manuales series.
- Oleada C: Fase 5 + 6.1.
