# Checklist de compatibilidad legacy por comprobante

Cada comprobante que escriba en tablas MySQL administraNET debe tener una ficha que responda a este checklist y documente tablas, orden de escritura y validaciones. Crear `COMPAT_LEGACY_<TIPO>.md` al implementar la escritura completa (ej. COMPAT_LEGACY_ORDEN_PAGO.md, COMPAT_LEGACY_FACTURA_COMPRA.md).

## Checklist estándar

1. **Tablas:** ¿Inserta/actualiza exactamente las mismas tablas que VB6? (listar tablas y operación C/R/U/D.)
2. **Orden:** ¿Mismo orden lógico que VB6? (cabecera → detalle → numeración → op_factura/saldos.)
3. **Defaults:** ¿Mismos valores vacío/cero y defaults (vía `core.utils.administranet_types`)?
4. **Numeradores y estados:** ¿Misma tabla/SP o lógica de numeración? ¿Mismos códigos de estado?
5. **op_factura:** ¿Mismo impacto en saldo, estado, anulado?
6. **Visibilidad VB6:** ¿Comprobante queda visible y consistente al abrirlo desde VB6 justo después de guardar desde Django?

## Estado por comprobante

| Comprobante | Servicio legacy_db | Escritura implementada | Ficha COMPAT_LEGACY_*.md |
|-------------|--------------------|------------------------|---------------------------|
| Orden de Pago (a cuenta) | orden_pago_service | Stub (lock sí; confirmar pendiente) | Pendiente |
| Orden de Pago (por imputación) | orden_pago_service | Pendiente | Pendiente |
| Factura de Compra (FA/FB/FC) | factura_compra_service | Stub | Pendiente |
| Imputación comprobantes a OP | imputaciones_service | Stub | Pendiente |
| Desimputación | imputaciones_service | Stub | Pendiente |

## Referencia

- [CONVIVENCIA_VB6_DJANGO_LEGACY_DB.md](CONVIVENCIA_VB6_DJANGO_LEGACY_DB.md)
- [INVENTARIO_INGENIERIA_INVERSA_CARGA_COMPROBANTES_P.md](INVENTARIO_INGENIERIA_INVERSA_CARGA_COMPROBANTES_P.md)
