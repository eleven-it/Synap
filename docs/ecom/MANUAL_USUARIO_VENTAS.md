# Manual de usuario – Ventas

Guía práctica del módulo **Ventas** para vendedores, supervisores, administradores comerciales y operadores de **Finanzas / Créditos**.

**Antes de empezar:** iniciar sesión y seleccionar la empresa con la que va a trabajar.

En la mayoría de las pantallas del módulo verá **migas de pan** (breadcrumb) en la parte superior, con el formato **Ventas / …**, que indica dónde está dentro del módulo.

**Manual HTML en la app:** **`/ecom/manual/`** (requiere sesión). En cada pantalla del menú Ventas (y en crédito) hay un botón **Ayuda** que abre el manual en la sección correspondiente. Regenerar HTML: `python3 scripts/generar_manuales_html.py` (genera `ecom/static/ecom/manuales/manual_usuario_ventas.html` y copia en `docs/ecom/`).

**Fechas en pantalla:** siempre en formato **dd/MM/yyyy**.

---

## 1. Acceso al módulo

1. En el menú principal de Synap, abra **Ventas**.
2. Elija la opción según la tarea (presupuestos, pedidos, precios, objetivos, crédito, etc.).
3. Revise el breadcrumb **Ventas / …** para confirmar la pantalla activa.

---

## 2. Presupuestos

**Menú:** Ventas → Comprobantes → **Presupuestos**.

### Para qué sirve

Listar, crear y consultar **presupuestos de venta** antes de convertirlos en pedidos o facturas.

### Cómo acceder

Menú **Ventas** → **Presupuestos**. Breadcrumb: **Ventas / Presupuestos**.

### Pasos básicos

1. En el listado, filtre por fecha, cliente o estado si lo necesita.
2. Pulse **Nuevo presupuesto** para cargar cabecera, cliente y renglones.
3. Guarde o emita según su permiso (`carga_comp_ped`).
4. Para consultar uno existente, ábralo desde el listado (breadcrumb: **Ventas / Presupuestos / Detalle**).

### Crédito en presupuestos (PRE)

Si la empresa tiene activo el **workflow de crédito en pedidos**, al confirmar un **PRE** el sistema evalúa el mismo motor que en PED (políticas por canal **PRE**). El presupuesto puede quedar **No Autorizado** y, según configuración, entrar a cola Finanzas. El alta **no se bloquea**: el documento se registra y queda pendiente de revisión de crédito.

---

## 3. Pedidos (hub)

**Menú:** Ventas → Comprobantes → **Pedidos**.

**Ruta:** `/ecom/mayoristapp/pedidos/`  
**Breadcrumb:** **Ventas / Pedidos**.

### Para qué sirve

Pantalla **inicial de pedidos**: ver borradores, pedidos enviados, en curso, cerrados o anulados; continuar un trabajo pendiente o crear uno nuevo. También concentra las colas de **aprobación comercial** y de **crédito Finanzas** cuando están activas.

### Pasos básicos

1. Use la vista **Lista** o **Kanban** (según preferencia).
2. Busque por número de pedido, cliente o sucursal.
3. Pulse **Continuar** en un borrador o **Nuevo** → **Pedido simple** o **Masivo sucursales**.
4. Si el workflow de **aprobación comercial** está activo, revise columnas **Por autorizar** / **Aprobado**.
5. Si el workflow de **crédito** está activo, verá la columna **Crédito Finanzas** (o equivalente) con PED pendientes de liberación por Finanzas. Detalle completo en [§11. Flujo de crédito](#11-flujo-de-crédito-en-pedidos).
6. Los **lotes de carga masiva** aparecen como tarjetas en la columna operativa del Kanban (no hay una lane separada «Cargas masivas»). Los PED hijos del lote no se listan individualmente en el hub; use el **resumen de lote** para ver el detalle.
7. **Pedidos migrados desde BEST** (cutover): se identifican por comprobante/origen de migración. Al abrirlos verá el aviso de **solo lectura**. No se editan ni se confirman como un pedido operativo normal.
8. En vista **Lista**, las columnas son: **Pedido** (estado), **Documento**, **Cliente**, **Sucursal** (solo número), **Vendedor**, **Total** y **Fecha**.
9. En vista **Kanban**, cada tarjeta PED muestra el **cliente en violeta**, el total y la sucursal como **Sucursal N** (solo el número).

### Dos colas distintas (importante)

| Cola | Quién actúa | Permiso típico | Qué libera |
|------|-------------|----------------|------------|
| **Por autorizar** (comercial) | Supervisor / gerente comercial | `ecom.pedidos.aprobar` | Descuentos, montos, cliente nuevo, etc. |
| **Crédito Finanzas** | Finanzas / Créditos | `finance.credito.aprobar` | Pedido **No Autorizado** por límite de crédito |

Un mismo PED puede estar pendiente en **ambas** colas a la vez. En ese caso la tarjeta prioriza la columna de **crédito Finanzas** y muestra un aviso de pendiente dual. Aprobar crédito **no** aprueba lo comercial, y viceversa.

### CTAs en la tarjeta (crédito)

Si su usuario tiene permiso de crédito, en la tarjeta verá botones **Aprobar crédito** / **Rechazar**.

- **Aprobar:** libera ese PED (`Autorizado`), quita el hold de preparación si estaba activo. **No cambia** el cupo de crédito del cliente (`Credito` en ficha).
- **Rechazar:** pide **motivo obligatorio** (modal Synap). El PED sigue retenido para preparación.

Sin permiso de crédito no verá esos botones (aunque vea la columna).

---

## 4. Pedido masivo por sucursales (y pedido simple)

**Menú:** Ventas → Comprobantes → **Pedido masivo sucursales**.

**Breadcrumb:** **Ventas / Pedidos / Pedido masivo**.

### Para qué sirve

Cargar cantidades para **varias sucursales** del mismo cliente en una sola operación (matriz). También concentra el **pedido simple** (una sucursal) con `?modo=simple`.

### Pasos básicos

1. Desde el hub de pedidos, elija **Nuevo** → **Masivo sucursales** (o **Pedido simple**) o abra un borrador existente.
2. En la barra superior verá el título y las acciones (confirmar, hub, etc.). Debajo, la tarjeta **Contexto comercial** (colapsable) concentra cliente, fechas, lista y condición: complete esos datos antes de cargar la matriz. La **fecha de entrega** se completa sola la primera vez (10 días después del vencimiento; si cae fin de semana, el lunes siguiente). Lista, condición y descuentos los cambia el supervisor o el vendedor cuyo puesto tenga esos permisos en **Archivo → Permiso en sistema**.
3. Al elegir **cliente**, revise el **widget de crédito** en el encabezado (semáforo). Ver [§11.2](#112-semáforo-de-crédito-en-la-toma).
4. Busque artículos por código de sistema, código manual, nombre o **código de barra**; complete cantidades en la grilla (packs / múltiplos de empaque) y confirme el pedido.
   Si ingresa una cantidad inválida, el sistema muestra un aviso con la unidad de empaquetado antes de guardar o confirmar.
   Para clientes con muchas sucursales (p. ej. cadenas), use **Descargar plantilla** e **Importar Excel** en el contexto comercial: el archivo ya trae los artículos de su territorio (una fila por color/SKU; código, nombre y cantidades). El descuento al pie y el resto salen del cliente. No suba una plantilla de otro cliente. Si un SuperArt tiene varios colores, cada color es una fila.
5. Si el semáforo está **ámbar** o **rojo**, al confirmar puede aparecer un **modal de advertencia de crédito**. Puede **continuar** (el pedido se registra igual) o **cancelar** para revisar el carrito / cobranza.
6. Tras confirmar, puede abrir el **resumen del lote** para revisar lo cargado y, si aplica, el flujo de autorización comercial del lote completo.
7. Use **Hub pedidos** (o el breadcrumb) para retomar otros pedidos.

### Widget en pedido masivo

En la matriz, el crédito del cliente muestra por separado:

- **Cupo monetario** (tope en pesos, si aplica).
- **Límite de mora en días**.

No confunda ambos valores: un cliente puede tener cupo en pesos y a la vez estar excedido en días de atraso.

---

## 5. Vendedor · Cliente · Marca

**Menú:** Ventas → Comprobantes → **Vendedor · Cliente · Marca**.

**Breadcrumb:** **Ventas / Pedidos / Vendedor · Cliente · Sucursal · Marca**.

### Para qué sirve

Definir el **territorio comercial**: qué vendedor atiende a cada cliente, sucursal y marca.

### Pasos básicos

1. Busque y seleccione vendedor, cliente, sucursal y marca.
2. Cree la relación; el sistema avisa si ya existe otro vendedor para la misma combinación.
3. Para dar de baja una relación, utilice **Anular** en el listado de ternas activas.

---

## 6. Actualización de precios

**Menú:** Ventas → Comprobantes → **Actualización de precios**.

**Breadcrumb:** **Ventas / Actualización de precios** (o equivalente en pantalla).

### Para qué sirve

Consultar y modificar **precios terminados** de artículos según lista de precios vigente.

### Pasos básicos

1. Filtre por lista, rubro, marca o artículo.
2. Edite precios en la grilla (según permiso `ventas.precios_terminados.editar`).
3. Guarde los cambios; revise el historial si la pantalla lo ofrece.

---

## 7. Evolución de precios

**Menú:** Ventas → Comprobantes → **Evolución de precios**.

### Para qué sirve

Analizar la **variación de precios** en un período (ranking de artículos con mayor cambio).

### Pasos básicos

1. Elija lista de precios y rango de fechas.
2. Revise el ranking y exporte o navegue al detalle de un artículo si está disponible.
3. Desde el encabezado puede volver a **Actualización de precios**.

---

## 8. Ajustes de ventas

**Menú:** Ventas → Ajustes → **Ajustes de ventas**.

**Breadcrumb:** **Ventas / Ajustes de ventas**.

### Para qué sirve

Configurar parámetros del flujo de **pedidos mayorista**: validación de stock, mail al confirmar, workflow de aprobación comercial, atajos en el hub, etc.

### Pasos básicos

1. Revise cada toggle o umbral (requiere permiso `ecom.config_ajustes_ventas`).
2. Active o desactive reglas según política comercial de la empresa.
3. Guarde; los cambios aplican a pedidos nuevos o confirmaciones posteriores.

### Relación con crédito

La **aprobación comercial** (umbrales de monto / descuento) es **independiente** del workflow de crédito Finanzas.

Los flags maestros de crédito (`ecom_credito_pedidos_activa`, hold de preparación, SLA de mails) los configura el administrador de sistema / implementación en `configuracion_ecom` (herramienta de esquema / soporte). Ver [§11.8](#118-activación-para-administradores). Si el flag de crédito está **apagado**, el sistema se comporta como antes (solo control de mora en días al confirmar, sin cola Finanzas ni semáforo ampliado).

---

## 9. Asignación vendedor

**Menú:** Ventas → Gestión → **Asignación vendedor**.

### Para qué sirve

Reasignar **clientes entre vendedores** (operación administrativa distinta del territorio por marca).

### Pasos básicos

1. Busque el cliente o vendedor origen.
2. Seleccione el vendedor destino y confirme la reasignación.
3. Verifique en pedidos o listados que el cliente quede bajo el vendedor correcto.

---

## 10. Objetivos de venta

**Menú:** Ventas → Objetivos → **Objetivos de venta**.

### Para qué sirve

Definir y hacer seguimiento de **objetivos comerciales** por período, vendedor o dimensión configurada.

### Pasos básicos

1. En el listado de períodos, cree uno nuevo o abra un período existente.
2. Cargue metas y montos objetivo por vendedor o categoría según la grilla.
3. Guarde y consulte avance desde la misma pantalla o informes vinculados.

---

## 11. Flujo de crédito en pedidos

Esta sección describe el **control de límite de crédito** para pedidos (PED) y presupuestos (PRE) del canal mayorista, cuando la empresa lo tiene activo.

### 11.1. Conceptos en lenguaje de negocio

| Concepto | Qué significa para usted |
|----------|---------------------------|
| **Cupo monetario (`Credito`)** | Tope de deuda en pesos del cliente. Si vale **0**, el cliente **no tiene tope en pesos** (puede operar por monto; igual puede restringirse por mora en días). |
| **Saldo / cuenta corriente** | Deuda abierta del cliente. |
| **Exposición** | Suma de lo que “ocupa” crédito: cuenta corriente, pedidos abiertos, remitos no facturados, cheques en cartera y el documento que está cargando (según lo que active Finanzas en la política). |
| **Disponible** | Cupo − exposición (solo si hay cupo &gt; 0). |
| **Límite de mora (días)** | Días máximos de atraso del comprobante impago más antiguo. Si se supera → **No Autorizado**. |
| **Autorizado / No Autorizado** | Resultado del sistema en el pedido. **No Autorizado** no impide grabar el PED; sí puede impedir **prepararlo** hasta que Finanzas apruebe. |
| **Hold de preparación** | Bloqueo para pasar el pedido a “En preparación” / depósito mientras el crédito no esté liberado. |
| **Cola Finanzas** | Lista de PED que Finanzas debe aprobar o rechazar. |

Modelo de control: similar a un ERP de mercado (exposición por capas) + reglas propias de AdministraNET (mora en días y cheques opcionales).

### 11.2. Semáforo de crédito en la toma

Al seleccionar el cliente (pedido simple o masivo), el encabezado muestra un **widget de crédito** con colores:

| Color | Significado | Qué hacer |
|-------|-------------|-----------|
| **Verde** | Dentro de cupo y mora aceptable | Continúe con normalidad. |
| **Ámbar** | Cerca del límite o situación a revisar | Puede confirmar; el sistema puede pedir una confirmación consciente (modal). |
| **Rojo** | Excede cupo y/o mora | Puede confirmar igual (el pedido se registra). Espere revisión de Finanzas si la cola está activa. Ofrezca cobranza o ajuste de cantidades si corresponde. |

Datos que suele mostrar el widget (con workflow activo):

- Exposición y disponible (o «Sin tope monetario» si `Credito = 0`).
- Días de mora y límite de mora configurado.
- Mensaje en español (autorizado / requiere revisión).

Con workflow **inactivo**, verá el resumen clásico (saldo CC y límite en días / autorizado).

### 11.3. Confirmar el pedido (vendedor)

1. Complete cliente, renglones y totales.
2. Pulse **Confirmar**.
3. Si el semáforo es ámbar/rojo, lea el **modal de advertencia de crédito**:
   - **Cancelar:** vuelve al carrito.
   - **Continuar / Confirmar:** graba el PED/PRE.
4. El pedido **siempre se puede grabar** aunque quede No Autorizado (no hay hard-block de toma).
5. Si quedó No Autorizado y la cola Finanzas está activa:
   - El PED aparece en **Crédito Finanzas** del hub y/o en `/ecom/credito/cola/`.
   - Puede enviarse un **mail automático** al cliente (plantilla de aviso), sin spam (ver §11.7).
6. Informe al cliente: “el pedido quedó registrado; falta liberación de crédito / cobro” cuando corresponda.

**No use** ventanas nativas del navegador (`Aceptar`/`Cancelar` del sistema): Synap usa sus propios modales.

### 11.4. Qué ve Finanzas / Créditos

**Pantalla dedicada:** menú **Ventas → Crédito → Cola crédito Finanzas** (también en **E-commerce → Crédito**).  
**Ruta:** `/ecom/credito/cola/`  
**Título:** Pendiente crédito Finanzas.  
**Permiso para ver el ítem de menú y entrar:** `finance.credito.aprobar` (asignado al **puesto** del usuario).

#### Pasos en la cola

1. Abra la cola (o use los CTAs del hub).
2. Revise cada renglón: número de PED, cliente, fecha, **importe**, **cupo / saldo AdministraNET**, disponible, días de mora y **semáforo** (verde / ámbar / rojo) con motivos.
3. Filtre por cliente o número, o cambie la antigüedad (30 / 60 / 90 días).
4. **Aprobar crédito:** confirme en el modal Synap. Libera ese PED; el cupo del cliente **no se modifica**.
5. **Rechazar:** escriba el **motivo** (obligatorio) y confirme en el modal. El PED sigue retenido.
6. Use **Volver al hub** para seguir el resto del pipeline.

Si la cola está vacía: es normal cuando no hay PED **No Autorizado** recientes, o si el workflow está desactivado para la empresa. Los cupos cargados en AdministraNET se consultan en **Políticas de crédito** (panel «Consultar cupo»).

#### Qué implica aprobar

- `autorizacion_sistema` del PED pasa a **Autorizado**.
- Se quita el **hold de preparación** (si estaba activo).
- Queda auditoría del evento (quién / cuándo / motivo).
- El depósito / VB6 puede preparar el pedido (si también aplica el parche de preparación en escritorio).

#### Qué implica rechazar

- El PED permanece No Autorizado / hold según reglas.
- El vendedor debe gestionar cobro, reducir pedido o esperar nueva política.
- El motivo queda registrado para trazabilidad.

### 11.5. Políticas de crédito (configuración)

**Menú:** Ventas → Crédito → **Políticas de crédito** (también E-commerce → Crédito).  
**Ruta:** `/ecom/credito/politicas/`  
**Alta:** `/ecom/credito/politicas/nueva/`  
**Permiso para ver el menú y entrar:** `finance.credito.configurar` (distinto del de aprobar).

#### Para qué sirve

El **cupo en pesos** (`Credito`), el **saldo** y los **días base** viven en AdministraNET (ficha del cliente). En Synap se definen **overrides de política** por cliente y canal (PED o PRE):

- Límite de mora en días (si se completa, reemplaza el de AdministraNET para ese canal; vacío = usar el del cliente).
- Capas de exposición a sumar: cuenta corriente, pedidos abiertos, remitos no facturados, cheques, documento actual, incluir mora.
- Activo / inactivo.

En el listado use el panel **Consultar cupo AdministraNET** (búsqueda predictiva) para ver cupo, saldo y días **sin crear** una política. Con la opción **Usar política default empresa** activa, la política aplica a todos los clientes sin política propia.

#### Pasos

1. Abra el listado de políticas (revise cupos Adminet en el panel de consulta si lo necesita).
2. Pulse **Nueva política**.
3. Busque el cliente por **nombre, código o CUIT** (dropdown predictivo) o active default empresa.
4. Revise el panel **Límites AdministraNET** (solo lectura).
5. Complete canal (**solo PED o PRE**), días de política y capas; guarde.
6. Verifique en una toma de pedido de prueba el semáforo y el resultado al confirmar.

**Segregación:** un usuario que solo puede **aprobar** no puede cambiar políticas. Un usuario que solo puede **configurar** no puede aprobar/rechazar en la cola.

### 11.6. Plantillas de aviso / cobranza

**Menú:** Ventas → Crédito → **Plantillas aviso crédito**.  
**Ruta:** `/ecom/credito/plantillas/`  
**Permiso:** `finance.credito.configurar`.

#### Para qué sirve

Editar textos de correo que se disparan cuando un pedido queda bloqueado por crédito (y otros tipos de aviso configurados), por canal y opcionalmente por cliente.

#### Campos habituales

- Tipo de aviso (selector: **pedido bloqueado**, cobranza u otro).
- Canal (PED / PRE).
- Asunto y cuerpo del mensaje (puede insertar variables con los chips).
- Cliente opcional por búsqueda predictiva (vacío = plantilla general).

#### Anti-ruido (para no spam)

- Por defecto, no se reenvía el mismo tipo de aviso al mismo cliente/canal antes de **24 horas**.
- Para **pedido bloqueado**, además: **un solo mail por número de pedido** mientras esté retenido (si el vendedor confirma varias veces, no multiplica correos).

Los mails salen por la cola de correo de ecom (requiere SMTP / worker de cola configurado por IT).

### 11.7. Preparación de pedidos y hold

Con **hold de preparación** activo:

1. Un PED **No Autorizado** queda marcado para no prepararse.
2. En Synap, cualquier intento de avanzar a preparación debe **rechazarse** con mensaje en español.
3. En AdministraNET escritorio (VB6 **Pedido_prep**), el operador también debe ver el bloqueo cuando esté aplicado el parche companion (columna `credito_hold_prep`).
4. Solo tras **aprobar crédito** en Finanzas se libera la preparación de **ese** pedido.

Si el hold está **apagado** pero el PED está No Autorizado, el pedido igual puede requerir revisión operativa; consulte a su administrador.

### 11.8. Activación para administradores

Orden recomendado (equipo IT / implementación):

1. Ejecutar el proveedor de esquema **`ecom_credito_pedidos`** (herramienta global de migración MySQL legacy).
2. Dejar flags en **No** y validar pedidos normales.
3. Asignar a puestos:
   - Rol con `finance.credito.aprobar` → operadores de cola.
   - Rol con `finance.credito.configurar` → quien define políticas y plantillas.
4. Cargar políticas default PED/PRE y plantillas de aviso.
5. Activar `ecom_credito_pedidos_activa = Si` por empresa.
6. Cuando Finanzas esté lista, activar `ecom_credito_hold_prep_activo = Si`.
7. Coordinar parche VB6 de preparación con el mismo criterio.
8. Ajustar `ecom_credito_aviso_sla_horas` (default 24) si necesitan otra ventana.

**Apagar el módulo (rollback operativo):** `ecom_credito_pedidos_activa = No`. Vuelve el comportamiento legacy (evaluación solo por días). Las tablas y pantallas permanecen.

Documentación técnica: [CREDITO_PEDIDOS_WORKFLOW.md](CREDITO_PEDIDOS_WORKFLOW.md).

### 11.9. Permisos — resumen rápido

| Acción | Permiso | Pantalla / menú |
|--------|---------|-----------------|
| Ver / tomar pedidos | Sesión mayorista + permisos ecom habituales | Hub / toma |
| Aprobar o rechazar crédito | `finance.credito.aprobar` | **Ventas → Crédito → Cola crédito Finanzas** · hub CTAs · `/ecom/credito/cola/` |
| ABM políticas y plantillas | `finance.credito.configurar` | **Ventas → Crédito → Políticas / Plantillas** |
| Aprobación comercial (descuentos, etc.) | `ecom.pedidos.aprobar` | Columna Por autorizar |

Los permisos se asignan por **Puesto** en la administración de permisos Synap (`/core/permisos-puesto/` o flujo equivalente de su instalación).

### 11.10. Problemas frecuentes (crédito)

| Situación | Qué revisar |
|-----------|-------------|
| No veo semáforo / columnas Finanzas | Flag `ecom_credito_pedidos_activa` apagado, o sin recargar sesión/empresa. |
| Confirmo y el PED queda No Autorizado | Normal si hay exceso de cupo o mora. El alta es válida; espere Finanzas o gestione cobro. |
| No puedo preparar el pedido | Hold activo: pida aprobación a Finanzas o revise cobro. |
| No veo botones Aprobar crédito | Falta permiso `finance.credito.aprobar` en su puesto. |
| No puedo guardar políticas | Falta `finance.credito.configurar` (aprobar solo no alcanza). |
| El cliente tiene Credito = 0 y “pasa” por monto | Correcto: **0 = sin tope monetario**. Puede fallar igual por **días** de mora. |
| Llegan muchos mails al cliente | Revise SLA (24 h) y plantillas; un PED bloqueado no debe reenviar el mismo aviso. |
| Pedido masivo muestra mal el cupo | Debe verse cupo $ separado del límite en días; si no, reporte a soporte (bug de naming corregido en esta versión). |
| WhatsApp en avisos | No disponible en esta versión (solo correo). |
| Aprobé crédito y el cupo del cliente cambió | No debe pasar: la liberación es **solo del PED**. Si cambió el cupo, fue otra operación (ABM cliente). |

---

## 12. Resumen rápido por rol

### Vendedor

1. Elija cliente → mire el **semáforo**.
2. Cargue renglones → confirme (modal si ámbar/rojo).
3. Si quedó No Autorizado, avise cobranza / espere Finanzas.
4. No intente “forzar” preparación: el hold lo bloquea a propósito.

### Supervisor comercial

1. Atienda columna **Por autorizar** (descuentos / montos).
2. No use esa cola para liberar crédito: eso es Finanzas.
3. Coordine con Finanzas si el PED tiene pendiente dual.

### Finanzas / Créditos

1. Atienda `/ecom/credito/cola/` o CTAs del hub.
2. Apruebe o rechace **con motivo** cuando rechace.
3. Recuerde: aprobar **no sube** el cupo del cliente.
4. Quien configure políticas/plantillas necesita el permiso **configurar**.

### Administrador

1. Active flags por empresa tras capacitar a Finanzas.
2. Asigne permisos por puesto (aprobar ≠ configurar).
3. Valide una toma de pedido de punta a punta (semáforo → confirmación → cola → preparación).

---

## Referencias técnicas

| Tema | Documento |
|------|-----------|
| Hub de pedidos | [PEDIDOS_HUB_KANBAN.md](PEDIDOS_HUB_KANBAN.md) |
| Pedido masivo | [PEDIDO_MASIVO_SUCURSALES.md](PEDIDO_MASIVO_SUCURSALES.md) |
| Vendedor · Cliente · Marca | [VENDEDOR_CLIENTE_MARCA.md](VENDEDOR_CLIENTE_MARCA.md) |
| Ajustes de ventas | [AJUSTES_VENTAS.md](AJUSTES_VENTAS.md) |
| **Crédito pedidos (operativo)** | [CREDITO_PEDIDOS_WORKFLOW.md](CREDITO_PEDIDOS_WORKFLOW.md) |
| Índice ecom | [README.md](README.md) |

---

*Manual de usuario – Ventas. Synap. Actualizado 25/07/2026.*
