# Spec — Analizador y ajuste MSTOCK

**Capability:** `stock-inventario-fisico-ajuste`  
**Origen:** change `stock-inventario-fisico` (archivado 23/07/2026)  
**Ruta:** `/stock/inventario-fisico/` (analizador/autorización)

---

## Purpose

Permitir al supervisor analizar diferencias entre conteo físico y snapshot, autorizar ajustes auditados vía MSTOCK masivo (`administranet_stock.py`) y garantizar que ningún ajuste se aplique sin autorización explícita ni con sincronizaciones pendientes.

---

## Requirements

### Requirement: Cálculo de diferencia solo en escritorio supervisor

La diferencia por línea MUST calcularse como **contado − saldo_snapshot**. Este valor MUST ser visible únicamente en UI/API de gestión y autorización (supervisor/admin), MUST NOT exponerse al rol contador y MUST NOT incluirse en prefetch ni sync hacia PWA de conteo.

#### Scenario: Analizador muestra diferencia

- **GIVEN** una línea con `saldo_snapshot=100` y contado consolidado=95
- **WHEN** el supervisor abre el analizador de la campaña
- **THEN** ve diferencia −5 y detalle de conteos por operario

#### Scenario: API contador sin diferencia

- **GIVEN** la misma línea con diferencia calculable en servidor
- **WHEN** un operario consulta APIs de conteo móvil
- **THEN** la respuesta MUST NOT incluir diferencia ni saldo_snapshot

---

### Requirement: Monitor de campaña en escritorio

El supervisor MUST disponer de monitor de campaña (canon UI reports/MPR) con: estado de campaña, progreso por operario, conteos recibidos, conflictos de sync y resumen de líneas pendientes de conteo. Fechas MUST mostrarse como `dd/MM/yyyy`.

#### Scenario: Vista consolidada pre-autorización

- **GIVEN** una campaña Cerrado a revisión con conteos parciales y un conflicto entre operarios
- **WHEN** el supervisor abre el monitor
- **THEN** ve progreso, conflicto marcado y líneas sin conteo, sin poder aplicar MSTOCK aún

---

### Requirement: Autorización obligatoria antes de MSTOCK

Ningún ajuste de stock MUST aplicarse sin acción explícita de autorización por usuario con `stock.inventario_fisico.autorizar`. El sistema MUST NOT permitir ajuste directo desde pantalla de conteo ni atajos que omitan autorización.

#### Scenario: Intento de ajuste sin autorizar

- **GIVEN** diferencias calculadas en campaña Cerrado a revisión
- **WHEN** un usuario sin permiso de autorización intenta aplicar ajustes
- **THEN** el sistema deniega la operación

#### Scenario: Cero ajustes sin autorización en flujo normal

- **GIVEN** conteos registrados y campaña aún no autorizada
- **WHEN** se inspecciona `stock_deposito` y movimientos MSTOCK
- **THEN** MUST NOT existir movimiento MSTOCK vinculado a esa campaña

---

### Requirement: Bloqueo por sync pendiente

La autorización MUST NOT ejecutarse mientras la campaña reporte eventos de conteo con sincronización pendiente (ver capability `stock-inventario-fisico-sync-offline`). El analizador MUST mostrar indicador de bloqueo hasta resolución.

#### Scenario: Botón autorizar deshabilitado

- **GIVEN** campaña con sync pendiente en al menos un dispositivo asignado
- **WHEN** el supervisor abre analizador
- **THEN** la acción Autorizar MUST estar bloqueada con mensaje explicativo en español

#### Scenario: Autorizar tras sync completo

- **GIVEN** todos los conteos sincronizados o en estado resuelto
- **WHEN** el supervisor confirma autorización en modal Synap
- **THEN** el sistema procede a generar ajustes MSTOCK para líneas con diferencia distinta de cero

---

### Requirement: Aplicación MSTOCK masiva auditada

Tras autorización, el sistema MUST invocar ajuste masivo vía `administranet_stock.py` (MSTOCK) por las diferencias autorizadas, registrar auditoría (usuario, fecha/hora, campaña, líneas afectadas) y transicionar la campaña a **Aplicado**. Tipos de datos legacy MUST normalizarse con `administranet_types`.

#### Scenario: Autorización genera MSTOCK

- **GIVEN** tres líneas con diferencias +2, −1 y 0 tras sync completo
- **WHEN** el supervisor autoriza
- **THEN** se generan dos movimientos MSTOCK (+2 y −1), la línea con diferencia 0 MUST NOT generar movimiento y la campaña queda Aplicada

#### Scenario: Auditoría de autorización

- **GIVEN** una autorización exitosa
- **WHEN** un admin consulta trazabilidad
- **THEN** ve usuario autorizador, timestamp y detalle de líneas ajustadas

---

### Requirement: Anulación sin MSTOCK en estados tempranos

Campañas en Borrador o En conteo MUST poder anularse sin generar MSTOCK. Campañas Aplicadas MUST NOT anularse automáticamente; compensación MUST ser manual (fuera de alcance MVP automatizado).

#### Scenario: Anular campaña En conteo

- **GIVEN** campaña En conteo con conteos parciales
- **WHEN** admin stock anula con confirmación modal Synap
- **THEN** campaña queda Anulada y MUST NOT existir MSTOCK asociado

---

### Requirement: Separación de consulta pivote

Las pantallas de analizador y autorización MUST vivir bajo `/stock/inventario-fisico/` y MUST NOT confundirse con `/stock/inventario/` (`stock-inventario-tabla`). Etiquetas de menú MUST diferenciar «Inventario físico» de «Consulta inventario».

#### Scenario: Navegación desde menú Stock

- **GIVEN** menú Stock con ambas entradas
- **WHEN** el supervisor elige Inventario físico
- **THEN** accede al monitor/analizador y no a la tabla pivote MPR

---

### Requirement: UX analizador eficiente

El supervisor SHOULD poder identificar líneas con diferencia y acceder al detalle en menos de dos clics desde el resumen de campaña. Confirmaciones destructivas u operativas MUST usar modales Synap.

El analizador MUST mostrar una columna **Saldo final** = `saldo_actual_ref + diferencia_real` (NULL si la línea no fue contada), que indica el saldo previsto en `stock_deposito` tras autorizar el MSTOCK. Esa columna MUST ser solo lectura/UI y MUST NOT alterar conteos, eventos ni escribir stock por sí sola. Sin descuadre, Saldo final MUST coincidir con Contado.

#### Scenario: Acceso rápido a línea con diferencia

- **GIVEN** resumen de campaña con líneas ordenadas por magnitud de diferencia
- **WHEN** el supervisor selecciona una línea con diferencia
- **THEN** ve detalle de conteos y snapshot en una acción adicional como máximo

#### Scenario: Saldo final con descuadre

- **GIVEN** línea contada con `saldo_actual_ref` distinto del disponible ajustado y diferencia real ≠ 0
- **WHEN** el supervisor ve el analizador
- **THEN** la columna Saldo final muestra `saldo_actual_ref + diferencia_real` (no necesariamente igual a Contado)

---

### Requirement: Marcar no contados como cero (masivo)

Un supervisor con permiso `stock.inventario_fisico.gestionar` MUST poder marcar masivamente como **Contado = 0** todas las líneas de campaña con `cantidad_contada IS NULL`, desde el analizador, solo si la campaña está en **EnConteo** o **EnRevision**. El alcance MUST ser **toda la campaña** (MUST NOT limitarse al filtro de marcas activo en la tabla). El sistema MUST NOT aplicar MSTOCK, MUST NOT recrear snapshot y MUST NOT alterar líneas ya contadas. Por cada línea marcada: un `inv_fisico_evento` con `client_event_id` UUID de **36 caracteres**, `cantidad=0`, `motivo` en español fijo de supervisor (`Supervisor: no encontrado / contado 0`) y un `inv_fisico_ajuste_auditoria` con `accion=contado_cero_masivo`. Tras marcar MUST intentar recalcular ajuste post-snapshot sin MSTOCK (`pisar_overrides=False`); si el recálculo falla MUST NOT revertir el marcado y MUST devolver `advertencia` en español. La UI MUST mostrar chip «N no contados» (N = campaña completa), desglose en modal (total, snap≠0, mov. post), checkbox de acuse «Entiendo que no hay deshacer en pantalla» que habilita el CTA, y confirmación modal Synap (MUST NOT `alert`/`confirm`/`prompt`). La operación MUST ser idempotente.

#### Scenario: Marca masiva exitosa

- **GIVEN** campaña EnRevision con 5 líneas sin contar y 3 ya contadas
- **WHEN** el supervisor confirma con checkbox marcado
- **THEN** 5 líneas quedan con Contado=0; las 3 contadas permanecen intactas; respuesta `{ok, lineas_marcadas:5}`; analizador se recarga

#### Scenario: Alcance campaña completa (ignora filtro marcas)

- **GIVEN** filtro de marcas activo que oculta parte de no contados, pero la campaña tiene 12 líneas con `cantidad_contada IS NULL`
- **WHEN** el supervisor abre el analizador o confirma el modal
- **THEN** chip y modal muestran 12 (toda la campaña) y la acción marca las 12

#### Scenario: Desglose y checkbox antes de confirmar

- **GIVEN** 10 líneas sin contar de las cuales 3 con `saldo_snapshot ≠ 0` y 1 con movimiento post-snapshot neto ≠ 0
- **WHEN** el supervisor abre el modal
- **THEN** ve desglose 10/3/1; el CTA permanece deshabilitado hasta marcar «Entiendo que no hay deshacer en pantalla»

#### Scenario: Advertencia snapshot distinto de cero

- **GIVEN** al menos una línea sin contar con `saldo_snapshot ≠ 0`
- **WHEN** el supervisor abre el modal
- **THEN** ve advertencia en español de posible faltante/diferencia al autorizar MSTOCK más adelante

#### Scenario: Recálculo post-snapshot falla sin deshacer marcado

- **GIVEN** marcado exitoso y `recalcular_ajuste_post_snapshot` lanza error
- **WHEN** termina la API
- **THEN** las líneas quedan con Contado=0; respuesta `ok` con `advertencia`; MUST NOT rollback del marcado

#### Scenario: Sync móvil prevalece

- **GIVEN** línea con `cantidad_contada IS NULL` y sync concurrente que registra cantidad &gt; 0
- **WHEN** se ejecuta la marca masiva
- **THEN** esa línea MUST NOT quedar en 0 (condición `IS NULL`)

#### Scenario: Idempotencia

- **GIVEN** no quedan líneas con `cantidad_contada IS NULL`
- **WHEN** el supervisor repite la acción
- **THEN** `lineas_marcadas=0`; MUST NOT crear nuevos eventos ni auditorías

#### Scenario: Estado inválido

- **GIVEN** campaña Aplicada o Anulada
- **WHEN** POST a la API
- **THEN** HTTP 400 con mensaje en español; MUST NOT modificar datos

#### Scenario: Sin permiso

- **GIVEN** usuario sin `stock.inventario_fisico.gestionar`
- **WHEN** accede a la API o al analizador
- **THEN** API responde 403; botón de acción MUST NOT mostrarse

#### Scenario: No ejecuta MSTOCK

- **GIVEN** líneas marcadas con `diferencia_real ≠ 0` tras contado cero masivo
- **WHEN** se inspecciona movimientos MSTOCK
- **THEN** MUST NOT existir MSTOCK ni transición a Aplicada por esta acción

#### Scenario: UUID canónico y motivo español

- **GIVEN** N líneas marcadas en una ejecución
- **THEN** cada evento tiene `client_event_id` de longitud 36 (UUID); `motivo` = texto fijo en español de supervisor contado 0

#### Scenario: Auditoría contado_cero_masivo

- **GIVEN** N líneas marcadas en una ejecución
- **THEN** existen N filas en `inv_fisico_ajuste_auditoria` con `accion=contado_cero_masivo`

#### Scenario: Chip, botón y modal Synap

- **GIVEN** 12 líneas sin contar y permiso `gestionar`
- **WHEN** el supervisor abre el analizador
- **THEN** ve chip «12 no contados», botón de acción y modal Synap; si la respuesta incluye `advertencia`, toast warning además del éxito/reload
