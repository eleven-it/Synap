# Proposal: Workflow límite de crédito en pedidos

## Intent

Synap evalúa crédito PED/PRE solo por mora en días; sin tope $, exposición Balance+All ni cola Finanzas. Se requiere workflow **independiente del comercial**: políticas por cliente/canal, semáforo en toma, alta siempre con hold prep si `No Autorizado`, aprobación Finanzas que libera solo el PED sin mutar cupo.

## Scope

### In Scope
- Módulo `credito_pedidos` + tablas política/eventos (DDL `catalog.py`); evaluación $+días por canal PED/PRE; `Credito=0` sin límite $; capas ON/OFF (CxC, PED abiertos, remitos NF, cheques, doc actual)
- Checkout unificado; snapshot audit; hold prep hasta Finanzas; desacople `credito_no_autorizado`
- Cola Finanzas + permiso por Puesto; semáforo toma; fix `pedido_masivo_matriz`
- UI nueva look **Alta Movimiento** + canon reports/MPR: ABM políticas, cola Finanzas, plantillas; cobranzas auto mail v1
- Fases A (eval+semáforo) / B (cola+hold+cobranzas); flag master rollback

### Out of Scope
- TPV, WhatsApp, SAP FSCM; mutar `cliente.Credito`; extender pantallas ecom pedidos

## Capabilities

### New Capabilities
- `ecom-credito-pedidos`: Políticas cliente/canal, exposición Balance+All, evaluación checkout, hold prep, aprobación Finanzas, audit, cobranzas/plantillas, flag master

### Modified Capabilities
- `ecom-checkout-mayorista`: Autorización ampliada a $+días+exposición con snapshot
- `ecom-aprobacion-pedidos`: Retirar/redefinir `credito_no_autorizado`
- `ecom-pedidos-hub-kanban`: Columna «Pendiente crédito Finanzas» vs comercial
- `ecom-pedido-venta-shell`: Semáforo monto/días/disponible en header
- `permisos-synap-store`: Permiso `finance.credito.aprobar`
- `roles-synap-por-puesto`: Asignación Finanzas/Créditos por Puesto
- `ui-fuente-verdad-reportes-mpr`: Pantallas crédito con look Alta Movimiento

## Approach

Híbrido A→B, target módulo dedicado. **A:** DDL, `calcular_exposicion`/`evaluar_pedido`, checkout, semáforo, fix matriz. **B:** cola Finanzas (patrón `aprobacion_pedidos`), hold prep, mails. Finanzas aprueba PED puntual; comercial en `estado_aprobacion_comercial`. UI nueva, no templates ecom pedidos.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `ecom/services/credito_pedidos/` | New | Política, exposición, evaluación, aprobación |
| `mayorista_checkout_service.py` | Modified | Evaluación unificada |
| `aprobacion_pedidos.py`, `pedidos_hub_pipeline.py` | Modified | Desacople crédito/comercial |
| `catalog.py`, `constantes_permisos.py` | Modified | DDL + permiso Finanzas |
| Templates credito | New | ABM, cola, plantillas |

## Risks

| Risk | L | Mitigation |
|------|---|------------|
| Divergencia exposición vs Dynamics | M | Snapshot audit; validación fase A |
| Doble cola hub | M | Refactor pipeline |
| Hold prep sin VB6 | M | Bridge `autorizacion_sistema` |
| Performance lote masivo | M | Consultas optimizadas |

## Rollback Plan

Flag `ecom_credito_pedidos_activa` OFF → `mayorista_credito` solo-días; colas Finanzas ocultas; hold off. DDL permanece.

## Dependencies

`ecom_aprobacion_evento`, `administranet_types`, mail async, permisos Synap por puesto.

## Success Criteria

- [ ] Exceso $/días → `No Autorizado` + hold prep (B)
- [ ] Cola Finanzas con permiso; aprobación sin mutar cupo
- [ ] Semáforo en toma pre-confirmación
- [ ] Plantillas cobranzas mail v1 con anti-ruido
- [ ] Flag OFF → legacy solo-días sin regresión
