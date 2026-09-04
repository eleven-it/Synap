# 20 — V1 Change Ledger (sincronización continua v1 → v2)

**Estado:** ACTIVE PROCESS (activar en kickoff Fase 0)  
**Relacionado:** `19-SYNAP-V2-SOLUTION-ARCHITECTURE-PLAN.md` §2.5 · `17-V1-V2-BACKPORT-POLICY.md`

---

## Propósito

Mientras se construye Synap v2, **v1 seguirá recibiendo actualizaciones pequeñas**. Este ledger garantiza que **ningún cambio v1 post-kickoff se pierda** al diseñar, implementar o migrar capabilities en v2.

```text
v1 PR merge
    → fila en ledger
        → decisión APPLY NOW | APPLY WHEN PORT READY | DEFER | N/A
            → ticket v2 (si aplica)
                → cierre cuando está en develop/staging v2
```

---

## Kickoff

| Campo | Valor |
|-------|-------|
| **Kickoff date** | _(completar al crear repo v2)_ |
| **Tag v1 baseline** | `v1-kickoff-v2` |
| **Commit Staging** | _(sha)_ |
| **Ledger canónico** | Repo `Synap-v2` → `docs/migration/V1_CHANGE_LEDGER.md` |
| **Espejo v1 (opcional)** | Link en `docs/general/` apuntando al ledger v2 |

**Alcance del ledger:** todos los merges a `Desarrollo` / `Staging` (y hotfixes a runtime cliente) **después** del tag `v1-kickoff-v2`.

---

## Regla absoluta

> Un PR de v1 **no se aprueba** sin checklist de impacto v2.  
> Un merge a Staging v1 **no se considera cerrado** sin fila en el ledger.

---

## Checklist obligatorio en PR v1

Pegar en la descripción del PR:

```markdown
### Impacto Synap v2
- [ ] Clasificación: SECURITY | DATA | BUSINESS_RULE | FUNCTIONAL | UX_ONLY | SCHEMA | CONFIG | DOCS | OTHER
- [ ] Capabilities afectadas: (ej. sales.order, inventory.movement, reports.execute, …)
- [ ] Módulos/archivos tocados:
- [ ] ¿Cambia escritura MySQL / contrato API / artefacto (PDF,XLSX)? Sí/No — detalle:
- [ ] Decisión propuesta v2: APPLY NOW | APPLY WHEN PORT READY | DEFER | N/A
- [ ] Justificación (1–3 líneas):
- [ ] Issue v2 creado / link: (si APPLY*)
```

**Reviewer:** rechazar merge si el bloque falta o está incompleto.

---

## Plantilla de fila del ledger

| ID | Fecha | PR/Commit v1 | Tipo | Capability | Resumen | Decisión v2 | Ticket v2 | Estado | Owner |
|----|-------|--------------|------|------------|---------|-------------|-----------|--------|-------|
| V1C-001 | dd/MM/yyyy | #123 / abcdef | FUNCTIONAL | sales.order | Fix import Excel col C | APPLY WHEN PORT READY | Synap-v2#45 | OPEN | … |

### Estados

| Estado | Significado |
|--------|-------------|
| **OPEN** | Decisión tomada; trabajo v2 pendiente |
| **IN_PROGRESS** | Ticket v2 en curso |
| **CLOSED** | Cambiado reflejado en v2 (`develop` o superior) o N/A confirmado |
| **WAIVED** | Producto acepta no portar (excepción firmada) |

### SLA sugerido

| Decisión | SLA cierre |
|----------|------------|
| APPLY NOW | ≤ 5 días hábiles (security/data: ≤ 48 h) |
| APPLY WHEN PORT READY | Antes de marcar capability como migrada; grooming semanal |
| DEFER | Revisión mensual; máximo 90 días sin re-evaluación |
| N/A | Cerrar en el mismo día del merge |

---

## Matriz de decisión rápida

| Cambio en v1 | Decisión v2 |
|--------------|-------------|
| Security / corrupción de datos | **APPLY NOW** |
| Regla de negocio / validación / cálculo | **APPLY WHEN PORT READY** (o NOW si Port ya existe) |
| Fix en capability del R1 MUST/SHOULD | **APPLY WHEN PORT READY** |
| Solo template/Alpine/CSS v1 | **N/A** (UI v2 = shadcn) |
| Schema MySQL / `legacy_mysql_schema` | **APPLY NOW** (adapter + ownership doc) |
| Feature flag / config ecom/MPR | **APPLY WHEN PORT READY** → Installation/Policy |
| Docs / comentarios | **N/A** |
| Nueva feature grande | Evitar en v1; si no: **DEFER** + review producto |

---

## Cadencia operativa

| Ritual | Frecuencia | Quién |
|--------|------------|-------|
| Completar ledger al merge | Continuo | Autor PR + reviewer |
| Grooming “v1→v2 pending” | **Semanal** (15–30 min) | Tech lead + 1 backend v2 |
| Revisión DEFER | Mensual | Producto + arquitecto |
| Audit pre-pilot cliente | Antes de Gate D | QA + arquitecto |

---

## Gate: capability migrada

No declarar una capability lista para pilot/producción v2 si el ledger tiene filas **OPEN/IN_PROGRESS** con:

- esa capability, y  
- decisión `APPLY NOW` o `APPLY WHEN PORT READY`.

---

## Automatización recomendada (Fase 0–1)

1. **PR template** en repo Synap (v1) con checklist impacto v2.  
2. Label GitHub `needs-v2-ledger`.  
3. En repo Synap-v2: label `from-v1` + issue template `[v1→v2]`.  
4. (Opcional) Script CI que falle si el cuerpo del PR no contiene `### Impacto Synap v2`.  
5. (Opcional) Bot/lista: commits Staging desde `v1-kickoff-v2` sin ID `V1C-*` → alerta semanal.

---

## Ejemplo de entradas

| ID | Tipo | Resumen | Decisión | Nota |
|----|------|---------|----------|------|
| V1C-001 | FUNCTIONAL | Pedido masivo: priorizar nombre sobre IDArt col C | APPLY WHEN PORT READY | Cubrir en SalesOrderPort import |
| V1C-002 | SECURITY | IDOR captura factura list/detail | APPLY NOW | PolicyGate + object scope en purchasing |
| V1C-003 | UX_ONLY | Contraste matriz pedido masivo modo claro | N/A | shadcn tendrá tokens propios |
| V1C-004 | SCHEMA | Índice nuevo en tabla stock | APPLY NOW | Documentar en adapter + catalog |

---

## Ledger vacío (arranque)

_Copiar a `Synap-v2/docs/migration/V1_CHANGE_LEDGER.md` en kickoff:_

```markdown
# V1 Change Ledger

Baseline: tag `v1-kickoff-v2` — DATE — SHA

| ID | Fecha | PR/Commit v1 | Tipo | Capability | Resumen | Decisión v2 | Ticket v2 | Estado | Owner |
|----|-------|--------------|------|------------|---------|-------------|-----------|--------|-------|
| | | | | | | | | | |
```

---

## Relación con otras políticas

| Tema | Documento |
|------|-----------|
| Qué tipos de cambio van a v1 vs v2 | `17-V1-V2-BACKPORT-POLICY.md` |
| Coexistencia | `02-V1-V2-COEXISTENCE-MODEL.md` |
| Plan solución | `19-…` §2.5 |
| Acceptance capability | `13-MIGRATION-ACCEPTANCE-CRITERIA.md` |

---

*Sin ledger, v2 deja de ser producto y vuelve a ser una foto desactualizada de dos clientes.*
