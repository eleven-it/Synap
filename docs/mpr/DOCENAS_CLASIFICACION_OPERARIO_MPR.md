# Docenas operativas y clasificación por operario fabricante (MPR)

**Change OpenSpec:** `openspec/changes/mpr-docenas-clasificacion-operario/`  
**Estado:** Implementado en Desarrollo — aplicar migración MySQL en cada base empresa.  
**Fecha:** 08/07/2026

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

| Tema | Decisión |
|------|----------|
| Default presentación | Docenas en flujo operativo |
| Toggle | Sesión `mpr_presentacion_cantidad` |
| Divisor componentes | 12 u./docena |
| Filas clasificación | (máquina × artículo × turno × operario), pendiente > 0 o ya clasificadas (roster completo) |
| Alcance pendiente | Fecha obligatoria; turno opcional (vacío = todos los turnos del día) |
| Columnas grilla CC | Máquina, Artículo, Turno, Operario, **Parte** (referencial, fab. del parte), Semi, 2da, Scrap |
| Semi elaborado | Editable (docenas/pares). Precarga = remanente **atribuible del Parte** (no incluye extra). Tope fila = `max_clasificable` = atribuible + extra pool. **Descuento automático UI:** al cambiar 2da o Desperdicio, se descuenta el **delta** (en pares) del semi actual; semi sigue editable a mano; si `2da + desperdicio > max_clasificable` → semi = 0 y fila en error (`excede`) |
| Extra producción (CC) | `max(0, stock Producción − Σ atribuible_parte)` por artículo; tope fila = atribuible + extra pool; consumo secuencial en POST |
| Edición CC | **Semi elaborado**, **2da selección** y **Desperdicio** editables hasta `max_clasificable` |
| Validación CC | `semi + 2da + desperdicio ≤ max_clasificable` (UI Alpine + servidor); guarda física: Σ clasificado ≤ saldo vivo Prod |
| Solo lectura CC | Cuando `max_clasificable ≤ 0` **o** la celda tiene CC confirmada y agotó su atribuible del parte (`asignado_total > 0` y `atribuible ≤ 0`), sin depender de Ver roster. UI: mismos casilleros docenas/pares, en solo lectura (sin POST). |
| Persistencia extra | `mpr_transicion_lote.cantidad_extra` por ítem (semi/2da/scrap), reparto secuencial del extra de la celda |
| Bloqueo parte | Si un turno tiene CC en `mpr_transicion_lote` (fecha+turno), ese turno del parte queda bloqueado |
| Corrección post-CC | No se edita ni se revierte en la grilla CC. Reclasificar Semi/2da/Desperdicio vía **Ingreso de movimiento de stock** → transferencia interna (AdministraNET) |
| Clasificación parcial | Sí |
| Parte sin operario | Bloquear clasificación por rendimiento |
| Reportes | Mismo release que la grilla |
| Ledger | `id_operario` = fabricante; `id_usuario` = quien guardó |

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
- **Columna Parte + semi editable + bloqueo parte (27/07/2026):** la grilla CC muestra **Parte** (cantidad referencial del parte, sin restar clasificado). **Semi elaborado** es editable (docenas/pares, mismo patrón que 2da y scrap): precarga con el remanente **atribuible del Parte** (no Parte+extra); el tope editable es `max_clasificable` = atribuible + extra pool (stock Producción). Validación: `semi + 2da + desperdicio ≤ max_clasificable`. POST sin claves `semi_*` (tests legacy): fallback `semi = max(0, atribuible − 2da − scrap)`. Filas 100 % clasificadas se muestran en solo lectura con desglose persistido. Si un turno tiene CC registrada para la fecha, el **parte** bloquea la edición de ese turno (UI + `ValidationError` en registro/ajustes). Para **corregir** Semi/2da/Desperdicio después de guardar: **Ingreso de movimiento de stock** → transferencia interna (no hay reverse en el pipeline MPR). Ref: `mpr/repositories/transicion_lote.py` (`turno_tiene_control_calidad`), `construir_grilla_clasificacion_produccion`, `parte_produccion.html`.
- **Separador visual por máquina (27/07/2026):** en `clasificacion_produccion.html`, la primera fila de cada bloque de máquina (excepto la primera de la grilla) lleva borde superior `2px slate-400` (`clasif-inicio-maquina`). Las celdas Máq./Artículo con `rowspan` usan `align-top` para alinear el chip/nombre con la primera línea de turno del bloque.
- **Turnos y Pares en UI CC (27/07/2026):** columnas Turno/Operario/Parte con tinte suave por franja (`turno_franja`: mañana ámbar, tarde sky, noche violeta). Columna **Parte** en dos líneas (docenas / pares). Campos de carga y semi calculado etiquetan **Pares** (no «Unidades»); el POST sigue usando el sufijo `_unidades` por compatibilidad.
- **Extra producción en CC (27/07/2026):** si hay saldo en depósito **Producción** por encima del remanente atribuible del parte, la grilla permite clasificar ese extra (semi/2da/scrap) por operario. Tope por celda: `atribuible_parte + extra_pool_artículo`; el POST consume el pool secuencialmente (mismo orden que la grilla). Columna Parte muestra subtexto «+Nd Np extra» por artículo cuando aplica. Persistencia: `cantidad_extra` en `mpr_transicion_lote`. DDL: `mpr/sql/005_mpr_transicion_lote_cantidad_extra.sql`.
- **Borrador CC fase 1 (28/07/2026):** «Guardar borrador» persiste semi/2da/scrap en `mpr_clasificacion_borrador` / `_linea` **sin MSTOCK** ni filas en `mpr_transicion_lote`. Al volver a la pantalla, la grilla precarga `ini_*` desde el borrador. «Guardar control de calidad» ejecuta el flujo actual (transferencia + ledger) y elimina el borrador del turno. El borrador **no** cuenta como CC registrada: `turno_tiene_control_calidad` y lecturas equivalentes siguen solo en `mpr_transicion_lote`. No bloquea el parte. Tras confirmar, correcciones vía movimiento de stock (sin delta post-CC en esta fase). Ref: `mpr/repositories/clasificacion_borrador.py`, `RegistrarClasificacionProduccionView`, `006_mpr_clasificacion_borrador.sql`. Guía de usuario: [MANUAL_USUARIO_MPR.md](MANUAL_USUARIO_MPR.md) §5 (borrador vs confirmado) y §3 (Reserva / Urgente / Fabricando / ejemplo didáctico).
- **Descuento automático semi (29/07/2026):** en `clasificacion_produccion.html`, Alpine `clasificacionFila` observa `seg2daUnidades + scrapUnidades` (sin `immediate`: no altera la precarga ni borradores). Cada cambio aplica delta sobre el semi **actual** (`aplicarDescuentoOtros` → `asignarSemiDesdePares`); clamp a 0; si otros superan `max_clasificable`, semi = 0 y el getter `excede` marca la fila. No corre en solo lectura ni en init.
- **Chrome denso alineado a Parte (29/07/2026):** búsqueda y **Solo pendiente** / **Ver roster** viven en el encabezado oscuro (`clasificacion_encabezado.html`, una fila en desktop). Se eliminó la franja blanca de herramientas sobre la grilla. Viewport `100dvh-5.5rem` / md `7.5rem` con `-mt-4 md:-mt-8`; footer **Guardar borrador** + **Guardar control de calidad** `flex-shrink-0` siempre visible. Alpine página en el `section`. Ref: [TABLERO_PRODUCCION_CHROME_DENSIDAD.md](TABLERO_PRODUCCION_CHROME_DENSIDAD.md).
- **Rowspan artículo por máquina + tinte Máq. (29/07/2026):** el `rowspan` de Artículo ya no cruza de una máquina a otra (mismo `id_articulo` en Máq. 20 y 21 mostraba celda vacía). Columna Máq. con tinte/chip cíclico (`maquina_tint` 0–5) para referencia visual.
- **Modal de espera al guardar CC (29/07/2026):** «Guardar borrador» / «Guardar control de calidad» llaman `mprShowPostLoading` antes de `form.submit()` (el submit programático no dispara el listener global). Overlay `synap_post_loading_modal` vía `base_mpr.html`.
- **Solo pendiente vs roster + botones (29/07/2026):** «Solo pendiente» filtra estrictamente filas editables (`not solo_lectura`); las confirmadas solo aparecen con **Ver roster**. Flag `hay_filas_editables` deshabilita Guardar borrador / Guardar CC si no hay nada que guardar. Si no hay pendientes pero sí CC confirmado, `confirmadas_ocultas` muestra aviso + CTA a Ver roster (no confundir con «sin datos»). **Ver roster** está disponible para todo usuario con acceso a CC (`mpr.ver`); ya no exige rol supervisor / anular envíos.
- **Roster completo preserva el CC confirmado (29/07/2026):** una fila con clasificación persistida se muestra en solo lectura con su desglose Semi / 2da / Scrap. La existencia de stock extra de Producción no debe reemplazar esa visualización por el remanente atribuible (cero); el extra se clasifica desde filas pendientes.
- **CC confirmado preservado en pendiente (29/07/2026):** la misma regla de solo lectura aplica sin activar «Ver roster»: si la celda agotó su atribuible del parte y tiene desglose confirmado, muestra Semi / 2da / Scrap persistidos aunque haya extra de Producción. El extra continúa disponible para las otras filas pendientes; la corrección post-CC sigue siendo por movimiento de stock.
- **Fix remanente fantasma multi-máquina + 2ª (29/07/2026):** al repartir clasificado (semi→2da→scrap) por máquina, cada destino consume **capacidad restante** de la máquina (`cap_rest`), no el `fab_maq` completo otra vez. El bug previo sobreasignaba la 1.ª máquina (semi+2da sobre el mismo tope) y dejaba filas posteriores con `atribuible` fantasma aunque `Σ cls = Σ fab` a nivel operario×turno; eso permitió un segundo guardado (+125 pares el 22/07 en administranet). Helper `_consumir_desglose_contra_capacidad_maquina` usado por `_atribuible_clasificacion_por_celda` y `_asignacion_clasificado_por_celda`. Test: `TestAtribuibleMultiMaquinaSegunda`.
- **Reversión datos 22/07 en administranet (29/07/2026):** se anularon mstocks 1727–1735, se revirtió `stock_deposito` (Semi→Producción, 125 pares) y se eliminaron `mpr_transicion_lote` ids 254–262 (usuario 1). Post-check: fab=cls=16.935, 172/172 celdas. Auditoría 22–29/07: único exceso consumado fue ese día; 23/24/27 estaban expuestos al bug pero sin segundo guardado.
