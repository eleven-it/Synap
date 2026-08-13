# Deuda pendiente — Reflote Tienda Nube ↔ AdministraNET

Documentación del change SDD **`tiendanube-administranet-reflote`** (Engram).  
Fecha de corte: **13/08/2026**.

## Resumen

El reflote entrega inbox webhook ACK \<3s, handler único order/paid, outbox saliente, contratos API 2026 sobre versión **2025-03**, UI canon en pantallas prioritarias y normalización `administranet_types`. El módulo queda **cableado pero opt-in**: ops debe activar `ModuleConfig`, cron de drenaje y credenciales antes de producción.

## Implementado en el reflote

| Área | Entregable |
|------|------------|
| Inbox webhook | Persistir → 2xx → worker (`WebhookEvent.retry`, `next_retry_at`) |
| Handler único | `webhook_service.WebhookProcessor`; eliminado `webhook_processor.py` |
| Worker | `inbox_worker.py` + `tiendanube_drain_inbox` / `tiendanube_drain_outbox` |
| Outbox | Modelo `TiendanubeOutboxEvent` (migración **0027**), catch-up pedidos |
| Contratos 2026 | ADR [ADR_TIENDANUBE_CONTRATOS_API_2026.md](ADR_TIENDANUBE_CONTRATOS_API_2026.md) |
| Tipos Adminet | `administranet_types` + transacción REC+comp_ped en `adminet_service.py` |
| UI | Wizard, config, status, auto_sync y pantallas secundarias — `TnSynapConfirm` / `TnSynapMessages`; **cero** `alert`/`confirm`/`prompt` nativos |

## Deuda pendiente (ops / follow-up)

### 1. Celery y Beat comentados

| Ítem | Estado |
|------|--------|
| `django_project/celery.py` | **Comentado** — instalación mínima Synap sin Celery en requirements |
| Beat schedule | Documentado en `tasks/webhook_tasks.py` (bloque comentado, intervalo 60 s) |
| **Interim ops** | Cron cada **1 min** (ver checklist) — **no** descomentar Beat en este change |

Cuando ops reactive Celery + Redis: descomentar `celery.py`, registrar Beat `drain-webhook-inbox-every-60s` y `drain-outbox-every-60s`, y **retirar** cron duplicado.

### 2. Cron interim (sin Celery)

Hasta habilitar Beat:

```cron
*/1 * * * * docker exec Synap_app python manage.py tiendanube_drain_inbox
*/1 * * * * docker exec Synap_app python manage.py tiendanube_drain_outbox
```

Batch default: **50** eventos por ejecución (`--limit` opcional). Exit code **1** si hubo fallos en el lote.

### 3. `ModuleConfig` inactivo

El reflote **no** activa el módulo en producción. Tras despliegue, ops debe:

1. Registrar/actualizar fila: `docker exec Synap_app python manage.py add_tiendanube_administranet_module`
2. Activar menú y rutas: `docker exec Synap_app python manage.py setup_modules --activate tiendanube_administranet --reload-menus`

Ver pasos completos en [CHECKLIST_HABILITACION_TIENDANUBE_ADMINISTRANET.md](CHECKLIST_HABILITACION_TIENDANUBE_ADMINISTRANET.md) § Post-reflote.

### 4. OAuth real (fuera de este change)

- Wizard y formulario persisten token manual / renovación UI.
- Flujo OAuth completo con partner portal y callback en producción → **follow-up ops**, no bloqueante del merge de código.

### 5. Diálogos nativos (cerrado en 7.3b)

Grep **13/08/2026** post-lote 7.3b: **cero** `alert`/`confirm`/`prompt` en `tiendanube_administranet/templates/`.

Confirmaciones destructivas/operativas → `includes/synap_confirm_modal.html` (`TnSynapConfirm`) y `includes/tn_confirm_delete_links.html`. Feedback corto → `includes/tn_ui_scripts.html` (`TnSynapMessages`).

### 6. Migraciones pendientes de aplicar en entorno

| Migración | Contenido |
|-----------|-----------|
| `0026_tiendanubeconfig_location_id` | Campo opcional `TiendanubeConfig.location_id` |
| `0027_tiendanubeoutboxevent` | Modelo outbox + índice `(status, next_retry_at)` |

```bash
docker exec Synap_app python manage.py migrate tiendanube_administranet
```

## Tests del reflote

```bash
docker exec Synap_app python manage.py test tiendanube_administranet \
  --keepdb
```

Suite relevante: `test_sync_errors`, `test_webhook_inbox`, `test_tiendanube_api_auth`, `test_api_payload_contracts`, `test_config_ux`, outbox/catch-up, `test_adminet_service`.

## Referencias

- Checklist activación: [CHECKLIST_HABILITACION_TIENDANUBE_ADMINISTRANET.md](CHECKLIST_HABILITACION_TIENDANUBE_ADMINISTRANET.md)
- Contratos API: [ADR_TIENDANUBE_CONTRATOS_API_2026.md](ADR_TIENDANUBE_CONTRATOS_API_2026.md)
- Deuda histórica P0–P2: [TIENDANUBE_DEUDA_TECNICA_P0_P2.md](TIENDANUBE_DEUDA_TECNICA_P0_P2.md)
- Engram: `sdd/tiendanube-administranet-reflote/*`
