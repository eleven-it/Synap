# Design: Paridad TPV Synap ↔ AdministraNET (`TPV.frm`)

## Technical Approach

Implementar la paridad como **capas opcionales activadas solo con `modoTpv`**, sin ramificar el autoservicio por defecto.

1. **Presentación (Alpine):** `kiosco.html` / includes ya disponen de `modoTpv`. Las nuevas validaciones de cobro (suma de medios, bloqueo sin medios, etc.) se enganchan en **`confirmarVenta` / `confirmarVentaConMetodo`** y en el modal de pago **solo si `modoTpv`**.
2. **API:** Donde haga falta validación server-side duplicada, el payload puede incluir `modo_tpv: true` o deducirse de **configuración del kiosco** (`kiosk` / sesión) para no confiar solo en el cliente.
3. **Servicios:** `ConfirmationService` permanece la **única fuente de commit** legacy. Las extensiones TPV (p. ej. validación adicional antes de `_confirmar_interno`, o reglas de `tc_comprobante` ya existentes) se encapsulan en helpers privados o en **`CartService`** para validaciones previas al estado `pago_aprobado`.

Referencia de alcance: `docs/general/PARIDAD_TPV_ADMINISTRANET_ALCANCE.md`.  
Spec: `openspec/changes/paridad-tpv-administranet/specs/self-checkout-tpv/spec.md`.

## Architecture Decisions

### Decisión: Interruptor único `modoTpv`

**Elección:** Toda regla “paridad VB6” depende de **`modoTpv === true`** en UI y, en backend, del mismo criterio vía contexto de kiosco o flag explícito en request.

**Alternativas consideradas:** Feature flag global por empresa; segundo template solo TPV.

**Rationale:** Ya existe el estado Alpine y la barra TPV; duplicar plantilla aumenta drift.

### Decisión: Validación suma medios en cliente y servidor

**Elección:** Replicar la comprobación `sum(medios) == total` en **servidor** en `cart_confirm` (o servicio llamado desde ahí) cuando el contexto sea TPV, usando los mismos campos que envía el modal (efectivo, tarjeta, mixto, intereses si aplican).

**Alternativas:** Solo cliente (riesgo de bypass).

**Rationale:** Paridad con intención de `Aceptar_Click` y seguridad.

### Decisión: No bloquear autoservicio con límites de crédito/caja en v1

**Elección:** `verificar_limites` / `limite_efectivo_caja` equivalentes se implementan **tras** la cerrada de suma de medios y series, y **solo en ramas TPV**.

**Rationale:** El documento de alcance excluye self-checkout de estas reglas.

### Decisión: Stock y concurrencia

**Elección:** Mantener **UPDATE condicional** actual en `confirmation_service`. Documentar en observabilidad si ocurre conflicto; opcional fase 2: mensaje más explícito “otro usuario vendió la última unidad”.

**Alternativas:** Reserva de stock al agregar línea (impacto grande en legado).

## Data Flow (modo TPV)

```
UI kiosco (modoTpv)
  → validación medios / series / límites (fases)
  → POST /api/self-checkout/cart/:id/confirm/ (+ contexto TPV)
  → ConfirmationService.confirmar (transacción)
       → stock_deposito, codmov, cuentacliente, stock, tc_comprobante, caja, FE…
```

Flujo autoservicio: **sin** las cajas de validación TPV adicionales; mismo endpoint si el servidor discrimina por kiosco.

## File Changes (previsto, por fase)

| Área | Archivos típicos | Nota |
|------|------------------|------|
| UI | `self_checkout/templates/self_checkout/kiosco.html` | Condicionales `modoTpv` en confirmación y modal pago |
| API | `self_checkout/api_views.py` | Lectura modo TPV; validación suma medios |
| Dominio | `self_checkout/services/cart_service.py`, `confirmation_service.py` | Helpers validación; sin cambiar contrato FE/stock para no-Tpv |
| Docs | `docs/general/PARIDAD_TPV_ADMINISTRANET_ALCANCE.md` | Ya creado; actualizar con fases completadas |

## Fuera de alcance v1 (spec)

- NC / anulaciones desde kiosco.
- Cheques de terceros como medio (grid VB6) salvo que una fase lo priorice.
- Impresora fiscal Hasar/Olivetti (VB6); Synap usa FE web.

## Testing Strategy

| Capa | Qué |
|------|-----|
| Unit | Cálculo suma medios, tolerancia decimal, parseo body TPV |
| Integración | POST confirm con `modoTpv` simulado vs carrito; assert rechazo si suma ≠ total |
| Regresión | Confirmación autoservicio sin flags TPV sigue OK |

## Observabilidad

- Log estructurado o `audit_log` en rechazos de validación TPV (código motivo) para afinar reglas sin adivinar en producción.

## References

- VB6: `TPV.frm` — `Private Sub Aceptar_Click`, `Validaciones_Factura`, `Private Sub Guardar_Factura`.
- Synap: `self_checkout/services/confirmation_service.py`, `stock_service.py`, `api_views.py` (`cart_confirm`).
