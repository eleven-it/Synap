# Especificación — Armado surtido multi-pack (lote / carrito)

**Change:** `mpr-armado-surtido-multi-lote`  
**Estado:** especificación (pendiente diseño técnico / apply)  
**Fecha:** 26/06/2026  
**Ámbito:** MPR — pantalla `/mpr/armado-surtido/`, servicios `mpr/services.py`, tablas Synap `mpr_armado_surtido_*`, MySQL legacy (`movimiento_stock`, `stock`, `stock_deposito`).  
**Relacionado:** [SDD_ARMADO_SURTIDO_MULTI_LOTE.md](SDD_ARMADO_SURTIDO_MULTI_LOTE.md) (diseño), [SDD_ARMADO_SURTIDO_MVP.md](SDD_ARMADO_SURTIDO_MVP.md) (MVP implementado).

---

## 1. Contexto

El **MVP** de armado surtido permite **un pack por envío**: el operario completa pack, composición y operario, ejecuta, obtiene un MSTOCK y permanece en pantalla con formulario limpio.

**Limitación operativa:** en un turno de 2.ª selección el operario suele armar **varios packs distintos** antes de cerrar. Repetir el ciclo pack-a-pack sin visión del consumo agregado obliga a validar stock mentalmente cuando **el mismo componente** aparece en más de un pack.

**Objetivo de esta spec:** extender la misma pantalla con un **carrito (lote pendiente)** que acumule N armados, valide stock al agregar y al ejecutar, grabe **parcialmente** (un MSTOCK por pack exitoso) e informe en **modal** los ítems no grabados.

---

## 2. Decisiones de producto (normativas)

| ID | Tema | Decisión |
|----|------|----------|
| D1 | Comprobante | **Un MSTOCK por pack** (`codigo_movimiento` + `nro_comprobante` por armado exitoso). |
| D2 | Depósitos | **Origen y destino compartidos** en cabecera del lote (no por pack). |
| D3 | Validación stock | **Al agregar al lote** (estimación) **y al ejecutar** (definitivo en MySQL). |
| D4 | Componente compartido | Demanda **agregada** en todo el lote: `D[id] = Σ (cantidad_por_pack × cantidad_packs)`. |
| D5 | Atomicidad | **Parcial:** grabar ítems con stock suficiente; **modal** con fallidos. |
| D6 | UI | **Carrito:** formulario «armar pack» + tabla «lote pendiente». |
| D7 | Límite lote | Máximo **20** ítems (packs distintos) por lote. |
| D8 | OPT | Con `?id_lista=`, **cada armado exitoso** vincula esa OPT en detalle e historial (igual MVP). |

---

## 3. Capacidad modificada

### 3.1 `mpr-armado-surtido` (pantalla y POST)

**Comportamiento actual (MVP — a preservar en esencia):**

- GET `/mpr/armado-surtido/` con depósitos, packs `tipo_art_fab = 'Fabricado 2da'`, API stock origen, defaults 2.ª selección → Terminado.
- Un pack + composición + operario → `ejecutar_armado_surtido` → MSTOCK, `MprArmadoSurtidoMovimiento`, `PrecioCostoxU/R` desde `articulo.PrecioCosto`, FIFO lote.
- Tras éxito: permanece en pantalla.

**Comportamiento nuevo (requerido):**

1. **Cabecera de lote** (compartida): operario, origen, destino, detalle opcional, `id_lista` hidden si aplica.
2. **Zona «Armar pack»:** igual al MVP (pack, cantidad, composición, búsqueda stock).
3. **Acción «Agregar al lote»:** valida ítem; lo añade al carrito; limpia zona armar pack (no graba MSTOCK).
4. **Tabla «Lote pendiente»:** filas con pack, cantidad, nº componentes, acciones editar / quitar; **resumen consumo agregado** por componente.
5. **Acción «Ejecutar lote»:** POST del lote completo; backend procesa en **orden de filas**; resultado parcial + modal.
6. **Post-ejecución:** ítems **exitosos** salen del carrito; **fallidos** permanecen; mensaje flash resumen; modal detalle.

**Fuera de alcance:**

- Depósitos distintos por pack en el mismo lote.
- Un solo MSTOCK para todo el lote.
- Plantillas de composición guardadas.
- Tabla Django `MprArmadoSurtidoLote` (fase posterior).
- Acordeón con varios packs editables simultáneamente en pantalla.

---

## 4. Modelo de datos (contrato)

### 4.1 Cabecera lote

| Campo | Tipo | Obligatorio | Notas |
|-------|------|-------------|-------|
| `deposito_origen` | int | Sí | Mismo criterio MVP |
| `deposito_destino` | int | Sí | ≠ origen |
| `id_operario` | int | Sí | Un operario por lote |
| `detalle` | string ≤ 200 | No | Cabecera movimiento |
| `id_lista` | int | No | OPT; validar `opt_puede_armado_surtido` si presente |

### 4.2 Ítem del lote

| Campo | Tipo | Obligatorio | Notas |
|-------|------|-------------|-------|
| `id_articulo_pack` | int | Sí | `tipo_art_fab = 'Fabricado 2da'` |
| `cantidad_packs` | int ≥ 1 | Sí | Entero |
| `lineas` | array | Sí, ≥ 1 | Ver §4.3 |

### 4.3 Línea de composición (por ítem)

| Campo | Tipo | Obligatorio | Notas |
|-------|------|-------------|-------|
| `id_articulo` | int | Sí | Componente |
| `cantidad_por_pack` | int ≥ 1 | Sí | Entero |

### 4.4 Payload POST (normativo)

Campo hidden `lote_json` (UTF-8 JSON):

```json
{
  "armados": [
    {
      "id_articulo_pack": 1342,
      "cantidad_packs": 2,
      "lineas": [
        {"id_articulo": 813, "cantidad_por_pack": 3}
      ]
    }
  ]
}
```

Cabecera en campos de formulario HTML estándar (`deposito_origen`, `deposito_destino`, `id_operario`, `detalle`, `id_lista`).

### 4.5 Respuesta ejecución lote (servidor)

```json
{
  "exitosos": [
    {
      "id_articulo_pack": 1342,
      "codigo_articulo_pack": "1.1.1337",
      "descripcion_articulo_pack": "Pack surtido A",
      "cantidad_packs": 2,
      "codigo_movimiento": 17,
      "nro_comprobante": "0001-00000014"
    }
  ],
  "fallidos": [
    {
      "id_articulo_pack": 1500,
      "codigo_articulo_pack": "1.1.1500",
      "descripcion_articulo_pack": "Pack surtido B",
      "cantidad_packs": 1,
      "error": "Stock insuficiente de 1.1.809 en origen: tiene 2, se necesitan 5."
    }
  ]
}
```

Persistencia en sesión Django (`request.session['armado_surtido_resultado_lote']`) tras POST para renderizar modal en GET redirect.

---

## 5. Requisitos funcionales

### RF1 — Agregar pack al lote

**Dado** cabecera con origen/destino/operario válidos y un pack con composición válida (MVP),  
**cuando** el operario pulsa **Agregar al lote**,  
**entonces** el ítem se añade al carrito, se recalcula el resumen de consumo agregado y se limpia el formulario de armado (pack + composición).

### RF2 — Validación stock al agregar

**Dado** un componente con saldo `S` en origen y demanda ya reservada `R` por otros ítems del lote,  
**cuando** se intenta agregar un ítem cuya demanda incremental `Δ` cumple `R + Δ > S`,  
**entonces** el sistema **no** agrega el ítem y muestra mensaje indicando artículo, necesario, disponible estimado.

### RF3 — Pack duplicado en lote

**Dado** un pack `P` ya presente en el lote,  
**cuando** se intenta agregar otro ítem con el mismo `id_articulo_pack`,  
**entonces** el sistema rechaza con mensaje «Edite la fila existente del lote» (no duplicar filas).

### RF4 — Pack como componente de otro ítem

**Dado** un `IDArt` usado como pack en un ítem del lote,  
**cuando** el mismo `IDArt` aparece como componente en otro ítem (o viceversa),  
**entonces** el sistema rechaza al agregar con mensaje claro.

### RF5 — Ejecutar lote con al menos un ítem

**Dado** lote con ≥ 1 ítem y cabecera válida,  
**cuando** el operario pulsa **Ejecutar lote**,  
**entonces** el backend procesa ítems **en orden de tabla** (FIFO de captura).

### RF6 — Grabación parcial (D5)

**Dado** un lote donde el ítem en posición *k* falla por stock (u otro error de negocio),  
**cuando** se ejecuta el lote,  
**entonces** los ítems *1 … k−1* y *k+1 … n* que alcancen stock se graban (cada uno con su MSTOCK); el ítem *k* figura en `fallidos` sin revertir los ya confirmados.

### RF7 — Modal resultado

**Cuando** finaliza la ejecución del lote,  
**entonces** se muestra modal con tablas **Grabados** y **No grabados** (pack, cantidad, comprobante o motivo); al cerrar, el carrito contiene solo fallidos (si los hay).

### RF8 — Revalidación stock al ejecutar

**Dado** saldo cambió entre agregar y ejecutar,  
**cuando** se ejecuta el lote,  
**entonces** la validación definitiva es contra MySQL (`FOR UPDATE` por ítem); el ítem fallido aparece en modal con motivo actualizado.

### RF9 — Herencia MVP por ítem exitoso

**Por cada ítem exitoso** deben cumplirse las garantías MVP: salidas componentes origen, entrada pack destino, `PrecioCostoxU/R`, composición Synap, historial OPT si `id_lista`, FIFO lote en componentes seriados.

### RF10 — Límite 20 ítems

**Cuando** el lote ya tiene 20 ítems,  
**entonces** «Agregar al lote» se deshabilita o rechaza con mensaje «Máximo 20 armados por lote».

### RF11 — Lote vacío

**Cuando** se ejecuta con carrito vacío,  
**entonces** error «Agregue al menos un armado al lote»; sin MSTOCK.

### RF12 — Permanecer en pantalla

**Después** de ejecutar (éxito total, parcial o solo fallidos),  
**entonces** redirect a `/mpr/armado-surtido/` (con `?id_lista=` si aplica); no redirect a tablero.

---

## 6. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF1 | UI canon MPR: `base_mpr.html`, patrones wizard/OPT; textos en español. |
| RNF2 | Tipos AdministraNET: `core.utils.administranet_types` en lectura/escritura MySQL. |
| RNF3 | Tests unitarios servicios lote sin MySQL obligatorio; tests vista con mocks. |
| RNF4 | Idempotencia UX: overlay loading + deshabilitar submit durante POST (`mpr-post-loading`). |
| RNF5 | Tamaño POST: `lote_json` acotado a 20 ítems × composición razonable (< 64 KB). |

---

## 7. API auxiliar (recomendada)

### GET `/mpr/api/armado-surtido/validar-item-lote/`

**Query:**

| Parámetro | Descripción |
|-----------|-------------|
| `deposito` | Origen |
| `lote_json` | Lote actual (sin ítem candidato) URL-encoded |
| `item_json` | Ítem candidato |

**Respuesta 200:**

```json
{
  "ok": true,
  "conflictos": []
}
```

```json
{
  "ok": false,
  "conflictos": [
    {
      "id_articulo": 813,
      "codigo_articulo": "1.1.809",
      "necesario": 8,
      "disponible": 5,
      "mensaje": "Stock insuficiente para agregar al lote."
    }
  ]
}
```

La validación en cliente (Alpine) puede operar sin esta API; la API es **fuente de verdad** opcional para agregar.

---

## 8. Servicios backend (contrato)

| Función | Responsabilidad |
|---------|-----------------|
| `calcular_demanda_agregada_lote(armados)` | `Dict[id_articulo, Decimal]` demanda total componentes. |
| `validar_reglas_lote_armado_surtido(armados)` | Duplicados pack, pack↔componente cruzado, límite 20, composición no vacía. |
| `validar_stock_item_lote(...)` | Stock MySQL para un ítem dado demanda previa acumulada. |
| `_ejecutar_armado_surtido_tx(cursor, ...)` | Núcleo transaccional MVP (refactor desde `ejecutar_armado_surtido`). |
| `ejecutar_lote_armado_surtido(...)` | Loop ordenado; commit por ítem exitoso; retorna §4.5. |
| `parse_lote_armado_surtido_post(request)` | Parse `lote_json` + cabecera; normalización tipos. |

`ejecutar_armado_surtido` público **MUST** seguir funcionando para llamadas de un solo ítem (delegar en lote de 1 elemento o mantener wrapper).

---

## 9. Escenarios de aceptación

| ID | Escenario | Resultado esperado |
|----|-----------|-------------------|
| AC-M1 | 2 packs distintos, stock OK | Lote 2 filas; resumen consumo correcto; 2 MSTOCK al ejecutar. |
| AC-M2 | Mismo componente en 2 packs; suma > saldo | Bloqueo al agregar 2.º (o al ejecutar si saldo cambió). |
| AC-M3 | 3 ítems; falla el 2.º | 1.º y 3.º grabados; 2.º en modal; 2.º sigue en carrito. |
| AC-M4 | Ejecutar lote vacío | Error RF11. |
| AC-M5 | Pack no `Fabricado 2da` | Rechazo al agregar o al ejecutar. |
| AC-M6 | `?id_lista=22` | Exitosos con OPT en historial. |
| AC-M7 | Componente con lote FIFO, 2 packs | Consumo FIFO por ítem en orden de ejecución. |
| AC-M8 | 21.º ítem | Rechazo RF10. |
| AC-M9 | Editar fila lote | Carga formulario superior; al re-agregar actualiza fila. |
| AC-M10 | Solo fallidos tras ejecución | Carrito muestra solo fallidos; operario puede quitar o corregir. |

---

## 10. Criterios de verificación (tests)

| Test | Tipo | Archivo sugerido |
|------|------|------------------|
| `calcular_demanda_agregada_lote` varios packs | Unit | `mpr/tests/test_armado_surtido_lote.py` |
| Reglas duplicado pack / cruce pack-componente | Unit | idem |
| `ejecutar_lote_armado_surtido` parcial (mock cursor) | Unit | idem |
| Parse POST `lote_json` | Unit | idem |
| Vista POST redirect + sesión modal | Integration | `mpr/tests/test_armado_surtido_lote_view.py` (opcional) |

---

## 11. Dependencias

| Artefacto | Rol |
|-----------|-----|
| [SDD_ARMADO_SURTIDO_MULTI_LOTE.md](SDD_ARMADO_SURTIDO_MULTI_LOTE.md) | Diseño / decisiones / UI wireframe |
| [SDD_ARMADO_SURTIDO_MVP.md](SDD_ARMADO_SURTIDO_MVP.md) | Baseline implementado |
| [ARTICULO_PACK_COMPONENTE_MPR.md](ARTICULO_PACK_COMPONENTE_MPR.md) | Semántica pack/componente |
| [FUENTE_VERDAD_UI_REPORTES_MPR.md](../general/FUENTE_VERDAD_UI_REPORTES_MPR.md) | UI canon |
| `mpr/services.py` | Servicios existentes armado surtido |
| `mpr/templates/mpr/armado_surtido.html` | Plantilla a extender |

---

## 12. Seguimiento SDD

| Fase | Artefacto | Estado |
|------|-----------|--------|
| Propuesta / diseño | [SDD_ARMADO_SURTIDO_MULTI_LOTE.md](SDD_ARMADO_SURTIDO_MULTI_LOTE.md) | Acordado |
| **Especificación** | **Este documento** | **Actual** |
| Diseño técnico | [DESIGN_ARMADO_SURTIDO_MULTI_LOTE.md](DESIGN_ARMADO_SURTIDO_MULTI_LOTE.md) | **Actual** |
| Tareas | [TASKS_ARMADO_SURTIDO_MULTI_LOTE.md](TASKS_ARMADO_SURTIDO_MULTI_LOTE.md) | **Actual** |
| Apply | Código + tests | **Implementado** (Fases 1–7; 42 tests auto) |
| Verify | AC-M1 … AC-M10 | Pendiente QA manual en base prueba |

---

*Especificación normativa para implementación. Cualquier cambio de alcance debe actualizar §2 y §5 antes del apply.*
