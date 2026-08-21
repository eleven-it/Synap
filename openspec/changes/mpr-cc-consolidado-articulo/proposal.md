# Propuesta — Control de calidad consolidado por artículo

**Change:** `mpr-cc-consolidado-articulo`  
**Fecha:** 20/08/2026  
**Diseño:** [design.md](./design.md)  
**Plan de producto (vinculante):** `docs/mpr/PLAN_CC_CONSOLIDADO_POR_ARTICULO.md`

---

## 1. Intención

Cambiar Control de calidad (`/mpr/tablero-produccion/clasificacion-produccion/`) para clasificar el **saldo vivo de Depósito Producción** en un **bloque por artículo/día**, sin máquina y sin filtro Turno.

- **Semi elaborado:** un ingreso por artículo; ledger con `id_operario` y `id_mpr_turno` nulos.
- **2da / desperdicio:** por operario + turno del parte (máquinas colapsadas).
- **Huérfano** (saldo Producción sin parte): solo Semi; 2da/scrap rechazadas.
- **Tope:** `semi + Σ2da + Σscrap ≤ saldo vivo` con `SELECT … FOR UPDATE`.
- **Confirmación atómica por artículo** (no el best-effort de `transferir_stock_lote`).
- **Histórico:** no reescribir `mpr_transicion_lote` ni stock. Borradores viejos no se migran.

---

## 2. Problema

| Hoy | Dolor |
|-----|-------|
| Fila = máquina × artículo × turno × operario | Fragmenta la carga; no hay consolidado por artículo |
| Tope = parte + extra pool | Deja saldo Producción sin clasificar (huérfanos) y permite sobregiro entre filas |
| Semi por operario/máquina | Producto no quiere trazabilidad de Semi por operario |
| `transferir_stock_lote` best-effort | Semi puede salir y 2da fallar; el borrador se borra igual |
| Semi nuevo bloquea todos los turnos del parte | Impide seguir cargando parte el mismo día |

---

## 3. Alcance

### Incluido

- Grilla por bloque artículo; columna «Saldo producción»; sin Turno/Máquina en encabezado.
- Parser POST `semi_{art}`, `seg2da_…`, `scrap_…`; ignora `semi_*_op_*`.
- Wrapper CC atómico por artículo; `transferir_stock_lote` intacto.
- DDL 007 (`mpr_cc_borrador` / `_linea`, UK fecha, centinela 0) vía `catalog.py`.
- Bloqueo dual del parte: 2da/scrap **o** Semi histórico con operario.
- Filtro Solo pendiente; roster incluye saldo 0 y operarios confirmados.
- Tests S1–S9 / B1–B8 y docs MPR.

### Fuera de alcance

Migrar ledger histórico o borradores abiertos, planilla A4, prorrateo de Semi, corrección post-CC en la grilla, filtro por turno, rediseño visual.

---

## 4. Capabilities

### Modified

| Capability | Cambio |
|------------|--------|
| `mpr-clasificacion-operario-fabricante` | Bloque artículo, tope saldo vivo, Semi sin operario, huérfanos, borrador por fecha, bloqueo dual |
| `mpr-transiciones-lote` | Wrapper CC atómico por artículo; best-effort genérico intacto |
| `mpr-reporte-rendimiento-operario` | Semi `NULL` no entra al stack por operario; 2da/scrap sí |

No se crean capabilities nuevas. No se tocan `mpr-reporte-operario` ni `ui-fuente-verdad-reportes-mpr`.

---

## 5. Enfoque

Evolución controlada. El esquema de `mpr_transicion_lote` no cambia; cambia el convenio de escritura y la lectura agregada. Único DDL: borrador nuevo. Orden: auditoría SELECT → tests en rojo → DDL → servicio → POST atómico → bloqueo dual → UI → docs → verify.

---

## 6. Riesgos y rollback

- Reescritura de histórico Semi: prohibida (I3).
- Double-spend concurrente: lock de fila `stock_deposito`.
- Fallo parcial Semi/2da: TX MySQL por artículo.
- Rollback de código tras confirmar CC nuevo no es limpio (hueco visual en grilla vieja). Mitigación: Staging / empresa de prueba.
- Revertir deploy conjunto grilla+POST; no dropear tablas 007 en caliente; nunca prorratear Semi ni ajustar `stock_deposito` a mano.
