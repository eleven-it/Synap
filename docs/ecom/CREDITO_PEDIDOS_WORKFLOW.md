# Workflow crédito en pedidos (Synap + bridge VB6)

Documentación operativa del change **workflow-limite-credito-pedidos** (archivado 25/07/2026).  
Autoridad de negocio: paquete `ecom/services/credito_pedidos/`.

**Manual de usuario (operadores):** [MANUAL_USUARIO_VENTAS.md](MANUAL_USUARIO_VENTAS.md) §11–§12 · HTML `/ecom/manual/#credito-pedidos`.

## Resumen

El checkout mayorista evalúa crédito (monto, días, exposición por capas) y persiste el resultado en `comp_ped.autorizacion_sistema` y en `ecom_credito_evaluacion`. Si el PED queda **No Autorizado** y el flag master está ON, entra en **cola Finanzas** (`comp_ped.estado_credito_finanzas`) con hold de preparación opcional. Finanzas aprueba o rechaza **sin mutar** `cliente.Credito`. Los avisos a cobranzas se encolan en `EcomMailQueue` con anti-ruido SLA **24 h**.

## Flags (`configuracion_ecom`)

| Clave | Default | Efecto |
|-------|---------|--------|
| `ecom_credito_pedidos_activa` | `No` | Master. OFF ⇒ legacy solo-días (`mayorista_credito.py`). ON ⇒ evaluador unificado + cola Finanzas. |
| `ecom_credito_hold_prep_activo` | `No` | Si ON y PED No Autorizado: `comp_ped.credito_hold_prep='Si'` bloquea preparación. |
| `ecom_credito_aviso_sla_horas` | `24` | Ventana dedup avisos por `(id_cliente, tipo_aviso, canal)`. Override opcional en política. |

Helpers: `credito_pedidos_activo()`, `credito_hold_prep_activo()` en `ecom/services/ecom_config_mysql.py`.

**Rollback:** poner `ecom_credito_pedidos_activa=No` por empresa. El DDL permanece (idempotente); no hay que revertir tablas.

## Permisos Synap Store

| Permiso | Uso |
|---------|-----|
| `finance.credito.aprobar` | Cola Finanzas: aprobar/rechazar PED pendientes de crédito (hub, `/ecom/credito/cola/`). |
| `finance.credito.configurar` | ABM políticas por cliente/canal y plantillas de aviso. |

Segregación de funciones (ADR 8): quien libera un PED **no** puede cambiar topes ni plantillas. Comodines `finance.*` y `*` otorgan ambos.

Helpers: `puede_aprobar_credito()`, `puede_configurar_credito()` en `ecom/permissions.py`.

## Exposición por capas

Función `calcular_exposicion(cur, cliente, politica)` en `credito_pedidos/exposicion.py`:

| Capa (política) | Fuente aproximada |
|-----------------|-------------------|
| `cxc` | Saldo cuenta corriente (`cuentacliente`) |
| `ped_abiertos` | PED pendientes del cliente |
| `remitos_nf` | Remitos no facturados |
| `cheques` | Cheques en cartera |
| `doc_actual` | Importe del documento en evaluación |

Cada capa se activa/desactiva en la política (`ecom_credito_politica`).  
`exposicion = Σ capas ON`; `disponible = cliente.Credito − exposicion`.  
**`Credito = 0`** ⇒ sin tope en pesos (solo evalúa días si aplica).

El snapshot completo (capas, semáforo, motivos) se guarda en `ecom_credito_evaluacion` al confirmar checkout.

## Flujo Synap

```
Toma PED ── POST /ecom/credito/pre-check/ ──> evaluar_pedido(persistir=False) ──> semáforo
Checkout confirmar() ──> evaluar_pedido(persistir=True) ──> comp_ped.autorizacion_sistema
                              │
                    No Autorizado + flag ON
                              │
              estado_credito_finanzas='pendiente'
              credito_hold_prep='Si' (si subflag hold ON)
                              │
              Cola Finanzas (finance.credito.aprobar)
                    ├── aprobar → aprobado, hold OFF, autorizacion_sistema='Autorizado'
                    └── rechazar → rechazado (hold permanece)
                              │
              avisos.py → EcomMailQueue (tipo pedido_bloqueado, dedup 24 h + 1× por PED)
```

### Desacople comercial vs Finanzas

Con flag crédito ON, la regla `_REGLA_CREDITO` **no** participa en `aprobacion_pedidos.evaluar_reglas()`. La cola comercial (`estado_aprobacion_comercial`) y la cola Finanzas (`estado_credito_finanzas`) son independientes en el hub Kanban.

## Hold preparación y bridge VB6

### Columna `comp_ped.credito_hold_prep`

- Valores: `Si` | `No` (default `No`).
- Synap setea `Si` cuando `ecom_credito_hold_prep_activo=ON` y el PED queda No Autorizado tras checkout.
- Finanzas al **aprobar** setea `No` y `autorizacion_sistema='Autorizado'`.

### Gate Synap

- Función: `puede_avanzar_a_preparacion(cursor, cod_mov)` en `credito_pedidos/aprobacion.py`.
- Wrapper logística: `validar_gate_credito_preparacion(base_empresa, cod_mov)` en `logistica_estado_pedidos_relay.py`.
- **MUST** invocarse en toda transición Synap futura a «En preparación». Hoy la escritura de preparación sigue en AdministraNET desktop/VB6; el tablero Synap (`/ecom/mayoristapp/logistica/estado-pedidos/`) es solo lectura.

### Contrato VB6 `Pedido_prep`

Antes de permitir preparación del PED en desktop:

1. Si existe columna `credito_hold_prep` y valor `Si` → **denegar** preparación con mensaje al operador.
2. Fallback (columna ausente, flag empresa ON): denegar si `autorizacion_sistema='No Autorizado'`.

Parche VB6 documentado aquí; implementación fuera del árbol Python Synap (companion release).

## Avisos y SLA anti-ruido

- Plantillas editables: `ecom_credito_plantilla_aviso` (ABM con `finance.credito.configurar`).
- Render + encolado: `credito_pedidos/avisos.py` → `EcomMailQueue`.
- Dedup default **24 h** por `(id_cliente, tipo_aviso, canal)` usando `ecom_credito_aviso_log`.
- Tipo `pedido_bloqueado`: además **1 mail por `CodigoMovimiento`** mientras el hold esté activo (evita spam al reintentar checkout).

## Pantallas Synap

| Ruta | Permiso | Descripción |
|------|---------|-------------|
| `/ecom/credito/cola/` | `finance.credito.aprobar` | Cola Finanzas — menú **Ventas / E-commerce → Crédito → Cola crédito Finanzas** |
| `/ecom/credito/politicas/` | `finance.credito.configurar` | ABM políticas — menú **→ Políticas de crédito** |
| `/ecom/credito/plantillas/` | `finance.credito.configurar` | ABM plantillas aviso — menú **→ Plantillas aviso crédito** |
| Hub pedidos | CTAs gateados | Columna crédito Finanzas (REQ-HUB-02/11) |

Look visual: hero `slate-800`, patrón Alta Movimiento (`docs/stock/ALTA_MOVIMIENTO_UX.md`).

### UX de las pantallas (cupos AdministraNET visibles)

Principio de producto: el **cupo $** y los **días base** viven en AdministraNET (`cliente.Credito`,
`cliente.saldo`, `cliente.credito_limite_dias`). Las pantallas Synap los **muestran** y solo
administran los overrides de política (días por canal + capas de exposición); nunca los mutan.

- **Cola Finanzas** (`cola_finanzas.html`): cada fila muestra PED, cliente, fecha, **importe**,
 cupo AdministraNET, saldo, disponible (de la evaluación o aproximado), límite de días y
 **semáforo** verde/ámbar/rojo con motivos (misma paleta que `pedidos_order_header.html`).
 Banner cuando el workflow está desactivado por empresa, filtro de texto local + select de
 antigüedad (30/60/90 días, recarga `?dias=`) y empty state educativo. Aprobar y Rechazar usan
 **modales Synap** (sin `alert`/`confirm`) y feedback por `mprShowAviso`.
- **Políticas** (`politica_list.html`): panel *Consultar cupo AdministraNET* con búsqueda
 predictiva de cliente que solo lee `api_credito_cliente_resumen` (no crea política); tabla con
 cliente o «Default empresa», canal, días de política (o «Usa AdministraNET»), cupo, saldo,
 límite de días Adminet, chips de capas activas y estado.
- **Alta política** (`politica_form.html`): el input numérico de ID cliente fue reemplazado por
 **búsqueda predictiva** (combobox Alpine, debounce 280 ms, teclado), toggle *Usar política default
 empresa* (`id_cliente = null`), panel read-only **Límites AdministraNET** al seleccionar cliente,
 prefill editable de `limite_dias` desde `credito_limite_dias` (vacío = usar el del cliente) y
 toggles Activo/Inactivo para las capas (`capa_cxc`, `capa_ped_abiertos`, `capa_remitos_nf`,
 `capa_cheques`, `capa_doc_actual`, `incluir_mora`) que viajan en el POST.
- **Plantillas** (`plantillas.html`): `tipo_aviso` como `select` (`pedido_bloqueado`, `cobranza`,
 u otro identificador libre), cliente opcional por búsqueda predictiva (vacío = default empresa),
 chips para insertar variables (`nro_comprobante`, `nombre_cliente`, `importe`, `fecha`, `saldo`)
 y listado con jerarquía tipo · canal · estado · alcance.

Includes compartidos: `ecom/templates/ecom/credito/includes/cliente_predictivo.html` (combobox) y
`cliente_credito_panel.html` (panel read-only de límites Adminet). Contratos verificados en
`ecom/tests/test_credito_pedidos_ui_static.py`.

## Rollout recomendado

1. Ejecutar proveedor DDL `ecom_credito_pedidos` (`run_ecom_credito_pedidos_mysql` vía herramienta global).
2. Dejar flags OFF; validar regresión checkout/aprobación/masivo.
3. Activar `ecom_credito_pedidos_activa` por empresa tras validar snapshots vs Dynamics.
4. Activar `ecom_credito_hold_prep_activo` cuando Finanzas confirme operación de hold.
5. Desplegar parche VB6 `Pedido_prep` en desktop (mismo criterio de columna).

## Referencias

- Design: `openspec/changes/workflow-limite-credito-pedidos/design.md` (ADRs 1–9)
- Spec capability: `openspec/changes/workflow-limite-credito-pedidos/specs/ecom-credito-pedidos/spec.md`
- Tests: `ecom/tests/test_credito_pedidos_*.py`, integración `test_credito_pedidos_integration.py`
