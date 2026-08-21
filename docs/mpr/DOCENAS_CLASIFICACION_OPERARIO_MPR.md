# Docenas operativas y clasificación por operario fabricante (MPR)

**Change OpenSpec:** `openspec/changes/mpr-docenas-clasificacion-operario/`  
**Estado:** Implementado en Desarrollo — aplicar migración MySQL en cada base empresa.  
**Fecha:** 08/07/2026

> **Nota 20/08/2026 — CC consolidado por artículo:** la grilla de control de calidad migró al modelo **consolidado por artículo** (change `mpr-cc-consolidado-articulo`). Semi único por artículo; 2da/scrap por operario+turno; tope = saldo Producción. Ver [PLAN_CC_CONSOLIDADO_POR_ARTICULO.md](PLAN_CC_CONSOLIDADO_POR_ARTICULO.md). Las notas históricas de abajo describen el modelo **por celda** previo y se conservan como referencia de evolución.

### Prerrequisito esquema MySQL

Control de calidad (clasificación por operario) requiere columnas en `mpr_transicion_lote`: `id_operario`, `operario_nombre`, `fecha_produccion`, `id_mpr_turno`. Si falta alguna:

```bash
docker exec Synap_app python manage.py apply_mpr_core_tables <base_empresa>
```

DDL: `mpr/sql/002_mpr_transicion_lote_operario.sql` (vía `catalog.run_mpr_core_tables_mysql`).

---

## Resumen ejecutivo

Dos mejoras coordinadas para alinear MPR con la planta textil:

1. **Presentación en docenas** por defecto en tablero, envío, parte y clasificación (persistencia en unidades).
2. **Clasificación por operario que fabricó**, con reparto Semi elaborado / 2da selección / Scrap y reporte de rendimiento ampliado.

---

## Decisiones de producto

| Tema | Decisión (modelo consolidado 20/08/2026) |
|------|----------|
| Default presentación | Docenas en flujo operativo |
| Toggle | Sesión `mpr_presentacion_cantidad` |
| Divisor componentes | 12 u./docena |
| Bloques clasificación | **Un bloque por artículo**; subfilas **(operario, turno)** para 2da/scrap; máquinas colapsadas |
| Alcance pendiente | Fecha obligatoria; **sin filtro Turno** en encabezado (día completo) |
| Columnas grilla CC | Artículo, **Saldo producción**, Semi (único por bloque), Turno, Operario, 2da, Scrap |
| Semi elaborado | **Un ingreso por artículo/día**; ledger con `id_operario` y `id_mpr_turno` nulos; tope = saldo Producción del artículo |
| 2da / Scrap | Por **(operario, turno)** del parte; `id_operario` obligatorio en ledger |
| Artículo huérfano | Saldo Prod > 0 sin parte: solo Semi editable |
| Validación CC | `semi + Σ 2da + Σ scrap ≤ saldo Producción` (lock `FOR UPDATE`); 2da/scrap además ≤ atribuible operario+turno |
| Solo pendiente | Oculta artículos sin saldo Prod y operarios con 2da/scrap confirmados |
| Bloqueo parte | Dual: 2da/scrap o Semi **histórico con operario** bloquean turno; Semi nuevo sin operario **no** bloquea |
| Borrador | Tablas `mpr_cc_borrador` / `_linea` (007); cabecera por fecha; borrador viejo por turno incompatible |
| Corrección post-CC | Transferencia interna / movimiento de stock (sin reverse en grilla) |
| Reporte operario | Semi con `id_operario NULL` **no** suma al operario; fila «Sin atribución» para agregados NULL |
| Ledger | Semi nuevo: `id_operario` NULL; 2da/scrap: fabricante; `id_usuario` = quien guardó |

### Modelo anterior por celda (hasta 19/08/2026)

| Tema | Decisión (histórico) |
|------|----------|
| Filas clasificación | (máquina × artículo × turno × operario), pendiente > 0 o ya clasificadas (roster completo) |
| Alcance pendiente | Fecha obligatoria; turno opcional (vacío = todos los turnos del día) |
| Columnas grilla CC | Máquina, Artículo, Turno, Operario, **Parte** (referencial), Semi, 2da, Scrap |
| Semi elaborado | Editable por celda; tope fila = atribuible + extra pool |
| Extra producción (CC) | `max(0, stock Producción − Σ atribuible_parte)` por artículo repartido por celda |
| Bloqueo parte | Si un turno tiene CC en `mpr_transicion_lote` (fecha+turno), ese turno del parte queda bloqueado |

---

## Flujo en planta

```text
Parte (por operario) → Stock Producción agregado
                    → Clasificador revisa bultos por operario
                    → Clasificación (semi / 2da / scrap) con id_operario fabricante
                    → Reporte rendimiento por operario
```

---

## Artefactos SDD

| Documento | Ruta |
|-----------|------|
| Exploración | `openspec/changes/mpr-docenas-clasificacion-operario/exploration.md` |
| Propuesta | `openspec/changes/mpr-docenas-clasificacion-operario/proposal.md` |
| Diseño UX | `openspec/changes/mpr-docenas-clasificacion-operario/design.md` |
| Tasks | `openspec/changes/mpr-docenas-clasificacion-operario/tasks.md` |
| Spec docenas | `specs/mpr-presentacion-docenas-operativa/spec.md` |
| Spec clasificación | `specs/mpr-clasificacion-operario-fabricante/spec.md` |
| Spec reporte | `specs/mpr-reporte-rendimiento-operario/spec.md` |

---

## Cambio de esquema

`mpr_transicion_lote`:

- `id_operario` INT NULL — operario fabricante
- `operario_nombre` VARCHAR — snapshot al guardar

Migración vía `core/services/legacy_mysql_schema/catalog.py`.

---

## P1 completado

- Toggle **Ver roster completo** en clasificación (filas completadas solo lectura; disponible para todo usuario con acceso a CC).
- Hub reportes MPR: default **docenas** (GET, sesión operativa o fallback).
- Reporte operario: gráfico apilado **semi · 2da · scrap** (`hbar_stacked`).
- **Bloqueos CC (08/07/2026):** no bloquear fila si ya está 100 % clasificada o sin cantidad sin operario asignado (`construir_grilla_clasificacion_produccion`).
- **Fabricando unificado (08/07/2026):** tablero, parte y reporte pendientes usan `acreditado = max(stock, clasificado CC, partes acumulados)`; componentes sin columna Terminado. Ver [REPORTES_MPR.md](REPORTES_MPR.md), [TABLERO_CONSOLIDADO.md](TABLERO_CONSOLIDADO.md).
- **Guarda física CC corregida (08/07/2026):** al guardar Control de calidad, la validación agregada de stock ahora compara **solo lo que se clasifica ahora** contra el **saldo vivo de Producción** (`total_cls > disponible_real`). Antes sumaba el acumulado ya clasificado del turno (`prev_cls_art + total_cls`), lo que **duplicaba el descuento** y bloqueaba falsamente con "Stock Producción insuficiente" cuando parte del stock clasificado ya había salido del pipeline (p. ej. Semi Elaborado consumido en el armado del pack BOM). El tope por operario (`atribuible = fabricado − ya_clasificado`) se mantiene. Ref: `mpr/views.py::RegistrarClasificacionProduccionView.post`; tests `test_clasificado_previo_consumido_no_bloquea` y `test_bloqueo_si_supera_saldo_vivo_produccion` en `mpr/tests/test_etapa10_clasificacion_produccion.py`.
- **Columna Parte + semi editable + bloqueo parte (27/07/2026):** la grilla CC muestra **Parte** (cantidad referencial del parte, sin restar clasificado). **Semi elaborado** es editable (docenas/pares, mismo patrón que 2da y scrap). Tope editable: `max_clasificable` = atribuible + extra pool (stock Producción). Validación: `semi + 2da + desperdicio ≤ max_clasificable`. POST sin claves `semi_*` (tests legacy): fallback `semi = max(0, atribuible − 2da − scrap)`. Filas 100 % clasificadas se muestran en solo lectura con desglose persistido. Si un turno tiene CC registrada para la fecha, el **parte** bloquea la edición de ese turno (UI + `ValidationError` en registro/ajustes). Para **corregir** Semi/2da/Desperdicio después de guardar: **Ingreso de movimiento de stock** → transferencia interna (no hay reverse en el pipeline MPR). Ref: `mpr/repositories/transicion_lote.py` (`turno_tiene_control_calidad`), `construir_grilla_clasificacion_produccion`, `parte_produccion.html`.
- **Semi sin precarga del parte (19/08/2026):** las celdas editables de Semi/2da/Scrap arrancan en **0**; el usuario completa celda por celda. El atribuible del parte sigue siendo el tope (`max_clasificable`) y se muestra en la columna Parte. Borrador y roster confirmado (solo lectura) siguen precargando `ini_*` con lo guardado. Buscador de artículo: store Alpine `clasificacionCc` (antes `$root.busqueda` no filtraba porque `$root` es el DOM) + lista predictiva de coincidencias. Ref: `construir_grilla_clasificacion_produccion`, `clasificacion_produccion.html`, `clasificacion_encabezado.html`.
- **Separador visual por máquina (27/07/2026):** en `clasificacion_produccion.html`, la primera fila de cada bloque de máquina (excepto la primera de la grilla) lleva borde superior `2px slate-400` (`clasif-inicio-maquina`). Las celdas Máq./Artículo con `rowspan` usan `align-top` para alinear el chip/nombre con la primera línea de turno del bloque.
- **Turnos y Pares en UI CC (27/07/2026):** columnas Turno/Operario/Parte con tinte suave por franja (`turno_franja`: mañana ámbar, tarde sky, noche violeta). Columna **Parte** en dos líneas (docenas / pares). Campos de carga y semi calculado etiquetan **Pares** (no «Unidades»); el POST sigue usando el sufijo `_unidades` por compatibilidad.
- **Extra producción en CC (27/07/2026):** si hay saldo en depósito **Producción** por encima del remanente atribuible del parte, la grilla permite clasificar ese extra (semi/2da/scrap) por operario. Tope por celda: `atribuible_parte + extra_pool_artículo`; el POST consume el pool secuencialmente (mismo orden que la grilla). Columna Parte muestra subtexto «+Nd Np extra» por artículo cuando aplica. Persistencia: `cantidad_extra` en `mpr_transicion_lote`. DDL: `mpr/sql/005_mpr_transicion_lote_cantidad_extra.sql`.
- **Borrador CC fase 1 (28/07/2026):** «Guardar borrador» persiste semi/2da/scrap en `mpr_clasificacion_borrador` / `_linea` **sin MSTOCK** ni filas en `mpr_transicion_lote`. Al volver a la pantalla, la grilla precarga `ini_*` desde el borrador. «Guardar control de calidad» ejecuta el flujo actual (transferencia + ledger) y elimina el borrador del turno. El borrador **no** cuenta como CC registrada: `turno_tiene_control_calidad` y lecturas equivalentes siguen solo en `mpr_transicion_lote`. No bloquea el parte. Tras confirmar, correcciones vía movimiento de stock (sin delta post-CC en esta fase). **Feedback (31/07/2026):** éxito/error de confirmación en modal `mprShowAviso` (mensaje corto, sin listar comprobantes ni toast). Ref: `mpr/repositories/clasificacion_borrador.py`, `RegistrarClasificacionProduccionView`, `006_mpr_clasificacion_borrador.sql`. Guía de usuario: [MANUAL_USUARIO_MPR.md](MANUAL_USUARIO_MPR.md) §5 (borrador vs confirmado) y §3 (Reserva / Urgente / Fabricando / ejemplo didáctico).
- **Descuento automático semi (29/07/2026; vigente con Semi en 0 desde 19/08/2026):** en `clasificacion_produccion.html`, Alpine `clasificacionFila` observa `seg2daUnidades + scrapUnidades` (sin `immediate`: no altera ceros iniciales ni borradores). Cada cambio aplica delta sobre el semi **actual** (`aplicarDescuentoOtros` → `asignarSemiDesdePares`); clamp a 0; si otros superan `max_clasificable`, semi = 0 y el getter `excede` marca la fila. No corre en solo lectura ni en init. Con Semi inicial en 0, el descuento solo opera si el usuario ya cargó Semi.
- **Chrome denso alineado a Parte (29/07/2026):** búsqueda y **Solo pendiente** / **Ver roster** viven en el encabezado oscuro (`clasificacion_encabezado.html`, una fila en desktop). Se eliminó la franja blanca de herramientas sobre la grilla. Viewport `100dvh-5.5rem` / md `7.5rem` con `-mt-4 md:-mt-8`; footer **Guardar borrador** + **Guardar control de calidad** `flex-shrink-0` siempre visible. Alpine página en el `section`. Ref: [TABLERO_PRODUCCION_CHROME_DENSIDAD.md](TABLERO_PRODUCCION_CHROME_DENSIDAD.md).
- **Rowspan artículo por máquina + tinte Máq. (29/07/2026):** el `rowspan` de Artículo ya no cruza de una máquina a otra (mismo `id_articulo` en Máq. 20 y 21 mostraba celda vacía). Columna Máq. con tinte/chip cíclico (`maquina_tint` 0–5) para referencia visual.
- **Modal de espera al guardar CC (29/07/2026):** «Guardar borrador» / «Guardar control de calidad» llaman `mprShowPostLoading` antes de `form.submit()` (el submit programático no dispara el listener global). Overlay `synap_post_loading_modal` vía `base_mpr.html`.
- **Solo pendiente vs roster + botones (29/07/2026; default roster 04/08/2026):** por defecto se muestra el **roster completo** (confirmadas en solo lectura + pendientes editables). «Solo pendiente» (`ver_roster=0`) filtra estrictamente filas editables (`not solo_lectura`). Flag `hay_filas_editables` deshabilita Guardar borrador / Guardar CC si no hay nada que guardar. Si el usuario está en solo pendiente y no hay editables pero sí CC confirmado, `confirmadas_ocultas` muestra aviso + CTA a Ver roster. **Ver roster** está disponible para todo usuario con acceso a CC (`mpr.ver`).
- **Roster completo preserva el CC confirmado (29/07/2026):** una fila con clasificación persistida se muestra en solo lectura con su desglose Semi / 2da / Scrap. La existencia de stock extra de Producción no debe reemplazar esa visualización por el remanente atribuible (cero); el extra se clasifica desde filas pendientes.
- **CC confirmado preservado en pendiente (29/07/2026):** la misma regla de solo lectura aplica sin activar «Ver roster»: si la celda agotó su atribuible del parte y tiene desglose confirmado, muestra Semi / 2da / Scrap persistidos aunque haya extra de Producción. El extra continúa disponible para las otras filas pendientes; la corrección post-CC sigue siendo por movimiento de stock.
- **Fix remanente fantasma multi-máquina + 2ª (29/07/2026):** al repartir clasificado (semi→2da→scrap) por máquina, cada destino consume **capacidad restante** de la máquina (`cap_rest`), no el `fab_maq` completo otra vez. El bug previo sobreasignaba la 1.ª máquina (semi+2da sobre el mismo tope) y dejaba filas posteriores con `atribuible` fantasma aunque `Σ cls = Σ fab` a nivel operario×turno; eso permitió un segundo guardado (+125 pares el 22/07 en administranet). Helper `_consumir_desglose_contra_capacidad_maquina` usado por `_atribuible_clasificacion_por_celda` y `_asignacion_clasificado_por_celda`. Test: `TestAtribuibleMultiMaquinaSegunda`.
- **Reversión datos 22/07 en administranet (29/07/2026):** se anularon mstocks 1727–1735, se revirtió `stock_deposito` (Semi→Producción, 125 pares) y se eliminaron `mpr_transicion_lote` ids 254–262 (usuario 1). Post-check: fab=cls=16.935, 172/172 celdas. Auditoría 22–29/07: único exceso consumado fue ese día; 23/24/27 estaban expuestos al bug pero sin segundo guardado.
