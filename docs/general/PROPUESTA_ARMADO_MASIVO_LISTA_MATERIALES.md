# Propuesta: Armado masivo desde Lista de materiales con guardrail de stock terminado

**Contexto:** La pantalla "Conjuntos de armado (Lista de materiales)" hoy solo permite gestionar recetas (Ver / Editar) y ejecutar armado entrando a cada conjunto en forma individual. Se requiere poder **enviar a armar productos en forma masiva** desde esa misma ventana, con **cantidades editables** y **guardrail contra stock terminado**, y ejecutar el armado **directamente desde la pantalla** sin ir a cada uno por separado.

Este documento analiza el flujo actual, qué movimiento genera el armado, mejores prácticas y una propuesta de diseño (sin implementación aún).

---

## 1. ¿Qué movimiento genera el armado?

El armado en MPR no es un movimiento genérico: es una **operación de manufactura** que consume componentes y produce el producto armado según la receta (BOM).

### 1.1 Tablas y flujo actual (`ejecutar_armado` en `mpr/services.py`)

| Paso | Acción |
|------|--------|
| 1 | Validación de **stock de componentes** en el depósito origen: por cada componente de la receta (`en_abm_formula`), se exige `saldo` en `stock_deposito` (id_articulo + id_deposito = origen) ≥ cantidad_articulo × cantidad_a_armar. Si falta stock, se hace rollback y se devuelve mensaje de error. |
| 2 | Se obtiene un **CodigoMovimiento** (tabla `codmov`, código 1) y **NroComprobante** (talonario MSTOCK). |
| 3 | Se inserta **una fila en `movimiento_stock`**: tipo_mov = `'Armado'`, motivo_movimiento = `'Armado'`, deposito_origen, deposito_destino, detalle = `"Armado desde MPR (conjunto {id_en_abm}, {cantidad_a_armar} u.)"`. |
| 4 | Por cada **componente** de la receta: se inserta una fila en **`stock`** con **Salida** = cantidad_articulo × cantidad_a_armar en el depósito origen; se actualiza **`stock_deposito`** (decremento de saldo). |
| 5 | Una fila en **`stock`** para el **artículo armado**: **Entrada** = cantidad_a_armar en el depósito destino; se actualiza **`stock_deposito`** (incremento de saldo). |

**Resumen:** Un único comprobante de movimiento (tipo Armado) con múltiples renglones en `stock`: N salidas (componentes) + 1 entrada (producto armado). Los saldos por artículo y depósito se mantienen en `stock_deposito`.

### 1.2 Lo que hoy no se valida

- **Stock terminado del producto armado:** No hay ningún tope ni advertencia. Se puede armar cualquier cantidad mientras haya componentes; no se compara con demanda (pendiente de producción) ni con un máximo deseado de stock terminado. Es decir, **no existe guardrail contra sobreproducción** del producto armado.

---

## 2. Estado actual de la pantalla Lista de materiales

- **Vista:** Tabla de conjuntos (ID, Nombre, Detalle, Nº componentes, Estado, Acciones).
- **Acciones por fila:** Solo "Ver" y "Editar". No hay campo de cantidad ni botón "Armar" en la tabla.
- **Ejecución de armado:** Se hace desde (1) Detalle del conjunto → "Ejecutar armado", (2) pantalla `/mpr/armado/` eligiendo un solo conjunto, o (3) wizard paso 4 (un conjunto por paso). En todos los casos es **un conjunto y una cantidad por pantalla**.

---

## 3. Requisitos y mejores prácticas

### 3.1 Requisitos explícitos

1. **Armado masivo:** Poder indicar cantidades a armar para **varios conjuntos** en la misma pantalla (lista de materiales).
2. **Guardrail contra stock terminado:** Las cantidades a armar deben tener un techo coherente con la demanda o con el stock terminado (evitar armar de más).
3. **Ejecución desde la pantalla:** Confirmar y ejecutar el armado de todos los ítems seleccionados/cantidades sin tener que entrar a cada conjunto en forma individual.

### 3.2 Mejores prácticas (packs y recetas)

- **Unidad de armado = receta:** Cada conjunto (en_abm) define una receta: 1 unidad de producto armado = N unidades del componente A, M del B, etc. El armado masivo debe respetar **siempre** esas proporciones (ya lo hace `ejecutar_armado`).
- **Validación en dos frentes:**
  - **Componentes:** Stock disponible en depósito origen ≥ cantidad a armar × cantidad_articulo por componente (ya implementado).
  - **Producto armado (guardrail):** No armar más de lo “necesario” o no superar un tope de stock terminado, según la regla de negocio que se adopte (ver sección 4).
- **Transaccionalidad:** Cada armado (cada conjunto × cantidad) puede seguir generando **un movimiento de stock** (un CodigoMovimiento) para trazabilidad y posibilidad de anulación por comprobante. Alternativa: un solo movimiento con varios “bloques” de renglones (más complejo y menos alineado con el modelo actual). **Recomendación:** mantener **un movimiento por conjunto** en la ejecución masiva, llamando a `ejecutar_armado` una vez por fila con cantidad > 0.
- **Depósitos:** En masivo, se puede usar **un único par origen/destino** para toda la ejecución (más simple y habitual en planta) o permitir por fila (más flexible y más complejo). Recomendación para MVP: **origen y destino únicos** para la tanda, seleccionados una vez antes de ejecutar.

---

## 4. Guardrail contra stock terminado: opciones

Objetivo: acotar la cantidad a armar para no generar stock terminado “de más” sin control.

### 4.1 Opción A: Techo = pendiente de producción (recomendada para MPR)

- **Regla:** Para cada artículo armado, **cantidad máxima a armar** = suma de `cantidad_pendiente_prod` en `lista_produccion_agrupada` para ese artículo (solo líneas con pendiente > 0 o en_proceso_produccion = 'Si').
- **Ventaja:** Alineado con la demanda ya cargada (OPT/ventana pack). No se arma más de lo que se mandó a producir.
- **Implementación:** En la lista masiva, por cada conjunto se puede obtener el artículo armado (`get_articulo_armado_por_bom`) y el pendiente agregado (`listar_lista_produccion_agrupada` por id_articulo o consulta directa). Mostrar “Pendiente: X” y limitar la cantidad editable a X (o advertir si se supera).

### 4.2 Opción B: Techo = max(0, pendiente − stock_terminado)

- **Regla:** Cantidad máxima = max(0, cantidad_pendiente_prod − stock_terminado), donde stock_terminado = suma de saldo en depósitos con `suma_stock = 'Si'`.
- **Ventaja:** Evita armar si ya hay stock terminado que cubre la demanda (útil si OPP u otros movimientos ya dieron de alta producto).
- **Implementación:** Reutilizar la lógica de “cantidad a fabricar” / “stock terminado” que ya existe en ventana pack (listar_ventana_pack con stock_terminado por artículo).

### 4.3 Opción C: Tope configurable (stock máximo objetivo)

- **Regla:** No permitir que stock_terminado del producto armado supere un “tope” configurable por artículo (ej. campo en artículo o en parámetro MPR). Cantidad máxima a armar = max(0, tope − stock_terminado_actual).
- **Ventaja:** Control explícito de inventario objetivo. Requiere definir dónde se guarda el tope y en qué pantalla se configura.

### 4.4 Recomendación

- **MVP:** Implementar **Opción A** (techo = pendiente de producción) en la pantalla de armado masivo: mostrar pendiente por conjunto/artículo armado y no permitir (o advertir fuertemente) cantidades mayores. Si no hay pendiente, se puede permitir armar igual (con advertencia “Sin demanda registrada”) para casos de reposición o uso especial.
- **Fase siguiente:** Valorar Opción B (descontar stock terminado) para afinar y evitar sobreproducción cuando ya hay stock en depósitos terminados.

---

## 5. Propuesta de diseño (pantalla Lista de materiales)

### 5.1 Modo “Armado masivo” en la misma pantalla

- **Filtros actuales:** Se mantienen (Estado: Solo activos / Todos; Conjuntos: En producción / Todos los conjuntos).
- **Tabla actual:** Se extiende con:
  - **Columna “Cant. a armar”:** Input numérico (0 o entero positivo) por fila. Solo habilitado para conjuntos que tengan artículo armado asignado y, si se adopta guardrail, con indicador de techo.
  - **Columna “Pendiente” (o “Tope”):** Opcional. Muestra el pendiente de producción del artículo armado (Opción A) o el valor “máximo recomendado” para que el usuario sepa hasta cuánto puede armar.
  - **Checkbox “Incluir” (opcional):** Para marcar qué filas participan en la ejecución masiva; si no se usa, se consideran todas las filas con Cant. a armar > 0.
- **Bloque único de depósitos:** Antes de ejecutar, el usuario elige **Depósito origen (componentes)** y **Depósito destino (producto armado)** una vez (aplicado a todos los armados de la tanda).
- **Botón “Ejecutar armado”:** Valida y ejecuta en lote:
  - Solo filas con cantidad > 0 (y “Incluir” si existe el checkbox).
  - Por cada fila: validar stock de componentes en origen y guardrail (cantidad ≤ pendiente si Opción A); si algo falla, mostrar mensaje por fila y no ejecutar esa; opcionalmente ejecutar solo las que pasen y reportar las fallidas.
  - Para cada fila válida: llamar a `ejecutar_armado(base_empresa, id_usuario, id_en_abm, cantidad, deposito_origen, deposito_destino)` (un movimiento por conjunto).
- **Resultado:** Mensaje de éxito con cantidad de armados realizados y números de comprobante, y lista de errores por fila si hubo fallos.

### 5.2 Validaciones antes de ejecutar

1. **Por fila con cantidad > 0:**
   - Conjunto con artículo armado asignado.
   - Stock de componentes suficiente en depósito origen (igual que hoy).
   - (Si guardrail A) cantidad_a_armar ≤ pendiente de producción del artículo armado (o advertencia y bloqueo/confirmación).
2. **Global:** Depósito origen y destino seleccionados y distintos (si la regla de negocio lo exige).

### 5.3 UX sugerida

- Mostrar **Pendiente** (y/o stock terminado) en la tabla para que el usuario vea el contexto sin salir de la pantalla.
- Botón “Rellenar con pendiente” (opcional): rellenar “Cant. a armar” con el mínimo entre pendiente y un tope por fila, para agilizar.
- En móvil/vista reducida, considerar agrupar depósitos y botón de ejecución en un panel colapsable debajo de la tabla.
- Mantener enlace “Ver” / “Editar” para seguir entrando al detalle o al armado individual si lo desea.

---

## 6. Resumen de decisiones propuestas

| Tema | Propuesta |
|------|-----------|
| **Movimiento que genera el armado** | Un `movimiento_stock` tipo Armado por ejecución: salidas de componentes (stock + stock_deposito) y entrada del artículo armado (stock + stock_deposito). Sin cambio respecto al comportamiento actual. |
| **Ejecución masiva** | Desde la pantalla Lista de materiales: columnas Cant. a armar (y opcional Pendiente/Tope), depósito origen y destino únicos, botón “Ejecutar armado” que por cada fila con cantidad > 0 llama a `ejecutar_armado` (un movimiento por conjunto). |
| **Guardrail stock terminado** | MVP: techo = pendiente de producción del artículo armado (lista_produccion_agrupada). Mostrar pendiente en tabla y no permitir (o advertir) cantidades mayores. |
| **Packs/recetas** | Sin cambio: las cantidades a armar son en unidades del producto armado; los componentes se consumen según en_abm_formula (cantidad_articulo × cantidad_a_armar). |
| **Transaccionalidad** | Un movimiento (comprobante) por conjunto armado; si una fila falla, se puede continuar con el resto y reportar errores. |

---

## 7. Próximos pasos (cuando se implemente)

1. **Backend:** Función o vista que reciba lista de (id_en_abm, cantidad) + deposito_origen + deposito_destino; por cada ítem validar componentes y guardrail; llamar a `ejecutar_armado` y acumular resultados/errores.
2. **Contexto de lista:** Incluir en cada conjunto (o por artículo armado) el pendiente de producción y, si aplica, stock terminado (reutilizar lógica de listar_ventana_pack / listar_lista_produccion_agrupada).
3. **Plantilla:** Añadir columnas Cant. a armar y Pendiente, bloque depósitos y botón Ejecutar armado; enviar por POST las cantidades y depósitos.
4. **Documentación:** Actualizar `MANUAL_USUARIO_MPR.md` y, si aplica, `ANALISIS_MPR_PROPUESTA_MVP.md` con el flujo de armado masivo y el significado del guardrail.

---

*Documento creado a partir del análisis del código en `mpr/services.py` (ejecutar_armado, get_bom_detalle, get_articulo_armado_por_bom), `mpr/views.py` (BomListView, ArmadoView) y plantillas `mpr/bom_list.html`, `mpr/armado.html`. Sin cambios realizados en el código.*
