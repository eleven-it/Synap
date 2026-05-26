# Matriz de coherencia UI - Presupuesto operativo

Fecha: 06/05/2026

## 1) Objetivo

Definir el criterio de calidad UI para `ventas/presupuesto_*.html` como **formulario operativo**:

- No requiere alineacion estructural 100% con dashboards de reportes.
- Si requiere coherencia visual y de comportamiento con el sistema Synap.

Referencia de consistencia global: `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`.

## 2) Alcance y no alcance

### 2.1 Alcance (MUST)

- Componentes de filtros por tags con patron de reportes:
  - `tags-filter-container`, `tags-chips`, `tags-input`, `tags-dropdown`.
  - Logica compartida `reports/static/reports/js/tags_filter.mjs` (`initializeTagsFilter`).
- Paleta y estados base del sistema:
  - grises `slate`, foco `sky/cyan`, variantes dark mode.
- Campos de formulario y botones:
  - estados `hover`, `focus-visible`, `disabled` coherentes.
- Mensajeria y feedback:
  - errores de validacion visibles y en espanol.
  - modal de espera para operaciones de red/envio.
- Accesibilidad minima:
  - labels/`sr-only` en campos, `aria-live` donde aplica, navegacion por teclado funcional.

### 2.2 No alcance (OUT)

- No forzar shell de `reports/dashboard_detail.html`.
- No forzar `REPORT_CONFIG` ni `widget_engine.js`.
- No convertir presupuesto en pantalla tipo informe.

## 3) Matriz de control

## 3.1 Visual

- MUST: tipografia, bordes, radios, sombras y densidad consistentes con Synap.
- MUST: contraste correcto en modo claro/oscuro.
- SHOULD: reducir estilos inline propios y preferir tokens/clases compartidas.

## 3.2 Comportamiento

- MUST: filtros tags con seleccion, busqueda, teclado, cierre por click externo.
- MUST: foco visible en acciones primarias/secundarias y enlaces de accion.
- MUST: botones deshabilitados con estado visual claro y no interactivo.
- SHOULD: transiciones cortas y consistentes (`transition`).

## 3.3 Datos y validacion

- MUST: mantener `hidden` sincronizados con selects/inputs visibles.
- MUST: reglas de validacion operativa (cliente requerido, al menos una linea).
- SHOULD: mensajes de error unificados en tono y estilo.

## 4) Checklist rapido para PR

- [ ] Filtros de cabecera usan `initializeTagsFilter`.
- [ ] Todos los controles accionables tienen `focus-visible`.
- [ ] Hay coherencia de alturas y espaciado entre campos de linea.
- [ ] `disabled` se ve y se comporta igual en acciones principales y secundarias.
- [ ] Modal de espera y mensajes de error se muestran en operaciones criticas.
- [ ] Se probo teclado (tab, enter, escape, flechas en dropdown).
- [ ] Se reviso modo oscuro.

## 5) Aplicacion inicial en presupuesto

En `ventas/templates/ventas/presupuesto_nuevo.html` se aplicaron ajustes de hardening:

- foco visible y transicion en enlace `Cancelar/Volver`;
- foco visible y cursor no permitido en `+ Anadir renglon` y `Duplicar ultimo`;
- foco visible, hover y disabled consistente en boton Guardar mobile.

Estos cambios no alteran el flujo operativo ni la logica de negocio.
