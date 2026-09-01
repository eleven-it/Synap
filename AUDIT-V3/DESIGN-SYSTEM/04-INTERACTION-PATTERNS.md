# 04 — Interaction Patterns

**Estado:** COMPLETE

| Pattern | Current | Target |
|---------|---------|--------|
| Create | form POST + redirect | FormPage + success toast |
| Edit | form POST | same |
| Delete | confirm modal (3 variants) | **ConfirmDialog** unified |
| Cancel | link back / history.back | explicit Cancel → list |
| Search | navbar global + field filters | SearchInput component |
| Filter | 21 report filter partials | FilterBar composite |
| Bulk action | rare | DataGrid selection API |
| Drill-down | row click → detail | standard row link |
| Save | submit + post-loading | SubmitWithLoading |
| Export | button → API download | ExportButton with feedback |
| Upload | Excel pedido masivo | FileUpload with validation UI |
| Retry | manual refresh | RetryBanner on error state |

All patterns **SHOULD** use SynapMessages or ConfirmDialog — not native dialogs.
