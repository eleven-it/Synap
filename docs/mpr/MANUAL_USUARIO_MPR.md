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

---

## 3. Tablero de producción

**Menú:** Producción → Tablero de producción.

### Para qué sirve

Es la pantalla principal del día: muestra la demanda (según pedidos), cuánto falta, qué está en curso y permite **enviar cantidades a producción**.

### Cómo usarlo

1. Filtre por fechas de pedido, marcas o **Solo urgentes** si necesita enfocarse.
2. Elija vista **Pack** (producto terminado) o **Par** (componente). Para enviar a producción use modo **Par**.
3. Si hace falta, pulse **Actualizar vista** para refrescar la demanda desde los pedidos.
4. Complete **Enviar docenas** o **Enviar pares** en las filas que correspondan y pulse **Enviar a producción**. Confirme el envío.
5. Desde el encabezado puede ir a Parte de producción, Control de calidad o Armado.

### Avisos frecuentes

- «Sin cantidades a enviar»: cargue al menos una cantidad antes de confirmar.
- «Sin artículos/packs con demanda…» o «Sin resta urgente…»: no hay filas con el filtro actual; amplíe fechas o quite filtros.
- «Ningún artículo coincide con la búsqueda.»
- Tras un envío correcto: mensaje de componentes enviados a producción.

---

## 4. Parte de producción

Hay dos formas de cargar lo producido.

### 4.1 Parte de producción (supervisor)

**Menú:** Producción → Parte de producción.

1. Elija **Fecha**, **Turno** y marcas → **Cargar grilla**.
2. Por artículo y operario, cargue **Docenas** y/o **Pares**. La fila indica cuánto queda en **Fabricando**.
3. Pulse **Guardar parte de producción**.

**Avisos frecuentes**

- «No hay operarios asignados a este turno/fecha.» Complete la planificación de turnos.
- «No hay componentes con cupo en Fabricando…» Primero envíe trabajo desde el Tablero de producción.
- La suma por fila no puede superar lo que está en Fabricando (salvo que la planta permita otra regla).
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

---

## 5. Control de calidad

**Menú:** Producción → Control de calidad.

### Para qué sirve

Distribuir lo que está en **Producción** entre **Semi elaborado**, **2da selección** y **Desperdicio**, según el resultado del control.

### Cómo usarlo

1. Elija **Fecha** y **Turno** → **Cargar grilla**.
2. Por fila, cargue cantidades en las columnas de clasificación (sin superar el pendiente).
3. Pulse **Guardar control de calidad**.

**Avisos frecuentes**

- «No hay pendiente de control de calidad…»: primero debe existir un parte aprobado/registrado para esa fecha y turno.
- Corrija las filas en rojo (superan el saldo) antes de guardar.

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
3. En la grilla verá **Talle** y **Color** del artículo.
4. Pulse **Imprimir Control de Calidad** para la planilla de planta (hoja horizontal con casilleros para turnos y observaciones).

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

Sin turno del día, el operario no podrá cargar su parte.

---

## 9. Resumen rápido

| Momento | Pantalla | Acción |
|---------|----------|--------|
| Arranque de planta | Configuración (líneas → máquinas → depósitos → operarios → vínculos → turnos → planificación) | Dejar lista la fábrica |
| Mañana / turno | Tablero de producción | Enviar lo que hay que fabricar |
| Durante el turno | Parte / Carga de producción | Registrar lo producido |
| Supervisor | Partes pendientes | Aprobar partes de operarios |
| Después del parte | Control de calidad | Clasificar a semi, 2da o desperdicio |
| Cierre de producto | Armado | Armar packs 1ra o 2da |
| Contra pedidos | Imputación de pedido | Asignar Armado 1ra a pedidos |

---

## 10. Problemas frecuentes

- **No veo demanda en el tablero:** revise filtros de fecha y marcas; pulse Actualizar vista.
- **No puedo guardar el parte:** no hay cupo en Fabricando o faltan operarios en el turno.
- **El operario no puede cargar:** falta vínculo usuario–operario, turno del día, línea o artículos en la máquina.
- **No hay filas en Control de calidad:** no hay pendiente en Producción para esa fecha/turno (falta parte).
- **No puedo armar:** stock insuficiente en el depósito origen o el pack no tiene lista de materiales (1ra).
- **Nada para imprimir en la planilla:** no hay máquinas con artículos según el filtro; asigne artículos o cambie el filtro.
- **Empresa incorrecta:** cambie de empresa en la sesión e intente de nuevo.

---

*Manual de usuario – Producción (MPR). Synap. Actualizado 20/07/2026.*
