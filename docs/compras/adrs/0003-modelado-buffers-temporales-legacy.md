# ADR-0003: Modelado de buffers temporales del legacy (`cuerpostockp`, etc.)

**Estado:** Aceptado (especificación).  
**Fecha:** 2026-03-24

## Contexto

*Confirmado por auditoría:* el VB6 usa tablas buffer por usuario, p. ej. `cuerpostockp`, `percep_prov_temp`, `serie_entrada_temp`, `en_vale_factura_temp`, ligadas a `Principal.idUsuario` ([auditoria_facturas_compras_resumen.md](../auditoria_facturas_compras_resumen.md), [auditoria_facturas_compras_sql.md](../auditoria_facturas_compras_sql.md)).

El PWA no ejecuta el formulario PFactura; construye datos desde OCR y edición.

## Decisión

1. **No** depender de las tablas temp legacy durante el borrador en Synap.
2. Modelar **líneas, percepciones, series y vínculos a vales** como entidades en la DB interna del expediente ([domain_model.md](../domain_model.md)).
3. En el momento del posting, el **LegacyPostingCommand** materializa directamente las tablas **finales** (`stock`, `percep_prov`, `serie_entrada`, `en_vale_factura`, etc.) en el orden de la auditoría.

## Consecuencias

- Evita colisiones con usuarios VB6 que compartan `cuerpostockp` por `idUsuario`.
- Requiere mapeo explícito expediente → campos destino (Anexo A de [auditoria_facturas_compras_tablas_campos.md](../auditoria_facturas_compras_tablas_campos.md)).
- Si en el futuro se necesitara interoperar con VB6 en el mismo buffer, sería un ADR nuevo.

## Trazabilidad

- Uso de temps en VB6: *confirmado por auditoría*.
- Sustitución por modelo Synap: *decisión nueva de producto*.

## Riesgos

- `en_vale_factura_temp` y limpieza en VB6 quedó *pendiente* en [auditoria_facturas_compras_pendientes_dudas.md](../auditoria_facturas_compras_pendientes_dudas.md) §3 — Synap no depende de esa temp.
