# Módulo Stock (Synap) – Resumen

Módulo de movimientos de stock alineado con AdministraNET VB6. Mismas tablas y formato en MySQL para operación en paralelo.

## Menús

- **Stock** (permiso `stock.ver`): Ingreso Mov. Stock, Remito de Compra/Venta, Pedido interno, Inventario, Consulta Ficha de Stock, Consultas y Anulaciones, Informes.
- **Archivo > Parámetros:** Referencia de movimiento de stock (`stock.ref_movstock`).

## Permisos

| key_permiso | Uso |
|-------------|-----|
| stock.ver | Ver menú Stock |
| stock.crear_movimiento | Alta de movimiento (Ingreso Mov. Stock) |
| stock.consultas | Consultas y anulaciones, consulta ficha, detalle, PDF |
| stock.ref_movstock | ABM referencias de movimiento |
| stock.informes | Informes de stock |

El acceso a "Ingreso Mov. Stock" se otorga si el puesto tiene `stock.crear_movimiento` en **permiso_sistema_puesto** o la Clavemenu `keyCompStock` en la tabla **permisos** (mapeo automático). El comportamiento (depósitos, referencia, motivos) se lee de **permisos_sistema**. Ver [PERMISOS_STOCK_SYNAP_VS_VB6.md](PERMISOS_STOCK_SYNAP_VS_VB6.md).

El backend revalida permisos de puesto (cambia_deposito, acceso_ref_movstock, acceso_motivo_movstock, deposito_usr) en cada alta.

## URLs principales

- Alta movimiento: `/stock/ingreso-movimiento/`
- Listado movimientos: `/stock/movimientos/`
- Detalle: `/stock/movimientos/<codigo_movimiento>/`
- PDF comprobante: `/stock/movimientos/<codigo_movimiento>/pdf/`
- Referencias: `/stock/referencias/`, `/stock/referencias/nueva/`, `/stock/referencias/<id>/editar/`
- Consulta ficha: `/stock/consulta-ficha/`
- Consulta avanzada: `/stock/consulta-avanzada/`

## API

- **POST** `/core/api/movimiento-stock/`: alta de movimiento (cabecera + renglones). Requiere permiso `stock.crear_movimiento`. Respuesta: `codigo_movimiento`, `nro_comprobante`, `mensaje`.

## Flujo de alta y mitigación de riesgos

1. Renglones en temporal `cuerpostock_mstock` (por usuario).
2. **Verificación de esquema:** antes de abrir transacción, se comprueba que existan las tablas y columnas obligatorias (`verificar_esquema_ingreso_movimiento`). Si falta alguna tabla o campo, no se guarda ningún dato y se devuelve un error estructurado para mostrar en modal.
3. Al confirmar: una sola transacción MySQL: UPDATE codmov, SELECT talonarios FOR UPDATE, INSERT movimiento_stock, por cada renglón INSERT stock y UPDATE/INSERT stock_deposito, DELETE temporales del usuario.
4. En error: rollback total (incluido codmov y talonarios).

Véase `core/services/administranet_stock.py` y plan de migración (Fase 1).

### Error de esquema (tablas o campos faltantes)

Si la base de datos no tiene la estructura esperada (tabla o columna inexistente), el alta **no se ejecuta** y la API responde con `schema_error: true` y `detalle` (lista de `{tabla, campo, mensaje}`). La pantalla de ingreso muestra un **modal** con el mensaje en lenguaje natural y el detalle (tabla y campo faltante) para que el usuario o el administrador puedan corregir la base sin perder datos.

## Limpieza de temporales

Comando: `python manage.py limpiar_temporales_stock <base_empresa> [--horas 0]`. Ejecutar por cron o al cerrar sesión para evitar registros huérfanos en `cuerpostock_mstock`.

## Pack x 6 / Pack x 12 pares (producción / MPR)

En AdministraNET los packs por 6 o 12 pares **no son valores fijos**: se modelan con **multiplicador_comp** / **multiplicador_vta** y **tipo_unidad** (Unidad, Display, Bulto). Si la unidad base es el par, un artículo con `multiplicador_comp = 6` representa "bulto de 6 pares"; con 12, "bulto de 12 pares". La UI de CargaMovStock y Lista_Pedidos_OPT usa el combo tipo_unidad_bulto cuando `utiliza_bulto_cerrado` o `utiliza_display` = Si. Para el **módulo MPR** (OPT, Armado, OPP) debe reutilizarse la misma lógica: ver [ANALISIS_MPR_PROPUESTA_MVP.md](ANALISIS_MPR_PROPUESTA_MVP.md) sección 3.2.

## Documentación relacionada

- [ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md](ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md): formularios VB6, tablas, riesgos.
- [ESQUEMA_TABLAS_STOCK_MIGRACION.md](ESQUEMA_TABLAS_STOCK_MIGRACION.md): tablas, permisos e índices recomendados.
- [BUSQUEDA_PREDICTIVA_ARTICULO_MOVIMIENTO_STOCK.md](BUSQUEDA_PREDICTIVA_ARTICULO_MOVIMIENTO_STOCK.md): búsqueda predictiva con precios, stock por depósito y lote en ingreso de renglón.
