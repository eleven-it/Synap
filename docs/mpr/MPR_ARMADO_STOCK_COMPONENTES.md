# Armado: stock de componentes y flujo OPT/OPP

**Pack vs componente en tablas:** [ARTICULO_PACK_COMPONENTE_MPR.md](ARTICULO_PACK_COMPONENTE_MPR.md). Manual usuario: [MANUAL_USUARIO_MPR.md](MANUAL_USUARIO_MPR.md) §4.

## Qué movimientos genera MPR

| Fase | Qué se mueve | Tablas afectadas |
|------|--------------|------------------|
| **OPT (liberar)** | **Componentes** (explosión BOM de los packs) → depósito de **Producción** | `movimiento_stock`, `stock`, `stock_deposito`: entradas de los **componentes** en el depósito de producción. |
| **OPP (parte de producción)** | **Componentes** desde Producción → depósitos destino (Semi Elaborado, Scrap, 2ª Selección) | `movimiento_stock`, `stock`, `stock_deposito`: salida en origen y entrada en destino por **componente**. |
| **Armado** | **Componentes** (BOM) salen de Semi elaborado; **pack** entra en Terminado | `movimiento_stock`, `stock`, `stock_deposito`: salidas de componentes, entrada del pack. |

**Conclusión:** OPT y OPP generan movimientos de **artículos componentes** (explosión de la receta BOM de cada pack). La demanda y el pendiente en `lista_produccion_agrupada` siguen expresados en **unidades pack**; lo que se escribe en `stock` y `stock_deposito` son los componentes.

## Tablero Armado 1ra — cuándo aparece un pack (05/08/2026)

En `/mpr/armado/?modo=1ra&vista=tablero`, un pack **Terminado + BOM** se lista si **Máx. armable > 0** (hay stock de componentes en Semi elaborado para armar al menos un pack). **No** exige demanda PED ni `resta_armar > 0`: un pack con stock terminado cubierto y sin pedidos abiertos sigue visible si Semi permite armar. El orden prioriza mayor `resta_armar` y luego mayor `max_armable`. Ver [DISENO_ARMADO_TABLERO_PCP.md](DISENO_ARMADO_TABLERO_PCP.md).

## Por qué «Máx. armable» puede ser «Sin stock»

En el paso **Armado** (paso 4 del asistente o pantalla **Armado OPT** desde el detalle de la OPT), el sistema calcula **Máx. armable** a partir del **stock de los componentes de la receta (BOM)** en el depósito configurado como **Semi elaborado** (`deposito.tipo_mpr = 'SemiElaborado'`).

**Operario en armado (OPA):** no se solicita en la UI de Armado 1ra/2da ni en vistas legacy OPT. El operario fabricante se registra en **parte de producción** y **OPP**; el armado solo mueve stock pack/componentes. Si en el futuro se indica operario, se persiste opcionalmente en `id_operario_opt` vía `ejecutar_armado(..., id_operario=...)`.

- Si los **componentes** no tienen saldo en ese depósito, **Máx. armable** será 0 y se mostrará «Sin stock».
- En **Armado OPT** (`/mpr/opt/<id>/armado/`) la columna **Máx. armable** muestra **docenas enteras** del pack (packs ÷ `cantidad_promedio_bulto`, divisor 12 si no hay bulto) y debajo la cantidad en **packs**; no hay tooltip por depósito ni unidades sueltas, porque solo se arman packs completos.
- El stock de componentes en Semi elaborado proviene sobre todo de los **OPP** que movieron componentes desde Producción a Semi Elaborado (y opcionalmente de compras o transferencias).

## De dónde sale el stock de componentes en Semi elaborado

El stock de los **componentes** en el depósito Semi elaborado se genera principalmente al **registrar OPP**: el usuario indica cuántas unidades pack envía a cada depósito destino y el sistema explota a componentes vía BOM y mueve esos componentes desde Producción a Semi Elaborado (u otros destinos). Además puede existir stock de componentes por:

1. **Compras:** ingreso de insumos/componentes al depósito Semi elaborado (o a otro depósito y luego transferencia).
2. **Transferencias:** movimientos de stock que lleven los componentes al depósito configurado como Semi elaborado.

Si no se han registrado OPP que envíen componentes a Semi Elaborado (ni compras/transferencias), es esperado que en Armado aparezca «Sin stock» hasta que se distribuyan los componentes liberados en la OPT mediante OPP.

## Resumen

- **OPT (liberar):** mueve **componentes** (BOM) al depósito Producción. La cantidad se expresa en pack en la UI; internamente se explota a componentes.
- **OPP:** mueve **componentes** desde Producción a los depósitos destino (Semi Elaborado, Scrap, 2ª Selección). El usuario indica cantidades en pack; el sistema explota a componentes y valida stock en Producción.
- **Armado (BOM):** consume **componentes** desde Semi elaborado y genera el **pack** en Terminado. El stock de componentes en Semi elaborado viene en gran parte de los OPP.
- **Armado surtido:** composición **libre** por operación desde **2.ª selección** (u otro origen) hacia Terminado; sin BOM. El **pack** se habilita en `MprArticuloArmadoSurtido` (no en `ensamblado`). Servicio `ejecutar_armado_surtido` (consumo FIFO por lote si `articulo.Lote=Si`, igual que armado BOM). Pantalla `/mpr/armado-surtido/`; enlace desde detalle OPT en curso. Ver [SDD_ARMADO_SURTIDO_MVP.md](SDD_ARMADO_SURTIDO_MVP.md).

## Identificación pack / componente (resumen)

| Flujo | Pack | Componente |
|-------|------|--------------|
| BOM / armado receta | `articulo.ensamblado='Si'`, `id_en_abm` | `en_abm_formula` |
| OPT / OPP / demanda | `lista_produccion_agrupada.id_articulo` | Explosión BOM |
| Armado surtido | `MprArticuloArmadoSurtido` | Composición en pantalla → `MprArmadoSurtidoLinea` |

Detalle: [ARTICULO_PACK_COMPONENTE_MPR.md](ARTICULO_PACK_COMPONENTE_MPR.md).
