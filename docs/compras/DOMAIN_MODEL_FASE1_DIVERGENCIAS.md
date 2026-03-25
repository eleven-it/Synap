# Divergencias implementación Fase 1 vs `domain_model.md`

**Alcance:** módulos `factura_compra_captura` y `factura_compra_posting` (Fase 1).  
**Fuente:** [domain_model.md](domain_model.md).

## Alineado

- Agregado **ExpedienteFacturaCompra** como aggregate root con UUID.
- **LineaExpedienteCompra** con `orden`, `id_art_legacy`, cantidades/precios y referencias OC/remito opcionales (mapeo futuro a Anexo A).
- **Origen** del comprobante como enum `MANUAL` / `REMITO` / `OC` / `VALE` (`OrigenDatos`).
- Ciclo de estados cubre el diagrama §5: `borrador` → `ocr_completado` → `en_revision` → `listo_para_aprobar` → `aprobacion_solicitada` → `aprobado` / `rechazado` / `error_posting` (este último sin transición entrante en Fase 1).
- **Empresa** como FK a `core.Empresa` (multi-tenant Synap).
- Auditoría interna persistida como **EventoAuditoriaInterno** (equivalente funcional a «AuditLogInterno» del dominio).

## Diferencias intencionales (Fase 1)

| Tema | `domain_model.md` | Implementación Fase 1 |
|------|-------------------|------------------------|
| Documento fuente / OCR | `DocumentoFuente`, `ExtraccionOCR` | **No modelados** (Fase 2 según [phase_1_bootstrap_plan.md](phase_1_bootstrap_plan.md)). |
| Percepciones | `PercepcionExpediente` | **No modelado** (posting futuro). |
| Vale vinculado | `ValeVinculado` opcional | Solo cabecera `origen_datos=VALE`; sin entidad de vínculos. |
| Nombre auditoría | «AuditLogInterno» | Modelo **`EventoAuditoriaInterno`** (mismo rol). |
| Value objects | `Money`, `NumeroComprobanteFormateado`, etc. | **Decimales en modelo** (`DecimalField`); VOs explícitos en código no introducidos aún. |
| Sucursal | Contexto operativo legacy | Campo opcional **`sucursal_codigo_legacy`** (entero); no FK a `core.Branch` en Fase 1. |
| Servicios §6 | `crear_desde_captura`, `OCRPipeline`, etc. | **`ExpedienteService.crear`**, **`actualizar`**, **`aplicar_transicion`** (captura/OCR en Fase 2). |
| Resultado posting | `LegacyComprobanteCompraPosted` | Campos en expediente: `legacy_codigo_movimiento`, `legacy_nro_comprobante`, `posting_status` (suficiente para stub). |

## Sin integración legacy

- No ORM ni SQL sobre MySQL AdministraNET; posting solo vía **`FakeLegacyPostingAdapter`** / `noop` ([posting_contract.md](posting_contract.md) resultados mínimos).

## Revisión en Fase 2+

- Añadir `DocumentoFuente` y pipeline OCR.
- Valorar FK sucursal Synap vs código legacy.
- Modelar percepciones y vínculos vale cuando el mapper a `LegacyPostingCommand` lo exija.
