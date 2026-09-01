# 03 — Arquitectura Frontend Objetivo

**Estado:** COMPLETE | Recomendación justificada — **no implementar aún**

---

## Estado actual

| Capa | Tecnología | Evidencia |
|------|------------|-----------|
| Templates | Django 4.x | 471 HTML templates |
| CSS | Tailwind 3 (CDN + build dual) | `theme/static_src/` |
| Interactividad | Alpine.js 3 | MPR, reports, ecom |
| Charts | D3.js | `reports/static/` |
| Build | npm + tailwind CLI | `package.json` |
| SPA frameworks | **Ninguno** | No React/Vue en prod |

---

## Evaluación de alternativas

| Opción | Pros | Contras | Veredicto |
|--------|------|---------|-----------|
| **Django + Alpine + Tailwind (actual)** | 471 templates, equipo conocimiento, server-render, SEO N/A irrelevante, ERP density | Monolito template, dashboard_detail 5300 líneas | **MANTENER como base** |
| HTMX | Menos JS, partial updates | Requiere refactor endpoints; overlap Alpine | **Adoptar selectivamente** para listas/filtros |
| React/Vue SPA | Component reuse, ecosystem | Rewrite masivo, desync con Django auth | **NO full migration** |
| Hybrid (shell React + Django islands) | Gradual | Dos stacks, complejidad deploy | **Solo si módulo nuevo lo exige** |
| Server-driven UI (custom) | — | Sin framework maduro en stack | Descartado |

---

## Recomendación

### Mantener: Django Templates + Tailwind + Alpine

**Razones:**

1. **471 plantillas** — costo rewrite >> beneficio inmediato
2. **ERP UX** — server-render excelente para tablas densas y formularios
3. **Permisos** — Django template tags + session ya integrados
4. **Equipo** — convenciones establecidas (MPR, reports canon)
5. **Performance** — sin bundle SPA grande; Alpine ligero

### Evolucionar incrementalmente:

| Mejora | Cuándo |
|--------|--------|
| **Design tokens** en `tailwind.config` extend | Fase 1 refactor UI |
| **Django includes** como primitives (Button, Modal) | Fase 2 |
| **HTMX** en listas con filtro/paginación server | Nuevas pantallas lista |
| **Extraer JS** de `dashboard_detail.html` a módulos | P0 deuda |
| **Unificar** Tailwind CDN → solo build | P1 deuda |

### NO hacer:

- Big-bang React migration
- Reemplazar Alpine en MPR wizard sin caracterización tests
- Introducir segundo bundler (Vite) sin necesidad clara

---

## Estructura frontend objetivo

```text
theme/
  design_system/          # tokens, primitives, components (includes)
  templates/
    base_app.html         # shell estándar
    partials/
  static/
    js/
      synap-messages.js   # feedback unificado
      components/         # JS por componente (DataGrid, etc.)
    css/
      tailwind.output.css # único CSS build

<módulo>/
  templates/<módulo>/     # feature templates (componen DS)
  static/<módulo>/        # JS específico módulo solo si necesario
```

---

## Criterios para excepción (nuevo stack en módulo)

Solo si **todos** aplican:

- UI altamente interactiva (drag-drop complejo, canvas)
- Sin equivalente Alpine/HTMX razonable
- Módulo acotado con API REST clara
- Characterization tests antes de rewrite

**Candidatos futuros posibles:** ninguno identificado como P0 en V3.

---

*Referencia: `UIUX/01-UI-INVENTORY.md`, `UIUX/12-UI-TECHNICAL-DEBT.md`, `DESIGN-SYSTEM/06-DESIGN-SYSTEM-TARGET.md`*
