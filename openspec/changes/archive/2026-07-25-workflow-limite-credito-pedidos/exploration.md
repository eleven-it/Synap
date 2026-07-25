## Exploration: workflow-limite-credito-pedidos

### Current State

Synap hoy evalúa crédito en pedidos mayoristas/ecom de forma **parcial y acoplada a flujos distintos**:

1. **Solo mora en días (checkout PED/PRE)** — `ecom/services/mayorista_credito.py` consulta `cuentacliente` (comprobantes impagos FA/FB/FC/FE/FM/ND*) y compara atraso vs `cliente.credito_limite_dias`. Si excede (o el actor es cliente autogestión) setea `comp_ped.autorizacion_sistema = 'No Autorizado'`. **No evalúa monto $**, no calcula exposición Balance+All, no incluye PED abiertos/remitos/cheques. El exceso **no bloquea el alta** (paridad legacy PHP).

2. **Checkout transaccional** — `ecom/services/mayorista_checkout_service.py` invoca `evaluar_autorizacion()` en el commit (PED/PRE/DEV vía carrito). Tras el alta, si `ecom_aprobacion_pedidos_activa`, `aprobacion_pedidos.evaluar_reglas()` puede disparar cola comercial cuando `autorizacion_sistema == 'No Autorizado'` (regla `credito_no_autorizado`).

3. **Cupo monetario solo TPV** — `self_checkout/services/tpv_paridad_precheck.py` valida `cliente.Credito` vs `saldo + total_venta` y **bloquea** la venta TPV. Fuera de alcance v1 pero es la única lógica $ existente (simple, sin capas configurables).

4. **UI de toma de pedido** — `ecom/templates/ecom/includes/pedidos_order_header.html` muestra widget ámbar/verde con **saldo CC + límite en días** vía `cliente_seleccion_relay.py`. No hay semáforo rojo/amarillo/verde por monto disponible ni exposición desglosada.

5. **Hub kanban** — `pedidos_hub_pipeline._columna_ped_mysql()` mezcla `No Autorizado` con cola comercial «Por autorizar» cuando aprobación comercial está ON. No existe cola Finanzas/Créditos separada.

6. **Datos legacy disponibles** — `cliente`: `Credito`, `saldo`, `credito_limite_dias`, `credito_cheque`, `credito_cheque_tercero`; `cuentacliente`, `comp_ped`, `chequetercero`. No hay tabla de políticas por cliente/canal.

7. **Bug conocido** — `pedido_masivo_matriz.credito_cliente_masivo()` lee `cliente.Credito` ($) pero lo expone como clave `credito_limite_dias` (naming incorrecto).

8. **Preparación / hold** — AS-IS: `autorizacion_sistema` es informativo; preparación vive en VB6 (`Pedido_prep`, estados `En preparación`). Synap no implementa hold de preparación; la decisión v1 exige bloquear preparación mientras `No Autorizado` hasta aprobación Finanzas.

9. **Infra reutilizable** — Patrón aprobación comercial (`ecom_aprobacion_evento`, permisos `ecom.pedidos.aprobar`, routing jerárquico); catálogo DDL `core/services/legacy_mysql_schema/catalog.py`; permisos Synap por puesto (`synap_rol`, `core/constantes_permisos.py` con familia `finance.*`); mail async `ecom/services/comprobante_mail_async.py`; canon UI `stock/alta_movimiento.html` + `docs/stock/ALTA_MOVIMIENTO_UX.md`.

10. **Tests** — Cobertura en días/mora (`test_mayorista_checkout_service.py`) y regla comercial `credito_no_autorizado` (`test_aprobacion_pedidos.py`). Sin tests de exposición $ ni workflow Finanzas.

### Affected Areas

- `ecom/services/mayorista_credito.py` — reemplazar/ampliar evaluación (mora + monto + exposición); mantener contrato `autorizacion_sistema` para hold preparación.
- `ecom/services/mayorista_checkout_service.py` — punto único de evaluación en alta PED/PRE; persistir snapshot de evaluación para audit trail.
- `ecom/services/aprobacion_pedidos.py` — **desacoplar** regla `credito_no_autorizado` del workflow Finanzas (decisión #4); evaluar si eliminar o redirigir a cola comercial distinta.
- `ecom/services/pedidos_hub_pipeline.py` — columnas/kanban: separar «pendiente crédito Finanzas» vs «pendiente comercial».
- `ecom/services/cliente_seleccion_relay.py` + `ecom/templates/ecom/includes/pedidos_order_header.html` — semáforo en toma (monto + días + disponible); API pre-check antes de confirmar.
- `ecom/services/pedido_masivo_matriz.py` — corregir bug naming; alimentar widget con exposición real.
- `ecom/services/batch_checkout_masivo.py` — reutiliza `confirmar()`; hereda evaluación centralizada.
- `core/services/legacy_mysql_schema/catalog.py` — DDL tabla políticas crédito + eventos aprobación Finanzas + permiso en configuración.
- `core/constantes_permisos.py` — nuevo permiso tipo `ecom.pedidos.aprobar_credito` o `finance.credito.aprobar` asignable por Puesto.
- **Pantallas NUEVAS** (canon alta movimiento / reports-MPR): cola aprobación Finanzas, ABM políticas por cliente, editor plantillas aviso; **no** extender pantallas ecom actuales de pedidos.
- `ecom/services/comprobante_mail_async.py` (o servicio nuevo) — disparo cobranzas/reclamos/avisos con plantillas editables y anti-ruido.
- `openspec/specs/ecom-checkout-mayorista/spec.md` + `ecom-aprobacion-pedidos/spec.md` — deltas por separación crédito vs comercial.
- `docs/ecom/` — documentación obligatoria (CHECKOUT, JERARQUIA, políticas crédito).

### Approaches

1. **Extender `mayorista_credito.py` in-place** — Añadir cálculo $ y flags cliente en el mismo módulo; políticas como columnas extra en `cliente`.
   - Pros: Menor superficie inicial; un solo call site.
   - Cons: Viola decisión #1 (tabla dedicada); difícil configurar capas Balance+All por canal; mezcla evaluación, aprobación y notificaciones; no escala a plantillas/cobranzas.
   - Effort: Medium

2. **Módulo `credito_pedidos` + tabla política + cola Finanzas paralela (recomendado)** — Servicio dedicado: `resolver_politica(cliente, canal)`, `calcular_exposicion()`, `evaluar_pedido()`, `aplicar_hold()`, `resolver_aprobacion_finanzas()`. Tabla MySQL `ecom_credito_politica` (por cliente + canal PED/PRE) y `ecom_credito_aprobacion_evento` (audit). Checkout solo consume resultado. UI y APIs nuevas; desvincular `credito_no_autorizado` de comercial.
   - Pros: Alineado con las 12 decisiones cerradas; separación clara crédito/comercial; testeable por capas; reutiliza patrones de `aprobacion_pedidos` y `PoliticaAuditoriaContable` (concepto, no tabla PG).
   - Cons: Alto esfuerzo (DDL, 3+ pantallas, motor exposición, mails); riesgo paridad Dynamics/Adminet.
   - Effort: High

3. **Híbrido incremental (fase A/B)** — Fase A: tabla política + exposición + evaluación unificada en checkout + fix bug matriz + semáforo toma. Fase B: cola Finanzas, cobranzas auto, hold preparación en Synap/VB6 bridge.
   - Pros: Entrega valor temprano en toma/alta; reduce big-bang; permite validar fórmula exposición en producción.
   - Cons: Estado intermedio donde hold preparación o mails pueden quedar stub; requiere disciplina para no perpetuar acoplamiento comercial.
   - Effort: Medium → High

### Recommendation

Adoptar **Approach 3 (híbrido)** con diseño target del **Approach 2**:

- **Núcleo:** nuevo servicio `ecom/services/credito_pedidos/` (exposición, política, evaluación) registrado en `catalog.py` con tabla dedicada por cliente/canal.
- **Checkout:** `mayorista_checkout_service.confirmar()` llama evaluador unificado; persiste `autorizacion_sistema` + metadata (motivos monto/días, exposición snapshot) para audit trail.
- **Aprobación Finanzas:** workflow independiente con permiso por Puesto (`finance.credito.aprobar` o similar); libera **solo el PED** (`Autorizado`) sin mutar `cliente.Credito`.
- **Comercial:** retirar o redefinir `credito_no_autorizado` para que no duplique cola Finanzas; hub pipeline con columnas distintas.
- **UI:** semáforo en toma (API pre-evaluación); pantallas nuevas estilo `alta_movimiento.html` para cola Finanzas y ABM políticas.
- **Exposición:** implementar fórmula acordada con capas configurables en política (CxC + PED abiertos + remitos NF + cheques + doc actual); `Credito=0` → sin tope $.
- **Fix inmediato en v1:** corregir `credito_cliente_masivo` (Credito$ vs días).

### Risks

- **Paridad exposición:** Balance+All + capas Adminet (mora, cheques) no tienen implementación previa; riesgo de divergencia vs Dynamics/legacy hasta validación con datos reales.
- **Acoplamiento comercial existente:** Hub y aprobación comercial ya interpretan `No Autorizado`; refactor obligatorio para evitar doble cola/confusión UX.
- **Hold preparación:** Synap no controla `Pedido_prep` VB6 hoy; hace falta contrato claro (¿solo Synap prep futuro? ¿bridge lectura `autorizacion_sistema` en VB6?).
- **Notificaciones:** Sin subsistema de plantillas editables por cliente/canal; riesgo de spam si no hay deduplicación/SLA (decisión #12).
- **Performance:** Cálculo exposición por confirmación (especialmente lote masivo vía `batch_checkout_masivo`) puede requerir cache o consultas optimizadas.
- **Permisos:** Familia `finance.*` existe pero no hay permiso granular de aprobación crédito; definir en propuesta para no colisionar con `ecom.pedidos.aprobar`.
- **Alcance v1 vs TPV:** Reutilizar ideas de `tpv_paridad_precheck` sin mezclar código TPV en el módulo pedidos.

### Ready for Proposal

**Sí.** El orchestrator puede avanzar a `sdd-propose` con:

- Alcance v1 acotado a PED/PRE canal ecom/mayorista (TPV explícitamente fuera).
- Decisiones de negocio ya cerradas (no reabrir).
- Propuesta debe detallar: modelo tabla política, fórmula exposición por capas, permiso Finanzas, separación de colas hub, fases A/B, rollback (desactivar flag master crédito), y corrección bug `pedido_masivo_matriz`.
- Specs delta esperadas: nueva capability `ecom-credito-pedidos` + amendments a `ecom-checkout-mayorista` y `ecom-aprobacion-pedidos`.
