# Propuesta: Paridad de proceso TPV Synap con AdministraNET (`TPV.frm`)

## Intención

Alinear, de forma **evolutiva y controlada**, los **procesos de pago, validación previa al cierre y stock** del TPV web en Synap con el comportamiento de referencia de **`administranet_vb6/Formularios/TPV.frm`**, **únicamente cuando el kiosco opera en modo TPV** (`modoTpv`). El **autoservicio (self-checkout sin TPV)** permanece fuera de este alcance de paridad estructural.

## Documento de alcance (obligatorio)

- `docs/general/PARIDAD_TPV_ADMINISTRANET_ALCANCE.md` — criterio **solo modo TPV** / exclusión self-checkout.
- Análisis previo: flujos `Aceptar_Click`, `Validaciones_Factura`, `Guardar_Factura` (VB6) vs `CartService` + `ConfirmationService` (Synap); brechas identificadas (medios de cobro, límites, cheques, concurrencia stock, etc.).

## Capabilities

### New Capabilities

| ID | Descripción |
|----|-------------|
| **self-checkout-tpv** | Comportamiento exigible del TPV en Synap (kiosco con `modoTpv`) frente a reglas de negocio y persistencia comparables a `TPV.frm` en las áreas de **cobro**, **validación pre-confirmación** y **coherencia stock/legacy**, sin imponer el mismo criterio al flujo autoservicio. |

### Modified Capabilities

Ninguna con spec en `openspec/specs/` previo para este ID; el delta vive en `changes/paridad-tpv-administranet/specs/self-checkout-tpv/spec.md` como spec de **cambio** (base normativa: documento de alcance + esta propuesta).

## Enfoque

- **No reescribir** el legado: extender Synap en puntos acotados (`kiosco.html`, APIs, servicios) con **bifurcación explícita** `modoTpv`.
- **Fases:** matriz de paridad (inventario) → validaciones y medios (TPV) → ampliación según prioridad de negocio (p. ej. cheques, límites caja).
- **Pruebas:** TDD en servicios compartidos solo si el test no asume self-checkout; casos separados para `modoTpv` true/false cuando el contrato diverja.

## Riesgos / rollback

- Riesgo: regresión en autoservicio por condicionales mal aplicados → mitigar con tests de flujo `modoTpv === false` y revisión de API. Rollback: feature flags o revert por commit.
