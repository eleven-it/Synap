# CRITICAL-FINDINGS — Hallazgos Críticos

**Estado:** COMPLETE  
**Fecha:** 25/08/2026

---

## ARCH-001: Sin Anti-Corruption Layer

| Campo | Valor |
|-------|-------|
| **Severidad** | HIGH |
| **Componente** | Arquitectura global |
| **Descripción** | 15+ apps acceden directamente a tablas MySQL AdministraNET sin abstracción |
| **Evidencia** | 2300+ cursor.execute, imports directos mysql_pool |
| **Impacto** | Imposible cambiar ERP o productizar |
| **Escenario** | Migrar a Odoo requiere reescribir 15 apps |
| **Recomendación** | Implementar ACL incremental |
| **Prioridad** | P0 |

## ARCH-002: core como god module

| Campo | Valor |
|-------|-------|
| **Severidad** | HIGH |
| **Componente** | core/ |
| **Descripción** | 256 referencias entrantes; contiene lógica stock, permisos, DDL de todos los dominios |
| **Evidencia** | Matriz dependencias 04 |
| **Impacto** | Cuello de botella para cualquier refactor |
| **Prioridad** | P0 |

## DATA-001: PostgreSQL sin tenant isolation

| Campo | Valor |
|-------|-------|
| **Severidad** | CRITICAL |
| **Componente** | Todos los modelos PG |
| **Descripción** | Datos PostgreSQL globales sin filtro por empresa |
| **Evidencia** | 08-MULTITENANCY.md TENANT-002 |
| **Impacto** | Cross-tenant data leakage |
| **Escenario** | Usuario empresa A accede expediente empresa B por UUID |
| **Prioridad** | P0 |

## DATA-002: DEFAULT_BASE_EMPRESA fallback

| Campo | Valor |
|-------|-------|
| **Severidad** | HIGH |
| **Componente** | reports/query_runner |
| **Descripción** | Reportes sin sesión usan empresa por defecto |
| **Evidencia** | settings.py:221, query_runner.py |
| **Prioridad** | P1 |

## SEC-001: AES key hardcoded

| Campo | Valor |
|-------|-------|
| **Severidad** | CRITICAL |
| **Componente** | settings.py:280, administranet_users.py:14 |
| **Descripción** | ADMINISTRANET_MYSQL_AES_KEY default 'a7v8xx2' (duplicado en user service) |
| **Evidencia** | settings.py, core/services/administranet_users.py |
| **Impacto** | Compromiso validación passwords |
| **Prioridad** | P0 |

## SEC-003: IDOR factura compra API

| Campo | Valor |
|-------|-------|
| **Severidad** | HIGH |
| **Componente** | factura_compra_captura/api/views.py |
| **Descripción** | List/detail expedientes sin filtro empresa de sesión |
| **Evidencia** | API vs web_views — web filtra, API no |
| **Impacto** | Cross-tenant data leakage en PostgreSQL |
| **Escenario** | Usuario empresa A accede expediente empresa B por UUID |
| **Recomendación** | Filtrar por `empresa_activa_id` en todas las rutas API |
| **Prioridad** | P0 |

## SEC-002: SQL dinámico en reportes

| Campo | Valor |
|-------|-------|
| **Severidad** | CRITICAL |
| **Componente** | reports/services/query_runner.py |
| **Descripción** | SQL construido dinámicamente desde config reportes |
| **Impacto** | SQL injection potencial |
| **Prioridad** | P0 |

## DATA-003: SQL dinámico con nombre de tabla variable

| Campo | Valor |
|-------|-------|
| **Severidad** | HIGH |
| **Componente** | reports/services/relationship_validation_service.py:184 |
| **Descripción** | `f"SELECT COUNT(*) FROM \`{from_table}\`"` — nombre tabla dinámico |
| **Evidencia** | 05-DATA-ACCESS-ARCHITECTURE.md DA-008 |
| **Impacto** | SQL injection si `from_table` proviene de input no validado |
| **Prioridad** | P1 |

## LEGACY-001: Acoplamiento AdministraNET nivel 4

| Campo | Valor |
|-------|-------|
| **Severidad** | HIGH |
| **Componente** | Global |
| **Descripción** | Auth, permisos, maestros, transacciones dependen de MySQL VB6 |
| **Evidencia** | 18-ADMINISTRANET-COUPLING.md |
| **Prioridad** | P1 (estratégico) |

## INFRA-001: Celery sin worker

| Campo | Valor |
|-------|-------|
| **Severidad** | HIGH |
| **Componente** | tiendanube_administranet/tasks |
| **Descripción** | Tasks Celery definidas pero sin broker/worker en compose |
| **Evidencia** | docker-compose.yml, celery.py comentado |
| **Prioridad** | P1 |

## TEST-001: Paths críticos sin tests

| Campo | Valor |
|-------|-------|
| **Severidad** | HIGH |
| **Componente** | fe_afip, self_checkout, login |
| **Descripción** | 0-3 tests para facturación, TPV y autenticación |
| **Prioridad** | P1 |

## MODULE-001: Acoplamiento captura ↔ self_checkout

| Campo | Valor |
|-------|-------|
| **Severidad** | HIGH |
| **Componente** | factura_compra_captura, self_checkout |
| **Descripción** | 10 imports cruzados entre dominios sin contrato formal |
| **Evidencia** | 04-MODULE-DEPENDENCY-GRAPH.md DEP-007 |
| **Prioridad** | P2 |

## PRODUCT-001: No es SaaS-ready

| Campo | Valor |
|-------|-------|
| **Severidad** | HIGH |
| **Componente** | Plataforma |
| **Descripción** | Sin provisioning, billing, tenant isolation, auth independiente |
| **Prioridad** | P2 (estratégico) |

---

*Generado por auditoría READ ONLY.*
