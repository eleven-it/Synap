# Flujo de ramas y plan de referencia

## Ramas principales

| Rama | Uso |
|------|-----|
| **Desarrollo** | Rama principal de desarrollo. Todo el trabajo día a día se hace aquí. Es la rama por defecto para nuevas features, refactors y migraciones. |
| **Staging** | Preproducción. Se actualiza desde Desarrollo para pruebas integradas antes de desplegar a producción. |
| **Produccion** | Código desplegado en producción. Solo se actualiza desde Staging cuando el release está aprobado. |

### Flujo recomendado

1. **Desarrollar** siempre en la rama **Desarrollo**.
2. Cuando haya un conjunto estable de cambios: **merge Desarrollo → Staging** y desplegar Staging para pruebas.
3. Cuando Staging esté validado: **merge Staging → Produccion** y desplegar a producción.

Las ramas **Reports** y **Reports-1.0** se mantienen para historial y compatibilidad; el flujo estándar de versionado es Desarrollo → Staging → Produccion.

### Carpetas de documentación solo en Desarrollo

La documentación de desarrollo en **`docs/`**, **`openspec/`** y los archivos **`.md`** (raíz del repo) se versionan y suben **solo en la rama Desarrollo**. **No deben quedar** en el tip de Staging ni Produccion.

#### Forma recomendada (un solo commit de merge, sin tip con docs)

En el worktree de Staging, mergear **sin** crear el commit todavía, sacar docs/openspec del índice y recién ahí cerrar el merge. Así Staging **nunca** apunta a un árbol que tenga esas carpetas:

```bash
# Desde el worktree de Staging (rama Staging limpia)
git fetch origin
git merge --no-commit --no-ff origin/Desarrollo
git rm -rf --ignore-unmatch docs openspec
# .md solo en la raíz del repo (no borrar README de paquetes internos):
git ls-files '*.md' | awk -F/ 'NF==1' | xargs -r git rm -f --ignore-unmatch
git commit -m "Merge branch 'Desarrollo' into Staging"
git push origin Staging
```

En macOS (sin `xargs -r`) se puede omitir la línea de `.md` raíz si no hay ninguno, o usar `xargs git rm -f` con cuidado.

#### Forma legacy (evitar)

Merge completo + segundo commit `git rm -r docs openspec`. Funciona, pero deja un commit intermedio (o un tip momentáneo) con documentación que no debe vivir en Staging.

**Scripts SQL operativos** (DDL ejecutado en runtime por comandos o la herramienta global de esquema) deben vivir **fuera de `docs/`**, en la app correspondiente (ej. `mpr/sql/`, `self_checkout/sql/`), para que Staging y Produccion los incluyan al desplegar.

Luego continuar con el despliegue. Así Staging y Produccion no contendrán documentación de desarrollo.

---

## Plan de referencia (obligatorio)

**Todo el desarrollo, las decisiones de refactor y las implementaciones deben ajustarse al plan:**

**[Plan Principal FODA y brechas Synap](PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md)**

Ese documento define:

- Brechas de migración de Principal.frm a Synap y acciones sugeridas
- FODA del shell actual y oportunidades
- Optimizaciones viables (session store, fecha servidor, logout unificado, TPV/caja)
- Mejoras funcionales (barra de estado, cierre caja, notificaciones, etc.)
- Propuesta técnica ampliada (componentes, APIs, flujos)
- Riesgos de seguridad y mitigaciones (activar cuando `ENVIRONMENT=production`)
- Mejores prácticas ERP no contempladas

**Regla:** Cualquier cambio en el shell, login, sesión, TPV, caja o reportes debe ser coherente con ese plan. Los agentes y asistentes de desarrollo deben usarlo como referencia única para migración Principal → Synap y para seguridad/ERP.
