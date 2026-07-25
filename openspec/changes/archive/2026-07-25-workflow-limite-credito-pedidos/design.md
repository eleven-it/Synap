# Design: Workflow límite de crédito en pedidos

## Enfoque técnico

Módulo dedicado `ecom/services/credito_pedidos/` como **única autoridad** de crédito (política, exposición, evaluación, hold, aprobación, avisos). El checkout y la UI solo **consumen** su resultado. Entrega en dos fases sobre el mismo diseño target: **A** = datos + evaluación + semáforo; **B** = cola Finanzas + hold + avisos. Todo bajo flag master `ecom_credito_pedidos_activa`; OFF ⇒ comportamiento legacy solo-días de `mayorista_credito.py`.

Cubre las specs del change: capability nueva `ecom-credito-pedidos` y deltas `ecom-checkout-mayorista` (REQ-CHK-004), `ecom-aprobacion-pedidos` (REQ-APR-02), `ecom-pedidos-hub-kanban` (REQ-HUB-02/11), `ecom-pedido-venta-shell` (REQ-VTA-10/11), `permisos-synap-store`, `roles-synap-por-puesto` y `ui-fuente-verdad-reportes-mpr`.

## ADRs

| # | Decisión | Alternativa rechazada | Rationale |
|---|----------|----------------------|-----------|
| 1 | Paquete `ecom/services/credito_pedidos/` (`politica.py`, `exposicion.py`, `evaluacion.py`, `aprobacion.py`, `avisos.py`) + tablas MySQL creadas por proveedor `run_ecom_credito_pedidos_mysql` en `core/services/legacy_mysql_schema/catalog.py` (registrado en `PROVIDER_REGISTRY`, id `ecom_credito_pedidos`) | Extender `mayorista_credito.py` in-place; columnas extra en `cliente` | Regla obligatoria del repo: todo DDL legacy vive en `catalog.py`. Política por **cliente+canal** no cabe en `cliente`. Separa evaluación / aprobación / notificación y hace testeables las capas |
| 2 | `calcular_exposicion(cur, cliente, politica)` con capas ON/OFF parametrizadas en la política (`cxc`, `ped_abiertos`, `remitos_nf`, `cheques`, `doc_actual`); `exposicion = Σ capas activas`, `disponible = Credito − exposicion`; `Credito = 0` ⇒ sin tope $ | Fórmula fija Balance+All hardcodeada | Cada implementación AdministraNET difiere; parametrizar permite validar paridad Dynamics sin redeploy y apagar capas ruidosas en fase A |
| 3 | Cola Finanzas **desacoplada**: se retira `_REGLA_CREDITO` de `aprobacion_pedidos.evaluar_reglas()`; crédito vive en `comp_ped.estado_credito_finanzas` y eventos en `ecom_credito_evento`; comercial sigue en `estado_aprobacion_comercial` / `ecom_aprobacion_evento` | Reusar la cola comercial con una regla más | Distinto permiso, distinto routing (Finanzas no es jerarquía G→S→V) y doble cola en el hub. Se replica el **patrón** de `aprobacion_pedidos.py`, no su tabla |
| 4 | Pantallas **nuevas** bajo `ecom/templates/ecom/credito/` con el look de `stock/alta_movimiento.html` (hero bar `slate-800`, contenedor full-width sin `max-w-*`, secciones colapsables, footer sticky, modales Synap + `mprShowAviso`), según `docs/stock/ALTA_MOVIMIENTO_UX.md` | Extender `pedidos_hub.html` / `pedido_detalle.html` | Out of scope explícito del proposal; las pantallas ecom de pedidos ya están saturadas y no son canon visual |
| 5 | Semáforo **de solo lectura** en el shell de toma (`pedidos_order_header.html`) alimentado por endpoint pre-check `POST /ecom/credito/pre-check/`, que llama `evaluar_pedido(..., persistir=False)`; con semáforo ámbar/rojo, Confirmar abre **modal Synap** de advertencia (REQ-VTA-11), nunca `confirm` nativo | Bloquear el alta en la toma | El alta nunca se bloquea (paridad legacy); el semáforo informa antes de confirmar y usa el **mismo** evaluador que el checkout, evitando divergencia |
| 6 | Flag master `ecom_credito_pedidos_activa` en `configuracion_ecom` (helper `credito_pedidos_activo()` en `ecom_config_mysql.py`, patrón `_normalizar_si_no`, default `No`); subflag `ecom_credito_hold_prep_activo` para fase B | Setting Django o migración con rollback de DDL | El repo ya usa este patrón para `ecom_aprobacion_pedidos_activa`; permite rollback por empresa sin deploy. El DDL permanece (idempotente) |
| 7 | Avisos con plantillas editables en `ecom_credito_plantilla_aviso` renderizadas por `avisos.py` y encoladas en `EcomMailQueue` (`ecom/models.py`) usando `core.services.outbound_email`; anti-ruido por `ecom_credito_aviso_log` | Envío síncrono desde el checkout | `comprobante_mail_async.py` ya establece el patrón cola + `outbound_email`; el envío síncrono rompería la transacción del alta |
| 7b | **SLA anti-ruido (cerrado):** dedup por `(id_cliente, tipo_aviso, canal)` con ventana default **24 h** (`ecom_credito_aviso_sla_horas` en `configuracion_ecom`, override opcional en política). Tipo `pedido_bloqueado` adicionalmente MUST deduplicar por `CodigoMovimiento` (1 mail por PED mientras hold activo). | SLA fijo hardcodeado / sin dedup | 24 h equilibra cobranza vs spam; por-PED evita reenvíos al reintentar checkout |
| 8 | Permisos Finance: `finance.credito.aprobar` (cola) y **`finance.credito.configurar`** (ABM políticas + plantillas), ambos en `PERMISOS_POR_MODULO["Finance"]`, seed idempotente, asignables por **Puesto** | Un solo permiso para todo | Segregación de funciones: quien libera un PED no debe poder cambiar topes/plantillas de la empresa. Comodines `finance.*` / `*` otorgan ambos |
| 9 | **Hold prep / bridge VB6 (cerrado):** Synap persiste `comp_ped.credito_hold_prep` (`Si`/`No`) cuando flag hold ON y resultado `No Autorizado`. Toda transición Synap a «En preparación» MUST rechazarse si hold=`Si`. Contrato VB6: `Pedido_prep` MUST denegar preparación si `credito_hold_prep='Si'` (fallback legado: si columna ausente y flag empresa ON, denegar si `autorizacion_sistema='No Autorizado'`). Parche VB6 documentado en `docs/ecom/CREDITO_PEDIDOS_WORKFLOW.md` §bridge; no bloquea apply Synap | Solo confiar en `autorizacion_sistema` sin columna | Columna explícita permite liberar un PED sin confundir semántica histórica de `autorizacion_sistema` y da contrato testeable |

## Fases

- **A** — DDL + `politica.py` + `exposicion.py` + `evaluacion.py`; `mayorista_checkout_service.confirmar()` llama al evaluador unificado y persiste snapshot; semáforo en toma; fix naming `pedido_masivo_matriz.credito_cliente_masivo`. Hold y cola quedan inertes.
- **B** — `aprobacion.py` + cola Finanzas + hold de preparación (`comp_ped.credito_hold_prep`, leído por el pipeline y por VB6 como bridge) + `avisos.py` + ABM plantillas + columna hub.

## Flujo

```
Toma PED ──pre-check──> evaluar_pedido(persistir=False) ──> semáforo (verde/ámbar/rojo)
                                   │
Checkout confirmar() ──────────────┤ evaluar_pedido(persistir=True)
                                   ▼
              resolver_politica(cliente, canal) + calcular_exposicion(capas)
                                   ▼
        snapshot ecom_credito_evaluacion  ──>  comp_ped.autorizacion_sistema
                                   │
            ┌──────────────────────┴──────────────────────┐
       Autorizado                                    No Autorizado
            │                                              │
      flujo normal            estado_credito_finanzas='pendiente' + hold_prep='Si' (B)
                                                           ▼
                                    Cola Finanzas (finance.credito.aprobar)
                                              ├── aprobar → 'aprobado', hold OFF,
                                              │   autorizacion_sistema='Autorizado'
                                              │   (NO muta cliente.Credito)
                                              └── rechazar → 'rechazado', hold ON
                                                           ▼
                                    avisos.py → EcomMailQueue (cobranzas, anti-ruido)
```

## Archivos

| Archivo | Acción | Detalle |
|---------|--------|---------|
| `ecom/services/credito_pedidos/__init__.py` | Crear | Fachada pública del módulo |
| `ecom/services/credito_pedidos/politica.py` | Crear | `resolver_politica(cur, cliente, canal)` con fallback a default de empresa |
| `ecom/services/credito_pedidos/exposicion.py` | Crear | Capas CxC / PED abiertos / remitos NF / cheques / doc actual |
| `ecom/services/credito_pedidos/evaluacion.py` | Crear | `evaluar_pedido()` → autorización + motivos + snapshot |
| `ecom/services/credito_pedidos/aprobacion.py` | Crear (B) | Cola, `resolver_finanzas()`, eventos, hold |
| `ecom/services/credito_pedidos/avisos.py` | Crear (B) | Render de plantillas + encolado + dedup |
| `ecom/credito_views.py` | Crear | Pre-check, cola Finanzas, ABM política, ABM plantillas |
| `ecom/templates/ecom/credito/{cola_finanzas,politica_form,politica_list,plantillas}.html` | Crear | Look Alta Movimiento |
| `core/services/legacy_mysql_schema/catalog.py` | Modificar | `run_ecom_credito_pedidos_mysql` + `PROVIDER_REGISTRY` + fila `configuracion_ecom` |
| `core/constantes_permisos.py` | Modificar | `finance.credito.aprobar` + `finance.credito.configurar` |
| `ecom/services/ecom_config_mysql.py` | Modificar | `KEY_CREDITO_PEDIDOS_ACTIVA`, `KEY_CREDITO_HOLD_PREP`, helpers |
| `ecom/services/mayorista_checkout_service.py` | Modificar | Evaluador unificado + snapshot (reemplaza `evaluar_autorizacion` cuando el flag está ON) |
| `ecom/services/mayorista_credito.py` | Modificar | Queda como fallback legacy solo-días |
| `ecom/services/aprobacion_pedidos.py` | Modificar | Retirar `_REGLA_CREDITO` |
| `ecom/services/pedidos_hub_pipeline.py` | Modificar | Columna `credito_finanzas` + label, sin duplicar tarjeta cuando también hay pendiente comercial |
| `ecom/permissions.py` | Modificar | Helpers `puede_aprobar_credito` / `puede_configurar_credito` (comodines `finance.*` / `*`) |
| `ecom/templates/ecom/pedidos_hub.html` | Modificar | CTA Aprobar/Rechazar crédito gateado por permiso (REQ-HUB-11) |
| `ecom/services/cliente_seleccion_relay.py` | Modificar | Exponer exposición/disponible al header |
| `ecom/templates/ecom/includes/pedidos_order_header.html` | Modificar | Semáforo monto/días/disponible |
| `ecom/services/pedido_masivo_matriz.py` | Modificar | Fix `credito_limite_dias` vs `Credito` $ |
| `ecom/urls.py` | Modificar | Rutas `credito/*` |
| `ecom/tests/test_credito_pedidos_*.py` | Crear | Exposición, evaluación, aprobación, flag OFF |
| `docs/ecom/CREDITO_PEDIDOS_WORKFLOW.md` | Crear | Documentación obligatoria |

## Contratos

```python
@dataclass
class ResultadoCredito:
    autorizacion: str            # 'Autorizado' | 'No Autorizado'
    motivos: list[str]           # ['monto', 'dias']
    limite: Decimal              # cliente.Credito (0 = sin tope)
    exposicion: Decimal
    disponible: Decimal
    dias_atraso: int | None
    capas: dict[str, Decimal]    # detalle por capa para el snapshot
    semaforo: str                # 'verde' | 'ambar' | 'rojo'
```

Tipos MySQL vía `core.utils.administranet_types` (`to_int_or_none`, `to_decimal_or_none`, `str_or_default`, `to_date_or_none`).

## Testing

| Capa | Qué | Cómo |
|------|-----|------|
| Unit | Capas de exposición, `Credito=0`, semáforo, dedup avisos | `docker exec Synap_app python manage.py test ecom` con cursor mock (patrón `test_mayorista_checkout_service.py`) |
| Integración | Checkout con flag ON/OFF, cola Finanzas, permiso denegado, hold | pytest-django marker `integration` |
| Regresión | `test_aprobacion_pedidos.py` sin regla crédito; `test_batch_checkout_masivo.py` | Suite existente |

## Rollout

DDL idempotente primero (`run_ecom_credito_pedidos_mysql`), flag OFF. Se activa por empresa tras validar la fórmula de exposición contra Dynamics con los snapshots de `ecom_credito_evaluacion`. Rollback = flag OFF (DDL permanece).

## Decisiones cerradas (ex-abiertas)

| Tema | Decisión |
|------|----------|
| Bridge VB6 hold | Columna `credito_hold_prep`; gate Synap + contrato `Pedido_prep` (ADR 9); parche VB6 en docs, no bloquea apply |
| SLA anti-ruido | Default **24 h** por cliente+tipo+canal; `pedido_bloqueado` además 1× por `CodigoMovimiento` (ADR 7b) |
| Permiso ABM | **`finance.credito.configurar`** separado de `finance.credito.aprobar` (ADR 8) |
