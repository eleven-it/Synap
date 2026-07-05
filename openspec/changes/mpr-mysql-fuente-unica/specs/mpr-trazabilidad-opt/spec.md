# Delta for mpr-trazabilidad-opt

## MODIFIED Requirements

### Requirement: Servicio construir_trazabilidad_opt

El sistema MUST leer fuentes Synap desde **MySQL** (`mpr_parte`, `mpr_parte_linea`, `mpr_parte_ajuste`, `mpr_transicion_lote`, `mpr_armado_surtido_movimiento`, `mpr_imputacion_armado`, `mpr_envio_produccion`) usando `get_connection(base_empresa)`. MUST NOT depender de ORM Postgres tras cutover P3. Fuentes legacy (`lista_produccion_historico`, `movimiento_stock`) MUST seguir en MySQL.

(Previously: integración vía modelos Django Postgres + MySQL legacy.)

#### Scenario: Partes registrados aparecen con operario y turno

- DADO `mpr_parte` con `id_lista_produccion=42` en BD conectada
- CUANDO se llama `construir_trazabilidad_opt(base, 42)`
- ENTONCES eventos OPP MUST incluir operario, turno y fecha desde tablas `mpr_*`

#### Scenario: Historico inexistente no rompe

- DADO `lista_produccion_historico` ausente
- CUANDO se construye trazabilidad
- ENTONCES MUST completarse usando fuentes `mpr_*` y MSTOCK sin excepción

---

## ADDED Requirements

### Requirement: Trazabilidad por componente — mpr_evento (Fase P4)

En fase P4 el sistema MUST introducir **`mpr_evento`** MySQL para eventos sin `id_lista_produccion` (envíos tablero, partes E8). `construir_trazabilidad_componente(id_articulo)` MUST consultar `mpr_evento` además de MSTOCK.

#### Scenario: Parte E8 visible en trazabilidad componente

- DADO parte E8 con `id_lista_produccion` NULL en `mpr_parte`
- CUANDO se consulta trazabilidad del componente
- ENTONCES MUST aparecer evento tipo PARTE vinculado a `id_mpr_parte`
- Y MUST NOT requerir `id_lista_produccion`

---

## REMOVED Requirements

(Ninguno en P3; `lista_produccion_historico` se mantiene como fuente legacy hasta P4/P5.)

### Requirement: Dependencia exclusiva de Postgres para partes

(Razón: fuente única MySQL; partes en `mpr_parte`.)
