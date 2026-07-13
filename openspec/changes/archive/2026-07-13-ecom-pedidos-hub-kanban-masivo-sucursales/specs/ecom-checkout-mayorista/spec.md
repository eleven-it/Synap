# Spec delta: ecom-checkout-mayorista

## ADDED Requirements

### REQ-CHK-MAS-01 — Batch multi-PED
El sistema MUST exponer un servicio/API de confirmación de pedido masivo que cree N comprobantes PED reutilizando la lógica de checkout mayorista, uno por `id_cliente_domicilio` con líneas agregadas de esa columna.

### REQ-CHK-MAS-02 — Integridad del lote
Si cualquier alta del lote falla tras haber creado otras, el sistema MUST compensar (anular) las altas de esa corrida y MUST reportar el error sin marcar el borrador como CONFIRMADO.

#### Scenario: Compensación
- **GIVEN** el lote creó PED #1 OK y falla PED #2
- **WHEN** se aplica la política de lote
- **THEN** PED #1 MUST quedar anulado (o no persistido) y el borrador MUST seguir editable
