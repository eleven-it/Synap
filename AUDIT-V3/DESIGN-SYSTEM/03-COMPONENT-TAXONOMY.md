# 03 — Component Taxonomy

**Estado:** COMPLETE | Target taxonomy

```text
Primitive (Button, Input, Icon, Text, Badge)
    ↓
Component (FormField, DataGrid, Modal, Toast, Card, FilterBar)
    ↓
Composite (FormActions, KpiStrip, WizardStep, DashboardWidget)
    ↓
Pattern (CreateRecord, EditRecord, ConfirmDelete, ExportTable)
    ↓
Feature Component (PedidoHubKanban, MprWizard, ReportDashboard)
    ↓
Page Template (ListPage, DetailPage, DashboardPage, WizardPage)
```

## Mapping examples

| Current | Target level |
|---------|--------------|
| `bg-purple-600 rounded-xl` button | Primitive `Button variant=primary` |
| `mpr-post-loading` form | Pattern `SubmitWithLoading` |
| `opt_list.html` table section | Feature `OptListPage` using `DataGrid compact` |
| `dashboard_detail.html` | Page `DashboardPage` + `DashboardWidget` composites |

## Governance

- New screens **MUST** use taxonomy levels ≥ Component
- Primitives **MUST NOT** be redefined in feature templates
- Variants **SHOULD** be token-driven, not copy-paste classes
