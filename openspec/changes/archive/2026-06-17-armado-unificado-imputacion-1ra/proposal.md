# Proposal: Armado unificado 1ra/2da e imputación supervisor

## Intent

Desacoplar el armado de packs del ciclo OPT: una sola UX POS (carrito + lote) con modos **Armado 1ra** (Semi → Terminado, BOM) y **Armado 2da** (2.ª selección → SKU 2.ª, composición libre). La demanda de pedidos 1.ª se reconcilia después vía **imputación supervisor por MSTOCK**, no en piso ni desde `opt_detail`.

## Scope

### In Scope
- Vista unificada `/mpr/armado/` con toggle 1ra|2da; lote no mezcla modos.
- Armado 1ra: BOM precargada, carrito multi, MSTOCK por pack (reutilizar núcleo surtido).
- Armado 2da: paridad con implementación actual; sin gates OPT/OPP.
- Deprecar CTAs y rutas `opt/<id>/armado/`, wizard paso 4, `?id_lista=` bloqueante.
- Pantalla supervisor **Imputación armado 1ra** (MSTOCK pendientes, FIFO sugerido).
- Modelos Synap: lote de sesión + imputación; permiso supervisor.
- Ajustar `puede_cerrar` OPT: solo pendiente OPP, sin `hay_restante_armar`.
- Docs `docs/mpr/` + manual usuario.

### Out of Scope
- Imputación para Armado 2da (sin pedido origen).
- Plantillas de composición 2da.
- Refactor completo de `services.py` por dominio.
- Paridad flujo VB6 OPT-desde-pedido.

## Capabilities

### New Capabilities
- **mpr-armado-unificado**: Modos 1ra/2da, lote exclusivo por modo, ejecución MSTOCK, deprecación entradas OPT.
- **mpr-imputacion-armado-1ra**: Cola MSTOCK pendientes, imputación a `lista_produccion_detalle`/pedido, permiso supervisor.

### Modified Capabilities
- **ui-fuente-verdad-reportes-mpr**: Rutas canónicas de armado pasan a `/mpr/armado/`; `opt_detail` sin CTAs de armado.

## Approach

1. Generalizar `MprArmadoSurtido*` → `MprArmado*` con campo `modo` (`1ra`|`2da`); tabla `MprArmadoLote` agrupa ejecución UI.
2. Extraer núcleo transaccional común; 1ra valida BOM + `tipo_art` terminado; 2da mantiene reglas actuales.
3. `MprImputacionArmado` por `codigo_movimiento`; servicio FIFO sobre demanda abierta mismo `id_articulo`.
4. Redirects legacy; quitar `opt_puede_armado_surtido` y tarjetas en `opt_detail`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `mpr/views.py`, `mpr/services.py` | Modified | Vista unificada, imputación, cierre OPT |
| `mpr/templates/mpr/armado*.html` | New/Modified | Toggle 1ra/2da; renombrar surtido |
| `mpr/models.py` | Modified | Lote, imputación, modo armado |
| `mpr/urls.py` | Modified | `/mpr/armado/`, imputación |
| `mpr/templates/mpr/opt_detail.html` | Modified | Quitar CTAs armado |
| `docs/mpr/SDD_ARMADO_UNIFICADO_IMPUTACION.md` | New | Spec detallada |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| MSTOCK 1ra sin imputar | Med | KPI pendientes; no bloquear operario |
| URLs legacy en favoritos | Low | Redirect + mensaje único |
| Migración datos surtido | Low | `modo=2da` por defecto en filas existentes |

## Rollback Plan

Feature flag o revert merge: restaurar rutas `armado-surtido` y `armado_opt`; tablas Synap nuevas ignorables; sin ALTER legacy MySQL obligatorio.

## Dependencies

- Armado surtido multi-lote (implementado).
- Depósitos MPR configurados (Semi, 2.ª, Terminado).

## Success Criteria

- [ ] Operario arma 1ra y 2da solo desde menú; lote no mezcla modos.
- [ ] Sin gates OPT en armado 2da.
- [ ] Supervisor imputa MSTOCK 1ra a pedido con trazabilidad.
- [ ] Cerrar OPT no exige armado previo.
- [ ] Manual y glosario actualizados.
