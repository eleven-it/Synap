# 05 — Data Ownership Contract

**Estado:** COMPLETE | **Fecha:** 25/08/2026

## Principle

> Each business datum has exactly one logical System of Record at any time.

## Categories & rules

| Category | SoR | Synap may | ERP may | Rules |
|----------|-----|-----------|---------|-------|
| **SYNAP OWNED** | Synap PG / Synap MySQL DDL | R+W | — | Full control |
| **ERP OWNED** | AdministraNET MySQL | Read via Port; Write via Adapter only | R+W | No direct domain SQL |
| **EXTERNAL OWNED** | AFIP, TiendaNube, etc. | Sync metadata in PG | — | Integration module owns mapping |
| **DERIVED** | Computed | Cache with TTL | — | Must trace to SoR |
| **CACHE** | Redis / memory | Ephemeral | — | Tenant-scoped keys |
| **REPLICA** | Read copy | Refresh from SoR | — | Never authoritative |
| **TRANSITIONAL SHARED** | ERP (target) | Write during migration | Write | Document deviation; sunset date |

## Forbidden

- Synap field X + ERP field X writable without ownership doc.
- PG `core.Empresa` + MySQL `empresas` without mapping contract.

## Entity summary (see AUDIT-V2/03)

| Entity | SoR today | Target SoR |
|--------|-----------|--------------|
| Report metadata | Synap PG | Synap |
| Stock qty | ERP | ERP (via InventoryPort) |
| User credentials | ERP | Split: IdP Synap, profile ERP optional |
| Orders | ERP | ERP |
| OCR expediente | Synap PG | Synap |
