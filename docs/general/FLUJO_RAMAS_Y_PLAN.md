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

### Carpeta `docs/` y archivos `.md` solo en Desarrollo

La documentación en **`docs/`** y los archivos **`.md`** (raíz del repo) se versionan y suben **solo en la rama Desarrollo**. **No subir a Staging** la carpeta `docs/` ni archivos `.md`. Tras hacer **merge Desarrollo → Staging**, en la rama Staging ejecutar:

```bash
git rm -r docs
# Si hubiera .md en la raíz que no deban estar en Staging: git rm *.md
git commit -m "Release: quitar docs y .md (solo en Desarrollo)"
git push origin Staging
```

Luego continuar con el despliegue. Así Staging y Produccion no contendrán documentación.

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
