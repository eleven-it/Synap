# 06 — Reporting DataSource Contract

**Estado:** COMPLETE  
**Fecha:** 25/08/2026

---

## Estado actual del motor

### Execution path

```text
ReportQueryAPIView.post (api_views.py:87-124)
  → inyecta filters.base_empresa desde session (109-115)
  → QueryRunnerService.run (query_runner.py:261)
    → IF config.version == "declarative-v1":
        ReportExecutionEngine.run (execution_engine.py:1414)
          → SqlQueryBuilder.build → MySQL execute
    → ELSE: slug-dispatch legacy (query_runner.py:311+)
```

**Evidencia:** `reports/services/execution_engine.py:62-74` — `datasource: str` es **nombre de tabla MySQL literal**.

---

## ¿Puede Reports desacoplarse del ERP?

| Pregunta | Respuesta | Evidencia |
|----------|-----------|-----------|
| ¿Motor metadata independiente? | **SÍ** | PG: ReportDefinition, Widget, Dashboard |
| ¿Ejecución sin tablas legacy? | **NO hoy** | `datasource` required (`config_serializer.py:95-98`) |
| ¿Puede funcionar contra Odoo? | **PARCIAL** con nuevo adapter | Requiere ReportDataSourcePort |
| ¿Puede funcionar contra PG nativo? | **SÍ** con extensión | No implementado |

**Veredicto:** Reports es **productizable como Data Platform** en capa metadata; **execution engine requiere contrato DataSource** antes de independizarse.

---

## Contrato DataSource propuesto (descubierto desde necesidades reales)

```text
ReportDataSourcePort
├── SchemaDiscovery
│     list_entities(company_context) → [EntityDescriptor]
├── EntityDiscovery
│     get_entity_schema(entity_id) → [FieldDescriptor]
├── RelationshipDiscovery
│     get_relationships(entity_id) → [RelationshipDescriptor]
│     record_learned_join(...)  # LearnedRelationship
├── QueryExecution
│     execute_query(query_spec, params, security_context) → ResultSet
├── AggregateExecution
│     execute_aggregate(spec) → Scalar | GroupedResult
├── Metadata
│     get_dialect() → "mysql_latin1" | "postgresql" | "odoo_orm"
├── Capabilities
│     supports_joins, supports_subqueries, read_only
├── SecurityContext
│     user_id, permissions[], allowed_entities[]
└── TenantContext
      company_id, database_alias / connection_key
```

### Mapeo estado actual → contrato

| Capability | Implementación actual | Gap |
|------------|----------------------|-----|
| SchemaDiscovery | `SemanticService` + `information_schema` (`semantic_service.py:138`) | Atado a MySQL |
| EntityDiscovery | `SHOW COLUMNS` (`administranet_stock.py:81` pattern) | Tabla literal |
| RelationshipDiscovery | `LearnedRelationship` PG + `relationship_learning.py` | Almacena nombres tabla |
| QueryExecution | `SqlQueryBuilder` + `cursor.execute` | SQL embebido |
| SecurityContext | `BuilderReportsPermission`, supervisor bypass | Sin entity-level ACL |
| TenantContext | `base_empresa` en filters; fallback DEFAULT_BASE_EMPRESA | Inconsistente |
| ReadOnlyPolicy | `sql_validator.py` blocks DML keywords | No read-only DB user |

---

## SqlQueryBuilder — necesidades reales

**Input requerido hoy:**
- `datasource` — string tabla
- `metrics` — expresiones SQL
- `dimensions` — columnas
- `joins[]` — tablas + ON
- `filters` — field + operator + value
- `base_empresa` — selección BD

**Validación (`sql_validator.py`):**
- Bloquea: DROP, INSERT, UPDATE, DELETE, ALTER, `;`, `--`
- Valida columnas vía `SHOW COLUMNS` **solo si base_empresa presente**
- Sin base_empresa → validación débil (warnings only)

**Gap crítico:** expresiones en metrics/dimensions son **trusted config** — no re-parseadas en runtime.

---

## Trust boundary SQL (Reports)

```text
Actor (user con reports.builder)
  ↓
POST builder/config (api_views.py:1095+)
  ↓
validate_report_config (sql_validator) — on save only
  ↓
ReportDefinition.config JSON almacenado PG
  ↓
Runtime: SqlQueryBuilder embebe expressions en SQL
  ↓
MySQL execute — NO re-validación
```

**Riesgo real:** MEDIUM-HIGH — requiere permiso `reports.builder` o supervisor; no es anónimo.

---

## Path to independent Report Engine

### Fase A (sin cambiar ERP)
- Introducir `ReportDataSourcePort` interface
- `AdministraNETReportDataSource` wraps existing SqlQueryBuilder
- `datasource` becomes `entity_id` mapped internally

### Fase B
- `PostgreSQLReportDataSource` para datos Synap-native
- `SemanticService` behind port

### Fase C
- `OdooReportDataSource` (if product decision)
- Metric Graph / declarative-v1 unchanged at config level

---

## Respuestas explícitas

| # | Pregunta | Respuesta |
|---|----------|-----------|
| 15 | ¿Puede Reports desacoplarse del ERP? | Metadata sí; execution requiere DataSourcePort |
| 16 | ¿Qué contrato necesita? | ReportDataSourcePort (arriba) — no table repositories |

---

*Seguridad SQL detallada en `09-SECURITY-VALIDATION.md`.*
