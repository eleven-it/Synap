# Spec — Sincronización offline (IndexedDB)

**Capability:** `stock-inventario-fisico-sync-offline`
**Change:** `stock-inventario-fisico`
**Estado:** Propuesto

---

## Purpose

Soportar conteo físico offline-first en MVP: prefetch de catálogo ciego, cola local en IndexedDB, sincronización batch idempotente con `client_event_id`, resolución explícita de conflictos y bloqueo de autorización de ajustes mientras existan syncs pendientes en la campaña.

---

## Requirements

### Requirement: Prefetch de catálogo ciego

Con conectividad (al menos una vez por sesión/campaña), la PWA MUST descargar el catálogo de artículos de la campaña sin campos de saldo ni diferencia y persistirlo en IndexedDB para uso offline.

#### Scenario: Prefetch inicial con red

- **GIVEN** un operario asignado abre conteo con red disponible
- **WHEN** inicia la sesión de conteo
- **THEN** el catálogo ciego queda almacenado localmente y permite búsqueda/escaneo sin red posterior

#### Scenario: Catálogo prefetch sin saldo

- **GIVEN** el payload de prefetch completado
- **WHEN** se inspecciona el almacenamiento IndexedDB
- **THEN** MUST NOT existir `saldo_snapshot`, `saldo_sistema` ni `diferencia` en registros visibles al cliente contador

---

### Requirement: Cola local de eventos de conteo

Cada registro offline MUST encolarse como evento con: `client_event_id` único, campaña, artículo, cantidad, operario, marca temporal local y estado (`pendiente`, `enviado`, `conflicto`, `rechazado`). Los eventos MUST persistir en IndexedDB hasta confirmación del servidor o resolución explícita.

#### Scenario: Encolado sin red

- **GIVEN** catálogo prefetched y sin conectividad
- **WHEN** el operario registra tres conteos
- **THEN** la cola local contiene tres eventos `pendiente` con `client_event_id` distintos

#### Scenario: Persistencia tras cierre de PWA

- **GIVEN** eventos pendientes en cola
- **WHEN** el operario cierra y reabre la PWA sin red
- **THEN** la cola MUST conservar los eventos pendientes

---

### Requirement: Sync batch idempotente

Al reconectar, la PWA MUST enviar eventos pendientes en lote al endpoint de sync. El servidor MUST tratar cada `client_event_id` de forma idempotente: reintentos del mismo ID MUST NOT duplicar conteos en base de datos.

#### Scenario: Reintento de mismo client_event_id

- **GIVEN** un evento ya aceptado por el servidor
- **WHEN** el cliente reenvía el mismo `client_event_id` por timeout
- **THEN** el servidor responde éxito sin crear un segundo conteo

#### Scenario: Respuesta batch estructurada

- **GIVEN** cinco eventos pendientes al reconectar
- **WHEN** se ejecuta sync batch
- **THEN** la respuesta MUST clasificar cada evento en `{aceptados, conflictos, rechazados}`

---

### Requirement: Resolución de conflictos explícita

Conflictos MUST reportarse de forma explícita al supervisor y al operario afectado. Entre conteos del **mismo operario** sobre el mismo artículo, MUST aplicarse last-write-wins por timestamp del evento aceptado. Entre **distintos operadores** sobre el mismo artículo, MUST NOT aplicarse resolución silenciosa; el conflicto MUST quedar visible para gestión en monitor/analizador.

#### Scenario: Last-write-wins mismo operario

- **GIVEN** dos eventos offline del operario A para el mismo artículo con cantidades 10 y 15
- **WHEN** sincronizan en orden temporal
- **THEN** prevalece la cantidad del evento con timestamp más reciente y el anterior queda superseded sin duplicar línea activa

#### Scenario: Conflicto entre operarios

- **GIVEN** operario A contó 10 y operario B contó 12 del mismo artículo offline
- **WHEN** ambos eventos sincronizan
- **THEN** el sistema marca conflicto explícito, MUST NOT elegir ganador automático y el supervisor ve ambos valores en monitor

#### Scenario: Operario ve conflicto propio

- **GIVEN** un evento del operario marcado como conflicto tras sync
- **WHEN** consulta progreso en PWA
- **THEN** ve estado conflicto con mensaje en español sin revelar saldo de sistema

---

### Requirement: Resistencia offline prolongada

Tras al menos 30 minutos sin conectividad con conteos continuos, al reconectar el sistema MUST sincronizar el 100 % de eventos válidos o reportar conflictos/rechazos explícitos; MUST NOT perder eventos encolados silenciosamente.

#### Scenario: Sesión offline 30+ minutos

- **GIVEN** 50 eventos encolados tras 35 minutos sin red
- **WHEN** se restablece la conectividad y corre sync
- **THEN** cada evento aparece en aceptados, conflictos o rechazados; ninguno queda ignorado

---

### Requirement: Bloqueo de autorización con sync pendiente

Mientras una campaña tenga eventos de conteo con sync pendiente (local en cualquier dispositivo asignado o no confirmado en servidor), el supervisor MUST NOT autorizar ajustes MSTOCK para esa campaña. La UI de autorización MUST informar la causa del bloqueo.

#### Scenario: Autorización bloqueada por pendientes

- **GIVEN** una campaña Cerrado a revisión con sync pendiente reportado por el monitor
- **WHEN** el supervisor intenta autorizar ajustes
- **THEN** el sistema deniega la acción e indica conteos pendientes de sincronización

#### Scenario: Autorización tras sync completo

- **GIVEN** todos los eventos en estado sincronizado o resueltos sin pendientes
- **WHEN** el supervisor autoriza ajustes
- **THEN** el flujo de autorización procede (capability `stock-inventario-fisico-ajuste`)

---

### Requirement: Fuera de alcance MVP offline

En MVP, MUST NOT soportarse creación/anulación de campañas offline ni autorización offline. MUST NOT implementarse reconteo forzado, fotos adjuntas ni partición avanzada de prefetch (fase 2+).

#### Scenario: Intento de autorizar offline

- **GIVEN** supervisor sin conectividad
- **WHEN** intenta autorizar ajustes
- **THEN** el sistema MUST NOT completar autorización y muestra error de conectividad requerida
