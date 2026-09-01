# 02 — Document Artifacts

**Estado:** COMPLETE

| Artifact | Producer | Consumer | Format | Storage |
|----------|----------|----------|--------|---------|
| Pedido PDF | `ecom/pedido_comprobante_pdf.py` | Usuario ventas | PDF | HTTP response |
| Lista precios PDF | `ecom/lista_precio_pdf.py` | Comercial | PDF A3 | HTTP |
| OPT comprobante PDF | `mpr/views.py` | Producción | PDF | HTTP |
| Movimiento stock PDF | `stock/views.py` | Almacén | PDF | HTTP |
| SIA cycle report | `sia/services.py` | RRHH | PDF/XLSX | HTTP |
| Ticket TPV | `ticket_print.html` | Cliente | HTML print 80mm | Browser print |
| Manual usuario HTML | `*/manuales/manual_usuario_*.html` | Usuario | HTML | static |
| Expediente documento | `factura_compra_captura` | Compras | PDF/image | filesystem + PG |
| Backup artifacts | `core/backup/` | Admin | pg_dump, sql | configured storage |

**Permissions:** per module `@tiene_permiso` on generating views.
