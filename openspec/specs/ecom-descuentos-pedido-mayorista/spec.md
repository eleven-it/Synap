# Spec: Descuentos pedido mayorista (simple y masivo)

**Capability:** `ecom-descuentos-pedido-mayorista`  
**Origen:** change `ecom-pedidos-usabilidad-supervisor` (archivado 13/07/2026)

## Purpose

Contrato unificado de descuentos por renglón y al pie en pedido simple (carrito) y pedido masivo (matriz/lote). Paridad `SPEC_PRESUPUESTO_VENTAS_SYNAP.md` §1.3–§1.4.

## Requirements

### REQ-DSC-01 — Descuento renglón en pedido simple

El descuento por renglón MUST aplicarse como porcentaje 0–100 sobre neto unitario antes de IVA. MUST persistirse en `EcomCartItem.porcentaje_descuento`. MUST editable en UI y vía `PATCH` item. Al agregar ítem, MUST precargar `descRenglon` del cliente si no hay valor manual.

#### Scenario: Paridad descRenglon al agregar

- **GIVEN** cliente con `descRenglon=12`
- **WHEN** agrega artículo al carrito simple
- **THEN** renglón MUST iniciar con 12% descuento

#### Scenario: Override manual renglón

- **GIVEN** renglón con 12% precargado
- **WHEN** usuario cambia a 0%
- **THEN** MUST persistir 0% vía PATCH y recalcular totales backend

---

### REQ-DSC-02 — Descuento al pie en pedido simple

El descuento al pie MUST aplicarse como porcentaje sobre neto gravado por alícuota antes de recalcular IVA (paridad `Jcart`). MUST precargarse desde `cliente.Descuento` al seleccionar cliente. MUST persistirse vía `POST …/carrito/descuento-pie/`.

#### Scenario: Pie precargado y editable

- **GIVEN** cliente con `Descuento=5`
- **WHEN** selecciona cliente y luego cambia pie a 7%
- **THEN** carrito MUST quedar con 7% pie tras POST

---

### REQ-DSC-03 — Descuentos en pedido masivo

En pedido masivo, MUST existir % descuento por fila (artículo × sucursal o fila agregada según diseño) y descuento pie de lote. MUST aplicarse en preview y en `confirmar_lote_masivo` con `price_rules_engine`, no con `descuento_cliente=0` fijo.

#### Scenario: Confirmación con descuentos masivo

- **GIVEN** matriz con 10% desc fila y 5% pie lote
- **WHEN** confirma lote
- **THEN** importes en `comp_ped`/`stockp` MUST reflejar ambos descuentos

---

### REQ-DSC-04 — Autoridad de totales en backend

En simple y masivo, los importes finales (neto, IVA, total) MUST calcularse exclusivamente en backend (`mayorista_cart_service`, checkout, preview masivo). Frontend MUST NOT recalcular totales para display distinto al serializado por API.

#### Scenario: UI no contradice backend

- **GIVEN** preview masivo devuelve total 15000
- **WHEN** UI muestra resumen pre-confirmación
- **THEN** total mostrado MUST ser 15000 exacto

---

### REQ-DSC-05 — Orden de aplicación descuentos

El sistema MUST aplicar descuento renglón antes que descuento pie, en ambos flujos. MUST NOT invertir el orden respecto al legacy PHP (`jcart.php`).

#### Scenario: Renglón + pie acumulados

- **GIVEN** renglón neto 1000 con 10% renglón → 900, carrito neto gravado 900
- **WHEN** aplica 10% pie
- **THEN** neto final gravado MUST ser 810 antes de IVA
