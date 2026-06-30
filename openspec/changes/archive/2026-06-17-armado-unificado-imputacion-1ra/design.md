# Design: Armado unificado 1ra/2da e imputación supervisor

## Technical Approach

Generalizar armado surtido multi-lote en vista `/mpr/armado/` con `modo` (`1ra`|`2da`). Reutilizar `_ejecutar_armado_surtido_tx` y orquestador de lote; añadir `_ejecutar_armado_1ra_tx` con BOM fija. Persistir `MprArmadoLote` + extender movimientos Synap con `modo`. Imputación en vista separada con `MprImputacionArmado` y servicios sobre legacy MySQL.

## Architecture Decisions

| Decisión | Elección | Alternativa descartada | Rationale |
|----------|----------|------------------------|-----------|
| Vista única | `ArmadoView` + template `armado.html` | Dos apps separadas | Misma UX POS; modo fija reglas |
| Modelos Synap | Extender `MprArmadoSurtido*` → `MprArmado*` + `modo` | Tablas nuevas sin migración | Trazabilidad existente; backfill `2da` |
| Lote UI | `MprArmadoLote` UUID al ejecutar | Solo sesión | Agrupa imputación supervisor |
| Armado 1ra TX | Nueva `_ejecutar_armado_1ra_tx` | Reutilizar surtido con BOM editable | Validación distinta; composición read-only |
| Gates OPT | Eliminar `opt_puede_armado_surtido` | Mantener opcional | Producto: armado libre |
| Cierre OPT | Quitar `hay_restante_armar` de `puede_cerrar` | Mantener bloqueo | Armado desacoplado |
| Imputación | Tabla Synap + UPDATE legacy | Solo `cantidad_fabricada_acumulada` | Trazabilidad por MSTOCK y pedido |
| Permiso | `mpr.imputar_armado_1ra` | Rol Django genérico | Separar operario/supervisor |
| Rollout | Redirects legacy 6 meses | Big-bang delete | Bookmarks y capacitación |

## Data Flow

```text
Operario → GET /mpr/armado/?modo=*
        → Alpine carrito (modo fijo)
        → POST ejecutar_lote
        → ejecutar_lote_armado(modo)
        → por ítem: _ejecutar_armado_{1ra|2da}_tx → MSTOCK
        → MprArmadoLote + MprArmadoMovimiento (modo, estado_imputacion)

Supervisor → GET /mpr/imputacion-armado-1ra/
          → listar_mstock_pendientes_imputacion
          → sugerir_imputacion_fifo
          → POST confirmar → MprImputacionArmado + UPDATE lista_produccion_detalle
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `mpr/views.py` | Modify | `ArmadoView`; `ImputacionArmado1raView`; deprecar gates |
| `mpr/services.py` | Modify | `ejecutar_lote_armado`; imputación FIFO; `estado_acciones_opt` |
| `mpr/models.py` | Modify | `MprArmadoLote`, `MprImputacionArmado`; campo `modo` |
| `mpr/urls.py` | Modify | `/armado/`, `/imputacion-armado-1ra/`; redirects |
| `mpr/templates/mpr/armado.html` | Create | Evolución `armado_surtido.html` + toggle modo |
| `mpr/templates/mpr/imputacion_armado_1ra.html` | Create | Cola MSTOCK + FIFO |
| `mpr/templates/mpr/opt_detail.html` | Modify | Quitar tarjetas armado |
| `mpr/templates/mpr/wizard.html` | Modify | Paso 4 → enlace menú |
| `mpr/tests/test_armado_unificado*.py` | Create | Modos, lote, redirects |
| `mpr/tests/test_imputacion_armado_1ra*.py` | Create | FIFO, permisos, límites |
| `docs/mpr/MANUAL_USUARIO_MPR.md` | Modify | Armado 1ra/2da, imputación |

## Interfaces / Contracts

```python
# POST lote — extensión cabecera
{"modo": "1ra"|"2da", "deposito_origen", "deposito_destino", "id_operario", "armados": [...]}

# MprArmadoMovimiento (evolución)
modo: CharField choices=("1ra","2da")
id_lote_armado: FK MprArmadoLote
estado_imputacion: CharField choices=("pendiente","parcial","completo")  # solo 1ra

# confirmar_imputacion_armado(base_empresa, codigo_movimiento, lineas[{cod_ped, cantidad, origen_regla}], id_supervisor)
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | `validar_modo_lote`, FIFO, `puede_cerrar` | `SimpleTestCase` mocks MySQL |
| Integration | ejecutar lote 1ra/2da, imputación | `TestCase` + cursor mock patterns existentes |
| View | redirects, 403 imputación, sin gate OPT | `Client` MPR login mixin |

## Migration / Rollout

1. Migración Django: `MprArmadoLote`, campos en movimiento, `MprImputacionArmado`.
2. Data migration: `modo='2da'` en `MprArmadoSurtidoMovimiento` existentes.
3. Redirects: `armado-surtido` → `armado?modo=2da`; `armado_opt` → `armado?modo=1ra`.
4. Fase B imputación tras Fase A estable en staging.

## Open Questions

- [ ] ¿Permiso imputación = permiso existente MPR admin o nuevo codename?
- [ ] ¿KPI tablero MSTOCK pendientes en Fase A o C?
