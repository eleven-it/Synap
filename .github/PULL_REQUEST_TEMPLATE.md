## Qué cambia

<!-- 1–3 viñetas. Base del PR: siempre `Desarrollo` (hotfix: `Produccion`). -->

-

## Cómo probarlo

- [ ] Arranqué desde `origin/Desarrollo` actualizado (o desde `origin/Produccion` si es hotfix)
- [ ] Incorporé `Desarrollo` a esta rama antes del review (`merge` o `rebase` personal)
- [ ] Tests del módulo: `docker exec Synap_app python manage.py test <app>`
- [ ] Si toqué UI: verifiqué el flujo en el navegador (no solo el render)
- [ ] Documentación en `docs/` actualizada (o N/A)

## Riesgo de pisar trabajo

- Archivos/módulos tocados:
- ¿El otro dev está en el mismo módulo? Sí / No

## Checklist Synap

- [ ] Tipos AdministraNET (`core.utils.administranet_types`) si hay MySQL legacy
- [ ] Sin `alert` / `confirm` / `prompt` en pantallas nuevas
- [ ] UI alineada a Reportes/MPR si es pantalla nueva o migración
- [ ] No incluí `tmp_exports/`, `__pycache__/`, `.env` ni Excel de análisis

## Impacto Synap v2

> Obligatorio desde kickoff v2 (`AUDIT-V3.5/20-V1-CHANGE-LEDGER.md`).  
> Un PR no se considera cerrado sin fila en el ledger (o N/A justificado).

- [ ] Clasificación: SECURITY | DATA | BUSINESS_RULE | FUNCTIONAL | UX_ONLY | SCHEMA | CONFIG | DOCS | OTHER
- [ ] Capabilities afectadas: (ej. `sales.order`, `inventory.movement`, `reports.execute`, …)
- [ ] Módulos/archivos tocados:
- [ ] ¿Cambia escritura MySQL / contrato API / artefacto (PDF, XLSX, ticket)? Sí / No — detalle:
- [ ] Decisión propuesta v2: `APPLY NOW` | `APPLY WHEN PORT READY` | `DEFER` | `N/A`
- [ ] Justificación (1–3 líneas):
- [ ] Issue v2 / ID ledger `V1C-xxx`: (si APPLY*) / N/A
