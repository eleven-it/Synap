# 12 — Deuda Técnica UI

**Estado:** COMPLETE

| Category | Evidence | Impact | Freq | Priority |
|----------|----------|--------|------|----------|
| **Visual debt** | slate vs gray dual palette | Medium | High | P2 |
| **Component debt** | 5+ button variants | Medium | High | P1 |
| **CSS debt** | Tailwind CDN + build dual | Medium | Universal | P1 |
| **JS debt** | dashboard_detail 5300 lines | High | Reports | P0 |
| **Navigation debt** | duplicate pedidos paths | Medium | Daily users | P1 |
| **Interaction debt** | 3 confirm patterns | Medium | High | P1 |
| **A11y debt** | modals, icon buttons | Medium | Medium | P2 |
| **Responsive debt** | reports desktop-only | Low | Analysts | P3 |
| **IA debt** | EN/ES menu mix | Low | All | P2 |

## Excluded from reference (explicit product debt)

- `ventas/objetivos-venta`, `ventas/presupuestos` — **REWRITE** priority when touched
- Templates `* 2.html` — **REMOVE** after verification
