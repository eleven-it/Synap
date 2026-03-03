# Inventario: botón Aceptar / Confirmar movimiento de stock

Referencia del proceso completo de guardado al confirmar un movimiento de stock (paridad con CargaMovStock VB6). Tipos de dato según [TIPOS_DATOS_ADMINISTRANET.md](TIPOS_DATOS_ADMINISTRANET.md).

## Estado de fases de migración

| Fase | Descripción | Estado |
|------|-------------|--------|
| 1 | Normalización de tipos (guardado con `administranet_types`) | **Hecho** |
| 2 | Transferencia doble fila (stock + stock_deposito origen y destino) | **Hecho** |
| 3 | Cliente/Vendedor condicionados por motivo (UI) | Pendiente |
| 4 | Campo maquina / cantidad_armado (definición y persistencia) | Pendiente |
| 5 | Asiento contable | Pendiente |
| 6 | Impresión comprobante MSTOCK | **Hecho** |
| 7 | Verificación de schema y pruebas de integración | Pendiente |
| 8 | Documentación final (este doc) | En curso |

## Implementación del guardado

- **Servicio:** `core/services/administranet_stock.py` → `alta_movimiento()`.
- **API:** `stock/api_views.py` → `api_ingreso_confirmar` (POST con `cabecera`; renglones desde `listar_renglones_temporales`).

### Normalización de tipos (Fase 1)

En `alta_movimiento` se usa de forma sistemática:

- `to_int_or_none`: id_pv, deposito_origen, deposito_destino, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, IDArt, CodDeposito, CodViajante, id_lote, codmov_movstock, codmov_pedi.
- `to_date_or_none`: fecha (cabecera), vto_lote (alta de lote).
- `str_or_default`: detalle, CodigoArticulo, Descripcion.
- `to_decimal_or_none`: cant_desarme, Cantidad, entrada, salida.

### Transferencia doble fila (Fase 2)

Para **motivo 6 (Transferencia)**:

- Por cada renglón se escriben **dos filas** en `stock`: una de salida en depósito origen (Orden = idx*2+1) y una de entrada en depósito destino (Orden = idx*2+2).
- Se actualiza `stock_deposito` en **origen** (resta) y en **destino** (suma).
- Si el renglón tiene lote: salida se descuenta en origen (lote_stock/lote); entrada en destino puede crear/actualizar lote en depósito destino.

## Tablas que se escriben al confirmar

| Tabla | Operación |
|-------|-----------|
| codmov | UPDATE CodigoMovimiento |
| talonarios | UPDATE Nro (MSTOCK, id_punto_venta) |
| movimiento_stock | INSERT cabecera |
| stock | INSERT una o dos filas por renglón (dos si motivo 6); incluye **saldo** (saldo en depósito tras el movimiento) para que el informe de AdministraNET muestre la columna Saldo correcta |
| stock_deposito | UPDATE o INSERT por depósito afectado (origen y, si transfer, destino) |
| lote / lote_stock | UPDATE o INSERT según entrada/salida con lote |
| movstock_pedi | INSERT por renglón con nro_pedi |
| serie_entrada / serie_movimiento | Desde temp si hay artículos seriados |
| cuerpostock_mstock, serie_entrada_temp, serie_salida_temp | DELETE (limpieza) |

### Alineación con AdministraNET (nro comprobante, detalle, id_pv)

- **Nro. comprobante:** Se guarda con el mismo formato que AdministraNET: `PV-Nro` (ej. `0001-00000288`), donde PV es `id_punto_venta` en 4 dígitos y Nro es el número del talonario MSTOCK en 8 dígitos. Se usa el talonario según `cabecera.id_pv` o `id_punto_venta` (por defecto ver abajo).
- **Detalle:** Si el motivo es **Transferencia (6)** y el usuario no escribe observaciones, se completa automáticamente con "Transferencia de {nombre dep. origen} a {nombre dep. destino}", como en AdministraNET. En el resto de los casos se persiste el texto del campo Observaciones.
- **id_usuario:** Se toma de la sesión (`ctx["id_usuario"]`); no se envía desde el front.
- **id_pv:** Se persiste en `movimiento_stock.id_pv` cuando la tabla tiene la columna (paridad con AdministraNET).

**Cómo se elige el punto de venta en AdministraNET:** En AdministraNET el PV del movimiento **no se selecciona en el formulario** de CargaMovStock. El punto de venta que realiza el movimiento es el **asignado al usuario** en Modificar usuario (CargaUsuario): campo **Punto de Venta** (`usuarios.id_punto_venta`). Ese mismo PV se usa en TPV, Caja y numeración de comprobantes (talonarios MSTOCK por `id_punto_venta`). **En Synap:** Si el front no envía `id_pv` ni `id_punto_venta` en la cabecera, se usa el PV de la sesión (`request.session["user"]["id_punto_venta"]`, cargado en el login desde `usuarios.id_punto_venta`); si no hay, se usa 1. El front puede seguir enviando `id_pv` para casos especiales (p. ej. pruebas o flujos futuros).

### Comprobante PDF (Fase 6)

El enlace "Descargar comprobante PDF" usa la **plantilla corporativa** de Synap: encabezado con datos de empresa (razón social, domicilio, CUIT) y logo si existe en el modelo Django `Empresa`, pie de página "Synap · Generado el DD/MM/AAAA HH:MM". Los datos de empresa se obtienen de forma dinámica desde `obtener_empresa(base_empresa)` (AdministraNET). Base reutilizable para todos los PDF de reportes: **`core/report_pdf.py`** (`get_empresa_para_reporte`, `draw_report_header`, `draw_report_footer`).

## Documentación relacionada

- [ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md](ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md): eventos VB6 y paridad Synap.
- [TIPOS_DATOS_ADMINISTRANET.md](TIPOS_DATOS_ADMINISTRANET.md): criterios de tipos para MySQL AdministraNET.
