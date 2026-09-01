# 04 — Límites del Refactor UI

**Estado:** COMPLETE | Clasificación por área — guía para implementación futura

---

## Leyenda

| Acción | Significado |
|--------|-------------|
| **REUSE AS IS** | Mantener; solo bugfixes |
| **RESTYLE** | Misma estructura; aplicar tokens/canon visual |
| **RECOMPONENTIZE** | Extraer a design system includes |
| **REDESIGN** | Cambiar layout/UX con characterization tests |
| **REWRITE** | Reimplementar pantalla/módulo |
| **REMOVE** | Eliminar (obsoleto/duplicado) |

---

## Por módulo

| Área | Pantallas clave | Acción | Prioridad | Notas |
|------|-----------------|--------|:---------:|-------|
| **Login** | login, empresa, password | RESTYLE | P2 | Funcional; gradient standalone |
| **Core shell** | navbar, status bar, dashboard módulos | RECOMPONENTIZE | P1 | Base de todo |
| **Reports** | dashboard_detail, catalog | RECOMPONENTIZE + extraer JS | **P0** | 5300 líneas JS |
| **MPR** | base_mpr, wizard, opt_* | REUSE AS IS → RESTYLE gradual | P1 | **Canon UI** |
| **Ecom** | pedidos hub, mayorista, masivo | RESTYLE hub; REWRITE masivo si UX gaps | P1 | Hub kanban OK estructura |
| **Ventas** | objetivos, presupuestos | **REWRITE** | P1 | Excluidos del canon |
| **Stock** | movimientos, conteo móvil | RESTYLE desktop; REUSE móvil | P1 | MOBILE CRITICAL conteo |
| **TPV** | kiosco, config | REUSE AS IS | P2 | Touch-first funciona |
| **TN** | dashboard, mappings | RESTYLE | P2 | Wizard steps OK |
| **Contabilidad audit** | tablero, export | RESTYLE | P2 | Tablas densas OK |
| **Captura compras** | upload, OCR | REDESIGN upload UX | P2 | Seguridad IDOR aparte |
| **IA** | chat, tools | RESTYLE | P3 | Bajo tráfico relativo |
| **SIA** | reportes RRHH | RESTYLE | P3 | — |

---

## Componentes transversales

| Componente | Acción |
|------------|--------|
| SynapMessages | RECOMPONENTIZE → Toast primitive |
| mprShowAviso | RECOMPONENTIZE → unificar con SynapMessages API |
| synap_post_loading_modal | RECOMPONENTIZE → SubmitWithLoading pattern |
| Confirm modals (3 variantes) | RECOMPONENTIZE → ConfirmDialog único |
| Filter partials reports (21) | RECOMPONENTIZE → FilterBar |
| Data tables MPR/reports | RECOMPONENTIZE → DataGrid compact |

---

## Eliminar

| Item | Acción | Condición |
|------|--------|-----------|
| Templates `* 2.html` | REMOVE | Tras verificar no referenciados |
| Tailwind CDN en prod | REMOVE | Tras unificar build |
| `dashboard/` stub app | REMOVE o REDIRECT | Si sin uso |
| Paleta gray-* paralela | REMOVE | Tras token slate unificado |

---

## No tocar en fase 1

- TPV kiosco flow (WF-06) — business critical
- MPR wizard steps logic — solo estilo
- Login/session bootstrap — arquitectura identity separada

---

*Referencia: `UIUX/04-SCREEN-CATALOG.md`, `UIUX/12-UI-TECHNICAL-DEBT.md`*
