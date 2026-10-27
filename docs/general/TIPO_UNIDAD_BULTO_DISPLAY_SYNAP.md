# Tipo unidad / Bulto / Display en Ingreso Mov. Stock (Synap)

**Objetivo:** Permitir elegir por renglón la presentación (Unidad, Display, Bulto) en cualquier motivo de movimiento de stock.

## Configuración (tabla `configuracion`)

- **utiliza_bulto_cerrado** y **utiliza_display:** se reciben para compatibilidad con otros circuitos; no restringen las opciones del movimiento de stock.
- **tipo_unidad_defecto:** (opcional) Valor por defecto al agregar renglón: `'Unidad'`, `'Display'` o `'Bulto'`. Si la columna no existe en la base, el backend devuelve `'Unidad'`.

## Visibilidad en la UI

- La columna **Presentación** y el selector en la fila de búsqueda se muestran al elegir cualquier motivo.
- El selector ofrece Unidad, Display y Bulto. Los artículos con lote o serie usan únicamente Unidad.

## Convención de interfaz para nuevos circuitos

- Presentación, embalaje y modo de lectura usan un `<select>` nativo, con etiqueta asociada y ancho completo en móvil. Así Android ofrece su selector habitual.
- Mantener borde gris, fondo blanco, esquinas redondeadas y variante oscura como en Pedido interno. La apariencia no debe cambiar el significado ni los valores de cada opción.
- Armado de cajas conserva Display y Unidad; Pedido interno e Ingreso Mov. Stock ofrecen también Bulto cuando corresponde al circuito.

## Flujo

1. **Datos iniciales** (`api_ingreso_datos_iniciales`): el front recibe `utiliza_bulto_cerrado`, `utiliza_display`, `tipo_unidad_defecto`.
2. **Fila de búsqueda:** el select de tipo_unidad tiene valor por defecto `tipo_unidad_defecto`; al seleccionar un artículo se asigna `filaBusqueda.tipo_unidad = tipo_unidad_defecto`.
3. **Al agregar renglón:** se envía `tipo_unidad: filaBusqueda.tipo_unidad || tipo_unidad_defecto` en el body del POST.
4. **Por renglón:** la columna Embalaje muestra un select con `x-model="r.tipo_unidad"` y `@change="actualizarMovimientoCantidad(r)"` para persistir el cambio.

## Backend

- **Servicio:** `core.services.administranet_stock.get_config_unidad_bulto_display(base_empresa)` devuelve el dict con las tres claves; si `tipo_unidad_defecto` no existe en la tabla, se devuelve `'Unidad'`.
- **Alta/actualización de renglón:** ya se persiste `tipo_unidad` en `cuerpostock_mstock` y se devuelve en `listar_renglones_temporales`.
- **Confirmación:** `factor_presentacion` verifica que el artículo tenga la equivalencia elegida y guarda stock en unidades base. El motivo no restringe Display ni Bulto.
- **Ajuste por saldo deseado:** convierte la diferencia de unidades a presentaciones completas; si no es divisible, se debe elegir Unidad.

## Referencia

- Plan: Fase 3 tipo_unidad_bulto (análisis artefactos VB6 stock).
- VB6: CargaMovStock combo tipo_unidad_bulto / unidad_art_peso; opciones según configuración.
