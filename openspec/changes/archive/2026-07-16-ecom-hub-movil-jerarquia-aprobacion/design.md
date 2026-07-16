# Design: Hub pedidos móvil + jerarquía comercial y aprobación

**Change:** `ecom-hub-movil-jerarquia-aprobacion` · **Fecha:** 16/07/2026

## Technical Approach

Dos capas gobernadas por flags en `configuracion_ecom` (master `ecom_workflow_jerarquia_comercial`, sub `ecom_aprobacion_pedidos_activa`). Flag OFF = paridad actual (JSON carteras + filtro CodViajante). Servicio único `alcance_comercial` reemplaza `cartera_permitida` como origen de alcance; hub, objetivos e informe lo consumen. Aprobación se modela como estado comercial SEPARADO de `comp_ped.autorizacion_sistema` (crédito legacy). UI canon MPR/reports (no ventas/objetivos).

## Architecture Decisions

| Decisión | Opción elegida | Rechazado | Rationale |
|---|---|---|---|
| Modelo org | 2 tablas árbol 1-padre | tabla self-ref única; N:M mesh | Roles explícitos, valida 1 padre por FK+unique, migración directa desde JSON |
| Estado aprobación | Columna `estado_aprobacion_comercial` en `comp_ped` (+ eventos) | Reusar `autorizacion_sistema` | Evita colisión crédito/comercial; filtro SQL en hub |
| Alcance | `alcance_comercial.alcance_viajantes_comercial` con cache request | Query inline | DRY; un solo punto workflow ON/OFF |
| DDL | Provider `ecom_jerarquia_aprobacion` en `catalog.py` | ALTER suelto | Regla repo: DDL en catálogo central |
| Reglas aprobación | Evaluación en `confirmar` tras precio/crédito | Post-alta batch | Datos en transacción; estado correcto al nacer PED |
| Migración JSON | Comando idempotente; no borra claves JSON | Migración destructiva | Rollback OFF vuelve a JSON intacto |

## Data Model

- **`ecom_org_gerente_supervisor`**, **`ecom_org_supervisor_vendedor`**: árbol 1-padre G→S→V.
- **`comp_ped`** (ALTER): `estado_aprobacion_comercial`, aprobador, fecha, motivo.
- **`ecom_aprobacion_evento`**: auditoría y routing.

Tipos vía `administranet_types`.

## Services

- `ecom/services/jerarquia_comercial.py`: CRUD árbol, `subarbol_de`, `rol_de`.
- `ecom/services/alcance_comercial.py`: `alcance_viajantes_comercial`.
- `ecom/services/aprobacion_pedidos.py`: `evaluar_reglas`, `resolver` con routing S→G.

## Integration Points

- `pedidos_hub_pipeline`: filtro alcance + columna `por_aprobar`.
- `vendedor_operativo.cartera_permitida`: delega a alcance cuando ON.
- `checkout_service.confirmar`: hook post-autorización crédito.
- `objetivos_mysql` / `ventas_objetivos_bo_runner`: filtro por alcance.

## Rollout / Rollback

Rollout: DDL → backfill JSON → flags OFF validar → master ON piloto → subflag aprobación ON. Rollback: flags→No (instantáneo).
