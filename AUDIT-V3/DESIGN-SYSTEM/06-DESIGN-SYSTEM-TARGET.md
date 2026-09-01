# 06 — Design System Target + Contract

**Estado:** COMPLETE

## Architecture

```text
Design Tokens (tailwind extend + CSS vars)
        ↓
Primitives (Button, Input, Text, Icon, Badge)
        ↓
Components (Modal, Toast, DataGrid, FormField, Card)
        ↓
Patterns (ConfirmDelete, SubmitWithLoading, FilterBar)
        ↓
Feature Components (module-specific, compose only)
        ↓
Page Templates (ListPage, DetailPage, DashboardPage)
```

## Location (proposed)

```text
theme/design_system/
  tokens/
  primitives/        # Django includes or web components
  components/
  patterns/
  pages/
```

## Design System Contract

| Rule | Norm |
|------|------|
| Tokens | **MUST** be defined in single `tailwind.config` extend; **MUST NOT** hardcode hex in templates |
| Components | **MUST** have variants documented; states: default, hover, disabled, loading, error |
| Accessibility | **MUST** meet WCAG 2.1 AA for new components |
| Interaction | **MUST NOT** use `alert/confirm/prompt` |
| Ownership | `theme/` owns primitives/components; modules own feature components only |
| Versioning | Semantic versioning for breaking component API changes |
| Deprecation | 2-release warning before removing component |
| Canon | New screens **MUST** follow Reports/MPR patterns until DS components exist |

## Governance

- Design system changes require review from platform + 1 module owner
- Module **MUST NOT** fork Button/Modal/Table markup

## Implementation order

1. Tokens (slate unification, purple scale)
2. Button, Input, Modal, Toast (unify SynapMessages + mprShowAviso API)
3. DataGrid compact variant
4. FilterBar, FormField
5. Page templates
