# Jerarquía comercial, hub móvil y aprobación de pedidos

**Change:** `ecom-hub-movil-jerarquia-aprobacion`  
**Fecha:** 16/07/2026  
**Master flag:** `ecom_workflow_jerarquia_comercial` (default **No**)

## Propósito

Cuando el master flag está **activo**, Synap reemplaza las carteras JSON legacy por un organigrama **Gerente → Supervisor → Vendedor**, filtra hub/objetivos/informes por **alcance comercial** y opcionalmente activa un **workflow de aprobación comercial** separado de `autorizacion_sistema`.

Con master **inactivo** (REQ-GLOB-01), el sistema conserva el comportamiento anterior: JSON `ecom_vendedores_a_cargo_*`, alcance propio del vendedor, hub sin cola comercial y checkout sin `estado_aprobacion_comercial`.

## Flags y configuración

Ver [AJUSTES_VENTAS.md](AJUSTES_VENTAS.md). Resumen:

| Flag | Efecto |
|------|--------|
| `ecom_workflow_jerarquia_comercial` | Master: organigrama + alcance org |
| `ecom_aprobacion_pedidos_activa` | Subflag: cola comercial (solo si master ON) |
| Umbrales monto / desc pie / desc renglón | Reglas del motor; vacío = regla inactiva |

Helpers: `ecom.services.ecom_config_mysql`.

## Organigrama (ABM)

- **UI:** sección «Jerarquía comercial» en `/ecom/mayoristapp/ajustes-ventas/` (canon reportes/MPR).
- **Permiso edición:** `ecom.jerarquia.editar`.
- **Servicio:** `ecom/services/jerarquia_comercial.py` — CRUD vínculos, `rol_de`, `subarbol_de`, validación 1-padre y sin ciclos.
- **API:** `GET/POST /ecom/api/mayoristapp/jerarquia/nodos/` (`ecom/jerarquia_views.py`).

Tablas MySQL (provider `ecom_jerarquia_aprobacion`):

- `ecom_org_gerente_supervisor`
- `ecom_org_supervisor_vendedor`

## Alcance comercial

`ecom/services/alcance_comercial.py` → `alcance_viajantes_comercial(base, ctx)`:

- **Master OFF:** delega cartera JSON / `[CodViajante]` (paridad legacy).
- **Master ON:** subárbol según rol + permiso `ecom.pedidos.ver_todos`.
- Cache por request en `ctx["_alcance_comercial_cache"]`.

Consumidores: hub pipeline, selector vendedor, objetivos ventas, informe `ventas-objetivos-vs-bo`.

## Hub de pedidos (móvil + kanban)

Ruta: `/ecom/mayoristapp/pedidos/`. Documento base: [PEDIDOS_HUB_KANBAN.md](PEDIDOS_HUB_KANBAN.md).

- **&lt; lg:** chips de estado + tarjetas (sin scroll horizontal); tap → `/mayoristapp/venta/?cod_mov=`.
- **≥ lg:** kanban existente (Lista | Kanban).
- **Filtro alcance:** `CodViajante IN (alcance)` vía pipeline.
- **Aprobación ON:** columna/cola «Por aprobar» con CTA aprobar/rechazar scoped (`ecom.pedidos.aprobar`).

Pipeline: `ecom/services/pedidos_hub_pipeline.py`.  
API: `GET /ecom/api/mayoristapp/pedidos/hub/`.

## Aprobación comercial

**Permiso:** `ecom.pedidos.aprobar`.

Motor: `ecom/services/aprobacion_pedidos.py`

- Reglas: monto, descuento pie/renglón, crédito no autorizado, cliente nuevo.
- Routing: Supervisor → Gerente según organigrama.
- Estados en `comp_ped.estado_aprobacion_comercial`: `-` | `pendiente` | `aprobado` | `rechazado`.
- Auditoría: `ecom_aprobacion_evento`.
- **No modifica** `autorizacion_sistema`.

Hook checkout: `ecom/services/mayorista_checkout_service.py` → `confirmar` tras `evaluar_autorizacion`.

| Método | Path |
|--------|------|
| GET | `/ecom/api/mayoristapp/aprobacion/pendientes/` |
| POST | `/ecom/api/mayoristapp/aprobacion/<cod_mov>/aprobar/` |
| POST | `/ecom/api/mayoristapp/aprobacion/<cod_mov>/rechazar/` |

## Migración JSON → organigrama

Comando idempotente (no borra claves legacy):

```bash
docker exec Synap_app python manage.py migrar_carteras_a_jerarquia <base_empresa>
docker exec Synap_app python manage.py migrar_carteras_a_jerarquia <base_empresa> --dry-run
```

También se ejecuta al aplicar el provider `ecom_jerarquia_aprobacion` (backfill automático).

Detalle operativo: [../general/JERARQUIA_COMERCIAL_ECOM.md](../general/JERARQUIA_COMERCIAL_ECOM.md).

## Rollout recomendado

1. Aplicar DDL provider `ecom_jerarquia_aprobacion` en base empresa (staging → prod).
2. Verificar backfill / ejecutar comando manual si hace falta.
3. Activar master en Ajustes de ventas; validar ABM y alcance en hub.
4. Activar subflag aprobación y umbrales; probar cola en hub móvil.
5. Capacitar supervisores/gerentes con permiso `ecom.pedidos.aprobar`.

## Tests

```bash
docker exec Synap_app python manage.py test \
  ecom.tests.test_jerarquia_comercial \
  ecom.tests.test_alcance_comercial \
  ecom.tests.test_aprobacion_pedidos \
  ecom.tests.test_migrar_carteras_jerarquia \
  ecom.tests.test_aprobacion_flujo_api \
  ecom.tests.test_pedidos_hub_pipeline
```
