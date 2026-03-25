# ADR-0005: Aislamiento del posting legacy respecto al workflow UI

**Estado:** Aceptado (especificación).  
**Fecha:** 2026-03-24

## Contexto

El workflow de expedientes (captura, OCR, revisión) evoluciona con frecuencia. El posting legacy es **crítico** y debe alinearse a la auditoría VB6 ([legacy_integration_spec.md](../legacy_integration_spec.md)).

Mezclar ambos en un mismo módulo monolítico aumenta el riesgo de regresiones y dificulta tests.

## Decisión

1. **App/capa separada** `factura_compra_posting` (o paquete Python equivalente) que solo recibe `LegacyPostingCommand` y habla MySQL.
2. La **API de expedientes** llama al posting mediante **interfaz inyectable** (servicio o use-case) sin SQL legacy en vistas.
3. Los tests de posting **no** cargan plantillas OCR ni PWA.

## Consecuencias

- Mayor claridad de dependencias y capacidad de mockear MySQL en tests unitarios.
- Posible duplicación leve de DTOs entre expediente y comando — aceptable con mappers explícitos.

## Trazabilidad

- Comportamiento legacy encapsulable: *inferencia desde auditoría* (procedimiento `Guardar` cohesivo en VB6 pero traducible a capa dedicada en Django).
- Separación Synap: *decisión nueva de arquitectura* ([architecture.md](../architecture.md)).

## Relación con ADR-0001

El posting solo se invoca post-aprobación; la UI nunca abre transacciones legacy.
