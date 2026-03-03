# Tipo unidad / Bulto / Display en Ingreso Mov. Stock (Synap)

**Objetivo:** Permitir elegir por renglón la unidad de medida (Unidad, Display, Bulto) cuando la empresa usa bulto cerrado o display, alineado con CargaMovStock VB6.

## Configuración (tabla `configuracion`)

- **utiliza_bulto_cerrado:** `'Si'` / `'No'`. Si es `'Si'`, se ofrece la opción "Bulto" en el select de embalaje.
- **utiliza_display:** `'Si'` / `'No'`. Si es `'Si'`, se ofrece la opción "Display" en el select de embalaje.
- **tipo_unidad_defecto:** (opcional) Valor por defecto al agregar renglón: `'Unidad'`, `'Display'` o `'Bulto'`. Si la columna no existe en la base, el backend devuelve `'Unidad'`.

## Visibilidad en la UI

- La columna **Embalaje** (y el select en la fila de búsqueda) solo se muestran cuando **mostrarEmbalaje** es verdadero: `utiliza_bulto_cerrado === 'Si'` **o** `utiliza_display === 'Si'`.
- Opciones del select: siempre "Unidad"; "Display" solo si `utiliza_display === 'Si'`; "Bulto" solo si `utiliza_bulto_cerrado === 'Si'`.

## Flujo

1. **Datos iniciales** (`api_ingreso_datos_iniciales`): el front recibe `utiliza_bulto_cerrado`, `utiliza_display`, `tipo_unidad_defecto`.
2. **Fila de búsqueda:** el select de tipo_unidad tiene valor por defecto `tipo_unidad_defecto`; al seleccionar un artículo se asigna `filaBusqueda.tipo_unidad = tipo_unidad_defecto`.
3. **Al agregar renglón:** se envía `tipo_unidad: filaBusqueda.tipo_unidad || tipo_unidad_defecto` en el body del POST.
4. **Por renglón:** la columna Embalaje muestra un select con `x-model="r.tipo_unidad"` y `@change="actualizarMovimientoCantidad(r)"` para persistir el cambio.

## Backend

- **Servicio:** `core.services.administranet_stock.get_config_unidad_bulto_display(base_empresa)` devuelve el dict con las tres claves; si `tipo_unidad_defecto` no existe en la tabla, se devuelve `'Unidad'`.
- **Alta/actualización de renglón:** ya se persiste `tipo_unidad` en `cuerpostock_mstock` y se devuelve en `listar_renglones_temporales`.

## Referencia

- Plan: Fase 3 tipo_unidad_bulto (análisis artefactos VB6 stock).
- VB6: CargaMovStock combo tipo_unidad_bulto / unidad_art_peso; opciones según configuración.
