# Unidad de peso y lista_unidad_art_peso en Ingreso Mov. Stock (Synap)

**Objetivo:** Permitir capturar el peso por unidad por renglón cuando la empresa usa multiplicador bulto promedio y báscula, alineado con CargaMovStock VB6 (unidad_art_peso, lista_unidad_art_peso, Carga_Unidad_Peso).

## Configuración (tabla `configuracion`)

- **usa_multiplica_bulto_promedio:** `'Si'` / `'No'`. Debe ser `'Si'` para que se ofrezca la funcionalidad de peso.
- **tipo_balanza:** En VB6 la visibilidad es cuando además `tipo_balanza = 'Bascula'`. En Synap se muestra la columna Peso y el botón lista cuando **usa_multiplica_bulto_promedio = 'Si'** y **tipo_balanza = 'Bascula'**.

## Visibilidad en la UI

- La columna **Peso** (input + botón «lista»), el input en la fila de búsqueda y el modal **Ingresar peso** solo se muestran cuando **mostrarUnidadPeso** es verdadero: `usa_multiplica_bulto_promedio === 'Si'` **y** `tipo_balanza === 'Bascula'`.

## Flujo

1. **Datos iniciales** (`api_ingreso_datos_iniciales`): el front recibe `usa_multiplica_bulto_promedio`, `tipo_balanza`.
2. **Por renglón:** columna Peso con input numérico (`r.unidad_art_peso`) y botón con ícono «list» que abre el modal **Ingresar peso** (equivalente a lista_unidad_art_peso → Carga_Unidad_Peso en VB6). Al cambiar el input o al Aceptar en el modal se persiste vía `actualizarMovimientoCantidad(r)`.
3. **Fila de búsqueda:** input opcional `filaBusqueda.unidad_art_peso`; al agregar renglón se envía en el body del POST.
4. **Modal Ingresar peso:** título «Ingresar peso», campo «Peso (unidad)», botones Cancelar y Aceptar; al Aceptar se asigna el valor al renglón y se llama a `actualizarMovimientoCantidad(r)`.

## Backend

- **Servicio:** `core.services.administranet_stock.get_config_peso_balanza(base_empresa)` devuelve `usa_multiplica_bulto_promedio` y `tipo_balanza`.
- **Alta/actualización de renglón:** ya se persiste `unidad_art_peso` en `cuerpostock_mstock` y se devuelve en `listar_renglones_temporales`.

## Diferencia con VB6

- En VB6 **Carga_Unidad_Peso** puede integrar báscula (captura de peso desde dispositivo). En Synap el modal solo permite ingresar el valor manualmente; no hay integración con báscula real.

## Referencia

- VB6: CargaMovStock Form_Load (lista_unidad_art_peso.Visible cuando usa_multiplica_bulto_promedio y tipo_balanza = Bascula), lista_unidad_art_peso_Click → Carga_Unidad_Peso, AgregarRenglon con unidad_art_peso.
- Fase 4: unidad_art_peso + lista_unidad_art_peso (plan análisis artefactos VB6 stock).
