# ecom-credito-pedidos Specification

## Purpose

Workflow de crédito **independiente del comercial** para pedidos mayoristas PED/PRE: políticas por cliente/canal, exposición Balance+All configurable, evaluación en checkout, hold de preparación, cola y aprobación Finanzas, auditoría, cobranzas automáticas y plantillas. Fuera de alcance v1: TPV, WhatsApp, SAP FSCM y mutación de `cliente.Credito`.

## Requirements

### Requirement: Flag master y fases A/B

El sistema MUST exponer flag master `ecom_credito_pedidos_activa`. Con flag OFF MUST conservar evaluación legacy solo-días sin regresión. Con flag ON MUST activar evaluación unificada (fase A: política, exposición, checkout, semáforo, fix matriz) y, cuando corresponda fase B, cola Finanzas, hold de preparación y cobranzas automáticas.

#### Scenario: Flag OFF — paridad legacy

- **GIVEN** `ecom_credito_pedidos_activa` desactivado
- **WHEN** se confirma un PED mayorista
- **THEN** MUST evaluarse crédito únicamente por mora en días según comportamiento legacy
- **AND** MUST NOT mostrarse cola Finanzas ni pantallas de crédito nuevas

#### Scenario: Flag ON — evaluación ampliada fase A

- **GIVEN** flag master activo y política configurada para el cliente/canal
- **WHEN** se confirma checkout PED o PRE
- **THEN** MUST evaluarse monto, días y exposición según política
- **AND** MUST persistir snapshot de evaluación para auditoría

---

### Requirement: Políticas por cliente y canal

El sistema MUST persistir políticas de crédito en tabla dedicada MySQL (DDL vía `catalog.py`), indexada por cliente y canal (`PED`/`PRE`). Cada política MUST definir al menos: tope monetario de referencia, límite de días, capas de exposición activables ON/OFF (CxC, PED abiertos, remitos NF, cheques propios/terceros, documento actual) e inclusión opcional de mora y cheques. MUST NOT almacenar políticas solo como columnas ad hoc en `cliente`.

#### Scenario: Política distinta por canal

- **GIVEN** cliente con política PED estricta y política PRE relajada
- **WHEN** se evalúa un presupuesto PRE
- **THEN** MUST aplicarse la política del canal PRE, no la de PED

#### Scenario: Alta de política desde ABM

- **GIVEN** usuario con `finance.credito.configurar`
- **WHEN** crea política para cliente y canal PED
- **THEN** MUST persistirse fila en tabla de políticas
- **AND** MUST quedar disponible para evaluación en checkout y semáforo

---

### Requirement: Exposición Balance+All y Credito=0

El evaluador MUST calcular exposición agregando solo las capas habilitadas en la política. Si `cliente.Credito = 0`, el sistema MUST tratar al cliente como **sin tope monetario** (solo aplica control por días y capas no monetarias según política). MUST NOT bloquear el alta por exceso de monto cuando `Credito=0`.

#### Scenario: Cliente sin tope monetario

- **GIVEN** cliente con `Credito=0` y mora dentro del límite de días
- **WHEN** el total del pedido supera cualquier umbral nominal de monto
- **THEN** MUST NOT marcar `No Autorizado` por exceso de cupo $
- **AND** MUST evaluar mora en días según política

#### Scenario: Exposición con capas parciales

- **GIVEN** política con CxC y PED abiertos ON y cheques OFF
- **WHEN** se calcula exposición pre-checkout
- **THEN** MUST sumar CxC y PED abiertos
- **AND** MUST NOT incluir cheques en el total

---

### Requirement: Evaluación en checkout — alta siempre, hold si No Autorizado

En confirmación PED/PRE, el sistema MUST invocar evaluador unificado, persistir `comp_ped.autorizacion_sistema` y metadata de evaluación (motivos monto/días, snapshot exposición). El exceso de crédito MUST NOT impedir el alta del comprobante. Si el resultado es `No Autorizado`, el sistema MUST aplicar **hold de preparación** (fase B) hasta resolución Finanzas. Pedidos de autogestión cliente MUST quedar siempre `No Autorizado`.

#### Scenario: Exceso de monto — alta con hold

- **GIVEN** cliente con cupo agotado según exposición calculada
- **WHEN** el vendedor confirma PED
- **THEN** MUST crearse el comprobante con `autorizacion_sistema='No Autorizado'`
- **AND** MUST impedirse avance a preparación hasta aprobación Finanzas (fase B)

#### Scenario: Cliente al día y dentro de cupo

- **GIVEN** exposición + total pedido dentro de límites de política
- **WHEN** se confirma PED
- **THEN** MUST persistir `autorizacion_sistema='Autorizado'`
- **AND** MUST registrar snapshot sin motivos de rechazo

---

### Requirement: Cola y aprobación Finanzas independiente

El workflow Finanzas MUST ser independiente de `estado_aprobacion_comercial`. Solo usuarios con permiso `finance.credito.aprobar` (asignable por Puesto) MUST poder aprobar o rechazar desde cola dedicada. La aprobación MUST liberar **únicamente el PED puntual** (`autorizacion_sistema='Autorizado'`) y MUST NOT mutar `cliente.Credito` ni cupo legacy.

#### Scenario: Aprobación Finanzas libera PED

- **GIVEN** PED con `No Autorizado` y evento pendiente en cola Finanzas
- **WHEN** usuario Finanzas con permiso aprueba
- **THEN** MUST actualizar `autorizacion_sistema='Autorizado'` en ese PED
- **AND** MUST NOT modificar `cliente.Credito`
- **AND** MUST registrar evento de auditoría

#### Scenario: Sin permiso Finanzas

- **GIVEN** supervisor comercial sin `finance.credito.aprobar`
- **WHEN** intenta aprobar desde cola Finanzas
- **THEN** MUST rechazarse la operación con mensaje en español
- **AND** MUST NOT cambiar `autorizacion_sistema`

---

### Requirement: Cobranzas, plantillas y canal

El sistema MUST permitir plantillas editables de aviso/cobranza por cliente y/o canal, gateadas por `finance.credito.configurar`. El disparo automático de mails (v1) MUST respetar anti-ruido: ventana default **24 horas** por `(id_cliente, tipo_aviso, canal)` (configurable en `configuracion_ecom` / política); tipo `pedido_bloqueado` MUST además deduplicar por `CodigoMovimiento` (un envío por PED mientras el hold esté activo). MUST NOT integrar WhatsApp ni SAP FSCM en v1.

#### Scenario: Disparo cobranza con plantilla

- **GIVEN** PED `No Autorizado` y plantilla activa para el canal PED
- **WHEN** se cumple regla de aviso configurada
- **THEN** MUST encolarse mail usando plantilla del cliente/canal
- **AND** MUST NOT reenviar duplicado dentro del SLA anti-ruido de 24 h (salvo override)

#### Scenario: Dedup pedido bloqueado por PED

- **GIVEN** mismo `CodigoMovimiento` con hold activo y aviso `pedido_bloqueado` ya enviado
- **WHEN** se dispara de nuevo la regla de aviso
- **THEN** MUST NOT encolar otro mail del mismo tipo para ese PED

#### Scenario: Canal fuera de alcance v1

- **GIVEN** intento de configurar canal WhatsApp
- **WHEN** se guarda política o plantilla
- **THEN** MUST NOT ofrecerse canal WhatsApp en v1

---

### Requirement: Hold de preparación y bridge VB6

Con `ecom_credito_hold_prep_activo` ON, si el PED queda `No Autorizado` el sistema MUST persistir `comp_ped.credito_hold_prep='Si'`. Toda transición Synap a estado de preparación MUST rechazarse mientras hold=`Si`. Al aprobar Finanzas MUST poner hold=`No`. El contrato para VB6 `Pedido_prep` MUST documentarse: denegar si `credito_hold_prep='Si'` (fallback: `autorizacion_sistema='No Autorizado'` si la columna aún no existe).

#### Scenario: Hold bloquea preparación Synap

- **GIVEN** PED con `credito_hold_prep='Si'`
- **WHEN** un operador intenta pasar a «En preparación» desde Synap
- **THEN** MUST rechazarse con mensaje en español
- **AND** MUST NOT cambiar el estado de preparación

#### Scenario: Aprobación libera hold

- **GIVEN** PED con hold activo pendiente Finanzas
- **WHEN** usuario con `finance.credito.aprobar` aprueba
- **THEN** MUST setear `credito_hold_prep='No'` y `autorizacion_sistema='Autorizado'`

---

### Requirement: Corrección pedido masivo matriz

El servicio `pedido_masivo_matriz` MUST exponer límite de días y cupo monetario con claves semánticas correctas. MUST NOT mapear `cliente.Credito` ($) a la clave `credito_limite_dias`.

#### Scenario: Widget matriz con datos correctos

- **GIVEN** cliente con `Credito=50000` y `credito_limite_dias=30`
- **WHEN** la matriz masiva consulta crédito del cliente
- **THEN** MUST devolver cupo $ y límite días en campos distintos y nombrados correctamente
