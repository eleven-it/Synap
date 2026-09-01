# 11 — Evaluación de Accesibilidad

**Estado:** COMPLETE | WCAG 2.1 referencia conceptual

| Criterio | Estado | Evidence |
|----------|--------|----------|
| Semantic HTML | **Partial** | div-heavy dashboards; some tables proper |
| Keyboard navigation | **Partial** | forms OK; modals focus trap weak |
| Focus management | **Gap** | Alpine modals without consistent focus return |
| Labels | **Partial** | most forms labeled; icon-only buttons in TPV |
| Contrast | **Likely OK** | slate/purple on white — not audited with tool |
| ARIA | **Sparse** | few `aria-*` in modals |
| Screen reader | **Untested** | dynamic widgets (D3) lack live regions |
| Error messaging | **Partial** | toasts may not announce |
| Color-only meaning | **Risk** | status badges color-coded |
| Tab order | **Generally logical** | |

## Priority fixes (future)

1. Confirm modals — focus trap + aria-labelledby
2. Icon buttons — aria-label
3. Dashboard widget updates — aria-live polite
4. TPV scan field — label + instructions

**Not blocking refactor start** but MUST be in design system contract.
