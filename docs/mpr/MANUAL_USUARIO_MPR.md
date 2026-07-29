# Manual de usuario – Producción (MPR)

Guía práctica del módulo **Producción** en Synap para supervisores y operarios. Explica el trabajo diario en planta y cómo dejar lista la configuración.

**Antes de empezar:** iniciar sesión y seleccionar la empresa con la que va a trabajar.

---

## 1. Acceso al módulo

1. En el menú de Synap, abra **Producción (MPR)**.
2. La pantalla de entrada habitual es el **Tablero de producción**.
3. Si su usuario es de **operario** (solo carga de parte), al ingresar verá directamente **Carga de producción** (su parte del día).

---

## 2. Flujo del día a día

Orden recomendado:

1. **Tablero de producción** — ver qué falta fabricar y enviar trabajo a la fábrica  
2. **Parte de producción** — registrar lo producido (supervisor u operarios)  
3. **Control de calidad** — clasificar lo producido  
4. **Armado** — armar packs terminados  
5. **Imputación de pedido** — asignar lo armado a pedidos (supervisor)

### Idea clave (una frase)

**Enviar** (tablero) → sube **Fabricando** → el **Parte** solo puede aprobar hasta ese cupo → **Control de calidad** mueve stock de Producción a Semi / 2da / Desperdicio → **Armado** convierte componentes en pack terminado.

---

## 3. Tablero de producción

**Menú:** Producción → Tablero de producción.

### Para qué sirve

Es la pantalla principal del día: muestra la demanda (según pedidos y reserva), cuánto falta, qué está en curso y permite **enviar cantidades a producción**.

### Cómo usarlo

1. Filtre por fechas de pedido, marcas o **Solo urgentes** (modo **Par**) si necesita enfocarse.
2. Elija vista **Pack** (producto terminado, pedido + reserva) o **Par** (componente). Para enviar a producción use modo **Par**.
3. Si hace falta, pulse **Actualizar** para refrescar la demanda desde los pedidos. La búsqueda actual se conserva al actualizar.
4. En modo **Par**, complete **Enviar docenas** o **Enviar pares** en las filas que correspondan y pulse **Enviar a producción**. Confirme el envío.
5. Si envió de más (porque después bajó el pedido o la reserva), use **Anular envíos** en el tablero: los envíos **no se reducen solos**. Detalle en §3.6.
6. En modo **Pack** no hay envío: use el botón **Ver en modo Par para enviar**.
7. Desde el encabezado puede ir a Parte de producción, Control de calidad o Armado.

### Pack vs Par (qué fila está mirando)

| Modo | Cada fila es… | ¿Se envía a fábrica? |
|------|----------------|----------------------|
| **Pack** | Artículo **terminado** (lo que vende / arma) | No. Solo consulta demanda. |
| **Par** | **Componente** (medias / pares que se tejen) | Sí. Acá se completa **Enviar pares/docenas**. |

La **reserva de stock** que alimenta la demanda se configura en el artículo **pack terminado** (`stock_reserva` en AdministraNET), **no** en el componente de la grilla Par. Ver §3.4 más abajo.

### 3.1 Columnas del modo Par (cómo leerlas)

Unidades según el conmutador **Docenas / Pares** (y Pack / Par).

#### Demanda a producir

| Columna | Qué significa | ¿Es un faltante? |
|---------|----------------|------------------|
| **Pedido** | Demanda que viene de pedidos abiertos, explotada a este componente por la receta (BOM). | Sí, en la medida en que no esté cubierta por stock. |
| **Reserva** | **Colchón objetivo** del pack terminado, mostrado en pares/docenas del componente (`coeficiente BOM × stock_reserva` del pack). | **No.** Es el target maestro, no “faltan N”. |
| **Urgente** | Brecha **operativa** real: demanda a cubrir **menos** stock ya en pipeline (Producido + Semi + 2da, etc.). Si está en **0 / gris**, no hay que mandar más a planta por demanda. | **Sí.** Este es el número que importa para producir. |

#### En curso

| Columna | Qué significa |
|---------|----------------|
| **Fabricando** | Trabajo **ya enviado** a producción que **todavía no está acreditado** del todo (parte / control de calidad / stock físico en Semi·2da·Scrap). Fórmula conceptual: `máximo(0, Enviado − acreditado)`. |
| **Enviado** | Total histórico de envíos a producción (ledger), no anulado. |

#### Stock en pipeline

| Columna | Qué significa |
|---------|----------------|
| **Producido** | Saldo en depósito tipo **Producción**. |
| **2da** | Saldo en **2da selección**. |
| **Semi** | Saldo en **Semi elaborado**. |
| **Total** | Suma del pipeline que cuenta para cubrir Urgente (sin Terminado ni Scrap en el mismo criterio de cobertura). |

#### Acción

| Columna | Qué significa |
|---------|----------------|
| **Enviar pares / docenas** | Cantidad a mandar ahora. El sistema sugiere / permite hasta aproximadamente `máximo(0, Urgente − Fabricando)`. Si **Urgente = 0**, **Enviar** queda en 0: no hay brecha que cubrir. |

### 3.2 Relación Reserva ↔ Urgente ↔ Enviar ↔ Fabricando

Cadena de causa y efecto:

1. **Pedido** + brecha de reserva del pack → demanda operativa del componente.
2. **Urgente** = máximo(0, demanda − stock en pipeline).
3. **Enviar** = máximo(0, Urgente − Fabricando).
4. Tras confirmar el envío → suben **Fabricando** y **Enviado**.
5. En el Parte, el cupo verde = **Fabricando**.

Si después del envío **cambia el pedido o la reserva**, Urgente y el sugerido a Enviar se recalculan; **Enviado/Fabricando no se reescriben solos**. Ver §3.6.

**Errores frecuentes de lectura**

1. Ver **Reserva = 1500** y pensar “faltan 1500” → incorrecto si **Urgente = 0**.
2. Querer cargar 288 en el Parte sin haber **Enviado** antes → el cupo verde sigue en Fabricando (p. ej. 17).
3. Subir la reserva del **componente** en AdministraNET → **no** mueve la columna Reserva del tablero Par; hay que tocar el **pack terminado**.

### 3.3 Ejemplo didáctico (artículo componente)

Datos reales de una fila en modo **Par / Pares** (artículo tipo *3120 T4 Reef Gmel Logo Negro 1Par*):

| Dato | Valor | Lectura |
|------|------:|---------|
| Pedido | 0 | No hay demanda de pedido abierta para este componente. |
| Reserva | 1500 | Colchón objetivo mostrado (pack × BOM). **No** es el faltante. |
| Urgente | 0 | La brecha operativa ya está cubierta por el pipeline. |
| Fabricando | 17 | Quedan 17 pares enviados aún no acreditados del todo. |
| Enviado | 72 | Se enviaron 72 en total a lo largo del tiempo (ledger). |
| Producido / 2da / Semi | 636 / 17 / 38 | Stock físico en pipeline. |
| Total | 691 | 636 + 17 + 38. |
| Enviar | 0 | Correcto: Urgente 0 → nada que mandar ahora. |

**¿La reserva está “cubierta”?**

- Si la pregunta es *“¿tengo que fabricar más ahora?”* → **No** (Urgente = 0, Enviar = 0).
- Si la pregunta es *“¿tengo 1500 pares de colchón listos?”* → **No necesariamente**: el colchón objetivo es 1500; en pipeline hay ~691 (más el terminado del pack, que no se ve en estas columnas de componente).

**¿Puedo cargar 288 pares en el Parte?**

En la planilla del supervisor, el badge verde muestra el **cupo Fabricando** (en el ejemplo, **17 pares**). Si carga 8 docenas × 3 operarios = **288 pares**, verá *Ingresado: 288* en rojo porque **supera el cupo**.

| Objetivo | Qué hacer |
|----------|-----------|
| Aprobar hasta 17 | Cargar ≤ 17 y **Guardar parte de producción**. |
| Aprobar 288 | Primero generar **Urgente ≥ 288** (p. ej. subiendo la reserva del **pack** y recalculando), luego **Enviar** ~271 (288 − 17 de Fabricando actual), y recién ahí el Parte acepta 288. |

Orden de magnitud orientativo (Pedido = 0 y pipeline ya cubriendo ~691):

- Para abrir Urgente ≈ 288 → demanda ≈ 691 + 288 = **979**.
- Si la Reserva UI actual es 1500 y la brecha escala ~1:1 → Reserva orientativa ≈ **1788** en el **pack terminado**, después **Enviar**, después Parte.

### 3.4 Dónde modificar la Reserva

1. Identifique el **componente** en el tablero Par (ej. *3120 T4 Reef Gmel Logo Negro 1Par*).
2. Busque el **artículo pack terminado** cuya **lista de materiales (BOM / receta)** incluye ese componente. Suele ser el mismo modelo/color en presentación pack (no “1Par” de tejido).
3. En AdministraNET / catálogo de artículos, edite **`stock_reserva`** (reserva de stock) de ese **pack**, no del componente.
4. Vuelva al tablero → **Actualizar**. Deberían cambiar Reserva / Urgente / Enviar en los componentes de su BOM.

Si el pack aparece en ámbar **Sin receta**, primero complete la BOM; sin receta el modo Par **no** genera filas de envío para ese terminado.

### Modo Pack y packs sin receta

En **Pack** cada fila es un **artículo terminado** (Pedido, Reserva maestro y columna **Urgente** = cantidad a fabricar, sin desglosar componentes). El filtro **Solo urgentes** no aplica en Pack: se listan todos los packs con demanda a fabricar, incluidos quiebres solo-reserva. Puede activar el chip **Sin receta** para ver solo packs sin lista de materiales (BOM).

En **Par**, la columna **Urgente** es la base del envío a producción (pedido + brecha de reserva menos pipeline).

Si el pack **no tiene receta** (lista de materiales / BOM) en AdministraNET:

- La fila se destaca en **ámbar** con el aviso **Sin receta**.
- Puede abrir el ícono de documento junto al aviso para ver los **pedidos PED** asociados (número, estado, fecha de entrega, cliente y cantidad) y revisar el caso.
- Ese aviso es **recomendado**: no bloquea el tablero. En modo **Par** ese pack **no genera** componentes para enviar; hay que cargar o corregir la receta del artículo antes de poder producirlo por el flujo normal.
- Al **generar una OPT** desde Orden de producción / ventana pack, el sistema **sí bloquea** packs sin receta hasta que tengan BOM.

### Avisos frecuentes

- «Sin cantidades a enviar»: cargue al menos una cantidad antes de confirmar.
- «Sin artículos/packs con demanda…», «Sin packs sin receta…» o «Sin Urgente…»: no hay filas con el filtro actual; amplíe fechas o quite filtros.
- «Ningún artículo coincide con la búsqueda.»
- Tras un envío correcto: mensaje de componentes enviados a producción.
- Badge **Sin receta** (modo Pack): el terminado no tiene lista de materiales; revise pedidos en el tooltip y complete la receta del artículo.

### 3.5 Por qué un artículo no aparece en el tablero

El tablero **no** lista todo lo asignado a máquinas. Solo muestra componentes con **demanda** (o con envíos previos). Causas habituales:

| Causa | Qué ve / no ve | Cómo resolver |
|-------|----------------|---------------|
| Sin **PED** abierto y sin **`stock_reserva`** en el pack | El componente no aparece en Par | Cargar reserva del **pack** (§3.4) o abrir/cargar un pedido PED del pack |
| Pack **sin BOM / sin receta** | Pack en ámbar; Par no explota componentes | Completar lista de materiales del pack |
| Filtro **Solo urgentes** activo y Urgente = 0 | Fila oculta aunque exista | Desactivar Solo urgentes o ampliar demanda |
| Rango de **fechas de pedido** / marcas / búsqueda | No coincide | Ampliar fechas, quitar marcas, buscar por código |
| Solo hay **asignación a máquina** (orden verbal / OPT legacy) | Aparece en el **Parte** con «Sin cupo Fabricando», **no** en el tablero | Misma resolución: demanda (reserva o PED) → **Enviar** → Parte |

**Caso típico de planta:** recibieron orden de producir, asignaron el artículo a las máquinas, pero **no gestionaron la reserva de seguridad** del pack ni hay pedido visible. Resultado: Parte con filas grises; tablero sin el artículo. No hay “enviar forzado” sin Urgente.

### 3.6 Si cambia el pedido o la reserva después de Enviar

**Regla clave:** los envíos ya confirmados **no se ajustan solos**. Cambiar un PED (cantidad, cancelación) o el `stock_reserva` del pack **solo recalcula** columnas derivadas (Pedido, Reserva, Urgente, sugerido a Enviar). El historial de envíos (`Enviado` / ledger) queda igual hasta que usted **envíe más** o **anule envíos**.

#### Qué se recalcula al recargar el tablero

| Columna | ¿Se actualiza sola? | Cómo |
|---------|---------------------|------|
| Pedido / Reserva / Urgente | **Sí** | Lectura en vivo de PED + `stock_reserva` del pack + stock en pipeline |
| Sugerido **Enviar** | **Sí** | `máximo(0, Urgente − Fabricando)` |
| **Enviado** (ledger) | **No** | Solo crece con «Enviar a producción» y baja con «Anular envíos» |
| **Fabricando** | **No por demanda** | Baja al acreditar (Parte aprobado / Control de calidad) o al anular envíos no consumidos |

«Actualizar» en el tablero **no reescribe** envíos: solo refresca la vista con la demanda actual.

#### Ejemplos (después de haber enviado 300)

Suponga que mandó **300** a fabricar y todavía no acreditó partes (Fabricando ≈ 300).

| Cambio posterior | Urgente | Enviado / Fabricando | Enviar sugerido | Qué hacer |
|------------------|---------|----------------------|-----------------|-----------|
| Cancela el PED o baja mucho la reserva → demanda operativa ≈ 0 | → **0** | Siguen ≈ **300** | **0** | Queda **sobre-enviado**. Para bajar cupo: **Anular envíos** (lo no consumido por partes) o dejar que el Parte/CC acredite. |
| Baja el pedido / reserva pero sigue faltando algo (ej. Urgente nuevo = 100) | → **100** | ≈ **300** | **0** (300 ya cubre 100) | No envíe más. Si no quiere producir de más, anule el excedente de envíos. |
| Aumenta el PED o sube la reserva → Urgente nuevo = 450 | → **450** | ≈ **300** | ≈ **150** | Complete **Enviar 150** y confirme. Se **suma** un nuevo envío; el de 300 no se modifica. |
| Aumenta demanda pero Fabricando ya es ≥ Urgente | → nuevo valor | sin cambio | **0** | Nada que enviar; el cupo del Parte ya alcanza. |

#### Cómo subir o bajar el cupo a propósito

**Subir (hacer Fabricando más grande)**

1. Aumente demanda: más cantidad en PED y/o suba `stock_reserva` del **pack**.
2. Tablero Par → recargar / Actualizar → verifique **Enviar > 0**.
3. **Enviar a producción** por el delta.

**Bajar (reducir Fabricando / Enviado)**

1. Abra **Anular envíos** en el Tablero (supervisor).
2. Anule filas de envío **no consumidas** por partes (el sistema no anula lo ya usado en un parte aprobado).
3. Alternativa operativa: seguir con Parte/CC hasta acreditar; Fabricando baja aunque el ledger histórico de Enviado conserve el rastro de lo no anulado según reglas de pantalla.

No existe «recalcular envíos = nueva demanda» ni anulación automática al cancelar un pedido.

#### Relación con el Parte

Mientras **Fabricando > 0**, el Parte permite cargar hasta ese cupo **aunque** Urgente ya sea 0 (porque cancelaron el pedido después). Eso es intencional del ledger: la planta ya tenía trabajo enviado. Si la orden se cayó, anule envíos antes de seguir produciendo de más.

---

## 4. Parte de producción

Hay dos formas de cargar lo producido.

### 4.1 Parte de producción (supervisor)

**Menú:** Producción → Parte de producción (Carga).

1. Elija **Fecha** (y opcionalmente línea/máquina) → **Cargar grilla**.
2. Use **Buscar artículo** en el encabezado para filtrar en vivo la grilla ya cargada (no recarga).
3. Por artículo y operario, cargue **Docenas** y/o **Pares**. La fila indica el cupo **Fabricando** (número verde).
4. Tiene dos acciones (mismo espíritu que el control de calidad):
   - **Guardar borrador** — guarda la carga **sin** mover stock. Puede retomarla después. Si el **día ya tiene parte aprobado**, el borrador se deshabilita (sigue visible).
   - **Guardar parte de producción** — **aprueba**: ingresa stock al depósito **Producción** (movimiento OPP) y consume cupo Fabricando.
5. Si el turno / la fecha ya tiene **control de calidad confirmado**, el parte queda en **solo lectura** para ese alcance.

**Cupo Fabricando (badge verde)**

- Es el máximo que puede **aprobar** en esa fila máquina × artículo.
- Sale del tablero: envíos menos lo ya acreditado (parte previo, CC, Semi/2da/Scrap).
- Si *Ingresado* supera Fabricando, el número ingresado se ve en rojo y **no** podrá aprobar (el borrador sí puede guardar cantidades por encima para seguir cargando, pero al aprobar se valida el tope).

**Ejemplo:** Fabricando = 17; tres operarios con 8 docenas cada uno → Ingresado = 288 → rojo. Hay que **Enviar** desde el tablero antes de poder aprobar 288.

### 4.1.1 «Sin cupo Fabricando» (celdas deshabilitadas)

Si la fila muestra el artículo en la máquina pero las celdas de turno dicen **Sin cupo Fabricando** y el badge verde está en **0 pares**:

1. **Asignar artículo a máquina** solo hace visible la fila en el Parte. **No** crea producción ni cupo.
2. El cupo aparece solo después de **Enviar a producción** en el Tablero (modo Par).
3. Si el artículo **tampoco está en el tablero**, falta demanda: vea §3.5 (reserva del pack o PED).
4. Secuencia: reserva/PED → Tablero **Actualizar** → **Enviar** → volver al Parte → **Cargar grilla**.

Otros motivos de celda no editable:

| Mensaje / estado | Causa | Qué hacer |
|------------------|-------|-----------|
| Sin cupo Fabricando | Fabricando = 0 (nunca enviaron o ya acreditaron todo) | Enviar desde tablero (§3.5 / §3.4) |
| Sin operario en el roster | Turno sin operario planificado en esa máquina/fecha | Planificación de turnos (§8.8) |
| Solo lectura / candado | Control de calidad **confirmado** | No editar el parte; correcciones de CC por movimiento de stock (§5) |

**Avisos frecuentes**

- «No hay operarios asignados a este turno/fecha.» Complete la planificación de turnos.
- «No hay componentes con cupo en Fabricando…» Primero envíe trabajo desde el Tablero de producción.
- La suma por fila no puede superar Fabricando al **aprobar**.
- «Parte de producción registrado exitosamente.»

### 4.2 Carga de producción (operario)

Pantalla del operario para cargar por **máquina y artículo**, en docenas y pares.

1. Revise línea, turno y fecha del día.
2. Busque máquina o artículo; puede ocultar máquinas sin artículos.
3. Cargue cantidades.
4. Guarde como **Borrador** o **Enviar parte** (queda pendiente de aprobación del supervisor).

Hasta que el supervisor apruebe, el stock **no** ingresa.

**Si no puede cargar**

- «Sin operario asociado», «Sin turno» o «Sin línea»: pida al supervisor el vínculo de usuario, el turno del día o la línea habitual.
- «Sin máquinas»: la línea no tiene máquinas activas o no hay artículos asignados a esas máquinas.

### 4.3 Partes pendientes (aprobación)

**Menú:** Producción → Partes pendientes (aprobación).

1. Filtre por fecha y turno (opcional: incluir borradores).
2. Abra el parte, revise cantidades **declaradas** y ajuste las **aprobadas** si hace falta.
3. Si cambia una cantidad, indique el **motivo**.
4. Pulse **Aprobar parte**. El stock ingresa al depósito de **Producción**.

### 4.4 Rectificar un parte ya aprobado

Si después de aprobar necesita bajar o subir cantidades del mismo día (planilla), el sistema registra un **ajuste por diferencia (delta)** en el mismo depósito de Producción (entrada o salida según el caso), no “borra” el movimiento original. El cupo y el tablero se recalculan con lo acreditado.

Si el día ya tiene **control de calidad confirmado**, no podrá modificar el parte de ese alcance: primero resuelva la clasificación (hoy, correcciones de CC por movimiento de stock; ver §5).

---

## 5. Control de calidad

**Menú:** Producción → Control de calidad.

### Para qué sirve

Distribuir lo del **Parte** (y eventual extra en Producción) entre **Semi elaborado** (primera), **2da selección** y **Desperdicio**.

### Cómo usarlo

1. Elija **Fecha** (y **Turno** opcional) → **Cargar grilla**. En la barra oscura también puede **buscar** artículo y alternar **Solo pendiente** / **Ver roster**.
2. La columna **Parte** muestra lo fabricado (referencial). Cargue **Semi elaborado**, **2da selección** y **Desperdicio** (docenas / pares).
   - Al abrir la grilla, **Semi elaborado** se precarga con lo atribuible del parte (docenas / pares).
   - Al cargar **2da selección** o **Desperdicio**, la pantalla **descuenta automáticamente** esa cantidad de Semi elaborado (en pares equivalentes). Ejemplo: semi precargado 5 docenas (60 pares) + 6 pares en 2da → semi queda en 4 docenas y 6 pares.
   - **Semi elaborado sigue siendo editable** a mano si necesita ajustar. Si después modifica 2da o desperdicio, el descuento se calcula sobre el semi **actual** (no vuelve a calcular desde la precarga).
   - Si 2da + desperdicio superan el tope clasificable de la fila, Semi baja a 0 y la fila se marca en rojo hasta corregir.
3. Los botones quedan fijos al pie de la grilla (siempre visibles):
   - **Guardar borrador** — guarda semi/2da/scrap **sin mover stock**. Puede cerrar y volver otro día: la grilla **precarga** lo guardado y muestra el chip *Borrador* en la barra.
   - **Guardar control de calidad** — **confirma**: transfiere stock de Producción → Semi / 2da / Scrap y deja registro oficial. **Elimina** el borrador de esa fecha+turno.
4. Solo el CC **confirmado** bloquea el Parte y cuenta como “hay control de calidad”. El **borrador no bloquea** el parte ni mueve Fabricando/stock.
5. En **Ver roster**, las filas ya confirmadas se muestran con los **mismos casilleros** (docenas/pares) en solo lectura. **No se puede reeditar** un CC confirmado desde esta pantalla.

### Borrador vs confirmado (resumen)

| Acción | ¿Mueve stock? | ¿Bloquea el Parte? | ¿Se pierde al salir? |
|--------|---------------|--------------------|----------------------|
| Guardar borrador | No | No | No (queda guardado) |
| Guardar control de calidad | Sí | Sí (turno/fecha) | — (borra el borrador) |

### Correcciones después de confirmar

Para reclasificar entre Semi / 2da / Desperdicio use **Ingreso de movimiento de stock** con una **transferencia interna**. En esta versión **no** hay “rectificar CC con delta” desde la misma pantalla (a diferencia del parte).

### Avisos frecuentes

- Sin filas: falta parte con desglose por operario para esa fecha, o todo ya está clasificado (las filas completas se ven en solo lectura).
- Corrija las filas en rojo (cantidades que superan el tope clasificable) antes de confirmar.
- Puede guardar borrador a mitad de carga aunque todavía falten filas.

---

## 6. Armado

**Menú:** Producción → Armado.

### Para qué sirve

Armar **packs terminados** a partir de componentes en depósito.

- **Armado 1ra:** usa la lista de materiales del pack; origen habitual **Semi elaborado**. Después el supervisor imputa a pedidos.
- **Armado 2da:** composición libre desde **2da selección** (venta u oportunidad de segunda).

### Cómo usarlo

1. Elija **Armado 1ra** o **Armado 2da**.
2. Complete la cabecera del lote: depósito origen, destino del pack y detalle opcional.
3. Busque el pack, indique cantidad (y composición en 2da) y agréguelo al carrito.
4. Revise el carrito y pulse **Ejecutar lote**. No cierre la ventana mientras procesa.

**Avisos frecuentes**

- «Carrito vacío» / «Agregue al menos un armado al lote.»
- Origen y destino deben estar indicados y ser distintos.
- «Sin stock suficiente…» o falta de lista de materiales del pack: revise depósitos y datos del artículo.
- «Máximo … armados por lote»: divida en varios lotes.

---

## 7. Imputación de pedido

**Menú:** Producción → Imputación de pedido.

### Para qué sirve

Asignar lo armado en **Armado 1ra** a los **pedidos** con demanda abierta. Lo armado en 2da no se imputa aquí.

### Cómo usarlo

1. Vea los comprobantes pendientes de imputar.
2. Pulse **Imputar** en el que corresponda.
3. Revise la sugerencia automática (pedidos más antiguos primero) y ajuste cantidades si hace falta.
4. Confirme la imputación.

**Avisos frecuentes**

- «No hay … pendientes de imputar»: primero ejecute Armado 1ra.
- Si no hay líneas sugeridas, verifique que el artículo tenga pedidos abiertos.

---

## 8. Configuración (orden recomendado)

Configure la planta **antes** de operar, o cuando cambie la organización del trabajo.  
**Menú:** Producción → Configuración.

Siga este orden:

### 8.1 Líneas

Alta y edición de **líneas** de producción (activo / inactivo). Las máquinas se agrupan por línea.

### 8.2 Máquinas

Catálogo de **máquinas** y a qué línea pertenecen. Al cambiar la línea se conserva historial.

#### Asignar artículo a máquina

Desde Máquinas o desde **Producción diaria → Asignar artículo a máquina**:

1. Filtre por línea o busque la máquina.
2. Habilite o quite los artículos que cada máquina puede producir.
3. Elija la **fecha** de vigencia de la asignación (un día pasado aplica solo ese día; no reescribe el futuro).
4. En la grilla verá **Talle** y **Color** del artículo.
5. Pulse **Imprimir Control de Calidad**, elija la **fecha** de la planilla y confirme. Se imprime la hoja horizontal con artículos vigentes a esa fecha, cantidades del parte en **1ra** por turno y una fila vacía debajo de cada artículo para anotar la clasificación a mano.

Si no hay filas con artículos según el filtro, el sistema avisa en pantalla.

### 8.3 Config. Depósitos

Indique, para cada depósito, si **suma al stock** y su **tipo** en producción, por ejemplo:

- Producción  
- Semi elaborado  
- 2da selección  
- Terminado  
- Desperdicio / scrap  

Sin esta configuración el tablero y el flujo de etapas no muestran saldos correctos.

### 8.4 Operarios

Alta y mantenimiento de **operarios** (activos / inactivos) que figurarán en partes y planificación.

### 8.5 Operarios y usuarios

Vincule cada **usuario de login** con un **operario**. Un usuario corresponde a un operario. Es necesario para la carga móvil.

### 8.6 Línea habitual (operarios)

Defina la línea por defecto de cada operario. La planificación diaria puede cambiarla para un día concreto.

### 8.7 Turnos de producción

Defina los turnos (por ejemplo Mañana, Tarde, Noche) con su horario. Solo los **activos** se usan en la planificación.

### 8.8 Planificación de turnos

**Menú:** Producción diaria → Planificación de turnos.

Asigne el turno de cada operario **día a día** (hoy y fechas futuras). Puede usar asignación masiva para varios operarios y un rango de fechas.

La pantalla usa la **barra densa de producción**: en la barra superior están la navegación de semana (Anterior / Siguiente), **Asignación masiva**, **Gestionar turnos** y los atajos al Tablero, Parte y Control de calidad. La grilla ocupa el resto de la pantalla y se desplaza sola. Al **quitar** un turno se pide confirmación en una ventana de Synap.

Sin turno del día, el operario no podrá cargar su parte.

---

## 9. Resumen rápido

| Momento | Pantalla | Acción |
|---------|----------|--------|
| Arranque de planta | Configuración (líneas → máquinas → depósitos → operarios → vínculos → turnos → planificación) | Dejar lista la fábrica |
| Ajustar colchón | Artículo **pack** en AdministraNET (`stock_reserva`) | Sube Reserva/Urgente en tablero tras Actualizar |
| Mañana / turno | Tablero de producción (modo **Par**) | Enviar solo si **Urgente > 0** |
| Durante el turno | Parte / Carga de producción | Borrador sin stock; aprobar ≤ **Fabricando** |
| Supervisor | Partes pendientes | Aprobar partes de operarios |
| Después del parte | Control de calidad | Borrador sin stock; confirmar mueve a Semi/2da/Scrap |
| Cierre de producto | Armado | Armar packs 1ra o 2da |
| Contra pedidos | Imputación de pedido | Asignar Armado 1ra a pedidos |

---

## 10. Problemas frecuentes

- **No veo el artículo en el tablero (sí en el Parte / máquinas):** falta demanda. Sin PED ni `stock_reserva` del **pack**, o pack sin BOM, o filtro Solo urgentes. Ver §3.5. Asignar a máquina **no** lo publica en el tablero.
- **No veo demanda en el tablero:** revise filtros de fecha y marcas; pulse Actualizar; desactive Solo urgentes; confirme reserva del pack o PED (§3.4 / §3.5).
- **Cancelé / bajé el pedido o la reserva pero Fabricando sigue alto:** es normal. Los envíos **no se ajustan solos**. Anule envíos no consumidos o acredite con Parte/CC. Ver §3.6.
- **Subí el pedido o la reserva y no puedo enviar el total de nuevo:** el sistema solo sugiere el **delta** (`Urgente − Fabricando`). Envíe esa diferencia; el envío anterior no se borra. Ver §3.6.
- **Veo un pack en ámbar «Sin receta»:** el terminado no tiene lista de materiales. Use el ícono de pedidos para ver qué PED lo piden; complete la BOM del artículo. En Par no podrá enviar componentes de ese pack hasta tener receta.
- **Reserva alta pero Urgente en 0:** es normal si el pipeline ya cubre la brecha. No envíe más; el colchón objetivo no es un faltante.
- **Parte con «Sin cupo Fabricando» / celdas grises:** nunca enviaron (o Fabricando = 0). No se puede cargar hasta **Enviar** desde el tablero. Si el artículo no está en el tablero, primero genere demanda (§3.5 / §4.1.1).
- **Quiero cargar más en el Parte que el verde (Fabricando):** primero **Enviar** desde el tablero (hace falta Urgente). Subir solo la columna Reserva del componente no alcanza; edite `stock_reserva` del **pack** y envíe.
- **No sé en qué artículo tocar la reserva:** el pack terminado cuya BOM incluye el componente de la fila Par (ver §3.4).
- **No puedo guardar el parte (aprobar):** no hay cupo en Fabricando, el día tiene CC confirmado, o faltan operarios en el turno.
- **El operario no puede cargar:** falta vínculo usuario–operario, turno del día, línea o artículos en la máquina.
- **No hay filas en Control de calidad:** no hay pendiente en Producción para esa fecha/turno (falta parte).
- **Perdí la carga a mitad de Control de calidad:** use **Guardar borrador**; al volver se precarga. El borrador no bloquea el parte.
- **No puedo armar:** stock insuficiente en el depósito origen o el pack no tiene lista de materiales (1ra).
- **Nada para imprimir en la planilla:** no hay máquinas con artículos según el filtro; asigne artículos o cambie el filtro.
- **Empresa incorrecta:** cambie de empresa en la sesión e intente de nuevo.

---

## 11. Migración BEST (cutover)

**Menú:** Producción → Migración BEST.

Herramienta de **migración desde BEST** hacia AdministraNET (artículos, clientes, depósitos, stock, pedidos). Úsela en el cutover con el equipo de implementación; no forma parte del día a día de planta.

### Artículos terminados vs fabricados

| Dominio | Qué mapea | ¿Bloquea pedidos? |
|---------|-----------|-------------------|
| **Artículos terminados** | SKU BEST de pedido → artículo Admin **Terminado** | Sí (gate de pedidos) |
| **Artículos fabricados** | **PP BEST con stock** (depósitos 4000/4002) → Admin **Fabricado** | No |

### Artículos fabricados (PP BEST → Admin)

**Ruta:** Migración BEST → **Artículos fabricados**.

1. Pulse **Resolver fabricados** para cargar los PP con stock y sugerir el Fabricado Admin.
2. Hay dos olas:
   - **Necesario pedido** (ola 1): PP requeridos por receta de pedidos abiertos.
   - **Stock** (ola 2): resto con stock, sin demanda de pedido.
3. Revise sugerencias (o use **Aceptar inferidos altos** / asigne a mano con el buscador).
4. Valide o descarte cada fila. Los PP que ya estén bien mapeados como **Terminado** en el dominio de terminados **no aparecen** aquí (es correcto).

### Pedidos sembrados desde BEST

Los pedidos migrados (comprobantes con origen cutover BEST) se abren desde el hub de **Ventas → Pedidos** en **solo consulta** (no se editan como un pedido normal). Ver el manual de Ventas, sección Pedidos.

---

## 12. Glosario rápido de pantalla

| Término | Significado corto |
|---------|-------------------|
| **Pack** | Artículo terminado (venta / armado). |
| **Par / componente** | Unidad que se teje o clasifica (medias, etc.). |
| **Reserva** | Colchón objetivo del pack (`stock_reserva`), mostrado explotado en Par. |
| **Urgente** | Faltante operativo a cubrir con producción. |
| **Fabricando** | Enviado aún no acreditado; cupo del Parte. |
| **Enviar** | Mandar trabajo desde el tablero a fábrica. |
| **Anular envíos** | Baja envíos no consumidos; no ocurre solo al cambiar PED/reserva. |
| **Borrador (parte o CC)** | Guardado intermedio **sin** stock. |
| **Confirmar / aprobar** | Persiste oficialmente y **sí** mueve stock (según pantalla). |
| **Pipeline** | Stock en Producción + Semi + 2da (cubre Urgente). |
| **BOM / receta** | Lista de materiales del pack → componentes. |

---

*Manual de usuario – Producción (MPR). Synap. Actualizado 29/07/2026.*
