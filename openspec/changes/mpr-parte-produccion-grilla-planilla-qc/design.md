# Design: Grilla analista alineada a planilla QC

## Technical Approach

Refactor de `/mpr/parte-produccion/` para pivotear la grilla a **máquina × artículo** (orden planilla QC) con columnas **Mañana | Tarde | Noche**. Se reutiliza `construir_datos_planilla_control_calidad` (`mpr/services_maquina_linea.py`) como fuente de filas/orden/roster y se enriquece con cupo `Fabricando` (de `services.py`) y precarga de partes. La persistencia reutiliza el patrón ya probado del móvil (`parte_movil._insertar_lineas`), que ya escribe `id_mpr_maquina`. **No requiere DDL** (columnas de `mpr_parte_linea` ya existen por `mpr/sql/004`). Alinea con specs `mpr-opp-parte-produccion` y `ui-fuente-verdad-reportes-mpr`.

## Architecture Decisions

| # | Decisión | Elegido | Alternativa rechazada | Rationale |
|---|----------|---------|-----------------------|-----------|
| ADR-1 | Pivote grilla | Filas máquina×artículo; turnos M/T/N en columnas | Mantener operario×componente; agregar Color/Talle | Paridad con planilla física QC y con móvil; Color/Talle fuera de scope y explota combinatoria |
| ADR-2 | Builder | **Nuevo** servicio `construir_grilla_parte_planilla` que envuelve `construir_datos_planilla_control_calidad` | Refactor in-place de `construir_grilla_parte` | `construir_grilla_parte` sirve al tablero E8; tocarlo arriesga regresión. Servicio dedicado aísla el cambio |
| ADR-3 | Persistencia máquina | Extender `crear_parte_con_lineas` para escribir `id_mpr_maquina`,`maquina_nombre`,`cantidad_declarada`(=`cantidad_aprobada`, `gap=0`) reusando patrón `_insertar_lineas` | Nueva función paralela | Evita duplicar SQL; columna ya existe (sin DDL) |
| ADR-4 | Operario por celda | Heredar de `operadores_por_linea` (roster línea/turno): 1→hidden; varios→`<select>` Synap; sin roster→celda `disabled` + aviso ES | Operario único global por parte | Refleja el roster real por turno; ya provisto por el builder de planilla |
| ADR-5 | Validación cupo | Bloqueante por fila: Σ pares equiv (docenas×12+pares) de M+T+N ≤ `Fabricando`; rechaza el submit completo con mensaje ES | Warning no bloqueante por componente (E8) | Spec exige rechazo; sustituye el warning E8 en este flujo |
| ADR-6 | Guardado | Un POST → **un `MprParte` por turno** (hasta 3) en una sola `transaction.atomic()`; idempotente por `uk_mpr_parte_linea_maq` | Parte multi-turno único; 3 submits | `MprParte.turno` es FK NOT NULL y la precarga es por turno; atómico y consistente |

## Data Flow

    GET filtros(fecha,línea,máquina,marcas,q)
        │
        ▼
    ParteProduccionView ─→ construir_grilla_parte_planilla
        │                     ├─ construir_datos_planilla_control_calidad (filas/orden/roster)
        │                     ├─ _fabricando_por_componentes (cupo por artículo)
        │                     └─ cantidades_parte_planilla_por_fecha (precarga M/T/N)
        ▼
    parte_produccion.html (tabla sticky, celdas docenas/pares + operario)
        │  POST parte_maq_{maq}_art_{art}_turno_{turno}_{docenas|pares} + op_...
        ▼
    RegistrarParteProduccionView ─→ registrar_parte_produccion
        ├─ validar cupo cross-turno (ADR-5) ── falla ─→ messages.error (ES)
        └─ por turno: crear_parte_con_lineas(id_mpr_maquina,...) ─→ asiento físico OPP (E8)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `mpr/services_maquina_linea.py` | Modify | `construir_grilla_parte_planilla(base, fecha, id_linea, id_maquina, marcas, q)`: filas máquina×artículo con `fabricando`, `ingresado`, `turnos[{docenas,pares,operarios[]}]`, `roster_por_turno` |
| `mpr/services.py` | Modify | `registrar_parte_produccion`: aceptar líneas con `id_mpr_maquina`/`maquina_nombre`/`turno`; agrupar y **validar cupo por fila**; crear un parte por turno. `construir_grilla_parte` sin cambios (E8) |
| `mpr/repositories/parte.py` | Modify | `crear_parte_con_lineas`: persistir `id_mpr_maquina`,`maquina_nombre`,`cantidad_declarada`,`cantidad_aprobada`,`gap=0`; helper de precarga por (fecha,máquina,art,turno) |
| `mpr/views.py` | Modify | `ParteProduccionView` (filtros server-side + builder nuevo); `RegistrarParteProduccionView` + `_parte_lineas_desde_post` (parseo `parte_maq_{}_art_{}_turno_{}`) |
| `mpr/templates/mpr/parte_produccion.html` | Modify | Layout planilla QC: sticky máquina+artículo+cupo, 3 columnas turno, modales Synap, filtros MPR |
| `mpr/tests/test_parte_planilla_qc.py` | Create | Grilla, cupo cross-turno, persistencia máquina, precarga, roster |
| `docs/mpr/PARTE_PRODUCCION.md` | Modify | Flujo analista planilla QC |

## Interfaces / Contracts

```python
# Payload por fila de grilla
{ "id_mpr_maquina": int, "maquina_nombre": str, "id_articulo": int,
  "descripcion": str, "codigo_tooltip": str,
  "fabricando": Decimal, "ingresado": int,
  "turnos": { turno_id: {"docenas": int, "pares": int,
                          "operarios": [{"id_operario": int, "nombre": str}]} } }
# Celda POST: parte_maq_{id_maq}_art_{id_art}_turno_{id_turno}_docenas|_pares
#             parte_maq_{id_maq}_art_{id_art}_turno_{id_turno}_op
```

## UX / Densidad (canon MPR)

Columnas sticky: **Máquina + Artículo + Cupo Fabricando** (izquierda). Tab order por fila: Mañana→Tarde→Noche→siguiente fila (docenas antes que pares por celda). Densidad media, tono Synap claro/confiable. Nombre de artículo sin código (código en `title`/tooltip). Toggle docenas/pares. Extiende `mpr/base_mpr.html`; feedback vía `mprShowAviso`/`SynapMessages`; sin `alert/confirm/prompt`.

## Testing Strategy

| Layer | Qué | Cómo |
|-------|-----|------|
| Unit | Builder orden==planilla; cupo cross-turno; herencia operario | `docker exec Synap_app python manage.py test mpr` |
| Integration | POST multi-turno persiste `id_mpr_maquina`; precarga; rechazo sobre cupo | Test vista con roster/máquina fixtures |
| Regresión | `construir_grilla_parte` (E8) y `/mpr/mi-parte/` intactos | Tests existentes |

## Migration / Rollout

Sin DDL (columnas ya en `mpr_parte_linea` vía SQL 004). Partes históricos con `id_mpr_maquina` NULL siguen legibles (lecturas tolerantes). Rollback = revertir servicio/vista/template.

## Open Questions

- [ ] Artículo en varias máquinas: el cupo `Fabricando` es por artículo (componente). Validación per-fila (spec) puede sobre-contar. Default propuesto: validar además Σ agregada por artículo (todas sus máquinas×3 turnos) ≤ Fabricando. Confirmar con producto.
- [ ] ¿La precarga de un turno ya guardado permite re-editar (upsert) o es solo lectura? Default: upsert vía `uk_mpr_parte_linea_maq`.
