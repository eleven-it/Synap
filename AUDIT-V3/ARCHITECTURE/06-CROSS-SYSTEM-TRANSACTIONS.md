# 06 — Cross-System Transactions

**Estado:** COMPLETE | **Fecha:** 25/08/2026

## Principle

> No code MAY assume atomicity across independent systems unless technically guaranteed.

Systems: PostgreSQL, MySQL (per company), Redis, AFIP WS, TiendaNube API, PHP relays, SMTP.

## Mandatory patterns (when cross-system write)

| Pattern | Use case | Evidence today |
|---------|----------|----------------|
| **Operation ID** | Trace multi-step | Partial — ReportExecutionLog |
| **Idempotency Key** | Retry-safe writes | TN outbox, webhook dedup |
| **Outbox** | Async reliable delivery | `TiendanubeOutboxEvent` |
| **Inbox** | Webhook processing | TN drain_inbox command |
| **Compensation** | Partial failure | **GAP** — manual ops |
| **Reconciliation** | Drift detection | contabilidad_audit |
| **Audit Trail** | Who/when/what | Expediente eventos, AgentToolExecution |
| **Correlation ID** | Request tracing | **GAP** — no global middleware |
| **Timeout + Retry Policy** | External APIs | Partial in TN sync |
| **Dead Letter** | Failed jobs | **GAP** — Celery inactive |

## Examples requiring non-ACID design

1. **Ecom checkout:** PG draft + MySQL comp_ped + stock — no 2PC (`mayorista_checkout_service.py`).
2. **TN order sync:** Webhook → MySQL writes + PG mapping — outbox pattern exists.
3. **Captura OCR:** PG expediente + filesystem + optional ERP proveedor write.
4. **Recibo + asiento:** ecom MySQL cuentacliente + cont_asiento.

## Rules

- Single-system transactions: use DB transaction (MySQL `get_connection` commit/rollback).
- Cross-system: saga or outbox; document compensation path.
- Jobs MUST carry CompanyContext + Operation ID.
