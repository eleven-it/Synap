# Tareas: reconciliar demanda al Actualizar (ventana Pack / OPT)

**Especificación:** `SPEC_RECONCILIAR_DEMANDA_VENTANA_PACK_OPT.md`  
**Diseño:** `DESIGN_RECONCILIAR_DEMANDA_VENTANA_PACK_OPT.md`  
**Código principal:** `mpr/services.py` — `actualizar_pedidos_produccion`

**Estado:** núcleo implementado en código (`actualizar_pedidos_produccion`: UPSERT, DELETE huérfanos por alcance de pedidos del SELECT, paso agrupada sin SUM, helper `_mpr_en_proceso_detalle_es_si`). Pendiente: revisión manual ventana_pack (3.x), ampliar tests de mocks si se desea (4.2–4.3), manual de usuario (5.2) opcional.

---

## Fase 1: Preparación y contrato de datos

- [ ] **1.1** Construir en memoria (en la misma ejecución que `filas_origen`) el conjunto `clave_origen_ped = {(cod_ped, id_art) para cada fila del cursor con qty > 0}` para reutilizar en UPDATE y en DELETE de huérfanos (evitar segundos SELECT del mismo SQL si se puede derivar del mismo `fetchall`).

- [ ] **1.2** Definir helper local (o bloque claro) para normalizar `en_proceso_produccion` igual que el resto del archivo: `COALESCE(NULLIF(TRIM(en_proceso_produccion), ''), 'No')` vs `TRIM` ya usado en SUM — **una sola convención** con el GROUP BY existente.

- [ ] **1.3** Verificar columnas opcionales del INSERT detalle (`id_usuario`, etc.) y mantener los mismos ramas `1054` que el INSERT actual.

---

## Fase 2: Implementación en `actualizar_pedidos_produccion`

- [ ] **2.1 — Fase A (UPSERT)**  
  Sustituir el bucle que hace solo `SELECT 1` + `continue` + `INSERT` por:  
  - si no existe fila: **INSERT** (lógica actual).  
  - si existe: leer `cantidad_pedida`, `cantidad_pendiente_prod`, `en_proceso` (y `id_lista_produccion` si hace falta).  
  - si `en_proceso` ⇒ pendiente (`No`): calcular `fab = max(0, ped_old - pend_old)`, `ped_new = qty_origen`, `pend_new = max(0, qty_origen - fab)`; **UPDATE** ambas columnas.  
  - si `en_proceso` ⇒ `Si`: **no modificar**.

- [ ] **2.2 — Fase B (DELETE huérfanos)**  
  Tras procesar todas las filas de origen: **DELETE** desde `lista_produccion_detalle` donde pendiente, `codigo_movimiento_pedido <> 0`, y `(codigo_movimiento_pedido, id_articulo) NOT IN` el conjunto de claves del origen (o equivalente con anti-join en SQL si el conjunto es grande — medir en implementación).  
  **Nunca** borrar `codigo_movimiento_pedido = 0`.

- [ ] **2.3 — Fase C (reserva)**  
  Mantener llamada a `_sincronizar_demanda_reserva_lista_detalle` **después** de A y B; si el orden previo era antes del SUM, confirmar que la reserva sigue coherente tras DELETE PED (ajustar orden solo si un test lo demuestra necesario).

- [ ] **2.4 — Fase D (agrupada SUM)**  
  Conservar el bloque actual `GROUP BY id_articulo` + UPDATE/INSERT `lista_produccion_agrupada` + UPDATE detalle `id_lista_produccion` por artículo.

- [ ] **2.5 — Fase E (agrupada obsoleta)**  
  Tras Fase D, identificar filas de `lista_produccion_agrupada` con `en_proceso = 'No'` cuyo `id_articulo` **no** tiene fila en el resultado del SUM **o** queda con demanda solo mal reflejada; aplicar **UPDATE** a `cantidad_pedida = 0` y `cantidad_pendiente_prod = 0` (o DELETE de agrupada vacía según FKs) **sin** afectar artículos que el SUM aún alimenta por reserva.  
  Documentar en comentario breve el criterio elegido (UPDATE vs DELETE).

- [ ] **2.6** Ampliar el **docstring** de `actualizar_pedidos_produccion` con: reconciliación de cantidades, eliminación de huérfanos, fórmula de pendiente, y paso E.

- [ ] **2.7** Ajustar el **mensaje** de retorno si aplica (p. ej. mencionar sincronización de líneas existentes) sin romper aserciones de tests que buscan «demanda por reserva».

---

## Fase 3: Vistas y alcance de filtros (verificación)

- [ ] **3.1** Revisar `VentanaPackView` y `VentanaPackActualizarView` (`mpr/views.py`): que `fecha_desde`, `fecha_hasta` y `busqueda` pasados a `actualizar_pedidos_produccion` coincidan con el alcance esperado del usuario para reconciliar (mismo criterio que el SELECT origen).

- [ ] **3.2** Si `busqueda` no se envía en el POST de Actualizar pero sí está en sesión, confirmar que GET/subsecuente usa el mismo filtro (documentar hallazgo en comentario o doc si hay gap).

---

## Fase 4: Pruebas automatizadas

- [ ] **4.1** Ampliar `mpr/tests/test_actualizar_pedidos.py` con mocks del cursor/conexión que simulen:  
  - origen devuelve `(cod_ped, id_art, qty)` distinto a una fila detalle ya existente con `en_proceso` pendiente → esperar **UPDATE** con `pend_new` según fórmula.  
  - origen ya no incluye una pareja que estaba en detalle → esperar **DELETE** (o SQL que lo represente).

- [ ] **4.2** Test de regresión: fila `codigo_movimiento_pedido = 0` no debe aparecer en DELETE de huérfanos.

- [ ] **4.3** Test de regresión: fila con `en_proceso` equivalente a `Si` no recibe UPDATE desde el bucle de origen.

- [ ] **4.4** Ejecutar `docker exec Synap_app python manage.py test mpr.tests.test_actualizar_pedidos -v 2` y suite `mpr` si el tiempo lo permite.

---

## Fase 5: Documentación y cierre SDD

- [ ] **5.1** En `SPEC_RECONCILIAR_DEMANDA_VENTANA_PACK_OPT.md`, marcar estado de implementación o enlazar PR cuando exista.

- [ ] **5.2** Actualizar `MANUAL_USUARIO_MPR.md` o nota breve en `docs/mpr/README.md` si el manual describe «Actualizar» como solo altas nuevas.

- [ ] **5.3** (`sdd-verify`) Validar manualmente en ventana_pack: cambiar cantidad en PED en BD de prueba → Actualizar → totales y tooltips coherentes.

---

## Orden de dependencias

```
1.* → 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6 → 2.7 → 3.* → 4.* → 5.*
```

---

## Artefacto SDD (Engram)

Topic sugerido al cerrar fase: `sdd/mpr-opt-demanda-reconciliar/tasks`
