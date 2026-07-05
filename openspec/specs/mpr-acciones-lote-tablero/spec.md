# mpr-acciones-lote-tablero

## Purpose

Gestión de la **clasificación de producción en modo lote** mediante una **pantalla única**
("Clasificación de producción") accesible desde la barra global del tablero de producción.

A partir de la **Etapa 10**, el planchado deja de ser una etapa con stock (es un momento
dentro de la producción y nunca deja saldo). La clasificación sale **directo de Producción**
hacia `{SemiElaborado | 2daSeleccion | Scrap}`. Esta pantalla **reemplaza** las dos pantallas
de la Etapa 9 (Inspección `Producción→Planchado/Scrap` y Clasificación `Planchado→2da/Semi`)
y sus dos botones globales por **un solo botón** y una sola pantalla.

Reutiliza `transferir_stock_entre_etapas` (Etapa 5, ahora con parámetro `fecha`) a través del
wrapper `transferir_stock_lote` (best-effort, ver `mpr-transiciones-lote`).

Origen del cambio: change SDD `mpr-pipeline-etapa10-clasificacion-consolidada` (2026-07-03).
Documento operativo asociado: `docs/mpr/ACCIONES_LOTE_TABLERO.md`.

---

## Requirements

### Requirement: Grilla de Clasificación de Producción

`construir_grilla_clasificacion_produccion(base_empresa)` MUST retornar
`{componentes: [...], componentes_vacio: bool}` con los componentes que tienen
`stock_deposito[art, Produccion] > 0`, cada entrada: `{id_articulo, codigo_manual, descripcion, disponible}`.
MUST filtrar por `base_empresa` y MUST retornar lista vacía (sin error) si no hay stock.
El universo de candidatos se obtiene por consulta directa
`stock_deposito JOIN deposito WHERE tipo_mpr='Produccion' AND saldo>0`, confirmado con `_pivot_stock_por_tipo_mpr`.

#### Scenario: Producción con stock disponible

- DADO componente A con `stock_deposito[A, Produccion]=15` en `base='EMP1'`
- CUANDO se llama `construir_grilla_clasificacion_produccion('EMP1')`
- ENTONCES retorna `[{id_articulo: A, disponible: 15, codigo_manual, descripcion}]`

#### Scenario: Sin stock en Producción

- DADO ningún componente con `stock Producción > 0` en `base='EMP1'`
- CUANDO se llama `construir_grilla_clasificacion_produccion('EMP1')`
- ENTONCES retorna `componentes_vacio=True` y lista vacía sin error

---

### Requirement: Pantalla Clasificación de Producción (GET)

`ClasificacionProduccionView` MUST responder GET con `clasificacion_produccion.html` pasando:
grilla desde `construir_grilla_clasificacion_produccion`, `titulo='Clasificación de producción'`,
`tipo_origen='Produccion'`, `fecha_hoy` en `dd/MM/yyyy`, y `url_registrar=mpr:clasificacion_produccion_registrar`.

#### Scenario: GET renderiza grilla

- DADO usuario autenticado con `base_empresa` activa y componentes con Producción > 0
- CUANDO hace GET a `/mpr/tablero-produccion/clasificacion-produccion/`
- ENTONCES HTTP 200; grilla lista componentes con `disponible` correcto y selector de fecha

---

### Requirement: Registro de Clasificación de Producción (POST)

`RegistrarClasificacionProduccionView` MUST parsear POST con una `fecha` (`dd/MM/yyyy`, obligatoria)
y prefijos `semi_{id}`, `seg2da_{id}`, `scrap_{id}`, `disponible_{id}`.

- MUST rechazar (redirect con mensaje en español, sin registrar) si la `fecha` es inválida o falta.
- Por cada componente con al menos un destino > 0 MUST validar
  `semi_{id} + seg2da_{id} + scrap_{id} <= disponible_real` — BLOQUEO si excede (fila saltada; mensaje en español).
- El `disponible_real` MUST obtenerse del stock real en BD (`_pivot_stock_por_tipo_mpr`),
  NO del valor `disponible_{id}` enviado por el cliente.
- Para filas válidas MUST llamar `transferir_stock_lote(..., fecha=<fecha_parte>)` con un item por
  destino con cantidad > 0 (origen `Produccion`).
- MUST redirigir a la pantalla con mensajes de éxito/error consumidos inline.

#### Scenario: Distribución válida en tres destinos

- DADO componente A con `disponible=8`; fecha=`03/07/2026`; POST `semi_A=5, seg2da_A=2, scrap_A=1`
- CUANDO se procesa `RegistrarClasificacionProduccionView`
- ENTONCES 3 transferencias (Produccion→SemiElaborado, →2daSeleccion, →Scrap); redirect HTTP 302

#### Scenario: Suma excede disponible → BLOQUEO por fila

- DADO componente A con stock real `Produccion=5`; POST `semi_A=4, seg2da_A=3, scrap_A=1` (suma=8>5)
- CUANDO se procesa la vista
- ENTONCES NO se emite MSTOCK para A; mensaje en español; otras filas válidas se procesan

#### Scenario: Disponible manipulado en cliente → server re-valida

- DADO componente A con stock real `Produccion=5`; POST `disponible_A=100, semi_A=80`
- CUANDO se procesa la vista
- ENTONCES la vista consulta stock real desde BD; detecta `80 > 5`; BLOQUEO sin emitir MSTOCK

#### Scenario: Fecha del parte se propaga al asiento

- DADO POST con `fecha=03/07/2026` y `semi_A=5` válido
- CUANDO se procesa la vista
- ENTONCES `transferir_stock_lote` recibe `fecha=date(2026,7,3)` y el MSTOCK se fecha ese día

#### Scenario: Fecha inválida bloquea

- DADO POST sin campo `fecha` (o con formato inválido)
- CUANDO se procesa la vista
- ENTONCES redirige con mensaje de error en español; NO se llama a `transferir_stock_lote`

---

### Requirement: No Funcionales Clasificación de Producción

| Requisito | Norma |
|-----------|-------|
| Scoping | Todas las queries MUST filtrar por `base_empresa` |
| Auth | Las vistas MUST usar `MprLoginRequiredMixin` |
| Tipos | reads/writes MySQL MUST usar `to_int_or_none`, `to_decimal_or_none`, `str_or_default` |
| Fechas UI | Fecha de carga MUST enviarse/mostrarse en `dd/MM/yyyy` |
| Mensajes | MUST estar en español; consumidos inline en la propia pantalla |
| Template | MUST extender `base_mpr.html` (`clasificacion_produccion.html`, estética slate del tablero) |
| Schema | MUST NOT requerir migración de BD |
| Rutas | Bajo prefijo `/mpr/tablero-produccion/` |

#### Scenario: Usuario no autenticado

- DADO usuario no autenticado
- CUANDO hace GET a `/mpr/tablero-produccion/clasificacion-produccion/`
- ENTONCES redirige a login (HTTP 302)

#### Scenario: Aislación base_empresa

- DADO componentes de `EMP1` y `EMP2`
- CUANDO `construir_grilla_clasificacion_produccion('EMP1')` se ejecuta
- ENTONCES retorna solo componentes de `EMP1`

---

## Fuera de Alcance

- Tabla de auditoría agrupada `MprTransicionLoteMasiva`
- Drill-down por fila reactivado
- Armado de packs (Terminado)
- Migración de esquema MySQL (el depósito Planchado puede quedar sin uso)

---

## Notes

- **Superseción:** esta capability reemplaza la versión Etapa 9 (dos pantallas Inspección/Clasificación
  y wrapper sin fecha). Las vistas `InspeccionLoteView`, `RegistrarInspeccionLoteView`,
  `ClasificacionLoteView`, `RegistrarClasificacionLoteView`, sus URLs, las grillas
  `construir_grilla_inspeccion`/`construir_grilla_clasificacion` y el template
  `transicion_lote_masiva.html` fueron **eliminados**.
- **Best-effort:** `transferir_stock_lote` no usa `atomic()` entre conexiones MySQL legacy;
  cada transferencia emite su propio MSTOCK auditable, ahora fechado con la fecha del parte.
- **Guard definitivo:** la re-validación server-side del `disponible_{id}` contra
  `_pivot_stock_por_tipo_mpr` es la protección real; el feedback Alpine.js es UX auxiliar no normativo.
- **Estado final:** suite `mpr` 390/390 (skip=1), 0 regresiones; lints limpios; sin migración de esquema.
