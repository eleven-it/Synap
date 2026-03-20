# Diagnóstico Demanda MPR

Comando para verificar por qué podrían no aparecer pedidos en la pantalla **Demanda** (Orden de Producción de Trabajo / ventana pack) o para revisar el estado de lista_produccion_detalle y lista_produccion_agrupada.

---

## Comportamiento de la vista Demanda

La vista **Demanda** (ventana pack) **lee lista_produccion_agrupada**: muestra artículos con `cantidad_pendiente_prod > 0` y `en_proceso_produccion = 'No'`.

- Esa tabla se alimenta con **actualizar_pedidos_produccion**, que se ejecuta **al cargar la página** (con los filtros de sesión o por defecto: mes actual) o al pulsar el botón **Actualizar**.
- El origen de Actualizar es la query de pedidos pendientes (comp_ped + stockp + articulo tipo_art_fab='Terminado', estado_pedido_opt en Pendiente/Parcial), con los **filtros de fecha y búsqueda** configurados en la pantalla.
- **pedidos_resumen** en la tabla se arma desde **lista_produccion_detalle** + comp_ped.

Por tanto, para que un artículo aparezca en Demanda:

1. Debe haber pedidos pendientes que lo incluyan (en el rango de fechas y búsqueda que tenga la pantalla).
2. Esos pedidos deben haber sido incorporados a lista_produccion_detalle y agrupada mediante Actualizar (automático al cargar o al pulsar Actualizar).

---

## Comando de diagnóstico

```bash
docker exec Synap_app python manage.py diagnosticar_demanda_mpr --base-empresa=administranet92
```

Opcionales (mismos criterios que los filtros de la pantalla):

- `--fecha-desde=YYYY-MM-DD` y `--fecha-hasta=YYYY-MM-DD`
- `--busqueda=texto` (filtro por NroCompBusq/NroComprobante)

El comando:

1. **Sección 1:** Ejecuta la query de **pedidos pendientes** (origen de actualizar_pedidos_produccion) y muestra cuántas filas devuelve y por artículo. Con los mismos filtros, Actualizar inserta/actualiza detalle y agrupada.
2. **Sección 2:** Indica cuántos pares (pedido, artículo) están ya en **lista_produccion_detalle**.
3. **Sección 3:** Muestra la agregación desde lista_produccion_detalle (en_proceso_produccion='No'), que Actualizar usa para escribir en agrupada.
4. **Sección 3b:** Artículos que están en pedidos pero no en la agregación de detalle (no aparecerán en Demanda hasta ejecutar Actualizar con filtros que los incluyan).
5. **Sección 4:** Estado actual de **lista_produccion_agrupada** (lo que la vista Demanda muestra: filas con pendiente > 0 y en_proceso='No').
6. **Sección 5:** Nombres de columnas en detalle/agrupada por si hay diferencias de mayúsculas.

**Conclusión:** Si la sección 1 tiene filas válidas pero la 3 o 4 están vacías, hay que cargar la página (o pulsar Actualizar) con el mismo rango de fechas/búsqueda para que se llenen detalle y agrupada. Si tras eso no se ven artículos, revisar filtros y base_empresa en sesión.

---

## Cuándo usar el diagnóstico

- La pantalla Demanda está vacía pero hay pedidos que deberían cumplir condiciones: ejecutar el comando con los **mismos filtros de fecha** (y búsqueda) que tiene la pantalla para ver si la query de origen (sección 1) devuelve filas y si detalle/agrupada se han actualizado (secciones 2–4).
- Revisar el estado de lista_produccion_detalle/agrupada tras pulsar Actualizar o antes de crear una OPT.
- Verificar que tipo_art_fab='Terminado' y estado_pedido_opt estén correctos en los datos.

---

## Referencias

- **Actualizar** ejecuta `actualizar_pedidos_produccion` (inserta/actualiza lista_produccion_detalle y lista_produccion_agrupada). La vista Demanda lee agrupada; al cargar la página también se ejecuta actualizar_pedidos_produccion con los filtros de sesión.
- Comando **inspeccionar_pedidos_pendientes_mpr** para revisar solo pedidos con estado_pedido_opt='Pendiente' y tipo_art_fab.
