# Alcance: paridad con AdministraNET (`TPV.frm`) — solo modo TPV

## Decisión de producto

Las mejoras orientadas a **igualar procesos de pago, stock y persistencia legacy** con el TPV de AdministraNET (`administranet_vb6/Formularios/TPV.frm` y flujos asociados) deben **implementarse y condicionarse únicamente cuando el kiosco opera en modo TPV**.

El **modo autoservicio (self-checkout)** — mismo template `kiosco.html` pero con **`modoTpv === false`** — **no** debe recibir esas extensiones: mantiene flujo simplificado (cliente final, menos validaciones tipo mostrador, sin obligar la misma matriz de medios de cobro / reglas de `Principal.*` del escritorio).

## Criterio técnico en Synap

| Modo | Variable Alpine (pantalla kiosco) | Paridad AdministraNET TPV.frm |
|------|-------------------------------------|-------------------------------|
| **TPV** | `modoTpv === true` | **Sí**: objetivo de cobertura de reglas de negocio y tablas legacy alineadas al VB6 donde aplique. |
| **Self-checkout** | `modoTpv === false` | **No**: no sumar validaciones ni pasos extra solo por paridad TPV; cambios de fondo compartidos (API, `ConfirmationService`) solo si ya son transversales y no degradan el autoservicio. |

- Activación del modo: habitualmente vía **barra TPV** / configuración de kiosco que habilita la UI tipo mostrador (cliente, lista de precio, vendedor, medios mixtos, etc.). El detalle de activación debe documentarse en el PR o en `SELF_CHECKOUT_UI.md` cuando cambie.

## Implicancias para desarrollo

1. **UI / Alpine**: usar `x-show="modoTpv"`, `if (this.modoTpv)` o equivalente antes de mostrar campos o ramas “solo TPV” (medios de cobro extendidos, límites, obligatoriedad vendedor/PV, etc.).
2. **API**: si un endpoint gana parámetros solo para paridad TPV, deben ser **opcionales** o rechazados fuera de modo TPV según diseño, para no complicar el flujo del cliente autoservicio.
3. **Documentación y SDD**: especificaciones de “paridad TPV” deben declarar explícitamente **exclusión del modo self-checkout** salvo acuerdo explícito de negocio.

## Precheck servidor (Fase 5)

Con **modo TPV** activo en el kiosco, antes de `ConfirmationService.confirmar` se ejecuta **`evaluar_precheck_tpv_paridad`** (`self_checkout/services/tpv_paridad_precheck.py`): permisos del **puesto** en sesión (`permisos_sistema` por `id_puesto`), obligatoriedad de **PV** y **vendedor**, tope de **crédito** del cliente (`Credito` / `saldo`) y **límite de efectivo** en la caja ABM asociada al kiosco (`caja_abm`, configuración Mercado Pago / `get_config_for_kiosk`). Detalle de columnas y códigos API: `docs/self_checkout/TPV_PRECHECK_PERMISOS_LEGACY.md`.

## Referencias

- OpenSpec (propuesta, spec delta, diseño): `openspec/changes/paridad-tpv-administranet/` (`proposal.md`, `specs/self-checkout-tpv/spec.md`, `design.md`).
- Interfaz kiosco: `self_checkout/templates/self_checkout/kiosco.html` (`kioscoApp`, `modoTpv`).
- Confirmación y legacy: `self_checkout/services/confirmation_service.py` (compartido; cualquier ramificación “solo TPV” debe quedar clara en código y tests).
- Plan maestro shell/sesión/TPV: `docs/general/PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md` (actualizar si la decisión de alcance afecta hitos).

---

*Documento alineado con la conversación de análisis TPV.frm vs Synap (paridad proceso pago/stock).*
