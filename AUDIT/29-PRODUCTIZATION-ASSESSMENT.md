# 29 — Productization Assessment

**Estado:** COMPLETE (Fase 29)  
**Fecha:** 25/08/2026

---

## ¿Qué es productizable hoy?

| Componente | Productizable | Notas |
|------------|:------------:|-------|
| Motor reportes (metadatos) | **Sí** | ReportDefinition/Widget/Dashboard genéricos |
| Sistema módulos | **Sí** | ModuleConfig + url_registry |
| Theme/UI Tailwind | **Sí** | Design system reutilizable |
| Backup DR | **Sí** | Con abstracción de fuentes |
| IA agents framework | **Parcial** | LlmGateway + AgentDefinition |
| Hook/Plugin system | **Parcial** | Infra presente, bajo uso |
| Support RAG | **Sí** | Proyecto separado ya aislado |

## ¿Qué requiere refactor?

| Componente | Bloqueador |
|------------|-----------|
| Todo el monolito | Acoplamiento MySQL AdministraNET |
| ecom, mpr, self_checkout | SQL crudo + core hub |
| Auth/login | Identidad AdministraNET |
| Permisos | Dual legacy/synap |
| PostgreSQL data | Sin tenant isolation |

## ¿Qué debería eliminarse?

- `mtrix/` (huérfano)
- `dashboard/` stub Firebase
- Apps comentadas en settings (sales, inventory, etc.)
- Archivos `* 2.py` duplicados
- Celery config muerto (o activar)
- Firebase legacy code

## ¿Qué debería reescribirse?

- Capa acceso datos MySQL → Anti-Corruption Layer
- Auth → Identity provider independiente
- query_runner → Motor SQL sandboxed
- Tenant resolution → Middleware PG+MySQL unificado

## ¿Qué dependencias AdministraNET encapsular?

1. **Auth** — login/administranet_auth.py
2. **Permisos** — administranet_permisos_usuario.py
3. **Maestros** — articulo, cliente, proveedor
4. **Transacciones** — ventas, compras, stock
5. **Contabilidad** — cont_asiento, legacy_db
6. **Configuración** — configuracion, talonarios, empresas

## ¿Qué debería formar Synap Core?

Identity, Tenant, Permissions, Configuration, Data Access Framework, Events, Audit, Integration Framework (ver `09-SYNAP-CORE.md`).

## ¿Qué módulos podrían instalarse independientemente?

| Módulo | Independencia | Requisito |
|--------|:------------:|-----------|
| theme | Alta | Ninguno |
| ia | Media | Core auth + PG |
| reports (metadatos) | Media | PG + data source adapter |
| support | Alta | Ya separado |
| fe_afip | Media | Certs + pyafipws |
| ecom | Muy baja | Core + MySQL + PHP + FE |
| mpr | Muy baja | Core + MySQL intenso |

## ¿Puede Synap ser SaaS?

**No hoy.** Requiere: tenant isolation PG, provisioning automático, auth independiente, ACL AdministraNET, billing, onboarding.

## ¿Puede funcionar sin AdministraNET?

**No.** Auth, permisos, maestros y transacciones dependen de MySQL legacy.

## ¿Puede conectarse a otro ERP?

**Sí, con ACL.** El patrón adapter es viable; el esfuerzo es proporcional al acoplamiento actual (nivel 4).

---

*Generado por auditoría READ ONLY.*
