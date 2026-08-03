# Checklist QA device — VMM PWA + Cotización BCRA (P7)

**Change:** `vmm-pwa-cotizacion-bcra`  
**Fecha documento:** 02/08/2026  
**Empresa piloto sugerida:** Best Sox (`base_empresa=administranet`)  
**Estado global:** **pendiente ejecución en dispositivo** — este documento es plantilla operativa; **no** implica corrida realizada.

**Referencias:** [SPEC_INFORME_VENTAS_MARCAS_MENSUAL.md](SPEC_INFORME_VENTAS_MARCAS_MENSUAL.md) §10–10.3, [PLAN_INFORME_VENTAS_MARCAS_MENSUAL.md](PLAN_INFORME_VENTAS_MARCAS_MENSUAL.md) §9 Frente P, [PLAN_COTIZACION_BCRA_SYNAP.md](../mpr/best/PLAN_COTIZACION_BCRA_SYNAP.md).

---

## Precondiciones (ambos dispositivos)

| # | Paso | iOS Safari PWA | Android Chrome PWA | Resultado |
|---|------|----------------|---------------------|-----------|
| P1 | Synap desplegado en Staging (o entorno acordado) con change `vmm-pwa-cotizacion-bcra` | ☐ | ☐ | pendiente |
| P2 | Usuario con permisos informe VMM + (opcional) `contabilidad.cotizacion.ver` | ☐ | ☐ | pendiente |
| P3 | PWA instalada desde `/login/` (manifest `start_url` válido) | ☐ | ☐ | pendiente |
| P4 | Hard-refresh / vaciar cache SW tras deploy (`?v=` o reinstalar PWA) | ☐ | ☐ | pendiente |
| P5 | Datos Best Sox: ventas PUM/PUW en período reciente (ver [SMOKE_BEST_SOX_VMM.md](SMOKE_BEST_SOX_VMM.md)) | ☐ | ☐ | pendiente |

**Dispositivos objetivo:** iPhone Safari (PWA «Añadir a pantalla de inicio») + Android Chrome (PWA instalada). Probar **portrait** (~390px) y **landscape** (&lt; `lg` 1024px).

---

## A. Informe Ventas marcas mensual — acceso

| # | Escenario | iOS | Android | Notas |
|---|-----------|-----|---------|-------|
| A1 | Deep-link `/reports/dashboard/ventas-marcas-mensual/` sin 403 en móvil | ☐ | ☐ | Nivel A allowlist |
| A2 | Entrada desde dashboard `/core/dashboard/` o Command Center | ☐ | ☐ | |
| A3 | `reports` **no** aparece en navbar PWA (ADR-2); acceso solo deep-link/CC | ☐ | ☐ | |

---

## B. Sheet filtros móvil (Fase 1 — P2)

| # | Escenario | iOS | Android | Notas |
|---|-----------|-----|---------|-------|
| B1 | Botón «Filtros» abre sheet inferior; overlay cierra al tocar fuera | ☐ | ☐ | `reports_filters_sheet.js` |
| B2 | CTA «Actualizar» sticky ≥44px; ejecuta consulta | ☐ | ☐ | |
| B3 | Chips/badge muestran filtros activos (marca, período, PV, preset) | ☐ | ☐ | |
| B4 | Período desde–hasta editable en sheet | ☐ | ☐ | dd/MM/yyyy |
| B5 | Tags marca + SuperArt + PV operables touch | ☐ | ☐ | |
| B6 | Sección «Licencia y proyección» (regalía, TC, proyección) usable | ☐ | ☐ | |
| B7 | Preset «Hombre» aplica SuperArts y dispara consulta | ☐ | ☐ | |
| B8 | Hint «TC vigente BCRA» visible con TC vacío (A9) | ☐ | ☐ | |

---

## C. KPIs móvil (Fase 2 — P3)

| # | Escenario | iOS | Android | Notas |
|---|-----------|-----|---------|-------|
| C1 | Portrait ~390px: 5 KPIs legibles en 1–2 columnas | ☐ | ☐ | Sin scroll horizontal de página |
| C2 | Landscape: KPIs en fila densa sin overflow | ☐ | ☐ | |
| C3 | Valores coherentes tras cambiar packs ↔ docenas | ☐ | ☐ | |

---

## D. Matriz móvil (Fase 2 — P4)

| # | Escenario | iOS | Android | Notas |
|---|-----------|-----|---------|-------|
| D1 | Portrait: matriz en **tarjetas** Ven→Cliente con chips por mes | ☐ | ☐ | |
| D2 | Expand/colapsar vendedor touch ≥44px; estado persiste | ☐ | ☐ | |
| D3 | Landscape: tabla con 1.ª columna sticky + scroll horizontal | ☐ | ☐ | |
| D4 | Selector orden «Facturación ↓/↑» y «Unidades ↓/↑» persiste tras recarga | ☐ | ☐ | `localStorage` |
| D5 | Banner U.M. desconocidas visible sin bloquear matriz | ☐ | ☐ | |
| D6 | Aviso cap 24 meses (`#vmm-aviso-meses`) si aplica | ☐ | ☐ | |

---

## E. Comparar marcas PWA (Fase 3 — P5)

| # | Escenario | iOS | Android | Notas |
|---|-----------|-----|---------|-------|
| E1 | Toggle «Una marca / Comparar marcas» accesible en sheet o cabecera | ☐ | ☐ | |
| E2 | Portrait: tabs **Marca A / Marca B** conmutan vista sin nueva consulta | ☐ | ☐ | G15 |
| E3 | KPIs delta % facturación visibles en ambas marcas | ☐ | ☐ | |
| E4 | Landscape: matriz dual o scroll horizontal controlado | ☐ | ☐ | |
| E5 | Aviso Synap si marca A = marca B (sin HTTP 500) | ☐ | ☐ | G14 |

**Datos sugeridos:** PUM vs PUW, período 01/01/2026–31/01/2026 (ajustar a ventas reales en Staging).

---

## F. Export PWA (Fase 3 — P6)

| # | Escenario | iOS | Android | Notas |
|---|-----------|-----|---------|-------|
| F1 | Export Excel descarga o inicia descarga nativa | ☐ | ☐ | Hojas Matriz + Detalle |
| F2 | Si Safari/Chrome bloquea descarga: toast `mprShowAviso` / `SynapMessages` (sin `alert`) | ☐ | ☐ | G16 |
| F3 | Archivo coherente con filtros en pantalla (nombre `Ventas_marcas_mensual_*.xlsx`) | ☐ | ☐ | Validar en desktop si móvil bloquea |

---

## G. Cotización dólar PWA (Fase 4 — B5/B6)

| # | Escenario | iOS | Android | Notas |
|---|-----------|-----|---------|-------|
| G1 | Menú PWA contabilidad muestra «Cotización dólar» con permiso | ☐ | ☐ | `contabilidad_cotizacion_dolar` |
| G2 | `/contabilidad/cotizacion-dolar/` carga vigente + historial | ☐ | ☐ | |
| G3 | Sugerencia BCRA visible (o mensaje fail-soft si API caída) | ☐ | ☐ | |
| G4 | Modal Synap «Aceptar sugerido» (sin `confirm` nativo) | ☐ | ☐ | |
| G5 | Modal «Valor manual» con validación | ☐ | ☐ | |
| G6 | Historial dd/MM/yyyy legible en portrait | ☐ | ☐ | |
| G7 | Tras aceptar/manual: VMM con TC vacío refleja TC vigente (hint + KPI Regalías/TC) | ☐ | ☐ | A9 |

---

## H. Regresión desktop (smoke rápido en mismo build)

| # | Escenario | Desktop Chrome | Notas |
|---|-----------|----------------|-------|
| H1 | Matriz tabla completa ≥ `lg` sin degradación PWA | ☐ | |
| H2 | Modo comparar dual columnas desktop | ☐ | |
| H3 | Cotización dólar desktop + modales | ☐ | |

---

## Acta de ejecución (completar en campo)

| Campo | Valor |
|-------|-------|
| Fecha ejecución | _pendiente_ |
| Build / commit / entorno | _pendiente_ |
| Ejecutor | _pendiente_ |
| iOS — modelo / versión Safari | _pendiente_ |
| Android — modelo / versión Chrome | _pendiente_ |
| Incidencias | _pendiente_ |
| Evidencia (capturas / enlaces) | _pendiente_ |

**Criterio cierre P7:** todas las filas A–G marcadas en **al menos** un dispositivo iOS y uno Android, acta firmada, incidencias críticas resueltas o documentadas como backlog.
