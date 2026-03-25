# ADR-0001: Momento de escritura en MySQL legacy (AdministraNET)

**Estado:** Aceptado (especificación).  
**Fecha:** 2026-03-24

## Contexto

La auditoría del VB6 describe `Guardar` en `PFactura.frm` que persiste de inmediato en MySQL al confirmar el comprobante en el formulario legacy ([auditoria_facturas_compras_flujo_completo.md](../auditoria_facturas_compras_flujo_completo.md)).

El nuevo producto introduce **expedientes en borrador** con OCR y revisión humana ([product_requirements.md](../product_requirements.md)).

## Decisión

**Escribir en las tablas legacy AdministraNET únicamente cuando el expediente Synap pasa a estado `aprobado` y el posting legacy completa con éxito.**

Hasta entonces, toda la información reside en la base de datos interna del workflow (Synap).

## Consecuencias

- Positivas: no contamina `codmov`, `cuentaproveedor`, `stock` con borradores; separación clara ERP vs captura.
- Negativas: no hay «vista previa» en listados VB6 del comprobante hasta aprobar; el analista usa solo Synap para el borrador.

## Trazabilidad

- *Decisión nueva de producto* (no existe en VB6).
- Comportamiento a replicar **tras** aprobación: *confirmado por auditoría* (`Guardar`).

## Alternativas rechazadas

- **Escribir en tablas temp legacy (`cuerpostockp`) desde Synap:** acopla el PWA al esquema de buffers por `Principal.idUsuario` y complica multi-dispositivo (ADR-0003).
