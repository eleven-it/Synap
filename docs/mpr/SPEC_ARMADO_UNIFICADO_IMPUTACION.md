# Especificación — Armado unificado 1ra/2da e imputación supervisor

**Change:** `armado-unificado-imputacion-1ra`  
**Estado:** especificación (17/06/2026)  
**OpenSpec:** `openspec/changes/armado-unificado-imputacion-1ra/specs/`  
**SDD:** [SDD_ARMADO_UNIFICADO_IMPUTACION.md](SDD_ARMADO_UNIFICADO_IMPUTACION.md)

---

## 1. Capabilities

| Capability | Tipo | Archivo OpenSpec |
|------------|------|------------------|
| `mpr-armado-unificado` | Nueva | `specs/mpr-armado-unificado/spec.md` |
| `mpr-imputacion-armado-1ra` | Nueva | `specs/mpr-imputacion-armado-1ra/spec.md` |
| `ui-fuente-verdad-reportes-mpr` | Delta | `specs/ui-fuente-verdad-reportes-mpr/spec.md` |

---

## 2. Requisitos normativos — Armado unificado

### R-A1 Entrada canónica

- MUST: menú MPR → `/mpr/armado/?modo=1ra|2da`.
- MUST NOT: exigir OPT abierta para ejecutar armado.
- SHOULD: redirect `/mpr/armado-surtido/` → `modo=2da`; `/mpr/opt/<id>/armado/` → `modo=1ra`.

### R-A2 Lote por modo

- MUST NOT: mezclar 1ra y 2da en un lote.
- MUST: origen Semi (1ra) o 2.ª selección (2da) según modo.
- MUST: confirmar y vaciar carrito al cambiar modo con ítems.

### R-A3 Armado 1ra

- MUST: packs con BOM; composición precargada no editable.
- MUST: validar stock en Semi.
- MUST: marcar MSTOCK con `estado_imputacion = pendiente`.

### R-A4 Armado 2da

- MUST: paridad [SPEC_ARMADO_SURTIDO_MULTI_LOTE.md](SPEC_ARMADO_SURTIDO_MULTI_LOTE.md).
- MUST NOT: gates `opt_puede_armado_surtido`.

### R-A5 Deprecación OPT

- MUST NOT: CTAs armado en `opt_detail`.
- MUST: `puede_cerrar` solo con pendiente OPP = 0.

---

## 3. Requisitos normativos — Imputación 1ra

### R-I1 Cola supervisor

- MUST: listar MSTOCK 1ra pendientes; agrupar UI por lote.
- MUST NOT: incluir MSTOCK 2da.

### R-I2 Permiso

- MUST: permiso `mpr.imputar_armado_1ra`; 403 sin él.

### R-I3 Unidad MSTOCK

- MUST: imputar por `codigo_movimiento`.
- MUST NOT: `Σ imputado > cantidad_armada`.

### R-I4 FIFO

- SHOULD: sugerir FIFO sobre demanda abierta mismo `id_articulo`.
- MUST: registrar `origen_regla` FIFO | MANUAL.

### R-I5 Legacy

- MUST: actualizar `lista_produccion_detalle` y `estado_pedido_opt` al confirmar.

---

## 4. Criterios de aceptación (resumen)

Ver AC-A*, AC-B*, AC-C* en [SDD_ARMADO_UNIFICADO_IMPUTACION.md](SDD_ARMADO_UNIFICADO_IMPUTACION.md) §9.

---

## 5. Siguiente fase

→ [DESIGN_ARMADO_UNIFICADO_IMPUTACION.md](DESIGN_ARMADO_UNIFICADO_IMPUTACION.md) · `/sdd-continue` → **tasks**
