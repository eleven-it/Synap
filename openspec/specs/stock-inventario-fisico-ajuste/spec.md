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

#### Scenario: Acceso rápido a línea con diferencia

- **GIVEN** resumen de campaña con líneas ordenadas por magnitud de diferencia
- **WHEN** el supervisor selecciona una línea con diferencia
- **THEN** ve detalle de conteos y snapshot en una acción adicional como máximo
