# Manual de usuario – Ventas

> **Manual en construcción / primera versión.** Este documento resume el menú **Ventas** en Synap; se ampliará con capturas y casos frecuentes.

Guía práctica del módulo **Ventas** para vendedores, supervisores y administradores comerciales.

**Antes de empezar:** iniciar sesión y seleccionar la empresa con la que va a trabajar.

En la mayoría de las pantallas del módulo verá **migas de pan** (breadcrumb) en la parte superior, con el formato **Ventas / …**, que indica dónde está dentro del módulo.

**Manual HTML en la app:** **`/ecom/manual/`** (requiere sesión). En cada pantalla del menú Ventas hay un botón **Ayuda** que abre el manual en la sección correspondiente. Regenerar HTML: `python3 scripts/generar_manuales_html.py` (genera `ecom/static/ecom/manuales/manual_usuario_ventas.html` y copia en `docs/ecom/`).

---

## 1. Acceso al módulo

1. En el menú principal de Synap, abra **Ventas**.
2. Elija la opción según la tarea (presupuestos, pedidos, precios, objetivos, etc.).
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

---

## 3. Pedidos (hub)

**Menú:** Ventas → Comprobantes → **Pedidos**.

**Ruta:** `/ecom/mayoristapp/pedidos/`  
**Breadcrumb:** **Ventas / Pedidos**.

### Para qué sirve

Pantalla **inicial de pedidos**: ver borradores, pedidos enviados, en curso, cerrados o anulados; continuar un trabajo pendiente o crear uno nuevo.

### Pasos básicos

1. Use la vista **Lista** o **Kanban** (según preferencia).
2. Busque por número de pedido, cliente o sucursal.
3. Pulse **Continuar** en un borrador o **Nuevo** → **Pedido simple** o **Masivo sucursales**.
4. Si el workflow de aprobación está activo, revise columnas **Por autorizar** / **Aprobado**.
5. Los **lotes de carga masiva** aparecen como tarjetas en la columna operativa del Kanban (no hay una lane separada «Cargas masivas»). Los PED hijos del lote no se listan individualmente en el hub; use el **resumen de lote** para ver el detalle.

---

## 4. Pedido masivo por sucursales

**Menú:** Ventas → Comprobantes → **Pedido masivo sucursales**.

**Breadcrumb:** **Ventas / Pedidos / Pedido masivo**.

### Para qué sirve

Cargar cantidades para **varias sucursales** del mismo cliente en una sola operación (matriz). También concentra el **pedido simple** (una sucursal) con `?modo=simple`.

### Pasos básicos

1. Desde el hub de pedidos, elija **Nuevo** → **Masivo sucursales** (o **Pedido simple**) o abra un borrador existente.
2. En la barra superior verá el título y las acciones (confirmar, hub, etc.). Debajo, la tarjeta **Contexto comercial** (colapsable) concentra cliente, fechas, lista y condición: complete esos datos antes de cargar la matriz.
3. Busque artículos por código de sistema, código manual, nombre o **código de barra**; complete cantidades en la grilla (packs / múltiplos de empaque) y confirme el pedido.
   Si ingresa una cantidad inválida, el sistema muestra un aviso con la unidad de empaquetado antes de guardar o confirmar.
4. Tras confirmar, puede abrir el **resumen del lote** para revisar lo cargado y, si aplica, el flujo de autorización comercial del lote completo.
5. Use **Hub pedidos** (o el breadcrumb) para retomar otros pedidos.

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

## Referencias técnicas

| Tema | Documento |
|------|-----------|
| Hub de pedidos | [PEDIDOS_HUB_KANBAN.md](PEDIDOS_HUB_KANBAN.md) |
| Pedido masivo | [PEDIDO_MASIVO_SUCURSALES.md](PEDIDO_MASIVO_SUCURSALES.md) |
| Vendedor · Cliente · Marca | [VENDEDOR_CLIENTE_MARCA.md](VENDEDOR_CLIENTE_MARCA.md) |
| Ajustes de ventas | [AJUSTES_VENTAS.md](AJUSTES_VENTAS.md) |
| Índice ecom | [README.md](README.md) |

---

*Manual de usuario – Ventas. Synap. Actualizado 22/07/2026.*
