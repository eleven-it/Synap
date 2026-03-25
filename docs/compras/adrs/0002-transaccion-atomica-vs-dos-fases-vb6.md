# ADR-0002: Transacción atómica vs dos fases como VB6 (`codmov`)

**Estado:** Aceptado (especificación).  
**Fecha:** 2026-03-24

## Contexto

*Confirmado por auditoría:* el VB6 ejecuta **dos transacciones consecutivas**: (1) incremento `codmov` + `CommitTrans`; (2) cuerpo del comprobante + `CommitTrans` o rollback en error ([auditoria_facturas_compras_resumen.md](../auditoria_facturas_compras_resumen.md), [auditoria_facturas_compras_flujo_completo.md](../auditoria_facturas_compras_flujo_completo.md) §C.7–C.8).

Esto implica una ventana donde el numerador ya avanzó aunque falle el segundo bloque (*riesgo de huecos* en `CodigoMovimiento`).

## Decisión

En Synap, el **posting legacy** usará **una única transacción MySQL** que:

1. Bloquee y lea el registro `codmov` (p. ej. `SELECT … FOR UPDATE` donde `codigo = 1`).
2. Incremente y persista el numerador.
3. Ejecute el resto de inserts/updates en el mismo `BEGIN … COMMIT`.

Si cualquier paso falla → **rollback completo** (sin consumir numerador de forma persistente).

## Consecuencias

- Paridad funcional: el `CodigoMovimiento` final es único y consistente con todas las tablas hijas (*mismo objetivo que VB6*).
- Diferencia respecto al legacy: **no hay huecos** por fallo post-numerador en la misma operación atómica.
- Documentar para auditores internos que el comportamiento difiere del VB6 en **atomicidad**, no en **resultado** de un posting exitoso.

## Trazabilidad

- VB6 dos fases: *confirmado por auditoría*.
- Estrategia Synap: *decisión nueva de arquitectura* alineada a [legacy_integration_spec.md](../legacy_integration_spec.md) §3.

## Alternativas rechazadas

- **Replicar dos commits estrictos:** reproduce huecos y dificulta tests de idempotencia.
