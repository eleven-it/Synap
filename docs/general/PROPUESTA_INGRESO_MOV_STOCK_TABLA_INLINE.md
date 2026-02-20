# Propuesta: Ingreso Mov. Stock – Entrada en tabla (inline) y Serie

**Objetivo:** Refactorizar el formulario de Ingreso de Movimiento de Stock para que la búsqueda de artículo e ingreso del movimiento se realicen **directamente en la tabla**, con edición y eliminación por línea, y definir el alcance de la funcionalidad **Serie** según AdministraNET.

**Estado:** Propuesta para revisión (sin implementación aún).

---

## 1. Situación actual

- **Bloque “Agregar ítem”** separado: combobox de artículo con búsqueda predictiva, cantidad, Entrada/Salida y botón “Agregar a la lista”.
- **Tabla “Renglones”**: solo lectura; muestra Código, Descripción, Cantidad, E/S y acción “Quitar”.
- No hay **edición** de un renglón ya agregado (en VB6 existe `ModificarRenglon_Click`: carga el renglón en los controles para editar).
- **Serie**: en VB6 está soportada (serie_entrada_temp / serie_salida_temp, GuardarSerie, ValCantSerie); en Synap no hay UI ni persistencia de series en el alta.

---

## 2. Comportamiento objetivo (UX)

### 2.1 Entrada directa en la tabla

- **Una sola sección “Renglones”** (sin bloque “Agregar ítem” aparte).
- La tabla tiene:
  - **Filas de renglones ya guardados**: muestran artículo (código/descripción), cantidad, tipo (Entrada/Salida) y **acciones**: Editar, Quitar.
  - **Una fila “Nueva línea”** (siempre visible, al final o debajo de la última línea recién creada según se defina).
- En la **fila “Nueva línea”** el usuario:
  - Elige artículo (dropdown con búsqueda predictiva).
  - Ingresa cantidad.
  - Elige Entrada o Salida.
  - Confirma con “Agregar” (o Enter).
- **Al agregar**:
  - Se persiste el renglón vía API (como hoy).
  - La fila recién creada pasa a ser una fila “normal” con Editar / Quitar.
  - **Debajo** de esa fila se muestra de nuevo la “Nueva línea” (o una única “Nueva línea” al final de la tabla; ver opciones más abajo).
- **Edición**: en cada renglón existente, “Editar” pone esa fila en **modo edición inline** (mismos controles: artículo, cantidad, E/S). “Guardar” actualiza el renglón; “Cancelar” vuelve a modo solo lectura.
- **Eliminado**: “Quitar” elimina el renglón del temporal (como hoy) y se actualiza la tabla.

### 2.2 Opciones de colocación de “Nueva línea”

| Opción | Descripción | Pros / contras |
|--------|-------------|-----------------|
| **A** | Una sola fila “Nueva línea” **al final** de la tabla | Implementación simple; flujo claro. No permite “insertar” entre líneas. |
| **B** | Botón “Agregar nueva línea” **debajo de cada fila** | Permite insertar entre líneas; más fiel a “debajo de la recién creada”. Implica definir orden (renumerar Órdenes o usar decimales). |

**Recomendación:** Opción **A** para la primera iteración: una única fila “Nueva línea” al final. Si más adelante se pide insertar entre líneas, se puede añadir “Insertar línea debajo” que llame a una API que inserte con un Orden dado y reordene (o usar campo Orden decimal).

---

## 3. Cambios técnicos necesarios

### 3.1 Backend (servicio y API)

- **Nueva función** en `core/services/administranet_stock.py`:
  - `actualizar_renglon_temporal(base_empresa, id_usuario, orden, datos)`  
  - `UPDATE cuerpostock_mstock SET IDArt=..., CodigoArticulo=..., Descripcion=..., Cantidad=..., entrada=..., salida=..., ES=..., ... WHERE CodUsuario=%s AND Orden=%s` (y mismo filtro visualiza/CodigoMovimiento si aplica).
- **Nuevo endpoint** en `stock/api_views.py`:
  - `PUT` o `PATCH` `/stock/api/ingreso/renglones/<orden>/` (o `.../update/`)  
  - Body: mismo que el POST de agregar (IDArt, CodigoArticulo, Descripcion, Cantidad, ES, CodDeposito, cod_deposito_destino).  
  - Respuesta: `{ "ok": true, "renglones": [...] }` (lista actualizada).

No es estrictamente necesario cambiar la lógica de `agregar_renglon_temporal` ni de `quitar_renglon_temporal`.

### 3.2 Frontend (plantilla + Alpine.js)

- **Eliminar** el bloque “Agregar ítem” actual (sección con combobox, cantidad, E/S y botón).
- **Tabla única “Renglones”**:
  - **Cabecera:** Código, Descripción, Cantidad, E/S, Acciones.
  - **Filas de datos:** `x-for="r in renglones"`; cada fila en modo “lectura” muestra texto y botones Editar / Quitar.
  - **Fila “Nueva línea”:** una fila fija al final con:
    - Celda artículo: mismo combobox con búsqueda predictiva (por fila, o un solo combobox compartido para la nueva línea).
    - Celda cantidad: input numérico.
    - Celda E/S: select Entrada/Salida.
    - Celda acciones: botón “Agregar” (y opcionalmente indicador de saldo si E/S = Salida).
  - **Modo edición:** cuando `renglonEditando === r.Orden`, esa fila muestra inputs/select en lugar de texto y botones “Guardar” / “Cancelar”; al guardar se llama al nuevo endpoint de actualización y se sale del modo edición.
- Estado Alpine: mantener `renglones`, `cabecera`, mensajes; añadir `renglonEditando: null` (Orden de la fila en edición, o null). Para la nueva línea: mismo patrón que hoy (`nuevoRenglon`, `busquedaArt`, `sugerencias`) pero acoplados a la fila nueva (una sola “nueva línea” al final).
- **Saldo disponible:** si en la nueva línea (o en la fila en edición) el tipo es Salida, se puede seguir mostrando “Saldo disponible: X” debajo del input cantidad o en una celda auxiliar, usando la API actual de saldo.

---

## 4. Funcionalidad “Serie” (VB6 y Synap)

### 4.1 En AdministraNET (VB6)

- **Tablas:** `serie_entrada_temp`, `serie_salida_temp` (por usuario, tipo `'Mstock'`); `serie_entrada`, `serie_salida` (definitivas). En `cuerpostock_mstock` hay columnas `serie`, `desc_serie`, `id_serie_entrada`.
- **Flujo:** Si el artículo usa serie (`EsSerie` / `articulo.serie`):
  - Al agregar/editar renglón se exige que la **cantidad** coincida con la **cantidad de números de serie** cargados (ValCantSerie, ESerie).
  - Los números de serie se cargan en temporales (`serie_entrada_temp` / `serie_salida_temp`) vinculados al renglón (usuario, orden, tipo Mstock).
  - En **Aceptar** (confirmar movimiento): `GuardarSerie` graba desde los temporales a `serie_entrada` / `serie_salida` y se asocian al movimiento/renglón.
- **Formularios:** Serie_carga.frm, Serie_salida.frm, Serie_fstock_visualiza.frm; en CargaMovStock se abren o se usan para cargar/validar series por renglón.

### 4.2 En Synap hoy

- **Servicio:** El INSERT en `cuerpostock_mstock` no incluye `serie`, `desc_serie`, `id_serie_entrada`. No se escriben `serie_entrada_temp` ni `serie_salida_temp`. En `alta_movimiento` no se llama a ninguna lógica tipo GuardarSerie.
- **UI:** No hay selector ni carga de números de serie en el ingreso de movimiento.

### 4.3 Propuesta para Serie (alcance y fases)

- **Fase “Tabla inline” (esta propuesta):** No implementar Serie aún; dejar el modelo de datos y APIs listos para que un renglón pueda llevar serie en el futuro (el backend ya puede aceptar campos opcionales si se extiende el INSERT/UPDATE).
- **Fase “Serie” (siguiente):**
  1. **Detección:** Consultar si el artículo usa serie (p. ej. campo `serie` en tabla `articulo` o en respuesta de `buscar_articulos`).
  2. **UI por renglón:** Si el artículo tiene serie:
     - En “Nueva línea” o al “Editar”, si cantidad > 0 y E/S definido: mostrar botón “Cargar series” o un bloque inline que permita ingresar N números de serie (N = cantidad).
     - Validación: cantidad de series ingresadas = cantidad del renglón (como ValCantSerie en VB6).
  3. **Persistencia:** Al agregar/actualizar renglón, guardar en `serie_entrada_temp` o `serie_salida_temp` (según E/S) vinculado a CodUsuario, Orden, tipo 'Mstock'. Opcionalmente rellenar `serie` / `desc_serie` en `cuerpostock_mstock` si la BD lo usa para visualización.
  4. **Confirmar movimiento:** En `alta_movimiento`, después de escribir `stock` y `movimiento_stock`, ejecutar lógica tipo GuardarSerie: leer temporales del usuario para este “movimiento” (renglones del temporal), insertar en `serie_entrada` / `serie_salida` y asociar a los IDs de stock/movimiento generados; luego borrar los temporales de serie del usuario.

Incluir en la documentación del módulo Stock que la funcionalidad Serie se implementará en una fase posterior y que el diseño de la tabla inline no debe obstaculizar añadir después la columna/control “Serie” por renglón.

---

## 5. Resumen de la propuesta

| Tema | Propuesta |
|------|-----------|
| **Entrada en tabla** | Una sola tabla “Renglones”: filas existentes (lectura + Editar / Quitar) + una fila “Nueva línea” al final con artículo (combobox búsqueda), cantidad y E/S. Al agregar, la nueva línea se convierte en fila normal y se mantiene una única “Nueva línea” al final. |
| **Edición** | Botón “Editar” por renglón: la fila pasa a modo edición inline (mismos controles que la nueva línea). “Guardar” llama a nuevo endpoint de actualización; “Cancelar” vuelve a modo lectura. |
| **Eliminado** | Sin cambios: “Quitar” llama al endpoint actual de remove y se refresca la lista. |
| **API** | Añadir `actualizar_renglon_temporal` en el servicio y endpoint `PUT/PATCH .../renglones/<orden>/` para actualizar un renglón por Orden. |
| **Serie** | No implementar en este refactor. Dejar documentada la estrategia (detección por artículo, temporales, GuardarSerie en confirmar) para una fase siguiente; el diseño de la tabla inline debe permitir añadir después la carga de series por renglón. |

---

## 6. Columnas del grid AdministraNET y estrategia tabla vs modal

### 6.1 Qué muestra el grid en CargaMovStock (VB6)

El grid **GridArticulos** está enlazado a **CuerpoStock** (tabla temporal `cuerpostock_mstock`). En el .frm están definidas **18 columnas** (índice 0..17). La visibilidad y el orden de cada una se configuran por puesto en `conf_grilla_final_puesto` (nombre_grilla = `'Grilla Mov Stock'`), por lo que cada puesto puede ver un subconjunto distinto.

Columnas definidas en el formulario (Caption → DataField):

| Índice | Caption / columna en VB6   | DataField (cuerpostock_mstock) |
|--------|----------------------------|---------------------------------|
| 0      | Cod. Sistema                | IDArt |
| 1      | Cod. Manual                | id_manual |
| 2      | Descripcion                 | Descripcion |
| 3      | E/S                         | ES |
| 4      | Cantidad                    | Cantidad |
| 5      | Saldo                       | CantidadOr |
| 6      | Nro Pedido Int.             | nro_pedi |
| 7      | Lote                        | cod_lote |
| 8      | Vto Lote                    | vto_lote |
| 9      | Pres. V                     | multiplicador_vta |
| 10     | Pres. C                     | cantidad_uni |
| 11     | Marca                       | marca |
| 12     | P. costo x U                | PrecioCostoxU |
| 13     | P. costo x R                | PrecioCostoxR |
| 14     | Embalaje                    | tipo_unidad |
| 15     | Unidad                      | unidad_art_peso |
| 16     | Cantidad armada             | cantidad_armada_opt |
| 17     | Artículo pedido armado      | nombre_articulo_armado |

Además, la tabla `cuerpostock_mstock` tiene muchas más columnas (CodigoArticulo, CodDeposito, cod_deposito_destino, entrada, salida, serie, desc_serie, etc.) que el grid puede no mostrar pero que existen en el Recordset.

### 6.2 Impacto en UX si se mostraran todas en la tabla web

Mostrar 10–18 columnas en una tabla web:

- Obliga a scroll horizontal en pantallas normales.
- Dificulta identificar de un vistazo “qué línea es” (artículo + cantidad + E/S).
- Sobrecarga la vista en móvil/tablet.

### 6.3 Propuesta: tabla mínima + “Más detalles” en modal

- **En la tabla (sección “Artículos”)**: mostrar solo lo **necesario para identificar la línea** y actuar sobre ella:
  - **Código** (CodigoArticulo o id_manual, según convención del módulo).
  - **Descripción**.
  - **Cantidad**.
  - **E/S** (Entrada / Salida).
  - **Acciones**: ícono Editar, ícono Quitar, e **ícono “Más detalles”** (p. ej. `info`, `visibility` o `expand_more`) que abre un **modal** con el detalle completo del renglón.
- **En el modal “Detalle del artículo”** (al hacer clic en “Más detalles” de esa fila): mostrar **toda la información disponible** del renglón que el backend devuelva (y que tenga sentido mostrar), por ejemplo:
  - Orden, IDArt, CodigoArticulo, id_manual, Descripcion, Cantidad, entrada, salida, ES, CodDeposito, cod_deposito_destino.
  - Si existen y se persisten: cod_lote, vto_lote, PrecioCostoxU, PrecioCostoxR, marca, tipo_unidad, nro_pedi, cantidad_armada_opt, serie/desc_serie, etc.
  - Solo lectura en el modal (no edición); para cambiar algo se usa “Editar” en la fila y la edición inline en la tabla.
- **Ventaja:** La tabla queda escaneable y usable en cualquier dispositivo; quien necesite ver lote, precios, pedido interno, etc., lo ve en el modal sin ensanchar la grilla.

### 6.4 Datos que devuelve hoy el backend (renglones)

El servicio `listar_renglones_temporales` devuelve por renglón (según el SELECT actual): **Orden, IDArt, CodigoArticulo, Descripcion, Cantidad, entrada, salida, ES, CodDeposito, cod_deposito_destino, id_lote, cod_lote, vto_lote**. Para el modal “Más detalles” se puede usar exactamente eso; si más adelante se agregan campos (PrecioCostoxU, marca, nro_pedi, etc.) al INSERT/SELECT del temporal, se incluirían en el modal sin necesidad de más columnas en la tabla.

### 6.5 Resumen de la estrategia

| Ubicación | Contenido |
|-----------|-----------|
| **Tabla “Artículos”** | Columnas: Código, Descripción, Cantidad, E/S, Acciones (ícono Más detalles, Editar, Quitar). Solo lo imprescindible para identificar la línea. |
| **Modal “Detalle del artículo”** | Todos los campos del renglón que el backend envíe (Orden, artículo, cantidades, depósitos, lote, vencimiento, etc.), en formato lectura. |
| **Fila “Nueva línea”** | Input búsqueda predictiva (caja de texto), cantidad, E/S, ícono Agregar. |

Con esto se mantiene paridad conceptual con el grid de AdministraNET (donde hay muchas columnas configurables) sin degradar la experiencia en la web.

---

## 7. Documentación a actualizar tras implementación

- `docs/general/MODULO_STOCK_SYNAP.md`: describir el flujo “entrada en tabla”, la sección “Artículos”, el botón “Más detalles” (modal) y el endpoint de actualización de renglón.
- `docs/general/ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md`: en la sección de decisiones Synap, añadir que el ingreso es inline en tabla, que la tabla muestra solo columnas de identificación y el detalle completo en modal, y que Serie queda para fase posterior.
- Si se añade el endpoint en `stock/urls.py`, mantener la lista de APIs en la documentación del módulo.

---

## 8. Próximos pasos (cuando se apruebe)

1. Implementar `actualizar_renglon_temporal` y `PUT/PATCH .../renglones/<orden>/`.
2. Refactorizar `stock/templates/stock/alta_movimiento.html`: eliminar bloque “Agregar ítem”, unificar tabla con fila “Nueva línea” al final y modo edición por fila.
3. Probar flujo: agregar varias líneas, editar una, quitar una, confirmar movimiento.
4. Actualizar documentación según §7.
5. (Fase posterior) Diseñar e implementar Serie según §4.3.

Si quieres ajustar la opción A/B de colocación de “Nueva línea” o el alcance de Serie, se puede revisar antes de pasar a implementación.
