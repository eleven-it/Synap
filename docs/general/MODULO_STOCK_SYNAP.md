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
2. Al confirmar: una sola transacción MySQL: UPDATE codmov, SELECT talonarios FOR UPDATE, INSERT movimiento_stock, por cada renglón INSERT stock y UPDATE/INSERT stock_deposito, DELETE temporales del usuario.
3. En error: rollback total (incluido codmov y talonarios).

Véase `core/services/administranet_stock.py` y plan de migración (Fase 1).

## Limpieza de temporales

Comando: `python manage.py limpiar_temporales_stock <base_empresa> [--horas 0]`. Ejecutar por cron o al cerrar sesión para evitar registros huérfanos en `cuerpostock_mstock`.

## Pack x 6 / Pack x 12 pares (producción / MPR)

En AdministraNET los packs por 6 o 12 pares **no son valores fijos**: se modelan con **multiplicador_comp** / **multiplicador_vta** y **tipo_unidad** (Unidad, Display, Bulto). Si la unidad base es el par, un artículo con `multiplicador_comp = 6` representa "bulto de 6 pares"; con 12, "bulto de 12 pares". La UI de CargaMovStock y Lista_Pedidos_OPT usa el combo tipo_unidad_bulto cuando `utiliza_bulto_cerrado` o `utiliza_display` = Si. Para el **módulo MPR** (OPT, Armado, OPP) debe reutilizarse la misma lógica: ver [ANALISIS_MPR_PROPUESTA_MVP.md](ANALISIS_MPR_PROPUESTA_MVP.md) sección 3.2.

## Documentación relacionada

- [ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md](ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md): formularios VB6, tablas, riesgos.
- [ESQUEMA_TABLAS_STOCK_MIGRACION.md](ESQUEMA_TABLAS_STOCK_MIGRACION.md): tablas, permisos e índices recomendados.
- [BUSQUEDA_PREDICTIVA_ARTICULO_MOVIMIENTO_STOCK.md](BUSQUEDA_PREDICTIVA_ARTICULO_MOVIMIENTO_STOCK.md): búsqueda predictiva con precios, stock por depósito y lote en ingreso de renglón.
