# Spec: Resumen de lote masivo confirmado

**Capability:** `ecom-pedido-masivo-lote-resumen`  
**Change:** `ecom-pedido-masivo-consolidado-hub`  
**Ruta:** `/ecom/mayoristapp/pedidos/lote/<draft_id>/`

## Purpose

Vista consolidada de un `EcomPedidoMasivoDraft` confirmado: totales, sucursales/PED generados, matriz read-only «Qué se cargó» y acciones comerciales de lote (autorizar/rechazar).

## Requirements

### REQ-LOT-01 — Pantalla resumen del lote

El sistema MUST servir `/ecom/mayoristapp/pedidos/lote/<draft_id>/` para drafts masivos en estado `confirmado` dentro del alcance comercial del usuario. MUST mostrar cabecera del lote (cliente, vendedor operativo, fecha confirmación, totales agregados) y tabla de sucursales con `cod_mov`, estado operativo y estado comercial por PED. Fechas en UI MUST formatearse `dd/MM/yyyy`. Textos MUST estar en español.

#### Scenario: Acceso desde hub

- **GIVEN** un lote confirmado visible en lane Cargas masivas
- **WHEN** el usuario pulsa «Ver resumen»
- **THEN** MUST navegar a `/ecom/mayoristapp/pedidos/lote/<draft_id>/`
- **AND** MUST mostrar cabecera y tabla de sucursales del lote

#### Scenario: Draft fuera de alcance

- **GIVEN** un `draft_id` de otro subárbol comercial
- **WHEN** el usuario intenta abrir el resumen
- **THEN** MUST responder 403 o redirigir con mensaje en español
- **AND** MUST NOT exponer datos del lote

#### Scenario: Draft no confirmado

- **GIVEN** un draft en estado `BORRADOR` o `confirmando`
- **WHEN** se solicita la pantalla resumen
- **THEN** MUST responder 404 o redirigir al flujo de edición/recuperación correspondiente

---

### REQ-LOT-02 — API JSON del resumen

El sistema MUST exponer API JSON del resumen del lote (misma ruta con `Accept: application/json` o subruta documentada en diseño) con: `draft_id`, `cliente`, `vendedor`, `fecha_confirmacion`, `totales`, `sucursales[]` (`id_domicilio`, `nombre`, `cod_mov`, `estado_pedido`, `estado_comercial`, `totales`) y `estado_aprobacion_lote` agregado. MUST respetar alcance comercial y autenticación del módulo pedidos.

#### Scenario: Payload coherente con pantalla

- **GIVEN** lote confirmado con 3 PED generados
- **WHEN** el cliente solicita JSON del resumen
- **THEN** MUST devolver 3 entradas en `sucursales[]` con `cod_mov` correspondientes
- **AND** totales agregados MUST coincidir con la suma de PED existentes

---

### REQ-LOT-03 — Pestaña «Qué se cargó» (matriz read-only)

La pantalla MUST incluir pestaña **Qué se cargó** que renderiza la matriz de carga del draft en modo solo lectura (`readonly=1`): filas artículo, columnas sucursal, cantidades packs, precios y descuentos persistidos al confirmar. MUST NOT permitir edición de celdas ni confirmación desde esta pestaña.

#### Scenario: Matriz sin inputs editables

- **GIVEN** lote confirmado con matriz persistida
- **WHEN** el usuario abre pestaña «Qué se cargó»
- **THEN** MUST ver la misma estructura fila/columna que en captura masiva
- **AND** MUST NOT existir inputs editables ni CTA confirmar lote

#### Scenario: Navegación entre pestañas

- **GIVEN** resumen del lote abierto
- **WHEN** alterna entre pestaña Resumen y «Qué se cargó»
- **THEN** MUST conservar contexto del lote sin recargar datos inconsistentes

---

### REQ-LOT-04 — Reconciliación draft vs PED

Para cada sucursal esperada según el draft confirmado, el resumen MUST reconciliar `codigos_movimiento[]` con PED MySQL: si existe PED activo MUST enlazar detalle; si PED anulado MUST marcar **Anulada**; si `cod_mov` ausente o PED no generado MUST marcar **No generada**. MUST mostrar contador `k/n` PED activos del lote.

#### Scenario: PED anulado tras confirmación

- **GIVEN** lote con `cod_mov` en draft cuyo PED fue anulado en AdministraNET
- **WHEN** se renderiza tabla de sucursales
- **THEN** fila MUST mostrar estado **Anulada**
- **AND** MUST incluirse en contador `k/n` solo si producto define PED activo (diseño documentará regla)

#### Scenario: cod_mov ausente

- **GIVEN** sucursal con cantidad > 0 en matriz pero sin entrada en `codigos_movimiento[]`
- **WHEN** se renderiza reconciliación
- **THEN** MUST mostrar **No generada** en español
- **AND** MUST NOT ocultar la fila de sucursal

---

### REQ-LOT-05 — CTAs Autorizar y Rechazar lote

Con subflag `ecom_aprobacion_pedidos_activa` ON y lote en estado comercial pendiente agregado, la pantalla MUST mostrar CTAs **Autorizar lote** y **Rechazar lote** visibles solo para usuarios con permiso `ecom.pedidos.aprobar` y alcance válido. Confirmaciones MUST usar modales Synap; MUST NOT usar `alert()`, `confirm()` ni `prompt()` nativos. Al autorizar/rechazar MUST invocar APIs de lote (REQ-APR-05/06) y refrescar estado agregado.

#### Scenario: Autorizar con modal Synap

- **GIVEN** lote pendiente de autorización comercial y usuario supervisor con permiso
- **WHEN** pulsa «Autorizar lote»
- **THEN** MUST abrir modal Synap de confirmación en español
- **AND** MUST NOT invocar `window.confirm()`

#### Scenario: Sin permiso de aprobación

- **GIVEN** vendedor sin `ecom.pedidos.aprobar`
- **WHEN** abre resumen de lote pendiente
- **THEN** MUST NOT mostrar CTAs Autorizar/Rechazar lote

#### Scenario: Lote ya resuelto

- **GIVEN** lote con `estado_aprobacion_lote` aprobado o rechazado
- **WHEN** se abre resumen
- **THEN** MUST mostrar badge de estado agregado
- **AND** MUST NOT mostrar CTAs de acción pendiente

---

### REQ-LOT-06 — Canon UI y accesibilidad operativa

La pantalla MUST seguir canon Synap operativo (header slate, tokens `.pedidos-*`, densidad desktop). MUST reutilizar componentes de matriz masiva en modo read-only. Enlaces a detalle PED individual MUST permanecer disponibles desde tabla de sucursales.

#### Scenario: Enlace a detalle PED

- **GIVEN** sucursal con PED activo `cod_mov=12345`
- **WHEN** el usuario pulsa el identificador en tabla
- **THEN** MUST abrir detalle/edición del PED según reglas vigentes del hub
