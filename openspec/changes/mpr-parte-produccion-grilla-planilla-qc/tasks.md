# Tasks: Grilla analista alineada a planilla QC

**Change:** `mpr-parte-produccion-grilla-planilla-qc`  
**TDD:** `docker exec Synap_app python manage.py test mpr.tests.test_parte_planilla_qc`  
**Out of scope:** PWA `/mpr/mi-parte/`; columnas Color/Talle; CC digital; DDL nuevo; cambios a `construir_grilla_parte` (E8)

---

## Fase 1 — Builder y precarga (backend)

- [x] **T1** *(RED, sin deps)* — Crear `mpr/tests/test_parte_planilla_qc.py`: tests fallidos de `construir_grilla_parte_planilla` (orden==planilla QC, payload fila, turnos M/T/N, `fabricando`/`ingresado`, filas sin cupo). Ejecutar contenedor.
- [x] **T2** *(GREEN, T1)* — Implementar `construir_grilla_parte_planilla` en `mpr/services_maquina_linea.py`: envolver `construir_datos_planilla_control_calidad` + `_fabricando_por_componentes`; **no** tocar `construir_grilla_parte`.
- [x] **T3** *(RED, T2)* — Tests fallidos helper precarga por `(fecha, id_mpr_maquina, id_articulo, turno)` en `mpr/repositories/parte.py`.
- [x] **T4** *(GREEN, T3)* — Implementar helper precarga/upsert lectura en `mpr/repositories/parte.py`; integrar en builder (T2).

## Fase 2 — Persistencia y registro (backend)

- [x] **T5** *(RED, T4)* — Tests fallidos `crear_parte_con_lineas`: persiste `id_mpr_maquina`, `maquina_nombre`, `cantidad_declarada`=`cantidad_aprobada`, `gap=0`; respeta `uk_mpr_parte_linea_maq`.
- [x] **T6** *(GREEN, T5)* — Extender `mpr/repositories/parte.py` reutilizando patrón `_insertar_lineas` móvil (SQL 004 existente).
- [x] **T7** *(RED, T6)* — Tests fallidos `registrar_parte_produccion`: validación cupo Σ M+T+N ≤ Fabricando por fila; agregación por artículo multi-máquina; rechazo atómico sin guardado parcial.
- [x] **T8** *(GREEN, T7)* — Refactor `registrar_parte_produccion` en `mpr/services.py`: parseo líneas con máquina/turno; un POST → hasta 3 `MprParte` en `transaction.atomic()`; upsert idempotente.
- [x] **T9** *(T8)* — `ParteProduccionView` en `mpr/views.py`: filtros server-side Fecha (oblig.), Línea, Máquina, Marcas, búsqueda; quitar turno como eje; contexto grilla planilla.
- [x] **T10** *(T8, T9)* — `RegistrarParteProduccionView` + `_parte_lineas_desde_post`: celdas `parte_maq_{maq}_art_{art}_turno_{turno}_{docenas|pares|op}`; mensajes ES; asiento físico E8 intacto.

## Fase 3 — Template y UX (canon MPR)

- [x] **T11** *(T9)* — `mpr/templates/mpr/parte_produccion.html`: barra filtros canon MPR (`mpr/base_mpr.html`); fecha dd/MM/yyyy; artículo sin código visible (tooltip/búsqueda con código).
- [x] **T12** *(T11)* — Tabla planilla: columnas sticky Máquina + Artículo + Cupo Fabricando; columnas fijas Mañana|Tarde|Noche; columna Ingresado (suma tres turnos).
- [x] **T13** *(T12)* — Celdas turno: inputs docenas/pares; activas solo si Fabricando>0; operario roster (hidden 1 op / `<select>` varios / disabled sin roster + aviso ES).
- [x] **T14** *(T13)* — JS/Alpine: tab order fila M→T→N (docenas antes pares); toggle docenas/pares; feedback vía `mprShowAviso`/`SynapMessages`; modales Synap; **sin** `alert`/`confirm`/`prompt`.

## Fase 4 — Tests integración y regresión

- [x] **T15** *(T8, T10)* — Tests integración vista: POST multi-turno persiste `id_mpr_maquina`; precarga re-edición; rechazo sobre cupo con mensaje ES (`docker exec Synap_app`).
- [x] **T16** *(T2)* — Regresión: suite E8 `test_etapa8_parte_por_componente` (`construir_grilla_parte`) y tests móvil `/mpr/mi-parte/` sin cambios de comportamiento.

## Fase 5 — Documentación

- [x] **T17** *(T14)* — Actualizar `docs/mpr/PARTE_PRODUCCION.md`: flujo analista planilla QC, filtros, turnos columnas, cupo, máquina en línea, operario roster.
- [x] **T18** *(T14)* — Actualizar `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`: citar `/mpr/parte-produccion/` como implementación alineada al canon (no nueva fuente de verdad).

---

## Mapa de dependencias

```
T1→T2→T3→T4→T5→T6→T7→T8→T9→T10→T11→T12→T13→T14→T17/T18
T8→T15; T2→T16
```

## Estimación por grupo

| Grupo | Tareas | IDs |
|-------|--------|-----|
| Backend grilla/precarga | 4 | T1–T4 |
| Backend persistencia/registro | 6 | T5–T10 |
| Template/JS UX | 4 | T11–T14 |
| Tests integración/regresión | 2 | T15–T16 |
| Docs | 2 | T17–T18 |
| **Total** | **18** | |
