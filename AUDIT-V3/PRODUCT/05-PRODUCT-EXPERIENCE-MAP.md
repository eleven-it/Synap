# 05 — Product Experience Map

**Estado:** COMPLETE

## Matriz end-to-end (capacidades críticas)

| Capability | User type | Workflow | Screen | Component | API | Port | Data |
|------------|-----------|----------|--------|-----------|-----|------|------|
| Pedido mayorista | Vendedor | WF-02 | pedidos_hub | kanban, filtros | ecom hub API | SalesOrderPort | comp_ped |
| Producción OPT | Supervisor MPR | WF-04 | mpr/wizard | wizard steps | mpr API | ProductionPort + InventoryPort | mpr_*, stock |
| TPV venta | Cajero | WF-06 | kiosco_view | cart, scan | sc venta API | PointOfSalePort | resumen_venta_cv |
| Dashboard ventas | Gerente | WF-07 | dashboard_detail | widgets, filters | reports execute | ReportDataSourcePort | MySQL read |
| Inventario físico | Almacén | WF-08 | conteo mobile | QR scanner | stock API | InventoryPort | inv_fisico_* |
| Auditoría contable | Contador | WF-09 | auditoria tablero | tables, export | contab API | AccountingPort (read) | cont_asiento |

## Relación experiencia → sistema

```text
USER EXPERIENCE (goal, screen, component)
       │
       ▼
PRODUCT CAPABILITY (what user perceives)
       │
       ▼
SOFTWARE CAPABILITY (module, API, service)
       │
       ▼
DOMAIN (Port contract)
       │
       ▼
DATA / ERP (System of Record)
```

**Purpose:** Evitar que rediseño UI rompa workflows sin equivalente en Ports.
