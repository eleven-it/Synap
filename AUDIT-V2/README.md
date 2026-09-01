# Auditoría V2 — Validación Arquitectónica y Fronteras de Producto

**Inicio:** 25/08/2026  
**Modo:** READ ONLY — validación contra código como fuente de verdad  
**Relación con V1:** `AUDIT/` es hipótesis; `AUDIT-V2/` la verifica y define fronteras de producto.

---

## Objetivo

1. **Validar** hallazgos de `AUDIT/` contra el repositorio real.
2. **Inventariar** todas las escrituras sobre AdministraNET MySQL.
3. **Descubrir** Systems of Record, Ports, extraction seams y contrato arquitectónico.

**No implica** convertir Synap en SaaS multi-tenant. Las opciones de deployment (dedicado, managed, on-premise, SaaS) se analizan sin imponer una.

---

## Estado de documentos

| Documento | Estado | Descripción |
|-----------|--------|-------------|
| [01-AUDIT-VALIDATION.md](./01-AUDIT-VALIDATION.md) | **COMPLETE** | Matriz validación AUDIT vs código |
| [02-MYSQL-WRITE-INVENTORY.md](./02-MYSQL-WRITE-INVENTORY.md) | **COMPLETE** | Inventario escrituras AdministraNET |
| [03-DATA-OWNERSHIP-BOUNDARIES.md](./03-DATA-OWNERSHIP-BOUNDARIES.md) | **COMPLETE** | Systems of Record por entidad |
| [04-ERP-CAPABILITY-MAP.md](./04-ERP-CAPABILITY-MAP.md) | **COMPLETE** | Capacidades ERP consumidas por Synap |
| [05-PORTS-CATALOG.md](./05-PORTS-CATALOG.md) | **COMPLETE** | Ports candidatos orientados a capacidades |
| [06-REPORTING-DATASOURCE-CONTRACT.md](./06-REPORTING-DATASOURCE-CONTRACT.md) | **COMPLETE** | Contrato DataSource para Reports |
| [07-IDENTITY-BOUNDARY.md](./07-IDENTITY-BOUNDARY.md) | **COMPLETE** | Auth / Identity / Authorization / Context |
| [08-TENANCY-OPTIONS.md](./08-TENANCY-OPTIONS.md) | **COMPLETE** | Opciones sin decisión prematura |
| [09-SECURITY-VALIDATION.md](./09-SECURITY-VALIDATION.md) | **COMPLETE** | Revalidación seguridad con trust paths |
| [10-STRONGLY-CONNECTED-COMPONENTS.md](./10-STRONGLY-CONNECTED-COMPONENTS.md) | **COMPLETE** | SCC conceptual (imports + datos) |
| [11-CHANGE-IMPACT-MATRIX.md](./11-CHANGE-IMPACT-MATRIX.md) | **COMPLETE** | Blast radius por componente |
| [12-SYNAP-PRODUCT-BOUNDARY.md](./12-SYNAP-PRODUCT-BOUNDARY.md) | **COMPLETE** | Qué es Synap como producto |
| [13-LEGACY-EXTRACTION-SEAMS.md](./13-LEGACY-EXTRACTION-SEAMS.md) | **COMPLETE** | Puntos de corte incremental |
| [14-TRANSITION-ARCHITECTURE.md](./14-TRANSITION-ARCHITECTURE.md) | **COMPLETE** | Arquitectura transitoria coexistencia |
| [15-ARCHITECTURAL-INVARIANTS.md](./15-ARCHITECTURAL-INVARIANTS.md) | **COMPLETE** | Reglas inviolables candidatas |
| [SYNAP-ARCHITECTURE-CONTRACT.md](./SYNAP-ARCHITECTURE-CONTRACT.md) | **COMPLETE** | Contrato normativo para código futuro |

---

## Hallazgos V2 más relevantes (preview)

| # | Hallazgo | Veredicto |
|---|----------|-----------|
| 1 | **587 escrituras** SQL a tablas AdministraNET/SHARED (excl. synap_*, mpr_*, sc_*, inv_fisico_*, ecom_* DDL) | CONFIRMADO |
| 2 | `mpr/services.py` concentra ~38% de escrituras legacy | CONFIRMADO |
| 3 | `compventa` **no se escribe** desde Synap; TPV usa `resumen_venta_cv` + `stock` + `cuentacliente` | REFUTA parcial AUDIT/06 |
| 4 | IDOR factura compra API | CONFIRMADO |
| 5 | Reports **no puede** ejecutar sin nombres de tabla en config | CONFIRMADO |
| 6 | IdP real = AdministraNET MySQL `usuarios` | CONFIRMADO |
| 7 | AdministraNETAdapter limpio es **viable incrementalmente** pero requiere ~15 Ports | INFERIDO ALTA CONFIANZA |
| 8 | No hay ciclos de import Python profundos; sí SCC por datos compartidos | CONFIRMADO |

---

## Punto de entrada recomendado

1. [01-AUDIT-VALIDATION.md](./01-AUDIT-VALIDATION.md) — qué de V1 sobrevive verificación  
2. [12-SYNAP-PRODUCT-BOUNDARY.md](./12-SYNAP-PRODUCT-BOUNDARY.md) — qué es Synap  
3. [SYNAP-ARCHITECTURE-CONTRACT.md](./SYNAP-ARCHITECTURE-CONTRACT.md) — reglas para código futuro

---

## Clasificación de conclusiones V2

| Etiqueta | Significado |
|----------|-------------|
| **CONFIRMADA** | Evidencia directa en código verificada |
| **PARCIALMENTE CONFIRMADA** | Dirección correcta, matices o conteos difieren |
| **REFUTADA** | Contradicha por código |
| **INCOMPLETA** | Afirmación V1 insuficiente; V2 amplía |
| **NO VERIFICABLE** | Requiere runtime/operaciones no disponibles |
| **REQUIERE DECISIÓN HUMANA** | Técnica + estrategia de producto |

---

## Stop condition

**NO iniciar refactor** hasta aprobación humana de `SYNAP-ARCHITECTURE-CONTRACT.md`.

---

*Auditoría V2 — READ ONLY — Completada 25/08/2026*
