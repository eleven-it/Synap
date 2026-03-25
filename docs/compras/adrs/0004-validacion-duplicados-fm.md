# ADR-0004: Política de validación de duplicados para comprobante tipo FM

**Estado:** Aceptado (especificación).  
**Fecha:** 2026-03-24

## Contexto

*Confirmado por auditoría:* `Validacion_Comp` en `PFactura.frm` consulta duplicados en `cuentaproveedor` para tipos `'FA'`, `'FC'`, `'FB'` pero **no incluye `'FM'`** en el `WHERE` ([auditoria_facturas_compras_sql.md](../auditoria_facturas_compras_sql.md), [auditoria_facturas_compras_pendientes_dudas.md](../auditoria_facturas_compras_pendientes_dudas.md) §2).

## Decisión (configurable por empresa)

**Por defecto en Synap:** aplicar **anti-duplicado también para FM** con la misma clave lógica que FA/FC/FB (proveedor + número + anulado), porque reduce riesgo operativo.

**Modo «paridad estricta VB6»** (flag configuración): excluir FM del anti-duplicado, replicando el comportamiento legacy documentado.

La elección debe quedar **auditada** en el expediente (qué modo usó el posting).

## Consecuencias

- Paridad estricta puede permitir duplicados FM como el VB6 (*confirmado por código*).
- Modo por defecto Synap mejora calidad de datos pero **diverge** del legacy si FM duplicado era «tolerado».

## Trazabilidad

- Comportamiento VB6: *confirmado por auditoría*.
- Default Synap: *decisión nueva de producto*; ya anticipado en [auditoria_facturas_compras_integracion_django.md](../auditoria_facturas_compras_integracion_django.md).

## Tests obligatorios

- Caso FM duplicado en modo estricto vs modo paridad ([test_cases.md](../test_cases.md)).
