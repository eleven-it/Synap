# Proposal: Artículos terminados/fabricados y olas stock inicial

**Change:** `best-articulos-terminados-fabricados-olas` · **Fecha:** 15/07/2026

## Intent

Completar la migración BEST→MPR con olas de stock anti-duplicado (backend hecho), colas de visualización claras y separación de dominios **Terminados** (cutover crítico) vs **Fabricados** (BOM Admin→BEST, opcional post-cutover). Evitar confusión en hub, gate PED y stock inicial.

## Scope

### In Scope
- Colas UI stock inicial: pendiente mapeo / listos carga / ya cargados; copy prioriza Terminados en cutover.
- Renombrar hub «Artículos» → «Artículos terminados» (display; `codigo="articulos"` estable).
- Nuevo dominio `articulos_fabricados`: hub + pantalla espejo; `obligatorio_para_pedidos=False`; no entra a `refresh_gate` ni `migracion_habilitada`.
- Matcher inverso: terminados VALIDADO → explosión `en_abm`/`en_abm_formula` → fabricados únicos → inferir SKU BEST 1:1.
- Stock fabricados opcional post-cutover: BEST Semi-Embalado (4002) ↔ Admin Semi-elaborado; misma máquina de olas (`CARGADO` preservado).
- Tests y docs: terminados vs fabricados; BOM solo Admin; no `REP_RECETAS`.

### Out of Scope
- Migrar recetas desde BEST (`REP_RECETAS`).
- Bloquear cutover o gate PED por fabricados o stock Semi.
- Stock Semi fabricados obligatorio en ola 1.
- Rollback MSTOCK al reiniciar migración.

## Capabilities

### New Capabilities
- `best-migracion-stock-inicial-colas`: colas por ola en stock inicial; foco cutover Terminados.
- `best-migracion-articulos-terminados`: rename dominio/UI; gate PED sin cambio semántico.
- `best-migracion-articulos-fabricados`: dominio no bloqueante, matcher BOM inverso, stock Semi opcional.

### Modified Capabilities
- None (sin spec vigente de migración BEST en `openspec/specs/`).

## Approach

1. **Colas stock** — `views.py` + `stock_inicial.html`: filtros/tabs por `SIN_MAPEO_*`, `LISTO`/`CONCILIADO`, `CARGADO`; reutilizar métricas de `cargar_stock_inicial_best`.
2. **Terminados** — `domains.py`, hub, templates, docs: rename display; mantener matcher Admin `tipo_art_fab=Terminado`.
3. **Fabricados** — `MigrationDomain` `articulos_fabricados`; `BestArticuloMap` con `origen_requerimiento=BOM_FABRICADO`; ruta `/mpr/migracion-best/articulos-fabricados/` espejo terminados; acción «Resolver fabricados».
4. **Matcher inverso** — servicio: terminados validados → `en_abm_formula` → componentes Fabricado → inferir BEST; UI Asignar sin límite solo Terminado.
5. **Stock Semi** — sync/carga post-cutover vía `BestDepositoMap` 4002↔SemiElaborado; checklist hub sin bloqueo PED.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `mpr/best_migration/domains.py` | Modified | Rename + dominio fabricados |
| `mpr/best_migration/views.py` | Modified | Colas stock; vista fabricados |
| `mpr/best_migration/services.py` | Modified | BOM inverso; stock Semi opcional |
| `mpr/best_migration/models.py` | Modified | `origen_requerimiento=BOM_FABRICADO` |
| `mpr/templates/mpr/best_migration/` | Modified | Hub, stock_inicial, articulos-fabricados |
| `docs/mpr/MODULO_MIGRACION_BEST_MPR.md` | Modified | Terminados vs fabricados; olas |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| BOM incompleta en Admin | Med | UI manual Asignar; no bloquear cutover |
| Confusión gate vs stock cutover | Med | Copy y semáforos explícitos en hub |
| Duplicar SKUs fabricados/terminados | Low | `origen_requerimiento` distinto; tests gate |
| Matcher inverso ambiguo | Med | Misma UX score/lote que terminados |

## Rollback Plan

Revertir commits del change: quitar dominio fabricados y colas UI; restaurar label «Artículos». Datos Postgres `BOM_FABRICADO` quedan inertes (no bloquean gate). Sin migración MySQL. Reinicio migración no deshace MSTOCK ya cargado.

## Dependencies

- Guardrails olas ya en `cargar_stock_inicial_best` y tests `test_cargar_stock_inicial_olas.py`.
- Depósitos: mapeo 4002↔SemiElaborado existente en `BestDepositoMap`.
- Plan acordado: `guardrails_stock_inicial_bde5200b.plan.md`.

## Success Criteria

- [ ] Colas stock inicial muestran pendiente mapeo / listos / cargados con copy Terminados prioritario.
- [ ] Hub muestra «Artículos terminados»; gate PED igual que antes.
- [ ] Dominio fabricados visible, no bloquea `migracion_habilitada`.
- [ ] Matcher BOM Admin→BEST infiere y valida fabricados desde terminados mapeados.
- [ ] Stock Semi fabricados cargable post-cutover; `CARGADO` nunca reprocesado.
- [ ] Tests en contenedor pasan; docs actualizadas.

## Decisiones producto (15/07/2026)

Olas: solo `LISTO`/`CONCILIADO`; `CARGADO` inmutable. Cutover stock = Terminados (dep. Terminado). Fabricados: BOM Admin fuente; matcher inverso; Semi-Embalado↔Semi-elaborado opcional. Gate PED solo terminados+clientes+unidades. No `REP_RECETAS`.
