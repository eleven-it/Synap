# Flujo de ramas y GitFlow Synap

Plan de trabajo en Git para **dos o más desarrolladores** sobre `eleven-it/Synap`. El objetivo es no perder commits, no pisar trabajo ajeno y promover código de forma predecible: **feature → Desarrollo → Staging → Produccion**.

Este documento es la fuente de verdad de ramas. El plan de producto sigue siendo [PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md](PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md).

---

## 1. Diagnóstico (por qué cambia el flujo)

Hasta ahora el trabajo diario se empujaba **directo a `Desarrollo`**. Eso funciona con una sola persona. Con dos:

| Riesgo | Qué pasa |
|--------|----------|
| Push rechazado / overwrite | Los dos commitean sobre el mismo tip y uno pisa al otro o se ve forzado a un merge sucio. |
| `git push --force` | Borra commits del compañero que ya estaban en remoto. **Prohibido** en ramas compartidas. |
| PR contra `Produccion` | La rama por defecto de GitHub hoy es `Produccion`. Un PR mal apuntado puede mezclar WIP en producción. |
| Fetch incompleto | El clone local puede estar configurado para traer solo `Desarrollo` y no ver `Staging` / ramas del otro. |
| Ramas sin protección | GitHub no tiene branch protection ni rulesets. Cualquiera con write puede pushear a `Produccion`. |

La regla nueva es: **nadie trabaja sobre `Desarrollo`, `Staging` ni `Produccion`**. Solo se integran por pull request (o por el merge controlado de promoción).

---

## 2. Modelo (GitFlow adaptado a Synap)

No usamos las ramas clásicas `master` / `develop` / `release/*`. Mapeo:

```
                    hotfix/* ──► Produccion ──► (back-merge a Staging y Desarrollo)
                                      ▲
                                      │  PR o merge aprobado
                                   Staging
                                      ▲
                                      │  merge sin docs/openspec
                                  Desarrollo  ◄── PRs de feat/* fix/* chore/* docs/*
                                      ▲
                                      │
                     feat/*  fix/*  chore/*  docs/*
```

| Rama GitFlow clásico | Rama Synap | Vida | Quién commitea |
|----------------------|------------|------|----------------|
| `master` | **Produccion** | permanente | nadie (solo merge desde Staging o hotfix) |
| `develop` | **Desarrollo** | permanente | nadie (solo merge de PRs) |
| `release/*` | **Staging** | permanente (preprod) | nadie (solo merge desde Desarrollo, sin docs) |
| `feature/*` | **feat/**, **fix/**, **chore/**, **docs/** | corta | el autor de esa rama |
| `hotfix/*` | **hotfix/** | corta | el autor; nace de Produccion |

Ramas históricas (`Reports`, `Reports-1.0`, `1.0`): solo lectura. No se usa para trabajo nuevo.

---

## 3. Ramas permanentes

| Rama | Rol | Deploy |
|------|-----|--------|
| **Desarrollo** | Integración diaria. Incluye `docs/` y `openspec/`. | entorno de desarrollo |
| **Staging** | Preproducción. **Sin** `docs/`, `openspec/` ni `.md` de raíz. | servidor Staging |
| **Produccion** | Código en producción. Mismo criterio de docs que Staging. | producción |

Promoción:

1. Features mergeadas y estables en **Desarrollo**.
2. Merge **Desarrollo → Staging** (quitando docs; ver §8) y deploy de pruebas.
3. Staging validado → merge **Staging → Produccion** y deploy.

---

## 4. Ramas de trabajo (obligatorias)

Nombrar en minúsculas, ASCII, con módulo adelante para que el otro vea de un vistazo **quién toca qué**.

| Prefijo | Uso | Ejemplo |
|---------|-----|---------|
| `feat/<modulo>-<slug>` | Feature o migración | `feat/ecom-masivo-precio-linea` |
| `fix/<modulo>-<slug>` | Bug en Desarrollo | `fix/reports-vmm-filtro-articulo` |
| `hotfix/<slug>` | Incidente en Produccion | `hotfix/login-sesion-expirada` |
| `chore/<slug>` | Tooling, deps, CI | `chore/gitignore-tmp-exports` |
| `docs/<slug>` | Solo documentación | `docs/gitflow-colaboracion` |

Módulos habituales: `ecom`, `mpr`, `reports`, `mtrix`, `login`, `stock`, `compras`, `contabilidad`, `self-checkout`, `core`.

Reglas de la rama de trabajo:

- Nace **siempre** de `origin/Desarrollo` (salvo hotfix, que nace de `origin/Produccion`).
- Un tema = una rama = un PR. No mezclar ecom + mpr en la misma rama.
- La rama es **personal**. El otro no commitea ahí salvo pair-programming acordado.
- Se sube al remoto el mismo día que se empieza (`git push -u origin HEAD`) para backup.
- Se borra después de mergear el PR.

---

## 5. Reglas de oro (para no perder ni pisar trabajo)

1. **Nunca** `commit` ni `push` directo a `Desarrollo`, `Staging` o `Produccion`.
2. **Nunca** `git push --force` (ni `--force-with-lease`) sobre esas tres ramas.
3. En tu rama de feature, si hace falta reescribir historia: solo `--force-with-lease`, y solo si **nadie más** está usando esa rama.
4. **Nunca** `git reset --hard` de un commit que ya está en remoto compartido. Si te equivocaste, revertí con `git revert`.
5. Antes de empezar el día y antes de abrir el PR: incorporar `Desarrollo` a tu rama (§6).
6. No trabajar los dos el mismo archivo el mismo día. Si el módulo se pisa, avisar y serializar (uno termina y mergea; el otro rebasea).
7. Abrir el PR en **draft** apenas hay el primer commit útil. Así el otro ve la rama en vuelo.
8. No commitear `tmp_exports/`, `__pycache__/`, Excel de análisis ni secretos (`.env`).
9. Tests y `manage.py` siempre en contenedor: `docker exec Synap_app ...`.
10. Cada cambio de comportamiento actualiza `docs/` en el mismo PR ([POLITICA_DOCUMENTACION.md](POLITICA_DOCUMENTACION.md)).

---

## 6. Rutina diaria (los dos)

### 6.1 Arranque de jornada

```bash
git fetch origin --prune
git checkout Desarrollo
git pull --ff-only origin Desarrollo
```

`--ff-only` falla si alguien pusheó un merge raro: **no fuerces**. Avisá y resolvé juntos.

### 6.2 Empezar una tarea

```bash
git checkout Desarrollo
git pull --ff-only origin Desarrollo
git checkout -b feat/mpr-mi-tarea
git push -u origin HEAD
# abrir PR draft a Desarrollo en GitHub
```

Worktree (si ya tenés otra tarea a medias, como hoy con Staging / ecom):

```bash
git fetch origin
git worktree add ../Synap-mpr-mi-tarea -b feat/mpr-mi-tarea origin/Desarrollo
```

### 6.3 Durante el día (evitar divergir)

Cada vez que el compañero mergea un PR, o al menos **antes de pushear** y **antes de pedir review**:

```bash
git fetch origin
git merge origin/Desarrollo
# resolver conflictos en tu rama, commitear, pushear
```

Alternativa (rama 100 % tuya, historia más limpia):

```bash
git fetch origin
git rebase origin/Desarrollo
git push --force-with-lease
```

Usar **rebase solo en ramas personales**. En `Desarrollo` / `Staging` / `Produccion`: merge, nunca rebase.

### 6.4 Cerrar la tarea

1. `git merge origin/Desarrollo` (o rebase) hasta que no queden conflictos.
2. Tests del módulo en `docker exec Synap_app`.
3. Marcar el PR como Ready for review.
4. El otro aprueba (o self-review + aviso si está ocupado).
5. Merge a `Desarrollo` con **Create a merge commit** (no squash si hay varios commits con sentido; squash sí si es ruido de WIP).
6. Borrar la rama remota (GitHub) y local:

```bash
git checkout Desarrollo
git pull --ff-only origin Desarrollo
git branch -d feat/mpr-mi-tarea
git push origin --delete feat/mpr-mi-tarea   # si GitHub no la borró
```

---

## 7. Pull requests

- **Base siempre `Desarrollo`**, nunca `Produccion` ni `Staging`.
- Título: mismo estilo que los commits (`feat(mpr): ...`, `fix(reports): ...`).
- Cuerpo: plantilla en `.github/PULL_REQUEST_TEMPLATE.md`.
- Un revisor: el otro desarrollador. No mergear a ciegas cambios del compañero en archivos que él no vio.
- PRs chicos (ideal < 400 líneas netas de producto). Si crece, cortar en dos ramas.
- Hotfix: base `Produccion`, y después back-merge (§9).

Merge recomendado en GitHub:

| Situación | Botón |
|-----------|--------|
| Feature con commits claros | **Create a merge commit** |
| Rama con 12 commits de “wip / typo / fix lint” | **Squash and merge** (un commit limpio en Desarrollo) |
| Nunca | **Rebase and merge** sobre PRs ajenos sin avisar (reescribe SHAs) |

---

## 8. Promoción Desarrollo → Staging (sin docs)

`docs/`, `openspec/` y los `.md` de la **raíz** viven solo en **Desarrollo**. Staging y Produccion no deben tenerlos.

Worktree de Staging (ya existe en esta máquina: `Synap-staging-worktree`):

```bash
cd /ruta/al/worktree-Staging
git fetch origin
git merge --no-commit --no-ff origin/Desarrollo
git rm -rf --ignore-unmatch docs openspec
# .md solo en la raíz del repo (no borrar README de paquetes internos)
git ls-files '*.md' | awk -F/ 'NF==1' | xargs git rm -f --ignore-unmatch
git commit -m "Merge branch 'Desarrollo' into Staging"
git push origin Staging
```

En Linux se puede añadir `-r` a `xargs` (`xargs -r`) para no fallar si no hay `.md` de raíz.

**No usar** la forma legacy (merge completo + segundo commit `git rm`): deja un tip intermedio con documentación.

Los SQL operativos (DDL de runtime) van en la app (`mpr/sql/`, `self_checkout/sql/`, catálogo `core/services/legacy_mysql_schema/`), no en `docs/`.

Staging validado → merge **Staging → Produccion** (fast-forward si Staging es ancestro; si no, merge commit) y deploy. No cherry-pick a mano a Produccion salvo hotfix.

---

## 9. Hotfix en producción

Solo para incidente real en Produccion. No para features.

```bash
git fetch origin
git checkout -b hotfix/sesion-expirada origin/Produccion
# parche mínimo + tests
git push -u origin HEAD
# PR contra Produccion, merge, deploy
```

Después **obligatorio** devolver el parche:

```bash
# 1) Staging
git checkout Staging
git pull --ff-only origin Staging
git merge origin/Produccion
git push origin Staging

# 2) Desarrollo (acá sí viajan docs si el hotfix tocó código documentado)
git checkout Desarrollo
git pull --ff-only origin Desarrollo
git merge origin/Produccion
git push origin Desarrollo
```

Si el merge a Desarrollo choca con features nuevas, resolver en una rama `chore/backmerge-produccion` y PR; no dejar Produccion y Desarrollo divergentes en el mismo bug.

---

## 10. Cómo no pisarse entre dos personas

### 10.1 Contrato informal de módulos

Antes de arrancar: un mensaje (“yo tomo MPR inventario, vos reports VMM”). Si los dos necesitan el mismo archivo:

1. El que está más avanzado termina y mergea a Desarrollo.
2. El otro hace `git merge origin/Desarrollo` y resuelve **una sola vez**.

### 10.2 Señales de “estoy en esto”

- Rama remota con el prefijo de módulo.
- PR draft abierto.
- No reutilizar nombres de rama viejos (`feat/ecom-masivo-precio-linea` ya existió: usar un slug nuevo).

### 10.3 Conflictos

Git no pierde trabajo si ambos pushearon a **ramas distintas**. El conflicto aparece al integrar. Resolver así:

```bash
git fetch origin
git merge origin/Desarrollo
# editar archivos conflictivos, quitar marcadores <<<<<< ====== >>>>>>
git add -A
git commit -m "merge(desarrollo): resolver conflictos con <rama-o-pr>"
git push
```

Si el conflicto es de `docs/` vs código, no borres la doc del compañero: quedate con ambas secciones y unificá.

### 10.4 Recuperar trabajo “perdido”

Nada se borra de inmediato. En la máquina donde estuvo el commit:

```bash
git reflog
git checkout -b rescue/<fecha> <sha>
git push -u origin HEAD
```

Si el compañero hizo force-push (no debe pasar): el SHA viejo sigue en reflog de quien lo tenía, o en GitHub → Activity / `git fetch origin <sha>`.

---

## 11. Configuración local (los dos iguales)

Ejecutar una vez por clone:

```bash
# Traer todas las ramas, no solo Desarrollo
git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
git fetch origin --prune

# Pull de Desarrollo: solo fast-forward (no crea merges basura)
git config branch.Desarrollo.mergeOptions "--ff-only"

# Evitar push a la rama equivocada
git config push.default simple
```

**No** cambiar `git config --global user.*` del compañero. Cada uno usa su nombre y mail.

Default de checkout para trabajo: `Desarrollo`, no `Produccion`.

```bash
git clone git@github.com:eleven-it/Synap.git
cd Synap
git checkout Desarrollo
```

Servidores Staging/Produccion clonan con `-b Staging` o `-b Produccion` (ver [GUIA_IMPLEMENTACION_SERVIDOR_STAGING.md](GUIA_IMPLEMENTACION_SERVIDOR_STAGING.md)).

---

## 12. Checklist GitHub (hacerlo juntos, una vez)

La API actual no muestra protecciones: **ninguna rama está protegida** y no hay rulesets. Hay que configurarlas en
https://github.com/eleven-it/Synap/settings/branches

### 12.1 Rama por defecto

Cambiar **default branch** de `Produccion` a **`Desarrollo`**.

Así los PR nuevos apuntan a integración, no a producción. Los deploys siguen usando `-b Staging` / `-b Produccion`.

### 12.2 Protecciones (Desarrollo, Staging, Produccion)

En cada una:

- Require a pull request before merging.
- Require approvals: **1** (el otro dev). En equipo de dos, permitir que el autor mergee solo si el otro está de acuerdo por chat y se deja constancia en el PR.
- Do not allow bypassing the above settings (salvo admin para hotfix urgente).
- Restrict who can push: nadie, solo vía PR.
- **Allow force pushes: off**.
- **Allow deletions: off**.
- Staging / Produccion: además “Restrict pushes that create files matching `docs/**`, `openspec/**`” no existe nativo; se cubre con el merge `--no-commit` de §8 y revisión humana.

### 12.3 Opciones de merge del repo

- Enable merge commits: on.
- Enable squash merging: on.
- Enable rebase merging: off (o solo admins).
- Automatically delete head branches: on.

### 12.4 Acceso del segundo desarrollador

- Invitarlo como **Write** al repo `eleven-it/Synap` (no Admin al inicio).
- Deploy keys de servidores: siguen en Settings → Deploy keys, solo lectura, una por ambiente.

### 12.5 Ramas remotas huérfanas

Limpiar cuando no se usen (hoy hay restos `cursor/ventas-bom-docenas-*`, `docs/reports-api-ia-openspec-map`, `feat/factura-compra-expediente-fase3`, etc.):

```bash
git push origin --delete <rama>
```

No borrar `Desarrollo`, `Staging`, `Produccion`, ni históricas `Reports` / `Reports-1.0` / `1.0` sin acuerdo.

---

## 13. Onboarding del segundo desarrollador

1. Acceso SSH a GitHub y `git clone` + `git checkout Desarrollo`.
2. Aplicar §11 (fetch de todas las ramas).
3. Docker según docs de instalación; no desarrollar contra Produccion.
4. Leer este documento, [POLITICA_DOCUMENTACION.md](POLITICA_DOCUMENTACION.md) y el plan FODA.
5. Primera tarea: una rama `feat/` o `fix/` chica, PR a Desarrollo, merge con el otro de revisor.
6. No reutilizar worktrees ajenos (`Synap-staging-worktree`, etc.): crear los propios.

---

## 14. Qué no hacer (anti-patrones que ya vimos)

| Anti-patrón | Por qué duele |
|-------------|---------------|
| Commitear en `Desarrollo` local y `git push origin Desarrollo` | El otro no puede empujar; historia entrelazada; fácil force-push. |
| PR con base `Produccion` | El default actual de GitHub induce este error (PR #1 quedó así, cerrado sin merge). |
| Feature branch que no se pushea en días | Si se rompe el disco, el trabajo no está en GitHub. |
| Una sola rama para tres tickets | Imposible revertir uno solo; el review se vuelve impresentable. |
| `git pull` sin fetch consciente en Staging | Puede meter docs en Staging si el merge no sigue §8. |
| Ignorar `git pull --ff-only` que falla | Suele significar que alguien reescribió historia; parar y hablar. |

---

## 15. Plan de referencia de producto (obligatorio)

Todo desarrollo, refactor e implementación se ajusta a:

**[Plan Principal FODA y brechas Synap](PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md)**

Ese documento define brechas de migración Principal.frm → Synap, FODA del shell, TPV/caja, seguridad (`ENVIRONMENT=production`) y prácticas ERP.

Cualquier cambio en shell, login, sesión, TPV, caja o reportes debe ser coherente con ese plan.
