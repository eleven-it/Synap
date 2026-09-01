# 01 — Version and Release Topology

**Estado:** COMPLETE | Evidencia: git remotes, `docs/general/FLUJO_RAMAS_Y_PLAN.md`, commits

---

## Hallazgo principal

**NO existen tres repositorios separados.** Existe **un único repositorio Git**:

```text
origin → git@github.com:eleven-it/Synap.git
```

Las líneas históricas "Development / Staging / Production" son **ramas**, no repos.

---

## Inventario por rama

| Repository (rama) | Default branch remoto | Purpose documentado | Uso real inferido |
|-------------------|----------------------|---------------------|-------------------|
| **Desarrollo** | No (activa localmente) | Desarrollo diario, features, docs | **Source of truth de desarrollo** |
| **Staging** | No | Preproducción, pruebas integradas | **Customer Production Runtime** (clientes actuales) |
| **Produccion** | **Sí** (`origin/HEAD`) | Producción aprobada | **Release archive / legacy prod** — rezagada vs Staging |

### Detalle por rama

| Campo | Desarrollo | Staging | Produccion |
|-------|------------|---------|------------|
| **Active development?** | ✅ Sí | Merge target | ❌ Solo hotfixes raros |
| **Contains docs/openspec?** | ✅ Sí | ❌ Removidos en merge | ❌ Removidos |
| **Deployment target** | DEV local / Docker | Servidores clientes actuales | Servidor prod histórico |
| **Customer traffic** | No | **Sí (CLIENT-A, CLIENT-B)** | Incierto / legacy |
| **Hotfix process** | Fix en Desarrollo → merge Staging | Deploy directo posible | Merge desde Staging (teórico) |
| **Rollback** | git revert en rama | Deploy imagen/commit anterior | Idem |

**Evidence:** `FLUJO_RAMAS_Y_PLAN.md`; `origin/HEAD → origin/Produccion`; divergencia git abajo.

---

## Divergencia entre ramas (remoto, 26/08/2026)

| Comparación | Solo en A | Solo en B | Interpretación |
|-------------|----------:|----------:|----------------|
| Desarrollo ↔ Staging | 19 | 325 | Staging tiene **325 commits** no presentes en Desarrollo (merges, fixes exclusivos, histórico divergente) |
| Staging ↔ Produccion | 678 | 8 | Staging **678 commits adelante** de Produccion; Produccion casi congelada |

**Conclusión:** El flujo documentado Desarrollo → Staging → Produccion **no se ejecuta de forma regular**. Staging acumula funcionalidad operativa que Produccion no tiene.

---

## Commits exclusivos (patrones)

| Tipo | Evidencia |
|------|-----------|
| Features solo en Desarrollo | 19 commits recientes (ecom masivo, docs) no mergeados a Staging |
| Features solo en Staging | 325 commits — MPR fixes, reportes, integraciones en runtime cliente |
| Hotfixes no backporteados | Produccion tiene 8 commits exclusivos (TPV, reportes migrations) |
| Config versionada | `.env` **no** en repo; `docker-compose.yml` compartido |
| Docs exclusivos Desarrollo | Política explícita: `git rm -r docs openspec` al merge a Staging |

---

## Clasificación de entornos reales

| Current Name | Actual Function | Customer Traffic | Business Critical | Future Name (v2) |
|--------------|-----------------|-----------------:|------------------:|------------------|
| **Desarrollo** (rama) | Development | 0 | Media (código) | — (v1 maintenance branch) |
| **Staging** (rama) | **Customer Production Runtime** | **Alto** | **Crítico** | v1 `maintenance` o congelar |
| **Produccion** (rama) | Legacy production / release archive | Bajo/desconocido | Baja hoy | Deprecar o alinear |
| **Docker local** | Developer Integration | 0 | Baja | DEV v2 local |
| **ENVIRONMENT=production** (config) | Runtime hardened (cookies, secrets) | En Staging servers | Crítico | Preprod + Prod v2 |

---

## Proceso de release actual (documentado vs real)

### Documentado (`FLUJO_RAMAS_Y_PLAN.md`)

```text
Desarrollo → merge → Staging → deploy → validar → merge → Produccion → deploy prod
```

### Real (inferido)

```text
Desarrollo ──(merge irregular)──► Staging ──► deploy clientes
                                      │
                                      ╳ (gap 678 commits)
                                      ▼
                                 Produccion (stale)
```

---

## Implicaciones para v2

1. **No replicar** el modelo de 3 ramas como 3 repos.
2. Tratar **Staging actual** como baseline funcional de clientes para parity v2.
3. **Produccion** rama no representa el estado operativo real de clientes.
4. v1 post-v2-launch: rama de mantenimiento desde snapshot Staging, no desde Produccion.

---

*Evidence: `git remote -v`, `git branch -a`, `git rev-list --left-right --count`, `docs/general/FLUJO_RAMAS_Y_PLAN.md`*
