# TPV Synap — Paridad funcional con AdministraNET (cambio `paridad-tpv-administranet`)

## Purpose

Definir requisitos para que el **TPV en Synap** (kiosco en **modo TPV**) se comporte de forma **alineada** con los procesos de **pago**, **validación previa a confirmar** y **tratamiento de stock** del formulario legacy **`TPV.frm`**, sin exigir la misma matriz de reglas al **modo autoservicio** (`modoTpv === false`).

Referencia de alcance: `docs/general/PARIDAD_TPV_ADMINISTRANET_ALCANCE.md`.

## Requirements

### Requirement: Ámbito exclusivo modo TPV

The system MUST apply las extensiones de paridad descritas en este spec **solo** cuando la sesión de kiosco indique **modo TPV** (p. ej. `modoTpv === true` en `kioscoApp`).

The system MUST NOT exigir al flujo **self-checkout** (sin modo TPV) validaciones, pasos de UI o reglas de cobro añadidas únicamente para paridad con `TPV.frm`, salvo decisión explícita de producto documentada.

#### Scenario: Autoservicio sin ramas TPV

- GIVEN un kiosco en modo autoservicio (`modoTpv` falso)
- WHEN el usuario completa una venta
- THEN no se aplica la capa de validaciones “solo TPV” definida en fases posteriores de implementación (límites caja, crédito extendido, cheques, etc.) salvo que ya existan transversalmente

#### Scenario: TPV con barra y medios extendidos

- GIVEN un kiosco en modo TPV (`modoTpv` verdadero)
- WHEN el operador confirma medios de cobro y la venta
- THEN el sistema aplica las reglas de paridad implementadas según fase (ver requisitos siguientes) y la persistencia legacy alineada al diseño

### Requirement: Cierre de medios de pago coherente con TPV.frm (objetivo)

The system MUST, en modo TPV, converger hacia el criterio legacy de que la **suma de importes por medio** (efectivo, tarjeta, cuenta corriente, cheques, intereses de tarjeta según corresponda) **cierra con el total** del comprobante, equivalente a la lógica de `Aceptar_Click` en VB6 (validación de suma = total y al menos un medio).

**Nota de implementación:** el detalle de columnas (p. ej. `interes_tarjeta_total`) se materializa en `design.md` y tareas; este requisito fija el **comportamiento observable**.

#### Scenario: Suma de medios distinta del total en TPV

- GIVEN modo TPV y total de venta T
- WHEN la suma declarada de medios ≠ T (tolerancia numérica definida en diseño)
- THEN el sistema MUST rechazar la confirmación con mensaje claro al operador

#### Scenario: Ningún medio informado en TPV

- GIVEN modo TPV
- WHEN todos los importes de medios son cero
- THEN el sistema MUST rechazar la confirmación (equivalente funcional a “al menos un medio de cobro”)

### Requirement: Validaciones pre-guardado según fase

The system SHOULD, en modo TPV y según priorización por fase, acercarse a las validaciones de `Validaciones_Factura` y `Guardar_Factura` previas al commit: obligatoriedad de **vendedor** / **PV** / **series** cuando los flags de empresa o permisos lo exijan; **límite de extracción de caja**; **límites de crédito** para clientes no consumidor final.

Cada subconjunto MUST documentarse como entregable de fase en `tasks.md` o design (no todo en un único PR obligatorio).

#### Scenario: Series incompletas con artículos seriados

- GIVEN líneas con artículo seriado y cantidad sin completar series en modo TPV
- WHEN el usuario intenta confirmar
- THEN el sistema MUST bloquear hasta resolver series (paridad con validación serie en VB6)

### Requirement: Stock — validación y descuento legacy

The system MUST mantener el modelo actual de Synap donde el **descuento real de `stock_deposito`** ocurre en **`ConfirmationService.confirmar`** dentro de transacción, con **UPDATE condicional** de saldo.

The system SHOULD, para modo TPV, evaluar en diseño/revisiones posteriores **riesgo de concurrencia** (dos mostradores restando el mismo saldo) y documentar mitigación (reintento, mensaje, bloqueo optimista) sin cambiar el contrato del autoservicio.

#### Scenario: Stock insuficiente al confirmar

- GIVEN saldo insuficiente respecto a cantidades vendidas al momento del commit
- WHEN se ejecuta la confirmación
- THEN el sistema MUST fallar la operación sin commit parcial de venta (comportamiento alineado a integridad legacy)

### Requirement: Persistencia compartida sin romper autoservicio

The system MUST NOT introducir en `ConfirmationService` ramas que alteren el resultado de confirmación para carritos **autoservicio** salvo corrección de bug o requisito transversal aprobado.

Cambios específicos TPV SHOULD usar parámetros explícitos o contexto de carrito/kiosco que indique modo TPV.

### Requirement: Exclusiones explícitas de esta versión de spec

The system MAY omitir en la primera oleada de implementación: **notas de crédito** desde este mismo flujo, **percepciones** completas si no están en el carrito TPV actual, **vínculos pedido/remito** si el TPV web no los expone.

Such omissions MUST listarse en `design.md` bajo “Fuera de alcance v1”.

## Cross-references

- Legacy: `administranet_vb6/Formularios/TPV.frm` (`Aceptar_Click`, `Validaciones_Factura`, `Guardar_Factura`).
- Synap: `self_checkout/services/confirmation_service.py`, `cart_service.py`, `stock_service.py`, `self_checkout/templates/self_checkout/kiosco.html`.
