# mpr-envio-produccion-tablero

## Purpose

Define la funcionalidad de **envío directo a producción desde el tablero consolidado** a nivel COMPONENTE y por lote, sin pasar por el wizard OPT. Incluye ledger Django Postgres (`MprEnvioProduccion`), servicio de lote atómico, helper de consulta backward-safe, vista POST y UI integrada en el tablero de producción.

Archivado desde el change SDD `mpr-pipeline-etapa7-enviar-desde-tablero` (03/07/2026).

Documentos operativos asociados: `docs/mpr/TABLERO_CONSOLIDADO.md`, `docs/mpr/ENVIO_PRODUCCION_TABLERO.md`.

---

## Requirements

### Requirement: Modelo MprEnvioProduccion

El sistema MUST persistir cada envío en `MprEnvioProduccion` con los campos: `base_empresa` (FK), `id_articulo` (int, COMPONENTE), `cantidad` (Decimal), `id_usuario` (int), `creado_en` (datetime, auto_now_add), `anulado` (bool, default False). MUST existir índices compuestos sobre `(base_empresa, id_articulo)` y `(base_empresa, creado_en)`. La migración 0014 MUST ser additive (solo CREATE TABLE) y MUST ejecutarse con `SYNAP_MIGRATIONS_POSTGRES_ONLY=1`.

#### Scenario: Registro de un envío

- DADO un componente válido con pendiente > 0 y un usuario autenticado
- CUANDO el servicio registra un envío de cantidad 10
- ENTONCES MUST existir una fila en `MprEnvioProduccion` con `id_articulo` correcto, `cantidad=10`, `anulado=False`, `creado_en` poblado

#### Scenario: Migración additive

- DADO la migración 0013 aplicada y la tabla `mpr_mprenvio_produccion` inexistente
- CUANDO se aplica la migración 0014
- ENTONCES MUST crearse la tabla sin modificar tablas existentes ni tablas MySQL legacy

---

### Requirement: Servicio de Envío por Lote

El sistema MUST proveer `enviar_a_produccion_lote(base_empresa, id_usuario, items)` que crea N registros `MprEnvioProduccion` en una transacción atómica. El servicio MUST omitir filas con `cantidad <= 0` sin error. El servicio SHOULD emitir warning (no bloqueo) si `cantidad > pendiente_componente`. El servicio MUST NOT escribir en tablas MySQL legacy (`lista_produccion_agrupada`, `movimiento_stock`) ni modificar `stock_deposito`. Un lote vacío MUST retornar resultado vacío sin error.

#### Scenario: Lote con 3 filas válidas crea 3 registros

- DADO un lote con 3 items con cantidades {5, 10, 15}
- CUANDO se llama `enviar_a_produccion_lote`
- ENTONCES MUST crearse exactamente 3 registros en `MprEnvioProduccion` en transacción única

#### Scenario: Rechaza filas con cantidad ≤ 0

- DADO un lote con items de cantidades {10, 0, -5, 8}
- CUANDO se llama `enviar_a_produccion_lote`
- ENTONCES MUST crearse 2 registros (cantidades 10 y 8)
- Y las filas con cantidad 0 y -5 MUST omitirse sin lanzar excepción

#### Scenario: Warning de sobreenvío (no bloqueante)

- DADO un componente con pendiente = 20 y un item con cantidad = 30
- CUANDO se llama `enviar_a_produccion_lote`
- ENTONCES MUST crearse el registro con cantidad = 30
- Y el servicio SHOULD retornar una advertencia de sobreenvío sin rechazar la operación

#### Scenario: Lote vacío retorna sin error

- DADO un lote con lista de items vacía
- CUANDO se llama `enviar_a_produccion_lote`
- ENTONCES MUST retornar resultado vacío (0 registros creados) sin error ni excepción

#### Scenario: Sin escritura MySQL legacy (ledger-only Synap)

- DADO un envío exitoso de lote de 3 items
- CUANDO finaliza la transacción
- ENTONCES NO MUST existir nuevas filas en `lista_produccion_agrupada` ni en `movimiento_stock` atribuibles al envío
- Y `stock_deposito` MUST permanecer sin cambios tras el envío

---

### Requirement: Helper de Consulta Backward-Safe

El sistema MUST proveer `_query_enviado_tablero_componente(base_empresa, comp_ids)` que retorne `{id_componente: Decimal}` con la suma de `cantidad` de filas `anulado=False`. Si no existen registros en `MprEnvioProduccion` para `base_empresa`, MUST retornar `{}` (dict vacío). El tablero MUST funcionar exactamente igual que en E1-E6 cuando el helper retorna `{}`.

#### Scenario: Con envíos registrados — suma correcta excluyendo anulados

- DADO comp_id=42 con 2 envíos activos (cantidades 10 y 15) y 1 anulado (cantidad 5)
- CUANDO se llama el helper
- ENTONCES MUST retornar `{42: Decimal('25')}` (solo suma activos)

#### Scenario: Sin envíos — backward-safe

- DADO base_empresa sin registros en `MprEnvioProduccion`
- CUANDO se llama el helper
- ENTONCES MUST retornar `{}`
- Y el tablero MUST funcionar sin error mostrando los mismos valores que en E6

---

### Requirement: Vista de Lote POST

El sistema MUST proveer `EnviarProduccionLoteView` (POST, `MprLoginRequiredMixin`) accesible en la URL `tablero-produccion/enviar/`. La vista MUST estar scoped a `base_empresa` del contexto de sesión. Tras procesar, MUST redirigir al tablero con mensaje de éxito en español que incluya el conteo de registros enviados. Si hay sobreenvíos, MUST mostrar warnings visibles en español sin rechazar la operación ni alterar el redirect.

#### Scenario: POST lote con cantidades válidas

- DADO un usuario autenticado con 3 filas seleccionadas con cantidades {10, 5, 8}
- CUANDO hace POST a `tablero-produccion/enviar/`
- ENTONCES MUST redirigir al tablero con mensaje de éxito en español indicando 3 envíos creados
- Y MUST existir 3 registros nuevos en `MprEnvioProduccion`

#### Scenario: Sobreenvío muestra warning y redirige igual

- DADO un componente con pendiente = 5 y cantidad enviada = 20
- CUANDO se procesa el POST
- ENTONCES el envío MUST ejecutarse y MUST mostrarse un warning en español
- Y el redirect al tablero MUST ocurrir normalmente

---

### Requirement: UI Integrada en Tablero

El tablero (`tablero_produccion.html`) MUST incluir una columna "Enviar" con inputs numéricos por fila. Los inputs MUST estar deshabilitados (`disabled`) si `pendiente <= 0`. MUST existir un botón "Enviar a producción" que envíe el lote en un único POST. La columna de acciones E5 (transiciones) MUST mantenerse en posición y funcionalidad sin cambios. Los mensajes MUST estar en español y las fechas MUST mostrarse en formato dd/MM/yyyy.

#### Scenario: Usuario carga cantidades en varias filas y envía

- DADO el tablero con varias filas con pendiente > 0
- CUANDO el usuario ingresa cantidades en múltiples inputs y hace clic en "Enviar a producción"
- ENTONCES MUST realizarse un único POST con todas las cantidades ingresadas
- Y tras redirigir, el tablero MUST reflejar los valores de Enviado y Pendiente actualizados

#### Scenario: Input deshabilitado si pendiente = 0

- DADO una fila con pendiente = 0
- CUANDO se renderiza el tablero
- ENTONCES el input numérico de esa fila MUST estar deshabilitado

#### Scenario: Columna acciones E5 preservada

- DADO el tablero con columna de acciones E5 (transiciones por fila)
- CUANDO se añade la columna "Enviar" en E7
- ENTONCES los botones de acción E5 MUST seguir presentes y funcionales
- Y NO MUST moverse ni ocultarse la columna de acciones

---

## Notes

- **Etapa 7 — Envío desde Tablero (03/07/2026):** Implementada capability `mpr-envio-produccion-tablero`. Ledger Django Postgres `MprEnvioProduccion` desacoplado de MySQL legacy. Fórmula unificada de "Enviado a producción" con DOS fuentes (OPT + tablero). Servicio de lote atómico `enviar_a_produccion_lote`, helper backward-safe `_query_enviado_tablero_componente`, vista POST `EnviarProduccionLoteView`, UI integrada con form HTML5 `form=` attribute (anti-nesting). Migración 0014 aplicada. Suite mpr: 348 tests PASS (26 nuevos E7, 322 previos), 0 regresiones. Verify #1030 = PASS.

- **Follow-ups pendientes (diferidos a E8+):**
  - Vínculo explícito bidireccional `MprEnvioProduccion` ↔ `MprParte` (traza de consumo del envío tablero al registrar parte)
  - Comprobante MSTOCK en MySQL legacy para envíos del tablero (actualmente ledger-only Synap)
  - UI de anulación de envíos desde el tablero (actualmente solo vía admin Django)
  - Deprecación efectiva del wizard OPT como camino de envío (coexiste como camino legacy en E7)
  - Filtro temporal de ventana para `MprEnvioProduccion.creado_en` en queries (actualmente sin filtro, todos los envíos históricos suman)
