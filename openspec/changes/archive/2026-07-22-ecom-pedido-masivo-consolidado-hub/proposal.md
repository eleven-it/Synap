# Proposal: Hub consolidado de cargas masivas

## Intent

Tras confirmar pedido masivo, el usuario ve N PED sueltos en el hub sin contexto de lote. Falta una vista consolidada del draft confirmado (`codigos_movimiento[]`) y autorización comercial unificada. Objetivo: lane **Cargas masivas**, resumen de lote y aprobación atómica del lote completo.

## Scope

### In Scope
- Pipeline: drafts confirmados como tarjetas `tipo=lote_masivo` en segmento `cargas_masivas`; mapa reverso `cod_mov → draft_id`; meta en PED hijos (`lote_draft_id`, chip k/n)
- UI hub: lane Cargas masivas (desktop) + chip móvil; tarjeta padre con rollup y CTA Ver resumen; ocultar CTA aprobar/rechazar en hijos de lote pendiente
- Pantalla/API resumen lote (`/ecom/mayoristapp/pedidos/lote/<draft_id>/`); pestaña matriz read-only «Qué se cargó»
- Servicio y APIs autorizar/rechazar lote completo (N PED); campo o derivación de estado comercial agregado del draft
- Tests pipeline, resumen, autorización lote; docs ecom afectadas

### Out of Scope
- Agrupar lotes en columnas Kanban de estado; quitar PED del tablero
- FK lote en MySQL; reescritura de `batch_checkout_masivo`
- Autorización PED-a-PED dentro de lote pendiente

## Capabilities

### New Capabilities
- `ecom-pedido-masivo-lote-resumen`: pantalla resumen del lote, API JSON, pestaña matriz read-only, acciones de lote (autorizar/rechazar/reabrir)

### Modified Capabilities
- `ecom-pedidos-hub-kanban`: ADD lane/segmento Cargas masivas; ADD meta lote en tarjetas PED; MOD CTAs aprobación en hijos de lote pendiente
- `ecom-aprobacion-pedidos`: ADD autorización/rechazo de lote completo; APIs por `draft_id`; política todo-o-nada
- `ecom-pedido-masivo-sucursales`: ADD post-confirmación vía resumen lote; matriz `readonly=1` como pestaña «Qué se cargó»

## Approach

Implementar en 5 fases secuenciales (plan 22/07/2026):

1. **Pipeline:** `_lotes_masivos_confirmados`, mapa reverso, enriquecer `_pedidos_mysql`, payload `cargas_masivas` separado de `columnas[]`
2. **UI hub:** lane + tarjeta padre + chips en hijos; filtro opcional Lista «Ocultar PED de lotes»
3. **Resumen lote:** vista canónica, totales, tabla sucursales, modales Synap (sin diálogos nativos)
4. **Autorización lote:** `resolver_lote_masivo` sobre todos los `codigos_movimiento`; compensación ante fallo parcial
5. **Tests + docs:** `PEDIDOS_HUB_KANBAN.md`, `PEDIDO_MASIVO_SUCURSALES.md`, `JERARQUIA_COMERCIAL_APROBACION.md`

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `ecom/services/pedidos_hub_pipeline.py` | Modified | Lotes confirmados, mapa reverso, meta hijos |
| `ecom/templates/ecom/pedidos_hub.html` | Modified | Lane Cargas masivas, chips, CTAs |
| `ecom/pedido_gestion_views.py`, `ecom/urls.py` | New/Modified | Vista resumen lote + API |
| `ecom/services/aprobacion_pedidos.py` | Modified | Autorización lote completo |
| `ecom/models.py` | Modified | Opcional `estado_aprobacion_lote` en draft |
| `docs/ecom/*.md` | Modified | Hub, masivo, aprobación |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Fallo parcial al aprobar N PED | Med | Compensación atómica lógica (patrón batch_checkout) |
| PED ausente vs `codigos_movimiento` | Med | Resumen muestra Anulada/No generada |
| Duplicar CTAs aprobación en hub | Low | `meta.puede_aprobar=False` en hijos de lote pendiente |
| Performance mapa reverso | Low | Ventana temporal + índice draft confirmado |

## Rollback Plan

1. Ocultar segmento `cargas_masivas` en template (feature flag o revert UI).
2. Revertir pipeline: PED sin meta lote; drafts confirmados no en hub.
3. Desactivar rutas/API lote; aprobación individual por `cod_mov` sigue operativa.
4. Campo draft nuevo nullable — código previo lo ignora.

## Dependencies

- Checkout masivo y draft confirmado ya operativos (`ecom-pedido-masivo-sucursales`, cabecera comercial)
- Subflag `ecom_aprobacion_pedidos_activa` para CTAs comerciales de lote

## Success Criteria

- [ ] Lote confirmado visible en lane Cargas masivas con rollup y enlace a resumen
- [ ] PED hijos muestran chip lote; sin CTA aprobar individual si lote pendiente
- [ ] Resumen lista sucursales/PED; pestaña matriz read-only operativa
- [ ] Autorizar/rechazar lote afecta todos los PED; fallo parcial no deja estado silencioso inconsistente
- [ ] Tests pipeline, resumen y aprobación lote verdes; docs actualizadas
