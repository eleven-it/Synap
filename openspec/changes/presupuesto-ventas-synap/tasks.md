# Tareas: presupuesto-ventas-synap

Checklist de implementación para el capability **ventas-presupuesto**. Orden sugerido: dependencias arriba; ítems marcados **[paralelo]** pueden avanzar en otra rama o por otra persona.

**Referencias:** `docs/general/SPEC_PRESUPUESTO_VENTAS_SYNAP.md`, `specs/ventas-presupuesto/spec.md`, `design.md`, `DESIGN_PUNTO8_*`, `DESIGN_PUNTO10_*`, `DESIGN_PUNTO13_*`.

---

## 1. Arranque y permisos de menú

- [x] Registrar rutas del flujo PRE en `ventas/urls.py` (lista home, `nuevo/`, detalle por `codigo_movimiento`, prefijo coherente con el resto de `ventas`).
- [x] Añadir entradas de menú / permisos granulares según patrón existente (`core`, navbar `?tab=navbar`): clave estable documentada para “Presupuesto” / listado PRE.
- [x] Exponer flags `permisos_sistema` en vistas PRE (`presupuesto_permisos.contexto_ui_presupuesto` + detalle/lista/nuevo). Alta usa `carga_comp_ped` / supervisor en guardado (`_puede_emitir_presupuesto`).

---

## 2. Servicios MySQL — dominio PRE

- [x] Servicio `ventas/services/presupuesto_mysql.py`: listado, cabecera y **renglones** (`stockp`). Pendiente: alta/modificación/transacciones completas.
- [x] Servicio transaccional MVP alta PRE (`ventas/services/presupuesto_guardado.py`: `codmov`, talonario PRE, `comp_ped`, `stockp`). Pendiente: temporales, percepciones, talonario manual, modificaciones.
- [ ] Implementar **numeración** sistema (talonario) y **manual** con validación anti-duplicado alineada a `Validacion_Comp` del SPEC.
- [ ] Implementar **alta** de PRE: escritura `comp_ped`, líneas `stockp`, `cliente_datos_adicionales` cuando aplique; normalización con `core.utils.administranet_types`.
- [ ] Implementar **temporales** `cuerpostockpe` (y limpieza post-guardado por usuario) según SPEC.
- [ ] Implementar **modificación** desde consulta respetando `mod_item_pre_ped` y reconciliación `stockp` (sin filas huérfanas).
- [ ] Implementar **`modificacion_comp`** (solo fecha/número) con validación de período fiscal y actualización consistente `comp_ped` / `stockp`.
- [ ] Implementar **percepciones** (`percep_cli_temp` / `percep_cli`) cuando el alcance del sprint las incluya (misma entrega que núcleo si es posible).
- [ ] Aplicar validaciones **V1–V11** del SPEC; integrar **supervisor** / bypass igual que `ventas/views.py` / reports (`cod_usuario` vs `supervisor`).
- [ ] **No** escribir `erp_proyecto` ni lógica CRM; revisión estática de imports y queries.

---

## 3. API HTTP y listados

- [x] API **GET** JSON listado PRE y **GET** detalle por `codigo_movimiento` (`api_presupuesto_list`, `api_presupuesto_retrieve`).
- [x] Listado servidor PRE (`comp_ped` tipo PRE) con filtros y **paginación** (home lista HTML).
- [x] Endpoint **POST** alta PRE (`/ventas/api/presupuestos/crear/`). Pendiente **PATCH** modificación y contrato JSON completo §4–§5.
- [x] API búsqueda cliente (`get_clientes` + `/ventas/api/presupuestos/clientes/buscar/`). Pendiente: wire en formulario de guardado.

---

## 4. UI Django (patrón TPV / MPR)

- [x] Plantilla **lista**: estado, filtros, paginación, botón **Nuevo** (`DESIGN_PUNTO8`). Vistas en `ventas/views_presupuesto.py`.
- [x] Flujo **nuevo**: cabecera + **varios renglones** en UI + POST guardado (`presupuesto_nuevo.html`, `_construir_lineas_desde_post`). Pendiente: validaciones V1–V11 completas.
- [x] Flujo **detalle** lectura por `codigo_movimiento` (cabecera + tabla **renglones `stockp`**). Pendiente: edición según `mod_item_pre_ped` y ramas SPEC.
- [x] Acción exportar documento enlazada al reporte operational (`documento-presupuesto-ventas`, Excel desde detalle). PDF pendiente.
- [x] Mensajes y copy en español en plantillas actuales. Revisión accesibilidad pendiente con formularios de edición.

---

## 5. Módulo Reportes — PDF Presupuesto

- [x] Alta de **`ReportDefinition`** categoría **operational**, slug **`documento-presupuesto-ventas`** (migración `0032`).
- [x] Pipeline / runner que arma dataset desde `comp_ped`, `stockp`, cliente (`presupuesto_ventas_runner`).
- [ ] Respetar permiso **`plantillas`** y variantes vía `config` + payload (`DESIGN_PUNTO10`) — una sola variante Excel en v1.
- [x] Documentar slug y ejemplo de payload en `docs/reports/DOCUMENTO_PRESUPUESTO_VENTAS_REPORT.md` y SPEC §9.5.

---

## 6. Tests

- [ ] Tests unitarios de validadores críticos (descuentos, duplicados manual, límites).
- [ ] Tests de integración MySQL (si hay BD de prueba): un flujo alta + una modificación mínima; asserts sobre filas `comp_ped`/`stockp`.
- [ ] Tests API HTTP listado/filtros donde aplique.

---

## 7. Documentación y cierre

- [x] Actualizar `docs/general/SPEC_PRESUPUESTO_VENTAS_SYNAP.md` y `docs/reports/` según cambios visibles (POLITICA_DOCUMENTACION).
- [ ] Completar matriz payload JSON §4–§5 en SPEC o anexo si quedó pendiente.
- [ ] Revisión cruzada con `INVENTARIO_PRESUPUESTO_VENTAS_ADMINISTRANET_VB6.md` para brechas.

---

## 8. [Paralelo / otro repositorio] Plataforma de licencias

No bloquea el núcleo PRE si no hay servicio en producción aún.

- [ ] Repositorio aparte: API de licencia + panel admin (`docs/general/SERVICIO_LICENCIAS_PROYECTO_SEPARADO.md`).
- [ ] Contrato OpenAPI v1 y registro de `installation_id`.
- [ ] En Synap (cuando se integre): settings + job de renovación + middleware según `DESIGN_PUNTO13`.

---

## Estado

Marcar ítems en este archivo conforme avance el equipo; al cerrar el cambio OpenSpec, **verify** contra `specs/ventas-presupuesto/spec.md`.
