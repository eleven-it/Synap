# 01 — Principios de Experiencia Objetivo

**Estado:** COMPLETE | Evidencia: workflows WF-01–WF-10, UX audit, deuda UI

Los principios **no son estéticos** — emergen del trabajo real documentado en V3.

---

## Principios permanentes

| # | Principio | Evidencia | Implicación |
|---|-----------|-----------|-------------|
| P1 | **Rápido para operación repetitiva** | TPV scan, parte operario, conteo QR | Atajos teclado, densidad alta, mínimos clics en flujos diarios |
| P2 | **Predecible** | 3 patrones confirm distintos hoy | Un solo ConfirmDialog + SubmitWithLoading |
| P3 | **Alta densidad informativa** | MPR opt_list, reports tables | No sacrificar columnas por minimalismo |
| P4 | **Preservación de contexto** | Sin breadcrumbs; cambio app abrupto | Breadcrumb + retorno explícito en flujos multi-paso |
| P5 | **Teclado-friendly** | MPR wizard, pedido masivo | Tab order, Enter submit, escape cancel en formularios críticos |
| P6 | **Consciente del rol** | 14 roles funcionales, permisos granulares | Menú y acciones filtradas por capability, no solo por app |
| P7 | **Resistente a errores** | Pedido masivo Excel, auditoría dry-run | Validación antes de commit; confirmación en acciones destructivas |
| P8 | **Accesible** | WCAG gaps en modales/iconos | AA en componentes nuevos; no depender solo de color |
| P9 | **Consistente** | Canon Reports/MPR vs ventas legacy | Nuevas pantallas siguen canon hasta DS formal |
| P10 | **Orientado al negocio** | Capabilities map 20+ áreas | Navegación por capacidad, no por paquete Django |
| P11 | **IA asistida, no dependiente** | PolicyGate en ia/ | IA complementa; workflows críticos funcionan sin IA |

---

## Anti-patrones a evitar en refactor

| Anti-patrón | Por qué |
|-------------|---------|
| Reducir columnas de tablas "por limpieza" | Operarios necesitan scan visual rápido |
| Mobile-first en reports/analytics | Gerentes usan desktop; clasificar MOBILE CRITICAL solo donde aplica |
| Unificar todo en React por moda | 471 templates + Alpine; migración incremental |
| Eliminar shortcuts VB6-equivalentes sin reemplazo | Usuarios expertos dependen de velocidad |
| `alert/confirm` nativos | Regla proyecto + inconsistencia actual |

---

## Validación por workflow crítico

| Workflow | Principios que **no** pueden romperse |
|----------|--------------------------------------|
| WF-06 TPV | P1, P3, P7 |
| WF-04 MPR OPT | P1, P3, P5 |
| WF-05 Parte móvil | P1, P4 (mobile) |
| WF-07 Reports | P3, P10 |
| WF-03 Pedido masivo | P7, P2 |
| WF-01 Login | P2, P6 |

---

*Referencia: `UIUX/02-UX-AUDIT.md`, `PRODUCT/03-WORKFLOW-CATALOG.md`*
