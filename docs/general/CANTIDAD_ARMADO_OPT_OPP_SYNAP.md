# Cantidad armado (OPT/OPP) en Ingreso Mov. Stock (Synap)

**Objetivo:** Permitir elegir si la cantidad a cargar en movimientos de Parte producción (OPT/OPP) se ingresa en **Unidad** o en **Armado**, alineado con CargaMovStock VB6 (cantidad_armado, Frame_Datos_OPT).

## Configuración

- **pedidos_parte_produccion:** Se lee de `configuracion.pedidos_parte_produccion` ('Si' / 'No'). Si la columna no existe, el backend devuelve 'No'. Cuando es 'Si', se muestran los controles OPT/OPP, incluido el select Cantidad armado para motivo **Parte producción** (código 12).

## Visibilidad

- El select **Cantidad armado** solo se muestra cuando **mostrarCantidadArmado** es verdadero: `pedidos_parte_produccion === 'Si'` **y** `motivo_movimiento === 12` (Parte producción).
- Opciones: **Unidad** (valor por defecto) y **Armado**.

## Flujo

1. **Datos iniciales** (`api_ingreso_datos_iniciales`): el front recibe `pedidos_parte_produccion`.
2. En **Datos del movimiento**, dentro del bloque OPT (Operario, Máquina), cuando aplica se muestra el label "Cantidad armado" y un select Unidad / Armado, con texto de ayuda: "Indica si la cantidad a cargar es en unidades o en armados (OPT/OPP)."
3. El valor se guarda en **cabecera.cantidad_armado** ('Unidad' o 'Armado') y se envía al confirmar el movimiento en el objeto cabecera.
4. **En VB6:** al agregar renglón con pedidos_parte_produccion = Si se usa cantidad_armado para calcular cantidad_armada_opt y Cantidad según la fórmula (cantidad_formula desde en_abm_formula). En Synap la conversión automática por fórmula (ensamble_desarme) no está implementada; el campo sirve para coherencia de datos y para uso futuro cuando se implemente la lógica de fórmulas.

## Backend

- **Servicio:** `core.services.administranet_stock.get_pedidos_parte_produccion(base_empresa)` devuelve 'Si' o 'No'.
- **Confirmar movimiento:** la cabecera enviada incluye `cantidad_armado`; el backend no persiste este valor en `movimiento_stock` (no hay columna en la tabla). Se puede extender más adelante si se agrega persistencia o si se usa al grabar renglones con cantidad_armada_opt.

## Referencia

- VB6: CargaMovStock Form_Load (cantidad_armado.Visible cuando pedidos_parte_produccion = Si), Motivo_Click (Frame_Datos_OPT para ListIndex 11 = Parte producción), cantidad_armado ListIndex 0 = Unidad / 1 = Armado; AgregarRenglon con cantidad_formula y cantidad_armada_opt.
- Fase 5: cantidad_armado (OPT/OPP).
