# Armado: stock de componentes y flujo OPT/OPP

## Qué movimientos genera MPR

| Fase | Qué se mueve | Tablas afectadas |
|------|--------------|------------------|
| **OPT (liberar)** | **Componentes** (explosión BOM de los packs) → depósito de **Producción** | `movimiento_stock`, `stock`, `stock_deposito`: entradas de los **componentes** en el depósito de producción. |
| **OPP (parte de producción)** | **Componentes** desde Producción → depósitos destino (Semi Elaborado, Scrap, 2ª Selección) | `movimiento_stock`, `stock`, `stock_deposito`: salida en origen y entrada en destino por **componente**. |
| **Armado** | **Componentes** (BOM) salen de Semi elaborado; **pack** entra en Terminado | `movimiento_stock`, `stock`, `stock_deposito`: salidas de componentes, entrada del pack. |

**Conclusión:** OPT y OPP generan movimientos de **artículos componentes** (explosión de la receta BOM de cada pack). La demanda y el pendiente en `lista_produccion_agrupada` siguen expresados en **unidades pack**; lo que se escribe en `stock` y `stock_deposito` son los componentes.

## Por qué «Máx. armable» puede ser «Sin stock»

En el paso **Armado** (paso 4 del asistente o pantalla **Armado OPT** desde el detalle de la OPT), el sistema calcula **Máx. armable** a partir del **stock de los componentes de la receta (BOM)** en el depósito configurado como **Semi elaborado** (`deposito.tipo_mpr = 'SemiElaborado'`).

**Operario por pack (OPA):** en el asistente (paso 4) y en **Armado OPT** (`mpr/armado_opt.html`), cada fila con **Cant. a armar** mayor a cero debe tener **Operario** seleccionado (`operario_armado_{id_articulo}`), igual que en OPT por línea (`id_operario_opt`) y en OPP por componente. Se persiste con `ejecutar_armado(..., id_operario=...)` en `movimiento_stock` / `lista_produccion_historico`.

- Si los **componentes** no tienen saldo en ese depósito, **Máx. armable** será 0 y se mostrará «Sin stock».
- El stock de componentes en Semi elaborado proviene sobre todo de los **OPP** que movieron componentes desde Producción a Semi Elaborado (y opcionalmente de compras o transferencias).

## De dónde sale el stock de componentes en Semi elaborado

El stock de los **componentes** en el depósito Semi elaborado se genera principalmente al **registrar OPP**: el usuario indica cuántas unidades pack envía a cada depósito destino y el sistema explota a componentes vía BOM y mueve esos componentes desde Producción a Semi Elaborado (u otros destinos). Además puede existir stock de componentes por:

1. **Compras:** ingreso de insumos/componentes al depósito Semi elaborado (o a otro depósito y luego transferencia).
2. **Transferencias:** movimientos de stock que lleven los componentes al depósito configurado como Semi elaborado.

Si no se han registrado OPP que envíen componentes a Semi Elaborado (ni compras/transferencias), es esperado que en Armado aparezca «Sin stock» hasta que se distribuyan los componentes liberados en la OPT mediante OPP.

## Resumen

- **OPT (liberar):** mueve **componentes** (BOM) al depósito Producción. La cantidad se expresa en pack en la UI; internamente se explota a componentes.
- **OPP:** mueve **componentes** desde Producción a los depósitos destino (Semi Elaborado, Scrap, 2ª Selección). El usuario indica cantidades en pack; el sistema explota a componentes y valida stock en Producción.
- **Armado:** consume **componentes** desde Semi elaborado y genera el **pack** en Terminado. El stock de componentes en Semi elaborado viene en gran parte de los OPP.
