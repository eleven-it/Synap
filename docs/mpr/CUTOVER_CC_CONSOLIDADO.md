# Cutover — Control de calidad consolidado por artículo

**Fecha:** 20/08/2026  
**Plan:** [PLAN_CC_CONSOLIDADO_POR_ARTICULO.md](PLAN_CC_CONSOLIDADO_POR_ARTICULO.md) §13

## Checklist cutover (no aplicar DDL a producción desde este doc)

- [x] **DDL:** `apply_mpr_core_tables` / catálogo en `administranet1` @ Server2 `181.174.198.194:30804` (20/08/2026). Tablas 007 + `idx_mpr_tl_fecha_art_dest`. No producción.
- [ ] **Deploy conjunto:** publicar grilla + POST + templates + `services_cc_consolidado.py` **en el mismo release** (no UI nueva con POST viejo). Humo local: código copiado al contenedor `Synap_app`.
- [x] **Baseline SELECT pre-confirm:** `docs/mpr/AUDITORIA_CC_CONSOLIDADO_RESULTADOS.md` §2 (Semi 3669 con operario / 0 NULL).
- [ ] **Borradores:** avisar que borradores del modelo anterior (por turno) **no precargan**; el usuario debe recargar cantidades.
- [ ] **Sin job de datos:** no hay migración/backfill de `mpr_transicion_lote` ni prorrateo de Semi.
- [ ] **Staging:** validar checklist §14 del plan y batería S1–S9 antes de producción.

## Rollback

| Acción | Efecto |
|--------|--------|
| Revertir **código** antes del primer confirm nuevo | Limpio |
| Revertir **código** después de confirm Semi con `id_operario NULL` | Ledger nuevo permanece; grilla vieja no muestra ese Semi → hueco visual |
| Revertir **DDL** 007 | Tablas nuevas pueden convivir; app vieja las ignora. No dropear en caliente |
| **Prohibido** | Prorratear Semi a operarios; ajustar `stock_deposito` a mano para cuadrar |

## Verificación local (20/08/2026)

Tests ejecutados vía `docker cp` desde worktree `Synap-cc-consolidado` → contenedor `Synap_app` (bind-mount apunta al repo principal). Resultados registrados en apply-progress PR5.
