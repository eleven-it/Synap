# 33 — Matriz de Riesgo de Refactor

**Estado:** COMPLETE (Fase 33)  
**Fecha:** 25/08/2026

---

| Component | Business Criticality | Tech Complexity | Data Risk | Regression Risk | Legacy Coupling | Sequence |
|-----------|:-------------------:|:---------------:|:---------:|:---------------:|:---------------:|:--------:|
| core/mysql_pool | 5 | 2 | 3 | 4 | 5 | **1** (stabilize) |
| login/auth | 5 | 4 | 4 | 5 | 5 | **5** (after ACL) |
| core/permisos | 5 | 3 | 4 | 4 | 5 | **3** (synap cutover) |
| reports/query_runner | 4 | 5 | 3 | 5 | 4 | **6** |
| reports/models | 3 | 2 | 1 | 2 | 1 | **2** (extract) |
| ecom/ | 5 | 5 | 5 | 5 | 5 | **8** |
| mpr/ | 5 | 5 | 5 | 5 | 4 | **8** |
| self_checkout/ | 5 | 4 | 5 | 5 | 4 | **7** |
| fe_afip/ | 5 | 3 | 2 | 4 | 2 | **4** (isolate) |
| legacy_db/ | 4 | 4 | 5 | 5 | 5 | **3** (expand ACL) |
| factura_compra_captura | 3 | 3 | 2 | 3 | 2 | **4** |
| tiendanube/ | 3 | 3 | 3 | 3 | 2 | **6** |
| ia/ | 2 | 3 | 2 | 2 | 1 | **9** |
| theme/ | 2 | 1 | 0 | 1 | 0 | **1** |
| PostgreSQL tenant | 5 | 4 | 5 | 5 | 0 | **2** |

Escala: 1 (bajo) — 5 (crítico)

---

## Secuencia recomendada

1. **Observabilidad + tests** en paths críticos (TPV, login, FE)
2. **Formalizar Synap Core** — separar infra de negocio en core/
3. **Tenant middleware** PostgreSQL
4. **ACL read-only** — repositories para maestros MySQL
5. **Permisos synap cutover** — eliminar dual mode
6. **ACL write** — transacciones detrás de adapter
7. **Refactor query_runner** — sandbox SQL
8. **Desacoplar dominios** — ecom, mpr, self_checkout
9. **Identity service** — reemplazar auth AdministraNET
10. **Productización** — provisioning, billing, onboarding

---

*Generado por auditoría READ ONLY.*
