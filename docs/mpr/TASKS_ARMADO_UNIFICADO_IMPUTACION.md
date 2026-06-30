# Tareas — Armado unificado 1ra/2da e imputación supervisor

**Change:** `armado-unificado-imputacion-1ra`  
**Especificación:** [SPEC_ARMADO_UNIFICADO_IMPUTACION.md](SPEC_ARMADO_UNIFICADO_IMPUTACION.md)  
**Diseño:** [DESIGN_ARMADO_UNIFICADO_IMPUTACION.md](DESIGN_ARMADO_UNIFICADO_IMPUTACION.md)  
**SDD:** [SDD_ARMADO_UNIFICADO_IMPUTACION.md](SDD_ARMADO_UNIFICADO_IMPUTACION.md)  
**Código principal:** `mpr/models.py`, `mpr/services.py`, `mpr/views.py`, `mpr/templates/mpr/armado.html`

**Estado:** apply completado (pendiente verify en contenedor)

---

## Fase A — Fundación (modelos + servicios 1ra)

### A.1 Modelos Django

- [ ] **A.1.1** Añadir `MprArmadoLote` en `mpr/models.py` (UUID PK, `modo`, depósitos, contadores, `ejecutado_en`).

- [ ] **A.1.2** Extender `MprArmadoSurtidoMovimiento`:
  - renombrar a `MprArmadoMovimiento` (migración RenameModel o alias temporal);
  - campos `modo`, `id_lote_armado` FK, `estado_imputacion` (`pendiente`|`parcial`|`completo`|`na`).

- [ ] **A.1.3** Crear `MprImputacionArmado` (`codigo_movimiento`, `id_articulo_pack`, `cantidad`, `codigo_movimiento_pedido`, `origen_regla`, `id_usuario_supervisor`, `imputado_en`, `notas`).

- [ ] **A.1.4** Migraciones: schema + data migration `modo='2da'`, `estado_imputacion='na'` en filas existentes.

- [ ] **A.1.5** Admin Django: list_display filtros por `modo` y `estado_imputacion`.

### A.2 Servicios Armado 1ra

- [x] **A.2.1** `listar_packs_armado_1ra(base_empresa)` — JOIN único `articulo` + `en_abm` + `en_abm_formula` (sin N+1 por pack).

- [ ] **A.2.2** `calcular_max_packs_armado_1ra(base, id_pack, deposito_semi)` — adaptar lógica de `get_lineas_armado_opt` sin `id_lista`.

- [ ] **A.2.3** `validar_composicion_bom_1ra(base, id_pack, lineas_post)` — anti-tamper vs `en_abm_formula`.

- [ ] **A.2.4** Implementar `_ejecutar_armado_1ra_tx` en `mpr/services.py`:
  - validar pack BOM;
  - consumir componentes desde Semi;
  - entrada pack Terminado 1.ª;
  - historial OPA sin `id_lista` obligatorio;
  - retornar `info_pack` para modal.

- [ ] **A.2.5** Tests unitarios `_ejecutar_armado_1ra_tx` y validación BOM en `mpr/tests/test_armado_unificado_lote_1ra.py`.

### A.3 Orquestador unificado

- [ ] **A.3.1** Renombrar/generalizar `ejecutar_lote_armado_surtido` → `ejecutar_lote_armado(..., modo)`:
  - `modo=2da` → `_ejecutar_armado_surtido_tx`;
  - `modo=1ra` → `_ejecutar_armado_1ra_tx`;
  - crear `MprArmadoLote` al inicio; vincular movimientos exitosos.

- [ ] **A.3.2** Extender `validar_reglas_lote_armado_surtido` → `validar_reglas_lote_armado`:
  - validar `modo` coherente con origen/destino;
  - reglas pack 1ra vs 2da;
  - mantener límite 20, duplicados, cruce pack-componente.

- [ ] **A.3.3** Extender `parse_lote_armado_surtido_post` con campo `modo` obligatorio.

- [ ] **A.3.4** Tras éxito 1ra: `estado_imputacion='pendiente'` en `MprArmadoMovimiento`.

- [ ] **A.3.5** Tests orquestador en `mpr/tests/test_armado_unificado_modo.py` (AC-A2, AC-A3).

---

## Fase B — Vista unificada y wiring

### B.1 Rutas y vistas

- [ ] **B.1.1** Crear `ArmadoView` en `mpr/views.py` (reemplaza/evoluciona `ArmadoSurtidoView`):
  - GET: `modo` query param default `1ra` (redirect si falta); alias `armado-surtido` → `modo=2da`;
  - context: catálogo packs según modo, depósitos default, URLs API.

- [ ] **B.1.2** Registrar en `mpr/urls.py`:
  - `path("armado/", ArmadoView, name="armado")`;
  - mantener alias `armado-surtido` → redirect `armado?modo=2da`;
  - `path("opt/<int:id_lista>/armado/", redirect armado?modo=1ra)`.

- [ ] **B.1.3** Eliminar llamadas `opt_puede_armado_surtido` en GET/POST armado.

- [x] **B.1.4** Menú MPR: un ítem **Armado** (`mpr:armado`); modos 1ra/2da en pantalla. Imputación 1ra aparte (supervisor).

### B.2 Template `armado.html`

- [ ] **B.2.1** Copiar/evolucionar `armado_surtido.html` → `armado.html`:
  - segmented control «Armado 1ra» | «Armado 2da»;
  - títulos y copy según P6 naming.

- [ ] **B.2.2** Alpine: prop `modo`; watcher cambio modo → confirm + vaciar carrito.

- [ ] **B.2.3** Modo 1ra: ocultar búsqueda libre componentes; tabla BOM read-only; precargar al elegir pack.

- [ ] **B.2.4** Modo 2da: paridad comportamiento actual.

- [ ] **B.2.5** Hidden `modo` en POST / `lote_json`.

- [ ] **B.2.6** Reutilizar `armado_surtido_modal_resultado_lote.html` (renombrar include genérico si aplica).

### B.3 Deprecación OPT

- [ ] **B.3.1** `opt_detail.html`: eliminar bloque `mostrar_tarjeta_armado_surtido` y tarjetas armado BOM.

- [ ] **B.3.2** `wizard.html` paso 4: reemplazar formulario armado por card enlace «Ir a Armado 1ra».

- [x] **B.3.3** `estado_acciones_opt_bulk` en tablero/opt_list (elimina N+1); cierre solo pendiente OPP.

- [ ] **B.3.4** Deprecar `ArmadoOptView` (clase vacía redirect o eliminar tras alias URL).

- [ ] **B.3.5** Test views: redirect legacy, GET armado sin `id_lista` (AC-A1, AC-A5).

---

## Fase C — Imputación supervisor

### C.1 Servicios imputación

- [ ] **C.1.1** `listar_mstock_pendientes_imputacion(base, filtros)` — JOIN Synap + legacy; excluir 2da.

- [ ] **C.1.2** `sugerir_imputacion_fifo(base, codigo_movimiento)` — demanda abierta mismo `id_articulo`.

- [ ] **C.1.3** `confirmar_imputacion_armado(base, codigo_mov, lineas, id_supervisor)`:
  - validar Σ ≤ cantidad armada;
  - INSERT `MprImputacionArmado`;
  - UPDATE `lista_produccion_detalle` / agrupada;
  - actualizar `estado_imputacion` movimiento;
  - `_actualizar_comp_ped_estado_produccion` si aplica.

- [ ] **C.1.4** Tests `mpr/tests/test_imputacion_armado_1ra.py` (AC-B1…B5).

### C.2 Vista imputación

- [ ] **C.2.1** `ImputacionArmado1raView` GET: filtros + lotes recientes + MSTOCK pendientes agrupados.

- [ ] **C.2.2** POST confirmar imputación (single y multi-línea mismo MSTOCK).

- [ ] **C.2.3** Permiso `mpr.imputar_armado_1ra` — mixin/decorador; 403 sin permiso.

- [ ] **C.2.4** Template `imputacion_armado_1ra.html` — UI canon MPR.

- [ ] **C.2.5** Ruta menú supervisor «Imputación armado 1ra» (visible solo con permiso).

---

## Fase D — OPT/reportes y docs

### D.1 Tablero (opcional P1)

- [ ] **D.1.1** KPI tablero MPR: contador MSTOCK 1ra sin imputar (si producto confirma fase).

### D.2 Documentación

- [ ] **D.2.1** Actualizar [MANUAL_USUARIO_MPR.md](MANUAL_USUARIO_MPR.md): flujos Armado 1ra/2da, imputación, OPT sin armado.

- [ ] **D.2.2** Actualizar [FUENTE_VERDAD_UI_REPORTES_MPR.md](../general/FUENTE_VERDAD_UI_REPORTES_MPR.md): `/mpr/armado/`, `/mpr/imputacion-armado-1ra/`.

- [ ] **D.2.3** Marcar tareas completadas en este archivo y estado SDD tras verify.

---

## Verificación (post-apply)

- [ ] **V.1** `docker exec Synap_app python manage.py test mpr.tests.test_armado_surtido mpr.tests.test_armado_surtido_lote` — sin regresión 2da.

- [ ] **V.2** Suite nueva armado unificado + imputación.

- [ ] **V.3** QA manual AC-A1…A6, AC-B1…B5, AC-C1…C2 (checklist SDD §9).

- [ ] **V.4** Staging: operario arma 2da sin OPT; supervisor imputa 1ra piloto.

---

## Orden de implementación recomendado

```text
A.1 → A.2 → A.3 → B.1 → B.2 → B.3 → [deploy staging Fase A]
→ C.1 → C.2 → D.2 → V.*
```

**Dependencia crítica:** A.2.4 (`_ejecutar_armado_1ra_tx`) antes de B.2.3 (UI 1ra).

**Paralelizable:** C.1 puede iniciarse tras A.1; C.2 requiere C.1 + al menos un MSTOCK 1ra de prueba.

---

## Performance MPR (auditoría jun/2026)

| Cambio | Archivos | Estado |
|--------|----------|--------|
| `estado_acciones_opt_bulk` (tablero / opt_list) | `services.py`, `views.py` | Hecho |
| `listar_packs_armado_1ra` JOIN único + `_first_column_value` | `services.py` | Hecho |
| `bulk_componentes_a_equivalentes_pack` (detalle OPT / armado legacy) | `services.py`, `views.py` | Hecho |
| `get_op_detalle_bulk` (OPT agrupada) | `services.py` | Hecho |
| KPI tablero: `contar_pedidos_fabrica`, `contar_opt_atrasadas_distintas`, `listar_opt_atrasadas_tablero` | `services.py`, `views.py` | Hecho |
| Wizard agrupar: `obtener_pp_ped_y_stock_pack_por_articulos` (P_ped + stock en vivo, sin ventana completa) | `services.py`, `views.py` | Hecho |
| P0 parcial: `listar_ventana_pack(modo_ligero=True)` en tablero (sin BOM/tooltips/pedidos) | `services.py`, `views.py` | Hecho |
| P2: catálogo armado lazy API (`api/armado/packs-catalog/`) | `services.py`, `views.py`, `armado_surtido.html` | Hecho |
| P2: `obtener_renglones_movimiento_bulk` (modal/PDF OPT) | `administranet_stock.py`, `views.py` | Hecho |
| P2: cache por request `get_depositos_con_suma_stock` (`mpr/request_scope_cache.py` + middleware) | `services.py`, `request_scope_cache.py`, `request_scoped_mysql.py` | Hecho |
| P0: `listar_ventana_pack` optimizado (1 cursor, GROUP BY SQL, enriquecer solo filas con brecha) | `services.py` | Hecho |

Tests: `mpr.tests.test_mpr_performance_bulk`, `test_estado_acciones_opt_bulk`, `test_armado_1ra_catalog`.

---

## Siguiente paso

`/sdd-apply armado-unificado-imputacion-1ra` — comenzar por **A.1.1**.
