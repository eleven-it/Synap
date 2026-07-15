# Design: Artículos terminados/fabricados y olas stock inicial

## Enfoque técnico

Extender el módulo `mpr/best_migration/` (no crear app ni tablas nuevas). Reutilizar `BestArticuloMap` marcando el dominio Fabricado con `origen_requerimiento=BOM_FABRICADO`, replicar la pantalla de artículos como espejo no bloqueante, agregar colas de visualización sobre `BestStockInicialMap` y renombrar el display del dominio Terminados. Los guardrails de olas (`cargar_stock_inicial_best`) ya existen: solo se referencian, no se rediseñan. Mapea al Approach 1–5 de la propuesta.

## Decisiones de arquitectura

| Decisión | Opción elegida | Alternativa descartada | Racional |
|----------|----------------|------------------------|----------|
| Persistir fabricados | Reusar `BestArticuloMap` + `origen_requerimiento=BOM_FABRICADO` | Tabla nueva `BestArticuloFabricadoMap` | Reusa matcher, validación, UI y estados; `unique_together(base_empresa,best_id_articulo)` no colisiona (SKU BEST distinto); solo migración de `choices` |
| Aislamiento del gate | Excluir `BOM_FABRICADO` de `refresh_parity_counters`/`recalcular_mapeo_articulos` | Flag ad-hoc por vista | El gate PED (`migracion_habilitada`) debe seguir contando solo Terminados; evita que fabricados bloqueen cutover |
| Rename Terminados | Cambiar solo `nombre` en `DOMAINS` (display); `codigo="articulos"` estable | Renombrar `codigo` | No rompe URLs, permisos, parity ni tests; cambio semántico nulo |
| Universo Admin matcher inverso | Nueva query `tipo_art_fab='Fabricado'` + explosión `en_abm_formula` | Migrar `REP_RECETAS` de BEST | BOM fuente de verdad = AdministraNET (decisión producto) |
| Depósitos stock Semi | Reusar `deposit_matcher` (4002→SemiElaborado ya existe) | Mapeo nuevo | Alineado con matcher vigente |
| Colas stock | Tabs sobre estados existentes de `BestStockInicialMap` | Nuevo campo "ola" | Estados `SIN_MAPEO_*`/`LISTO`/`CONCILIADO`/`CARGADO` ya expresan la cola |

## Flujo de datos

```
Terminados VALIDADO ──► explosión en_abm_formula (Admin BOM)
                              │
                              ▼
                     Fabricados únicos ──► inferir SKU BEST (matcher inverso)
                              │
                              ▼
              BestArticuloMap(origen=BOM_FABRICADO)  ── NO entra al gate PED
                              │ (opcional, post-cutover)
                              ▼
   Stock BEST 4002 Semi-Embalado ──► BestStockInicialMap ──► cargar_stock_inicial_best
                                        (olas: CARGADO inmutable) ──► Admin SemiElaborado
```

## Cambios de archivos

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `mpr/best_migration/models.py` | Modify | Añadir `BOM_FABRICADO` a `BestArticuloMap.OrigenRequerimiento` |
| `mpr/migrations/00XX_*.py` | Create | Migración de `choices` (sin DDL destructivo) |
| `mpr/best_migration/domains.py` | Modify | Rename display `Artículos`→`Artículos terminados`; nuevo `MigrationDomain("articulos_fabricados", obligatorio_para_pedidos=False)` |
| `mpr/best_migration/services.py` | Modify | Excluir `BOM_FABRICADO` de parity/gate y del `delete` de `recalcular_mapeo_articulos`; branch fabricados en `hub_context`; `_load_admin_fabricados()`; `resolver_fabricados_desde_terminados()`; filtro Semi en carga stock |
| `mpr/best_migration/views.py` | Modify | Excluir `BOM_FABRICADO` de la vista Terminados; `MigracionBestArticulosFabricadosView` + acciones (resolver/validar); colas en `MigracionBestStockInicialView` |
| `mpr/urls.py` | Modify | Rutas `/migracion-best/articulos-fabricados/…` espejo de terminados |
| `mpr/templates/mpr/best_migration/hub.html` | Modify | Label terminados; fila fabricados no bloqueante (semáforo informativo) |
| `mpr/templates/mpr/best_migration/articulos_fabricados.html` | Create | Espejo de `articulos.html` (canon UI reportes/MPR, textos español) |
| `mpr/templates/mpr/best_migration/stock_inicial.html` | Modify | Tabs colas: pendiente mapeo / listos carga / ya cargados; copy prioriza Terminados |
| `docs/mpr/MODULO_MIGRACION_BEST_MPR.md` | Modify | Terminados vs fabricados; BOM solo Admin; olas |

## Contratos / interfaces

```python
# services.py
def resolver_fabricados_desde_terminados(base_empresa: str) -> dict[str, Any]:
    """Terminados VALIDADO → explosión en_abm_formula → Fabricados únicos →
    inferir SKU BEST → upsert BestArticuloMap(origen_requerimiento=BOM_FABRICADO).
    No toca parity ni migracion_habilitada."""

def _load_admin_fabricados(base_empresa: str) -> list[dict]:
    """Universo Admin tipo_art_fab='Fabricado' para matcher inverso."""
```

Guard obligatorio en counters/cleanup: `.exclude(origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO)`.

## Estrategia de testing

| Capa | Qué | Cómo |
|------|-----|------|
| Unit | Gate ignora `BOM_FABRICADO`; rename display; explosión `en_abm_formula` | `docker exec Synap_app python manage.py test mpr.best_migration` |
| Integración | `resolver_fabricados_desde_terminados` infiere BEST; Semi 4002→SemiElaborado | fixtures BOM Admin |
| Regresión | `recalcular_mapeo_articulos` no borra filas `BOM_FABRICADO`; olas no re-tocan `CARGADO` | reusar `test_cargar_stock_inicial_olas.py` |

## Migración / rollout

Migración Django solo de `choices` (sin ALTER destructivo en MySQL legacy; datos en Postgres). Rollout: dominio fabricados y colas visibles pero no bloqueantes desde el inicio. Rollback: revertir commits; filas `BOM_FABRICADO` quedan inertes.

## Preguntas abiertas

- [ ] ¿La explosión `en_abm_formula` incluye subcomponentes recursivos o solo primer nivel Fabricado? (default asumido: Fabricados directos únicos).
- [ ] ¿Alguna base con `tipo_art_fab` distinto de `'Terminado'/'Fabricado'` que deba normalizarse?
