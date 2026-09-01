# 22 — Observabilidad

**Estado:** COMPLETE (Fase 22)  
**Fecha:** 25/08/2026

---

## Estado actual

| Capacidad | Estado | Evidencia |
|-----------|--------|-----------|
| Logging | Básico | `LOGGING` en settings — console handler |
| Métricas | **No** | Sin Prometheus/StatsD |
| Tracing | **No** | Sin OpenTelemetry/Jaeger |
| Error tracking | **No** | Sin Sentry configurado |
| Health checks | Docker | `docker-compose.yml` healthcheck HTTP |
| Request IDs | **No** | Sin correlation ID middleware |
| Audit funcional | Parcial | ReportExecutionLog, EventoAuditoriaInterno |
| Performance headers | Inactivo | PerformanceMiddleware comentado |

---

## Logging

```python
LOGGING = {
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'DEBUG' if DEBUG else 'INFO'},
}
```

- Sin log rotation configurada en app (Docker json-file driver con max 10m)
- Sin structured logging (JSON)
- Sin log aggregation (ELK/Datadog)
- Loggers por módulo eliminados (settings línea 485-487)

---

## Auditoría funcional existente

| Componente | Qué registra |
|----------|-------------|
| `ReportExecutionLog` | Ejecuciones reportes (duración, rows, error) |
| `EventoAuditoriaInterno` | Workflow factura compra |
| `SyncLog` (tiendanube) | Operaciones sync |
| `WebhookDeliveryLog` | Entregas webhook |
| `BackupJob` | Operaciones backup |
| `AgentExecution` | Ejecuciones IA |
| `HistorialPoliticaAuditoria` | Cambios políticas contables |
| `AuditoriaMiddleware` | **Inactivo** — POST/PUT/DELETE |

---

## ¿Podemos reconstruir qué ocurrió cuando falla?

| Escenario | Reconstruible | Gap |
|-----------|:------------:|-----|
| Error en reporte | Parcial | ReportExecutionLog tiene error message |
| Error en TPV venta | **No** | Sin audit trail transaccional |
| Error en sync TN | Sí | SyncLog + WebhookDeliveryLog |
| Error en backup | Sí | BackupJob.status + artefactos |
| Error en login | **No** | Sin log intentos fallidos estructurado |
| Error cross-request | **No** | Sin correlation ID |

**Respuesta: No de forma confiable** para la mayoría de operaciones críticas.

---

*Generado por auditoría READ ONLY.*
