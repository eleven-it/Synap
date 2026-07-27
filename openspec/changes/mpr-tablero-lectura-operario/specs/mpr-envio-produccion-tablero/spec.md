# Delta for mpr-envio-produccion-tablero

## ADDED Requirements

### Requirement: Anulación de envíos exige mpr.ver

Las vistas y endpoints POST de **anulación** de envíos desde el tablero MUST exigir `mpr.ver`. Un usuario con solo `mpr.tablero_ver` MUST recibir acceso denegado (403). La UI de anulación MUST ocultarse cuando el usuario no tiene `mpr.ver`.

#### Scenario: POST anular denegado con solo tablero_ver

- **GIVEN** un usuario autenticado con `mpr.tablero_ver` y sin `mpr.ver`
- **WHEN** envía POST de anulación de envíos desde el tablero
- **THEN** el sistema responde 403 y NO modifica registros de envío

#### Scenario: UI de anulación oculta en solo lectura

- **GIVEN** un usuario con `mpr.tablero_ver` y sin `mpr.ver` viendo el tablero
- **WHEN** se renderiza la pantalla
- **THEN** NO ve controles de anulación de envíos

---

## MODIFIED Requirements

### Requirement: Vista de Lote POST

El sistema MUST proveer `EnviarProduccionLoteView` (POST, `MprLoginRequiredMixin`) accesible en la URL `tablero-produccion/enviar/`. La vista MUST exigir `mpr.ver`; usuarios con solo `mpr.tablero_ver` MUST recibir 403. La vista MUST estar scoped a `base_empresa` del contexto de sesión. Tras procesar, MUST redirigir al tablero con mensaje de éxito en español que incluya el conteo de registros enviados. Si hay sobreenvíos, MUST mostrar warnings visibles en español sin rechazar la operación ni alterar el redirect.

(Previously: la vista solo exigía login MPR (`MprLoginRequiredMixin`) sin distinguir lectura vs escritura del tablero.)

#### Scenario: POST lote con cantidades válidas

- **DADO** un usuario autenticado con `mpr.ver` y 3 filas seleccionadas con cantidades {10, 5, 8}
- **CUANDO** hace POST a `tablero-produccion/enviar/`
- **ENTONCES** MUST redirigir al tablero con mensaje de éxito en español indicando 3 envíos creados
- **Y** MUST existir 3 registros nuevos en `MprEnvioProduccion`

#### Scenario: Sobreenvío muestra warning y redirige igual

- **DADO** un usuario con `mpr.ver`, un componente con pendiente = 5 y cantidad enviada = 20
- **CUANDO** se procesa el POST
- **ENTONCES** el envío MUST ejecutarse y MUST mostrarse un warning en español
- **Y** el redirect al tablero MUST ocurrir normalmente

#### Scenario: POST enviar denegado con solo tablero_ver

- **DADO** un usuario autenticado con `mpr.tablero_ver` y sin `mpr.ver`
- **CUANDO** hace POST a `tablero-produccion/enviar/`
- **ENTONCES** el sistema responde 403
- **Y** NO MUST crearse ningún registro en `MprEnvioProduccion`

---

### Requirement: UI Integrada en Tablero

El tablero (`tablero_produccion.html`) MUST incluir una columna «Enviar» con inputs numéricos por fila **solo** para usuarios con `mpr.ver`. Para usuarios con solo `mpr.tablero_ver`, la columna «Enviar», el botón «Enviar a producción» y controles de anulación MUST ocultarse u omitirse en el render. Los inputs MUST estar deshabilitados (`disabled`) si `pendiente <= 0` cuando el usuario tiene permiso de envío. La columna de acciones E5 (transiciones) MUST mantenerse en posición y funcionalidad sin cambios para quienes tengan permiso. Los mensajes MUST estar en español y las fechas MUST mostrarse en formato dd/MM/yyyy.

(Previously: la UI de envío se mostraba a todo usuario autenticado con acceso al tablero, sin distinguir `mpr.ver`.)

#### Scenario: Usuario con mpr.ver carga cantidades y envía

- **DADO** el tablero con varias filas con pendiente > 0 y un usuario con `mpr.ver`
- **CUANDO** ingresa cantidades en múltiples inputs y hace clic en «Enviar a producción»
- **ENTONCES** MUST realizarse un único POST con todas las cantidades ingresadas
- **Y** tras redirigir, el tablero MUST reflejar los valores de Enviado y Pendiente actualizados

#### Scenario: UI de envío oculta con solo tablero_ver

- **DADO** un usuario con `mpr.tablero_ver` y sin `mpr.ver` viendo el tablero
- **CUANDO** se renderiza la pantalla
- **ENTONCES** NO ve columna «Enviar», botón «Enviar a producción» ni controles de anulación
- **Y** SÍ ve filtros, Pack|Par, Actualizar y datos de consulta del tablero

#### Scenario: Input deshabilitado si pendiente = 0

- **DADO** una fila con pendiente = 0 y un usuario con `mpr.ver`
- **CUANDO** se renderiza el tablero
- **ENTONCES** el input numérico de esa fila MUST estar deshabilitado

#### Scenario: Columna acciones E5 preservada

- **DADO** el tablero con columna de acciones E5 (transiciones por fila)
- **CUANDO** un usuario con `mpr.ver` visualiza el tablero
- **ENTONCES** los botones de acción E5 MUST seguir presentes y funcionales
- **Y** NO MUST moverse ni ocultarse la columna de acciones
