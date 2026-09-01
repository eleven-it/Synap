# 08 — Reports Semantic Architecture

**Estado:** COMPLETE | **Fecha:** 25/08/2026

## Preserve declarative-v1

`config.version == "declarative-v1"` MUST remain supported as compatibility layer (`query_runner.py:265-276`, `execution_engine.py`).

## Target direction (not implemented)

```text
ReportDefinition (PG)
        │
        ▼
Semantic Query Model (semantic-v2)  ← future
  Entity, Field, Metric, Dimension, Filter,
  Relationship, Aggregation, Sort, TimeDimension
        │
        ▼
ReportDataSourcePort
        │
   ┌────┼────────┐
   │    │        │
 MySQL  PG    Odoo/API
```

## declarative-v1 today = thin semantic layer

- `datasource` = Entity (but stored as table name string)
- `metrics` / `dimensions` = Field expressions (SQL fragments)
- `joins` = Relationships (table names)
- `filters` = Filter specs

**Gap:** SQL leaks into config; semantic-v2 should use entity IDs resolved by DataSource.

## Migration path

1. Introduce `ReportDataSourcePort` — AN adapter wraps current SqlQueryBuilder.
2. Add optional `semantic_version: "v2"` with entity references.
3. declarative-v1 configs auto-map via DataSource entity registry.
4. Deprecate new slug runners — only DataSource + semantic config.

## AI integration

`ia/services/report_intent_refinement_service.py` should target semantic model, not raw SQL generation.
