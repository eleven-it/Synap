# Jerarquía comercial e-com — DDL, permisos y migración JSON

**Change:** `ecom-hub-movil-jerarquia-aprobacion`  
**Fecha:** 16/07/2026

## Provider MySQL legacy

**ID:** `ecom_jerarquia_aprobacion`  
**Ubicación:** `core/services/legacy_mysql_schema/catalog.py` → `run_ecom_jerarquia_aprobacion_mysql`

Aplicación: Archivo → **Migración esquema MySQL (legacy)** → «E-com — jerarquía comercial y aprobación de pedidos».

### Objetos creados

| Objeto | Descripción |
|--------|-------------|
| `ecom_org_gerente_supervisor` | Vínculo Gerente → Supervisor (1 supervisor activo por fila) |
| `ecom_org_supervisor_vendedor` | Vínculo Supervisor → Vendedor (1 supervisor activo por vendedor) |
| `ecom_aprobacion_evento` | Auditoría de solicitudes/aprobaciones/rechazos |
| `comp_ped.estado_aprobacion_comercial` | Estado comercial (`-`, `pendiente`, `aprobado`, `rechazado`) |
| `comp_ped.aprobador_codviajante` | CodViajante que resolvió |
| `comp_ped.aprobacion_fecha` | Fecha resolución |
| `comp_ped.aprobacion_motivo` | Motivo texto |
| Claves `configuracion_ecom` | Master, subflag, umbrales y atajos hub (ver [AJUSTES_VENTAS.md](../ecom/AJUSTES_VENTAS.md)) |

Tras DDL, el provider intenta **backfill** desde JSON legacy (`ecom_vendedores_a_cargo_*`).

## Permisos nuevos

Definidos en `core/constantes_permisos.py`:

| Permiso | Uso |
|---------|-----|
| `ecom.jerarquia.editar` | ABM organigrama en Ajustes de ventas |
| `ecom.pedidos.aprobar` | Aprobar/rechazar cola comercial (API + hub) |

Grupo default **E-com** incluye ambos permisos para perfiles comerciales ampliados.

## Migración JSON → tablas org

**Origen:** claves `ecom_vendedores_a_cargo_{CodSupervisor}` en `configuracion_ecom_conf` con lista JSON de CodViajante.

**Destino:** filas activas en `ecom_org_supervisor_vendedor`.

**Comando:**

```bash
docker exec Synap_app python manage.py migrar_carteras_a_jerarquia <base_empresa>
docker exec Synap_app python manage.py migrar_carteras_a_jerarquia <base_empresa> --dry-run
```

**Reglas:**

- Idempotente: re-ejecutar no duplica vínculos activos.
- **No elimina** claves JSON legacy (paridad rollback / master OFF).
- Supervisores sin gerente quedan como raíz del subárbol (sin vínculo GS automático).

Implementación: `ecom/services/jerarquia_comercial.py` → `backfill_carteras_desde_config`.

## Flag master y paridad legacy (REQ-GLOB-01)

Con `ecom_workflow_jerarquia_comercial = No`:

- Alcance: JSON / vendedor propio (`alcance_comercial` delega a `vendedor_operativo`).
- Subflag aprobación **sin efecto** aunque esté en Sí en DB.
- Hub, checkout, objetivos e informe BO mantienen comportamiento pre-change.

Documentación funcional: [../ecom/JERARQUIA_COMERCIAL_APROBACION.md](../ecom/JERARQUIA_COMERCIAL_APROBACION.md).

## Referencias

- Herramienta global DDL: [HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md](HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md)
- Tipos AdministraNET: [TIPOS_DATOS_ADMINISTRANET.md](TIPOS_DATOS_ADMINISTRANET.md)
- Móvil Nivel A (hub/venta/APIs): [MOBILE_SOLO_NIVEL_A.md](MOBILE_SOLO_NIVEL_A.md)
