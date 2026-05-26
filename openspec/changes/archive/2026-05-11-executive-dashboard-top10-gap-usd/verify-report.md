# Verificación — executive-dashboard-top10-gap-usd

**Fecha:** 11/05/2026

## Contrato y tests

- Comando: `docker exec Synap_app python manage.py test reports.tests.test_executive_summary_contract`
- Resultado (11/05/2026): **OK** (1 test). Valida `top_productos`, `gap_vs_ayer_monto` y `meta.top_productos_criterio`.

## Criterios manuales (smoke)

1. Abrir `/reports/dashboard/resumen-ejecutivo-ventas/` con usuario con permiso gerencial de reportes.
2. KPI «Vs ayer»: ver **porcentaje** y línea con **monto** (positivo verde / negativo rojo).
3. Bloque «Top 10 productos»: con datos, tabla en escritorio y tarjetas en móvil; sin datos, mensaje vacío.
4. «Actualizar» tras cambiar fecha sigue trayendo `top_productos` y gap coherentes.

## Riesgos residuales

- Rendimiento del `GROUP BY` en bases muy grandes: monitorear y considerar índice compuesto si hiciera falta.
