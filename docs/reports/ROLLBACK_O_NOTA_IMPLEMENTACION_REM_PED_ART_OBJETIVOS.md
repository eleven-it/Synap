# Registro y rollback — REM / PED en armado por artículo (objetivos vs BO) y KPI ventas consolidado

**Fecha de registro:** 30/04/2026  
**Motivo:** implementación alineada con `ANALISIS_REMITOS_PED_ARMADO_LINEAS_VS_CABECERA_OBJETIVOS.md` y planificación SDD en Engram. Índice de fases y observaciones: `SDD_OBJETIVOS_REM_PED_ART_FASE_PLANIFICACION.md`.

## Alcance previsto (resumen)

1. **Informe objetivos vs BO:** desglose por artículo de remitos y pedidos en armado usando líneas `stockp` (`PrecioNetoxR`), mismos criterios que `sql_rem_cli` / `sql_ped_arm` en `ventas_objetivos_bo_runner.py`, merge en árbol análogo a BO.
2. **Resumen ventas / consolidado:** columna o KPI de **PEDIDOS EN ARMADO** entre remitos y total, misma semántica que `total-consolidado-operativo` (`_get_pedidos_pendientes_total` sin filtrar por fecha en PED armado), manteniendo coherencia de **total consolidado**.

## Validación antes y después

```bash
docker exec Synap_app python manage.py verify_objetivos_remitos_ped_lineas_vs_cabecera \
  --base-empresa <BD> \
  --fecha-inicio YYYY-MM-DD \
  --fecha-fin YYYY-MM-DD
```

Tests orientativos: `reports.tests.test_objetivos_ventas_*`, `test_export_column_order`, `test_bo_report_real_db` (según lo tocado en cada commit).

## Commits atómicos sugeridos (rellenar SHAs tras implementar)

| Fase | Contenido | Commit (rellenar) |
|------|-----------|-------------------|
| A | Runner SQL + merge árbol + tests backend | |
| B | UI / export / plantillas | |
| C | `sales_summary` u otros KPI ventas (semántica PED armado) | |

## Rollback

1. **Revert por fase:** `git revert <sha-C>` luego `<sha-B>` luego `<sha-A>` (orden inverso al merge si hubo conflicto).
2. **Revert único:** si todo quedó en un solo commit, un solo `git revert -m 1 <merge_sha>` si fue merge, o `git revert <sha>` si fue commit lineal.
3. **Post-revert:** ejecutar de nuevo el comando `verify_*` y la batería de tests de la tabla anterior; comprobar pantalla informe objetivos y resumen ventas en staging.

## Notas

- Si solo falla el desglose por artículo pero los totales por cliente siguen correctos, se puede revertir solo la fase A/B dejando intacto el KPI de ventas (o al revés), según el aislamiento real del diff.
- Documentar en este archivo cualquier desviación de la propuesta (p. ej. doble métrica «PED período» vs «PED armado operativo») para no perder contexto en rollback parcial.
