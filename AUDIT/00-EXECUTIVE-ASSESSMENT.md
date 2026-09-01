# 00 — Executive Technical Assessment

**Estado:** COMPLETE  
**Fecha:** 25/08/2026

---

## Qué es Synap realmente hoy

Synap es un **monolito modular Django 4.2** de ~1.800 archivos Python que funciona como **plataforma web complementaria de AdministraNET** (ERP VB6 + MySQL). No es una interfaz web — es un sistema con 20 módulos activos que incluye reportes, e-commerce B2B, TPV, producción (MPR), facturación electrónica, auditoría contable, integraciones (Tienda Nube, Odoo) y asistentes IA.

Usa **PostgreSQL para metadatos propios** y accede **directamente a MySQL AdministraNET** para datos de negocio via pool de conexiones (`core/mysql_pool.py`), seleccionando la empresa por sesión (`base_empresa`).

---

## Nivel de madurez

| Área | Nivel | Justificación |
|------|:-----:|---------------|
| Funcional | **Alto** | 20 módulos operativos, 380 tests |
| Arquitectónico | **Bajo-Medio** | Monolito acoplado, sin ACL |
| Operacional | **Medio** | Docker, backup DR, sin observabilidad |
| Producto | **Bajo** | No SaaS, no multi-tenant PG |
| Seguridad | **Medio-Bajo** | Controles prod OK, gaps tenant/SQL |

---

## Scoring (0-10)

| Área | Score | Justificación |
|------|------:|---------------|
| Arquitectura | **4** | Monolito hub-and-spoke, sin boundaries formales |
| Modularidad | **5** | Sistema módulos bueno; imports acoplados |
| Calidad de código | **5** | Funcional pero monolitos (query_runner 4K, mpr 8K LOC) |
| Data architecture | **3** | Dual DB sin ACL, PG sin tenant, SQL disperso |
| Multi-tenancy | **3** | Database-per-tenant MySQL; PG global |
| Seguridad | **5** | Prod hardening OK; gaps IDOR, SQL dinámico |
| Testing | **5** | 380 tests pero gaps críticos (FE, TPV, login) |
| Observabilidad | **2** | Solo console logging |
| APIs | **4** | 750+ endpoints sin versionado ni OpenAPI |
| Integraciones | **6** | TN, AFIP, Odoo bien encapsulados |
| Escalabilidad | **4** | Pool MySQL limitado (5 conn), vertical |
| Maintainability | **4** | SQL disperso, god module core |
| Productizabilidad | **3** | Acoplamiento AdministraNET crítico |
| Legacy independence | **2** | Nivel acoplamiento 4/4 |

---

## Dependencia de AdministraNET

**Crítica (4/4).** Auth, permisos, maestros, transacciones, configuración — todo depende de MySQL legacy compartido con VB6. Synap también **escribe y altera** tablas legacy.

---

## Riesgo técnico global: **ALTO**

Factores: acoplamiento ERP, SQL disperso, sin tenant PG, monolitos de código, Celery dormido, observabilidad mínima.

## Riesgo de datos: **ALTO**

Escritura concurrente VB6+Synap, cross-tenant PG, SQL dinámico reportes.

---

## Recomendación

**Transformación incremental hacia Synap Platform** con:

1. **Corto plazo (0-3 meses):** Seguridad (AES key, tests críticos), observabilidad básica
2. **Medio plazo (3-12 meses):** ACL read, tenant PG, formalizar core, permisos synap cutover
3. **Largo plazo (12-24 meses):** ACL write, bounded contexts, identity service, productización

**No recomendar big-bang rewrite.** El sistema funciona y tiene valor — la estrategia es desacoplar progresivamente mientras se mantiene operativo.

---

*Ver informe completo en `SYNAP-AUDIT-FINAL-REPORT.md`.*
