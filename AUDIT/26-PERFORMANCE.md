# 26 — Performance

**Estado:** COMPLETE (Fase 26)  
**Fecha:** 25/08/2026

---

## Cuellos de botella identificados

| ID | Issue | Componente | Impacto |
|----|-------|-----------|---------|
| PERF-001 | Pool MySQL max 5 conexiones | core/mysql_pool.py | Contención bajo carga |
| PERF-002 | query_runner monolítico sin paginación universal | reports/ | Queries pesadas |
| PERF-003 | REPORTS_CACHE_ENABLED=false | settings | Re-ejecución constante |
| PERF-004 | 787 cursor.execute en mpr | mpr/services.py | Loops DB potenciales |
| PERF-005 | runserver en Docker CMD | Dockerfile | No producción-grade |
| PERF-006 | Bind mount .:/app en dev | docker-compose | I/O lento macOS |
| PERF-007 | DATA_UPLOAD_MAX_NUMBER_FIELDS=30000 | settings | Grids MPR grandes |

## N+1 queries

- Detectado en runners de reportes que iteran resultados con queries adicionales
- mpr/services.py: loops con queries por renglón en operaciones batch
- Mitigación parcial: caches in-memory en mpr/views.py (mov_cache)

## Queries pesadas

- Backorder reports: JOINs múltiples en cuentacliente + stockp
- Monthly reporting: importación .xlsb completa
- Inventario físico: scan completo stock_deposito

## Índices

- Synap DDL catalog crea índices en tablas synap_*/mpr_*
- No gestiona índices en tablas AdministraNET legacy
- DEPENDE de índices existentes VB6

## Recomendaciones (no implementar — solo auditoría)

1. Aumentar MYSQL_POOL_MAX_CONNECTIONS en producción
2. Activar REPORTS_CACHE_ENABLED con keys tenant-safe
3. Paginación obligatoria en query_runner
4. Gunicorn con workers = 2*CPU+1
5. Profiling con django-debug-toolbar (dev) o APM (prod)

---

*Generado por auditoría READ ONLY.*
