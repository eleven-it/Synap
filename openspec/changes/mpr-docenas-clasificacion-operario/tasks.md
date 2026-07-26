# Tasks: Docenas operativas MPR y clasificación por operario fabricante

**Change:** `mpr-docenas-clasificacion-operario`  
**Specs:** `specs/mpr-presentacion-docenas-operativa`, `specs/mpr-clasificacion-operario-fabricante`, `specs/mpr-reporte-rendimiento-operario`

---

## Phase 1: Esquema y repositorio

- [ ] 1.1 Añadir `id_operario`, `operario_nombre` a `mpr_transicion_lote` en `mpr/sql/` y `core/services/legacy_mysql_schema/catalog.py`
- [ ] 1.2 Actualizar `mpr/repositories/transicion_lote.py` (INSERT/SELECT con operario)
- [ ] 1.3 Test migración idempotente y tipos AdministraNET (`to_int_or_none`, `str_or_default`)

## Phase 2: Presentación docenas (sesión + servicios)

- [ ] 2.1 Vista/helper sesión `mpr_presentacion_cantidad` (default `docenas`)
- [ ] 2.2 Include `mpr/templates/mpr/includes/toggle_presentacion_cantidad.html`
- [ ] 2.3 Enriquecer `listar_tablero_por_articulo` con campos docenas / texto presentación
- [ ] 2.4 Tablero: columnas docenas + Enviar docenas/unidades + hint `= N u.`
- [ ] 2.5 POST envío: parsear docenas → unidades antes de servicio
- [ ] 2.6 Parte: alinear captura al toggle global (sin toggle duplicado)
- [ ] 2.7 Tests conversión y sesión

## Phase 3: Grilla clasificación por operario

- [ ] 3.1 `construir_grilla_clasificacion_operario` (pendiente por artículo × operario, fecha, turno)
- [x] 3.2 Sección arrastre turnos anteriores — **retirada** (26/07/2026): producto decidió no mostrar el chequeo; sin utilidad operativa frente al costo de UI.
- [ ] 3.3 Validaciones por fila y global stock Producción
- [ ] 3.4 Bloqueo si parte sin operarios
- [ ] 3.5 Plantilla `clasificacion_produccion.html` (grilla nueva)
- [ ] 3.6 POST guardado con `id_operario` fabricante
- [ ] 3.7 Tests grilla, validaciones, POST

## Phase 4: Reporte rendimiento operario

- [ ] 4.1 Extender query `reporte_mpr_operario_parte` (semi, 2da, scrap, %)
- [ ] 4.2 Plantilla reporte con columnas nuevas y presentación docenas
- [ ] 4.3 Fila «Sin atribución» para histórico NULL
- [ ] 4.4 Tests reporte con fixtures parte + transiciones

## Phase 5: P1 y pulido

- [x] 5.1 Toggle supervisor «Ver roster completo» en clasificación
- [x] 5.2 Default docenas en hub reportes MPR
- [x] 5.3 Gráfico apilado semi/2da/scrap en reporte operario

## Phase 6: Documentación

- [ ] 6.1 `docs/mpr/DOCENAS_CLASIFICACION_OPERARIO_MPR.md`
- [ ] 6.2 Actualizar `docs/mpr/CLASIFICACION_PRODUCCION.md`, `TABLERO_CONSOLIDADO.md`, `GLOSARIO_MPR.md`
