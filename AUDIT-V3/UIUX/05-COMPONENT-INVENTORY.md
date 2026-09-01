# 05 — Inventario de Componentes

**Estado:** COMPLETE | Sin librería formal — patrones implícitos

## Foundations

| Component | Implementación | Duplicación |
|-----------|----------------|:-----------:|
| Colors | Tailwind inline purple/slate/sky | **Alta** — slate vs gray |
| Typography | Inter + Material Icons | Baja |
| Spacing | `p-4 md:p-8`, `mpr-contenedor-pagina` | Media |
| Radius | `rounded-xl`, `rounded-2xl` | Baja |
| Shadows | `shadow-lg` cards | Baja |

## Inputs

| Component | Patrones | Clasificación |
|-----------|----------|---------------|
| Button primary | `bg-purple-600 rounded-xl` | **ACCIDENTAL DUPLICATE** ×N |
| Button secondary | gray outline variants | DUPLICATE |
| Toggle Activo/Inactivo | `btn-toggle-estado-usuario` | VARIANT — canon usuarios |
| Search | navbar + per-screen | VARIANT |
| Date filters | `reports/includes/filters_*.html` (21) | SPECIALIZED |
| File upload | pedido masivo, FE certs | SPECIALIZED |

## Navigation

| Component | Location |
|-----------|----------|
| Navbar apps | `theme/partials/navbar.html` |
| Status bar | `theme/partials/status_bar.html` |
| MPR quick-nav | `base_mpr.html` |
| Tabs | Alpine `x-show` en varias pantallas |

## Data display

| Component | Implementations |
|-----------|-----------------|
| Table dense | MPR `min-w-full divide-y` |
| Table reports | dashboard widgets |
| KPI strip | `mpr/reportes/_kpi_strip.html`, command center cards |
| Charts | D3 widget_engine, mpr_reportes_charts.js |
| Badge status | Tailwind colored pills |

## Feedback

| Component | API | Adoption |
|-----------|-----|----------|
| SynapMessages toast | `SynapMessages.show()` | Global via base_app |
| mprShowAviso modal | `mprShowAviso()` | MPR + contabilidad |
| Post-loading modal | `synapShowPostLoading` | ~35 forms |
| Confirm delete | ad-hoc + TN `synap_confirm_modal` | **DUPLICATE** |

## Duplication summary

| Intent | Implementations | Verdict |
|--------|----------------:|---------|
| Primary button | 5+ markup variants | ACCIDENTAL DUPLICATE → tokenize |
| Confirm destructive | 3+ modal patterns | ACCIDENTAL DUPLICATE |
| Toast/alert | SynapMessages vs mprShowAviso | VARIANT (acceptable if unified API) |
| Data table | 4+ implementations | SPECIALIZED per domain — extract DataGrid pattern |
