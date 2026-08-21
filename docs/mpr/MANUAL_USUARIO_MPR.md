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
2. Al abrir el tablero queda **Par** y **Docenas**. Los conmutadores **Pack|Par** y **Docenas|Pares** solo aparecen si su puesto tiene el permiso **Cambiar vista Pack/Par y Docenas/Pares del tablero** (`mpr.tablero_cambiar_vista`). Sin ese permiso la grilla queda fija en Par / Docenas (tampoco se puede forzar Pack o Pares por la URL). Para enviar a producción use modo **Par**.
3. Si hace falta, pulse **Actualizar** para refrescar la demanda desde los pedidos. El texto de **Buscar artículo** se conserva al cambiar Pack/Par, Docenas/Pares, Solo urgentes y al actualizar, hasta que lo borre.
4. En modo **Par**, complete **Enviar docenas** o **Enviar pares** en las filas que correspondan y pulse **Enviar a producción**. Confirme el envío.
5. Si envió de más (porque después bajó el pedido o la reserva), use **Anular envíos** en el tablero: los envíos **no se reducen solos**. Detalle en §3.6.
6. En modo **Pack** no hay envío: use el botón **Ver en modo Par para enviar**.
7. Desde el encabezado puede ir a Parte de producción, Control de calidad o Armado.

### Pack vs Par (qué fila está mirando)

| Modo | Cada fila es… | ¿Se envía a fábrica? |
|------|----------------|----------------------|
| **Pack** | Artículo **terminado** (lo que vende / arma) | No. Solo consulta demanda. |
| **Par** | **Componente** (medias / pares que se tejen) | Sí. Acá se completa **Enviar pares/docenas**. |

La **reserva de stock** (colchón de seguridad) se carga en el artículo **pack terminado** en AdministraNET, **no** en el componente que ve en la grilla Par. Ver §3.4 más abajo.

### 3.1 Columnas del modo Par (cómo leerlas)

Las cantidades se muestran en **docenas** o **pares**, según el conmutador de la barra.

#### Demanda a producir

| Columna | Qué significa | ¿Es un faltante? |
|---------|----------------|------------------|
| **Pedido** | Lo que **aún falta remitir/facturar** de pedidos abiertos, pasado a este componente según la **receta** del pack. **No** es la cantidad original del PED. | Sí, en la medida en que todavía no esté cubierto por stock. |
| **Reserva** | El **colchón objetivo** del pack terminado, mostrado en la unidad del componente. Es la meta de stock de seguridad, no “cuánto falta hoy”. | **No.** No lo tome como cantidad a fabricar. |
| **TOT Urgente** | Lo que **todavía falta fabricar** sumando pedido y reserva, y restando **Producido + Semi**. **No** resta 2.ª: esa calidad no entrega pedidos de terminado de 1.ª; hay que rehacerla. Si da **0** (gris), no hace falta mandar más. Es el número que usa **Enviar** y el filtro **Solo urgentes**. El total bajo el título se recorta con la búsqueda. | **Sí.** Este es el que importa para producir. |
| **PED Urgente** | Lo mismo, pero **solo con el pedido** (sin el colchón de reserva y sin 2.ª). Sirve para **consultar** cuánto falta por pedido. **No** define Enviar ni Solo urgentes. | Sí respecto del pedido; no incluye el colchón. |

Si hay reserva, **TOT Urgente** suele ser **mayor o igual** que **PED Urgente**. Si no hay pedido abierto y solo hay colchón, PED Urgente suele ser **0** y TOT Urgente puede ser mayor que 0.

#### En curso

| Columna | Qué significa |
|---------|----------------|
| **Fabricando** | Lo que **ya mandó** a fábrica y **todavía no se acreditó** del todo (parte, control de calidad o stock ya clasificado). Es el **cupo** que puede cargar el Parte (número verde). |
| **Enviado** | Todo lo que se envió a producción a lo largo del tiempo y no se anuló. |

#### Stock en camino

| Columna | Qué significa |
|---------|----------------|
| **Producido** | Stock en el depósito de **Producción**. |
| **2da** | Stock en **2da selección**. Se ve en el tablero, pero **no** baja Urgente ni PED Urgente (no entrega pedidos de 1.ª; hay que rehacerlo). |
| **Semi** | Stock en **Semi elaborado**. |
| **Total** | Suma física Producido + 2da + Semi. No es lo que se resta a Urgente (eso es solo Producido + Semi). |

#### Acción

| Columna | Qué significa |
|---------|----------------|
| **Enviar pares / docenas** | Cuánto mandar **ahora**. El sistema sugiere hasta lo que falta después de restar lo que ya está **Fabricando**. Si **Urgente** es 0, Enviar queda en 0: no hay nada pendiente que cubrir. |

### 3.2 Relación Reserva ↔ Urgente ↔ PED Urgente ↔ Enviar ↔ Fabricando

Cadena de causa y efecto:

1. El **pedido** y la **reserva** del pack definen cuánto se necesita del componente.
2. **Urgente** es lo que todavía falta: se resta Producido y Semi (no 2.ª); si ya alcanza, queda en **0**.
3. **PED Urgente** es lo mismo mirando **solo el pedido** (sin reserva). Es solo lectura.
4. **Enviar** es lo urgente menos lo que ya está **fabricando**. Si Fabricando ya cubre Urgente, Enviar queda en **0**. **No** usa PED Urgente.
5. Al confirmar el envío suben **Fabricando** y **Enviado**.
6. En el Parte, el cupo verde es **Fabricando**.

Si después del envío **cambia el pedido o la reserva**, se actualizan Urgente, PED Urgente y lo sugerido a Enviar; **Enviado** y **Fabricando** **no** bajan solos. Ver §3.6.

**Errores frecuentes de lectura**

1. Ver **Reserva = 1500** y pensar “faltan 1500” → incorrecto si **Urgente = 0**.
2. Ver **PED Urgente** alto y **Enviar** en 0 → revise **Urgente** y **Fabricando**; Enviar solo mira Urgente.
3. Confundir **PED Urgente** con lo que hay que mandar → PED Urgente es el faltante **solo de pedido**; el envío sigue **Urgente** (pedido + colchón).
4. Querer cargar 288 en el Parte sin haber **Enviado** antes → el cupo verde sigue en Fabricando (por ejemplo 17).
5. Subir la reserva del **componente** en AdministraNET → **no** cambia la columna Reserva del tablero Par; hay que tocar el **pack terminado**.

### 3.3 Ejemplo didáctico (artículo componente)

Datos reales de una fila en modo **Par / Pares** (artículo tipo *3120 T4 Reef Gmel Logo Negro 1Par*):

| Dato | Valor | Lectura |
|------|------:|---------|
| Pedido | 0 | No hay pedido abierto para este componente. |
| Reserva | 1500 | Colchón objetivo (según el pack y su receta). **No** es el faltante. |
| Urgente | 0 | Con pedido + reserva, el stock en camino **ya alcanza**: no hace falta mandar más. |
| PED Urgente | 0 | Sin pedido abierto, el faltante solo-por-pedido también es 0. |
| Fabricando | 17 | Quedan 17 pares enviados que todavía no se acreditaron del todo. |
| Enviado | 72 | En total se enviaron 72 a lo largo del tiempo (sin anular). |
| Producido / 2da / Semi | 636 / 17 / 38 | Stock físico. La 2.ª **no** cubre pedidos de 1.ª (hay que rehacer esos 17). |
| Total | 691 | 636 + 17 + 38 (físico). Urgente resta 636 + 38 = 674. |
| Enviar | 0 | Correcto: Urgente 0 → nada que mandar ahora. |

**¿La reserva está “cubierta”?**

- Si la pregunta es *“¿tengo que fabricar más ahora?”* → **No** (Urgente = 0, Enviar = 0).
- Si la pregunta es *“¿tengo 1500 pares de colchón listos?”* → **No necesariamente**: la meta es 1500; en camino hay unos 691 (más el terminado del pack, que no se ve en estas columnas de componente).

**¿Puedo cargar 288 pares en el Parte?**

En la planilla del supervisor, el badge verde muestra el **cupo Fabricando** (en el ejemplo, **17 pares**). Si carga 8 docenas × 3 operarios = **288 pares**, verá *Ingresado: 288* en rojo porque **supera el cupo**.

| Objetivo | Qué hacer |
|----------|-----------|
| Aprobar hasta 17 | Cargar como máximo 17 y **Guardar parte de producción**. |
| Aprobar 288 | Primero hacer que **Urgente** sea al menos 288 (por ejemplo subiendo la reserva del **pack** y actualizando), luego **Enviar** la diferencia (unos 271, porque ya hay 17 fabricando) y recién ahí el Parte acepta 288. |

Orientación numérica (Pedido = 0 y en camino ya hay ~691):

- Para que Urgente sea cerca de 288 hace falta una demanda total cerca de 691 + 288 = **979**.
- Si hoy la Reserva en pantalla es 1500, una reserva orientativa del **pack** cerca de **1788**, después **Enviar**, después Parte.

### 3.4 Dónde modificar la Reserva

1. Identifique el **componente** en el tablero Par (ej. *3120 T4 Reef Gmel Logo Negro 1Par*).
2. Busque el **artículo pack terminado** cuya **receta** (lista de materiales) incluye ese componente. Suele ser el mismo modelo/color en presentación pack (no “1Par” de tejido).
3. En AdministraNET / catálogo de artículos, edite la **reserva de stock** de ese **pack**, no del componente.
4. Vuelva al tablero → **Actualizar**. Deberían cambiar Reserva / Urgente / Enviar en los componentes de su receta.

Si el pack aparece en ámbar **Sin receta**, primero complete la lista de materiales; sin receta el modo Par **no** genera filas de envío para ese terminado.

### Modo Pack y packs sin receta

En **Pack** cada fila es un **artículo terminado**. Ve **Pedido** (saldo comercial pendiente de remitir/facturar, no la cantidad original del PED), Reserva, **TOT Urgente** (pedido + reserva menos stock terminado) y **PED Urgente** (solo pedido menos stock terminado). PED Urgente es solo consulta; el envío a planta se hace en modo **Par**. El filtro **Solo urgentes** no aplica en Pack: se listan los packs con demanda a fabricar, incluidos los que solo tienen quiebre de reserva. Puede activar el chip **Sin receta** para ver solo packs sin lista de materiales.

En **Par**, **TOT Urgente** es la base del envío. **PED Urgente** va al lado para comparar el faltante solo de pedido.

Si el pack **no tiene receta** en AdministraNET:

- La fila se destaca en **ámbar** con el aviso **Sin receta**.
- Puede abrir el ícono de documento junto al aviso para ver los **pedidos** asociados (número, estado, fecha de entrega, cliente y cantidad).
- Ese aviso es **recomendado**: no bloquea el tablero. En modo **Par** ese pack **no genera** componentes para enviar; hay que cargar o corregir la receta antes de producirlo por el flujo normal.

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
| Sin **pedido** abierto y sin **reserva** en el pack | El componente no aparece en Par | Cargar reserva del **pack** (§3.4) o abrir/cargar un pedido del pack |
| Pack **sin receta** | Pack en ámbar; Par no muestra componentes | Completar la lista de materiales del pack |
| Filtro **Solo urgentes** activo y Urgente = 0 | Fila oculta aunque exista | Desactivar Solo urgentes o ampliar demanda |
| Rango de **fechas de pedido** / marcas / búsqueda | No coincide | Ampliar fechas, quitar marcas, buscar por código |
| Solo hay **asignación a máquina** (orden verbal) | Aparece en el **Parte** con «Sin cupo Fabricando», **no** en el tablero | Misma resolución: demanda (reserva o pedido) → **Enviar** → Parte |

**Caso típico de planta:** recibieron orden de producir, asignaron el artículo a las máquinas, pero **no cargaron la reserva** del pack ni hay pedido visible. Resultado: Parte con filas grises; tablero sin el artículo. No hay “enviar forzado” sin Urgente.

### 3.6 Si cambia el pedido o la reserva después de Enviar

**Regla clave:** lo que ya envió **no se corrige solo**. Si cambia un pedido (cantidad, cancelación) o la reserva del pack, el tablero **recalcula** Pedido, Reserva, Urgente y lo sugerido a Enviar. El historial de **Enviado** queda igual hasta que usted **envíe más** o **anule envíos**.

#### Qué se recalcula al recargar el tablero

| Columna | ¿Se actualiza sola? | Cómo |
|---------|---------------------|------|
| Pedido / Reserva / Urgente / PED Urgente | **Sí** | Lee pedidos, reserva del pack y stock de cobertura 1.ª (Producido + Semi; PED Urgente no usa la reserva ni la 2.ª) |
| Sugerido **Enviar** | **Sí** | Lo que falta de Urgente después de restar Fabricando |
| **Enviado** | **No** | Solo crece con «Enviar a producción» y baja con «Anular envíos» |
| **Fabricando** | **No por demanda** | Baja al acreditar (Parte aprobado / Control de calidad) o al anular envíos no consumidos |

«Actualizar» en el tablero **no reescribe** envíos: solo refresca la vista con la demanda actual.

**Remito / facturación:** al remitir o facturar un renglón PED, AdministraNET baja `stockp.cantidad_pendiente`. Al recargar el tablero, **Pedido**, **PED Urgente** y **Urgente** bajan solos; no hace falta cancelar el PED. **Fabricando** no baja por eso: si quedó alto, use **Anular envíos** (más abajo).

#### Ejemplos (después de haber enviado 300)

Suponga que mandó **300** a fabricar y todavía no acreditó partes (Fabricando cerca de 300).

| Cambio posterior | Urgente | Enviado / Fabricando | Enviar sugerido | Qué hacer |
|------------------|---------|----------------------|-----------------|-----------|
| Cancela el pedido o baja mucho la reserva → casi no hay demanda | → **0** | Siguen cerca de **300** | **0** | Queda **sobre-enviado**. Para bajar cupo: **Anular envíos** (lo no usado en partes) o dejar que el Parte/CC acredite. |
| Baja el pedido / reserva pero sigue faltando algo (ej. Urgente nuevo = 100) | → **100** | cerca de **300** | **0** (300 ya cubre 100) | No envíe más. Si no quiere producir de más, anule el excedente de envíos. |
| Aumenta el pedido o sube la reserva → Urgente nuevo = 450 | → **450** | cerca de **300** | cerca de **150** | Complete **Enviar 150** y confirme. Se **suma** un nuevo envío; el de 300 no se modifica. |
| Aumenta demanda pero Fabricando ya alcanza o supera Urgente | → nuevo valor | sin cambio | **0** | Nada que enviar; el cupo del Parte ya alcanza. |

#### Cómo subir o bajar el cupo a propósito

**Subir (hacer Fabricando más grande)**

1. Aumente demanda: más cantidad en el pedido y/o suba la reserva del **pack**.
2. Tablero Par → Actualizar → verifique que **Enviar** sea mayor que 0.
3. **Enviar a producción** por esa diferencia.

**Bajar (reducir Fabricando / Enviado)**

1. Abra **Anular envíos** en el Tablero (supervisor).
2. Anule filas de envío **no usadas** por partes (no se puede anular lo ya usado en un parte aprobado).
3. Alternativa: seguir con Parte y Control de calidad hasta acreditar; Fabricando baja al acreditarse.

No existe un botón de «recalcular envíos = nueva demanda» ni anulación automática al cancelar un pedido.

#### Relación con el Parte

Mientras **Fabricando** sea mayor que 0, el Parte permite cargar hasta ese cupo **aunque** Urgente ya sea 0 (porque cancelaron el pedido después). Es intencional: la planta ya tenía trabajo enviado. Si la orden se cayó, anule envíos antes de seguir produciendo de más.

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
- Sale del tablero: lo enviado menos lo ya acreditado (parte previo, control de calidad, Semi/2da/Desperdicio).
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

Si después de aprobar necesita bajar o subir cantidades del mismo día (planilla), el sistema registra un **ajuste por diferencia** en el mismo depósito de Producción (entrada o salida según el caso); no “borra” el movimiento original. El cupo y el tablero se recalculan con lo acreditado.

Si el día ya tiene **control de calidad confirmado**, no podrá modificar el parte de ese alcance: primero resuelva la clasificación (hoy, correcciones de CC por movimiento de stock; ver §5).

---

## 5. Control de calidad

**Menú:** Producción → Control de calidad.

### Para qué sirve

Distribuir lo del **Parte** (y eventual extra en Producción) entre **Semi elaborado** (primera), **2da selección** y **Desperdicio**.

### Cómo usarlo

1. Elija **Fecha** → **Cargar grilla**. En la barra puede **buscar** artículo, alternar **Solo pendiente** / **Ver roster** y **Docenas | Pares**.
2. Cada bloque es un **artículo del día**. Arriba van los que tienen **turno y operario** en el parte (o CC ya cargado); al final, los que solo tienen saldo en Producción sin parte.
3. **Saldo producción** es el saldo vivo del depósito, en **docenas y pares enteros** (sin decimales). No usa el parte como tope.
4. **Semi elaborado** es uno por artículo. **2da** y **Desperdicio** van por operario + turno, **una sola casilla** cada uno. Si ya hay CC confirmado, esa casilla se muestra rellena en solo lectura y **no** se puede agregar más desde esta pantalla (correcciones por movimiento de stock). Si aún no hay confirmado, la casilla editable arranca en **0**.
5. Al abrir, los casilleros de carga nueva arrancan en **0** (el parte no se copia a Semi).
6. **Buscar artículo** es predictivo: al tipear se filtra la grilla en vivo.
7. Si Semi + 2da + desperdicio **nuevos** superan el saldo de producción, el bloque se marca en rojo hasta corregir.
8. Los botones quedan fijos al pie:
   - **Guardar borrador** — guarda sin mover stock. Un borrador viejo (por turno) no se convierte: aparece el aviso de recargar.
   - **Guardar control de calidad** — confirma y mueve stock Producción → Semi / 2da / Scrap.
9. Solo el CC **confirmado** con 2da/desperdicio (o Semi histórico con operario) bloquea el Parte. Semi nuevo sin operario no bloquea turnos.
10. En **Ver roster** se ve lo cargado aunque el saldo vivo ya sea 0. **No se reedita** un CC confirmado desde esta pantalla.

### Borrador vs confirmado (resumen)

| Acción | ¿Mueve stock? | ¿Bloquea el Parte? | ¿Se pierde al salir? |
|--------|---------------|--------------------|----------------------|
| Guardar borrador | No | No | No (queda guardado) |
| Guardar control de calidad | Sí | Sí (turno/fecha) | — (borra el borrador) |

### Correcciones después de confirmar

Para reclasificar entre Semi / 2da / Desperdicio use **Ingreso de movimiento de stock** con una **transferencia interna**. En esta versión **no** se puede corregir un control de calidad confirmado desde la misma pantalla (a diferencia del parte).

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
2. Elija la **fecha** en el selector (por defecto es **hoy**).
3. Habilite o quite los artículos que cada máquina puede producir **en esa fecha**.
4. En la grilla verá **Talle** y **Color** del artículo.
5. Pulse **Imprimir Control de Calidad**, elija la **fecha** de la planilla y confirme. Se imprime la hoja horizontal con artículos vigentes a esa fecha, cantidades del parte en **1ra** por turno y una fila vacía debajo de cada artículo para anotar la clasificación a mano.

Si no hay filas con artículos según el filtro, el sistema avisa en pantalla.

##### Fecha: cómo queda guardado el seteo (importante)

La grilla muestra los artículos **vigentes en la fecha elegida**. Lo que se guarda depende de si esa fecha es **hoy** o un **día pasado**:

| Si asigna con fecha… | Qué ocurre | ¿Sigue al día siguiente? |
|----------------------|------------|---------------------------|
| **Hoy** (fecha del día) | La asignación queda **persistente**: el artículo sigue habilitado mañana, pasado mañana, etc., hasta que alguien lo quite. | **Sí** |
| **Un día pasado** | La asignación (o el quitar) aplica **solo ese día**. Aparece el aviso amarillo en pantalla. No cambia lo que verá mañana ni lo ya seteado hacia adelante. | **No** |

**Regla práctica:** para que el seteo **persista** (que mañana y los días siguientes lo vean en Parte, planilla y esta pantalla), debe asignar con la fecha en **hoy**.

**Casos de uso:**

- **Armar o corregir la programación del día actual** → deje la fecha en **hoy**, asigne o quite artículos. Eso es lo que “queda” para la planta.
- **Completar o corregir un día ya pasado** (por ejemplo, para poder cargar un parte atrasado o imprimir la planilla de ese día) → elija ese día pasado. El cambio **no** se copia al día de hoy ni al futuro; si también lo necesita hoy, vuelva a poner la fecha en **hoy** y asigne de nuevo.

**Error frecuente:** entrar al día siguiente, poner el selector en el día de ayer, “cargar de nuevo” los artículos y esperar que eso quede para hoy. Eso solo deja rastro en el día pasado. Para persistir, hay que cargar con **hoy**.

Desde cada máquina puede abrir **Histórico** para ver las fechas en las que estuvo habilitado cada artículo.

### 8.3 Config. Depósitos

Indique, para cada depósito, si **suma al stock** y su **tipo** en producción, por ejemplo:

- Producción  
- Semi elaborado  
- 2da selección  
- Terminado  
- Desperdicio / scrap  

Sin esta configuración el tablero y el flujo de etapas no muestran saldos correctos.

**Bloquear parte que supera Fabricando:** interruptor que controla si al guardar o aprobar un parte se exige cupo Fabricando y respaldo de envíos del tablero. Con el bloqueo **activo**, las filas con Fabricando = 0 quedan sin carga. Con el bloqueo **inactivo**, esas celdas se habilitan y se puede aprobar aunque no haya envío (uso excepcional post-cutover). Dejarlo **activo** en operación normal y volver a activarlo cuando termine el ajuste.

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

Asigne el turno de cada operario **día a día**. Puede usar **asignación masiva** para varios operarios y un rango de fechas, con modos: **Agregar turno** (no quita otros del mismo día), **Solo si no tiene turno ese día**, o **Reemplazar día** (avanzado; quita turnos no bloqueados). En masiva puede elegir **plantilla de días** (todos, solo lun–vie o personalizado) y el atajo **Semana visible Lun–Vie**.

La pantalla usa la **barra densa de producción**: navegación de semana, **Asignación masiva**, **Gestionar turnos** y atajos al Tablero, Parte y Control de calidad. Debajo hay **filtros de grilla**: buscar operario por nombre, filtrar por **turno**, y vistas **Todos** / **Sin asignar** (días sin turno) / **Excepciones** (override de línea o multi-turno). Se muestra cuántos operarios coinciden; **Limpiar filtros** restaura la vista completa.

La **grilla es compacta**: cada celda muestra chips de turno (y candado si está bloqueada). **Hacé clic en una celda** para abrir el editor: cambiar línea, quitar o agregar turnos. Al quitar un turno o usar «Reemplazar día» en masiva, Synap pide confirmación en un modal (no ventanas del navegador).

Sin turno del día, el operario no podrá cargar su parte.

---

## 9. Resumen rápido

| Momento | Pantalla | Acción |
|---------|----------|--------|
| Arranque de planta | Configuración (líneas → máquinas → depósitos → operarios → vínculos → turnos → planificación) | Dejar lista la fábrica |
| Ajustar colchón | Artículo **pack** en AdministraNET (reserva de stock) | Sube Reserva/Urgente en tablero tras Actualizar |
| Mañana / turno | Tablero de producción (modo **Par**) | Enviar solo si **Urgente** es mayor que 0 |
| Durante el turno | Parte / Carga de producción | Borrador sin stock; aprobar hasta el cupo **Fabricando** |
| Supervisor | Partes pendientes | Aprobar partes de operarios |
| Después del parte | Control de calidad | Borrador sin stock; confirmar mueve a Semi/2da/Scrap |
| Cierre de producto | Armado | Armar packs 1ra o 2da |
| Contra pedidos | Imputación de pedido | Asignar Armado 1ra a pedidos |

---

## 10. Problemas frecuentes

- **No veo el artículo en el tablero (sí en el Parte / máquinas):** falta demanda. Sin pedido ni reserva del **pack**, o pack sin receta, o filtro Solo urgentes. Ver §3.5. Asignar a máquina **no** lo publica en el tablero.
- **No veo demanda en el tablero:** revise filtros de fecha y marcas; pulse Actualizar; desactive Solo urgentes; confirme reserva del pack o pedido (§3.4 / §3.5).
- **Remité o facturé y Pedido / PED Urgente / Urgente bajaron solos:** es lo esperado. El tablero lee el saldo comercial (`cantidad_pendiente`); no hace falta cancelar el PED. Si **Fabricando** quedó alto, use **Anular envíos** (§3.6).
- **Cancelé / bajé el pedido o la reserva pero Fabricando sigue alto:** es normal. Los envíos **no se ajustan solos**. Anule envíos no usados o acredite con Parte/Control de calidad. Ver §3.6.
- **Subí el pedido o la reserva y no puedo enviar el total de nuevo:** el sistema solo sugiere la **diferencia** (lo urgente menos lo que ya está fabricando). Envíe esa diferencia; el envío anterior no se borra. Ver §3.6.
- **Veo un pack en ámbar «Sin receta»:** el terminado no tiene lista de materiales. Use el ícono de pedidos para ver qué pedidos lo piden; complete la receta. En Par no podrá enviar componentes de ese pack hasta tener receta.
- **Reserva alta pero Urgente en 0:** es normal si el stock en camino ya alcanza. No envíe más; el colchón objetivo no es un faltante.
- **PED Urgente menor que Urgente:** normal cuando hay Reserva: Urgente incluye el colchón; PED Urgente solo el pedido.
- **PED Urgente = 0 y Urgente mayor que 0:** hay colchón a reponer pero no demanda de pedido abierta (o el pedido ya está cubierto).
- **Parte con «Sin cupo Fabricando» / celdas grises:** nunca enviaron (o Fabricando = 0). No se puede cargar hasta **Enviar** desde el tablero. Si el artículo no está en el tablero, primero genere demanda (§3.5 / §4.1.1).
- **Quiero cargar más en el Parte que el verde (Fabricando):** primero **Enviar** desde el tablero (hace falta Urgente). Subir solo la Reserva del componente no alcanza; edite la reserva del **pack** y envíe.
- **No sé en qué artículo tocar la reserva:** el pack terminado cuya receta incluye el componente de la fila Par (ver §3.4).
- **No puedo guardar el parte (aprobar):** no hay cupo en Fabricando, el día tiene control de calidad confirmado, o faltan operarios en el turno.
- **El operario no puede cargar:** falta vínculo usuario–operario, turno del día, línea o artículos en la máquina.
- **No hay filas en Control de calidad:** no hay pendiente en Producción para esa fecha/turno (falta parte).
- **Perdí la carga a mitad de Control de calidad:** use **Guardar borrador**; al volver se precarga. El borrador no bloquea el parte.
- **No puedo armar:** stock insuficiente en el depósito origen o el pack no tiene lista de materiales (1ra).
- **Nada para imprimir en la planilla:** no hay máquinas con artículos según el filtro; asigne artículos o cambie el filtro.
- **Ayer asigné artículos y hoy no aparecen / tuve que cargar de nuevo:** casi seguro se cargó con el selector en un **día pasado** (solo aplica ese día). La persistencia se logra asignando con la fecha en **hoy**. Ver §8.2.
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
| **Reserva** | Colchón objetivo del pack; se muestra repartido en los componentes. |
| **Urgente** | Lo que todavía falta fabricar (pedido + reserva menos Producido y Semi; no resta 2.ª). Define Enviar y Solo urgentes. |
| **PED Urgente** | Lo que falta solo por pedido (sin reserva ni 2.ª). Solo para consultar. |
| **Fabricando** | Lo enviado que aún no se acreditó; cupo del Parte. |
| **Enviar** | Mandar trabajo desde el tablero a fábrica. |
| **Anular envíos** | Baja envíos no usados; no ocurre solo al cambiar pedido o reserva. |
| **Borrador (parte o CC)** | Guardado intermedio **sin** mover stock. |
| **Confirmar / aprobar** | Cierra el registro oficial y **sí** mueve stock (según la pantalla). |
| **Stock en camino (cobertura 1.ª)** | Producción + Semi. Lo que el sistema resta al calcular Urgente / PED Urgente. La 2.ª no entra: hay que rehacerla. |
| **Receta** | Lista de materiales del pack → componentes. |

---

*Manual de usuario – Producción (MPR). Synap. Actualizado 20/08/2026.*
