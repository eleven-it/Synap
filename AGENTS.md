# Reglas de trabajo para Synap

La fuente de verdad del flujo Git es `docs/general/FLUJO_RAMAS_Y_PLAN.md` en
`Desarrollo`. Estas reglas se aplican al trabajo de Codex en `eleven-it/Synap`.

## Ramas y colaboración

- El flujo es `feat|fix|chore|docs` → `Desarrollo` → `Staging` → `Produccion`.
  No usar `master`, `develop` ni rebase-and-merge sobre ramas compartidas.
- `Desarrollo`, `Staging` y `Produccion` son permanentes. Nadie desarrolla ni
  commitea directamente en ellas. Nacer de `origin/Desarrollo`; un `hotfix/*`
  nace de `origin/Produccion`.
- Usar una rama corta por tema: `feat/<modulo>-<slug>`,
  `fix/<modulo>-<slug>`, `chore/<slug>`, `docs/<slug>` o `hotfix/<slug>`.
  Nombres en minúsculas y ASCII. Módulos: `ecom`, `mpr`, `reports`, `mtrix`,
  `login`, `stock`, `compras`, `contabilidad`, `self-checkout`, `core`.
- Antes de integrar: `git fetch origin --prune` y
  `git merge origin/Desarrollo` en la rama de trabajo. Rebase solo en una
  rama personal no compartida; su push reescrito requiere
  `--force-with-lease` exclusivamente en esa rama.
- Subir la rama de trabajo con `git push -u origin HEAD`. El PR de trabajo
  tiene base `Desarrollo` y se integra con **Create a merge commit**;
  squash solo para commits de WIP sin valor propio. Nunca rebase-and-merge.
- Excepción solicitada por el dueño del repositorio para integrar de inmediato
  sin protección de rama: actualizar `Desarrollo` con
  `git pull --ff-only origin Desarrollo` (si falla, parar), hacer
  `git merge --no-ff <rama>` y luego `git push origin Desarrollo`.

## Prohibiciones

- No hacer commit ni push directo de trabajo diario a ramas permanentes; no
  hacer `git push --force` ni `--force-with-lease` en ellas.
- No hacer `git reset --hard` sobre commits publicados en un remoto
  compartido. Corregirlos con `git revert`.
- No abrir PR de trabajo con base `Staging` o `Produccion`.
- No cambiar `git config` (`user.name`, `user.email` ni remotos).
- No commitear `__pycache__/`, `tmp_exports/`, medios de análisis, Excel,
  secretos (`.env`) ni duplicados llamados ` 2.py` o ` 2.html`.
- Ejecutar tests y `manage.py` solo dentro del contenedor:
  `docker exec Synap_app <comando>`.

## Promoción

- Promover `Desarrollo` a `Staging` solo cuando se solicite, en un worktree
  exclusivo de Staging. Actualizar Staging con `git pull --ff-only`, integrar
  Desarrollo con `git merge --no-commit --no-ff origin/Desarrollo`, retirar
  `docs/`, `openspec/` y únicamente los `*.md` de la raíz antes del commit.
  Comprobar el índice. No usar el flujo viejo de merge completo seguido de
  otro commit que borra documentación. Si un worktree bajo Documents se
  bloquea por iCloud o `index.lock`, usar uno en `/tmp`.
- Los SQL de runtime viven en la app: `mpr/sql/`, `self_checkout/sql/` o
  `core/services/legacy_mysql_schema/`, nunca en `docs/`.
- No promover a `Produccion` sin pedido explícito. Una vez validado Staging,
  integrarlo por merge; el cherry-pick a Produccion se reserva para hotfix,
  que después vuelve a Staging y Desarrollo.
- Al terminar una promoción, informar los SHA de `origin/Desarrollo` y
  `origin/Staging` y confirmar que Staging no contiene `docs/`, `openspec/`
  ni `*.md` en la raíz.

## Entorno local

El entorno separado de Codex se describe en
`docs/general/ENTORNO_LOCAL_AISLADO.md`. No modificar el Compose, la base,
los volúmenes ni los puertos de Odoo para instalar Synap.
