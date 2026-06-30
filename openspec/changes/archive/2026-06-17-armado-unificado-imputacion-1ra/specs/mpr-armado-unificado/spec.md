# mpr-armado-unificado Specification

## Purpose

Armado de packs **independiente de OPT** en dos modos: **1ra** (Semi → Terminado, BOM) y **2da** (2.ª selección → SKU 2.ª, composición libre). UX POS + carrito + lote.

## Requirements

### Requirement: Entrada canónica por menú

The system MUST expose Armado 1ra and Armado 2da desde menú MPR en `/mpr/armado/` con parámetro `modo=1ra` o `modo=2da`. The system MUST NOT require an open OPT to execute armado. The system SHOULD redirect legacy routes `/mpr/armado-surtido/` to `modo=2da` and `/mpr/opt/<id>/armado/` to `modo=1ra` without `id_lista`.

#### Scenario: Armado 2da sin OPT

- GIVEN depósito 2.ª con stock y packs `tipo_art_fab = 'Fabricado 2da'`
- WHEN el operario ejecuta un lote en modo 2da desde menú
- THEN MUST grabarse MSTOCK por pack exitoso
- AND MUST NOT validarse OPP ni `opt_puede_armado_surtido`

#### Scenario: Redirect legacy OPT armado

- GIVEN un usuario accede a `/mpr/opt/5/armado/`
- WHEN carga la URL
- THEN MUST redirigir a `/mpr/armado/?modo=1ra` con mensaje informativo único

### Requirement: Lote exclusivo por modo

The system MUST NOT permitir mezclar packs de modo 1ra y 2da en el mismo lote. The system MUST fijar origen según modo: Semi (1ra) o 2.ª selección (2da). Changing modo with items in cart MUST require confirmation and clear the cart.

#### Scenario: Cambio de modo con carrito ocupado

- GIVEN carrito con ítems modo 2da
- WHEN el usuario cambia a modo 1ra
- THEN MUST pedir confirmación
- AND MUST vaciar el carrito al confirmar

### Requirement: Armado 1ra con BOM

In modo 1ra, the system MUST listar packs con BOM (`ensamblado = 'Si'`). Composition MUST precargarse desde `en_abm_formula` and MUST NOT ser editable salvo cantidad de packs. Stock validation MUST usar depósito Semi configurado MPR.

#### Scenario: Pack 1ra sin stock semi

- GIVEN stock semi insuficiente para un ítem del lote
- WHEN ejecuta lote
- THEN MUST incluir ítem en fallidos
- AND MUST grabar ítems con stock suficiente (parcial)

### Requirement: Armado 2da composición libre

In modo 2da, the system MUST mantener reglas del armado surtido multi-lote (pack `Fabricado 2da`, composición libre, demanda agregada, máx. 20 ítems, un MSTOCK por pack).

#### Scenario: Paridad multi-lote 2da

- GIVEN lote 2da con dos packs distintos
- WHEN ejecuta lote
- THEN MUST generar dos MSTOCK independientes
- AND MUST mostrar modal con éxitos y fallos

### Requirement: Deprecación CTAs en OPT

The system MUST NOT mostrar tarjetas o botones de armado en `opt_detail.html`. Wizard paso 4 MUST NOT ser camino canónico; MAY enlazar a Armado 1ra en menú.

#### Scenario: Detalle OPT sin armado

- GIVEN OPT en proceso
- WHEN usuario abre detalle OPT
- THEN MUST NOT ver CTA «Armado surtido» ni «Armado desde esta OPT»

### Requirement: Cierre OPT sin armado

The system MUST permitir cerrar OPT cuando `SUM(cantidad_pendiente_prod) = 0` en sus líneas. Armado acumulado MUST NOT bloquear cierre.

#### Scenario: Cerrar OPT sin armado previo

- GIVEN OPT con pendiente OPP = 0 y sin MSTOCK de armado
- WHEN supervisor cierra OPT
- THEN MUST cerrarse correctamente
