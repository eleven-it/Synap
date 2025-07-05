# Manual de Usuario - Módulo de Ventas
## Sistema Synap

---

## Índice

1. [Introducción](#introducción)
2. [Acceso al Módulo](#acceso-al-módulo)
3. [Dashboard de Ventas](#dashboard-de-ventas)
4. [Gestión de Clientes](#gestión-de-clientes)
5. [Gestión de Pedidos de Venta](#gestión-de-pedidos-de-venta)
6. [Gestión de Facturas](#gestión-de-facturas)
7. [Gestión de Pagos](#gestión-de-pagos)
8. [Gestión de Entregas](#gestión-de-entregas)
9. [Gestión de Devoluciones](#gestión-de-devoluciones)
10. [Gestión de Notas de Crédito](#gestión-de-notas-de-crédito)
11. [Configuración](#configuración)
12. [Reportes](#reportes)
13. [Integración con Inventario](#integración-con-inventario)
14. [Flujos de Trabajo](#flujos-de-trabajo)
15. [Solución de Problemas](#solución-de-problemas)

---

## 1. Introducción

El módulo de Ventas de Synap es una solución completa para la gestión del ciclo comercial de su empresa. Permite administrar clientes, crear y gestionar pedidos de venta, facturar, procesar pagos, gestionar entregas y generar reportes detallados.

### Características Principales

- **Gestión completa de clientes** con información de contacto y límites de crédito
- **Pedidos de venta** con estados automatizados y validación de stock
- **Facturación automática** con diferentes tipos de documentos
- **Gestión de pagos** con múltiples métodos de pago
- **Control de entregas** con integración al inventario
- **Devoluciones y notas de crédito** para gestionar incidencias
- **Reportes detallados** para análisis comercial
- **Integración con inventario** para control de stock en tiempo real

---

## 2. Acceso al Módulo

### 2.1 Navegación Principal

1. Acceda al sistema Synap con sus credenciales
2. En el menú principal, haga clic en **"Ventas"**
3. Será dirigido al Dashboard de Ventas

### 2.2 Permisos Requeridos

Para acceder al módulo de ventas, necesita los siguientes permisos:
- `sales.view_salesorder` - Ver pedidos de venta
- `sales.add_salesorder` - Crear pedidos de venta
- `sales.change_salesorder` - Editar pedidos de venta
- `sales.delete_salesorder` - Eliminar pedidos de venta

---

## 3. Dashboard de Ventas

### 3.1 Vista General

El Dashboard de Ventas proporciona una visión completa del estado de su operación comercial:

#### Tarjetas de Estadísticas
- **Total Clientes**: Número total de clientes registrados
- **Total Pedidos**: Cantidad de pedidos de venta
- **Total Facturas**: Número de facturas emitidas
- **Total Pagos**: Cantidad de pagos procesados

#### Gráficos y Tablas
- **Pedidos por Estado**: Distribución de pedidos según su estado actual
- **Ventas Recientes**: Últimos pedidos procesados
- **Clientes Principales**: Top de clientes por volumen de ventas

### 3.2 Acciones Rápidas

Desde el dashboard puede acceder rápidamente a:
- **Nuevo Cliente**: Crear un nuevo cliente
- **Nuevo Pedido**: Crear un pedido de venta
- **Ver Todos**: Acceder a las listas completas de cada entidad

---

## 4. Gestión de Clientes

### 4.1 Lista de Clientes

**Acceso**: Ventas → Clientes

La lista muestra:
- Nombre del cliente
- Tipo (Empresa o Persona)
- Email y teléfono
- Estado (Activo/Inactivo)
- Límite de crédito
- Origen (Manual, E-commerce, etc.)

#### Filtros Disponibles
- Por tipo de cliente
- Por estado
- Por origen
- Por límite de crédito

### 4.2 Crear Nuevo Cliente

**Acceso**: Dashboard → Nuevo Cliente

#### Campos Requeridos
- **Nombre**: Nombre completo o razón social
- **Tipo**: Empresa o Persona
- **Email**: Correo electrónico (opcional)
- **Teléfono**: Número de contacto (opcional)
- **CUIT/CUIL**: Para empresas argentinas (opcional)

#### Campos Opcionales
- **Límite de Crédito**: Monto máximo de crédito disponible
- **Origen**: Cómo se registró el cliente
- **ID Cliente TiendaNube**: Para integración con e-commerce

### 4.3 Editar Cliente

1. En la lista de clientes, haga clic en el nombre del cliente
2. Haga clic en **"Editar"**
3. Modifique los campos necesarios
4. Guarde los cambios

### 4.4 Gestión de Contactos

Cada cliente puede tener múltiples contactos:

#### Agregar Contacto
1. En el detalle del cliente, vaya a la sección "Contactos"
2. Haga clic en **"Agregar Contacto"**
3. Complete:
   - Nombre del contacto
   - Email
   - Teléfono
   - Marcar como contacto principal (opcional)

#### Editar/Eliminar Contactos
- Use los botones de acción en cada contacto
- Solo puede eliminar contactos que no sean principales

---

## 5. Gestión de Pedidos de Venta

### 5.1 Estados del Pedido

Los pedidos de venta siguen un flujo de estados específico:

1. **Borrador (Draft)**: Pedido en creación
2. **Cotización Enviada (Quotation Sent)**: Cotización enviada al cliente
3. **Confirmado (Confirmed)**: Cliente confirma el pedido
4. **En Proceso (In Process)**: Preparando el pedido
5. **Listo para Entregar (Ready to Deliver)**: Pedido preparado
6. **Parcialmente Entregado (Partially Delivered)**: Entrega parcial
7. **Entregado (Delivered)**: Completamente entregado
8. **Facturado (Invoiced)**: Factura creada
9. **Pagado (Paid)**: Pago recibido
10. **Completado (Completed)**: Pedido finalizado
11. **Cancelado (Cancelled)**: Pedido cancelado

### 5.2 Crear Nuevo Pedido

**Acceso**: Dashboard → Nuevo Pedido

#### Paso 1: Información General
- **Cliente**: Seleccione el cliente del pedido
- **Sucursal**: Sucursal donde se procesa el pedido
- **Fecha del Pedido**: Fecha de creación
- **Condiciones de Pago**: Plazos de pago
- **Lista de Precios**: Lista de precios a aplicar
- **Vendedor**: Usuario responsable de la venta

#### Paso 2: Líneas del Pedido
- **Producto**: Seleccione el producto de la lista
- **Cantidad**: Cantidad solicitada
- **Precio Unitario**: Precio por unidad
- **Descuento**: Porcentaje de descuento (opcional)
- **Descripción**: Notas adicionales (opcional)

#### Validaciones Automáticas
- **Stock Disponible**: El sistema valida stock en tiempo real
- **Límite de Crédito**: Verifica el límite del cliente
- **Precios**: Aplica la lista de precios seleccionada

### 5.3 Gestionar Estados del Pedido

#### Confirmar Pedido
1. En el detalle del pedido, haga clic en **"Confirmar"**
2. El sistema:
   - Valida disponibilidad de stock
   - Reserva el stock automáticamente
   - Cambia el estado a "Confirmado"

#### Procesar Pedido
1. Haga clic en **"En Proceso"**
2. El pedido pasa a preparación

#### Marcar Listo para Entregar
1. Haga clic en **"Listo para Entregar"**
2. El pedido está preparado para entrega

#### Entregar Pedido
1. Haga clic en **"Entregar"**
2. El sistema:
   - Crea movimientos de stock automáticamente
   - Marca el pedido como entregado

### 5.4 Editar Pedido

#### Cuándo se puede editar
- Solo en estado "Borrador" o "Cotización Enviada"
- Pedidos confirmados requieren cancelación previa

#### Modificaciones Permitidas
- Cambiar cliente (si no hay facturas)
- Modificar líneas del pedido
- Ajustar precios y descuentos
- Cambiar condiciones de pago

### 5.5 Cancelar Pedido

1. En el detalle del pedido, haga clic en **"Cancelar"**
2. Ingrese el motivo de cancelación
3. El sistema:
   - Libera las reservas de stock
   - Marca el pedido como cancelado
   - Registra la cancelación en el log

---

## 6. Gestión de Facturas

### 6.1 Crear Factura desde Pedido

**Acceso**: Detalle del Pedido → "Crear Factura"

#### Facturación Automática
- El sistema pre-llena la información del pedido
- Incluye todas las líneas del pedido
- Aplica los precios y descuentos del pedido

#### Tipos de Factura
- **Factura A**: Para consumidores finales
- **Factura B**: Para empresas con CUIT
- **Factura C**: Para exportación

### 6.2 Gestión Manual de Facturas

#### Crear Factura Manual
1. Ventas → Facturas → Nueva Factura
2. Complete la información requerida
3. Agregue las líneas de facturación

#### Editar Factura
- Solo facturas en estado "Borrador"
- No se pueden modificar facturas enviadas

### 6.3 Estados de Factura

- **Borrador**: En creación
- **Enviada**: Enviada al cliente
- **Pagada**: Pago recibido
- **Cancelada**: Factura cancelada

---

## 7. Gestión de Pagos

### 7.1 Registrar Pago

#### Desde Factura
1. En el detalle de la factura, haga clic en **"Registrar Pago"**
2. Complete:
   - Fecha de pago
   - Monto
   - Método de pago
   - Referencia (opcional)

#### Pago Manual
1. Ventas → Pagos → Nuevo Pago
2. Asocie con factura o pedido
3. Complete la información del pago

### 7.2 Métodos de Pago

- **Efectivo**
- **Transferencia Bancaria**
- **Cheque**
- **Tarjeta de Crédito**
- **Tarjeta de Débito**
- **Mercado Pago**
- **Otros**

### 7.3 Conciliación de Pagos

- Los pagos se asocian automáticamente con facturas
- Puede ajustar la asociación manualmente
- El sistema calcula saldos pendientes

---

## 8. Gestión de Entregas

### 8.1 Crear Orden de Entrega

#### Desde Pedido
1. En el detalle del pedido, haga clic en **"Crear Entrega"**
2. El sistema pre-llena la información
3. Seleccione el almacén de origen
4. Confirme la entrega

#### Entrega Manual
1. Ventas → Entregas → Nueva Entrega
2. Asocie con un pedido
3. Complete la información de entrega

### 8.2 Procesar Entrega

1. En el detalle de la entrega, haga clic en **"Procesar"**
2. El sistema:
   - Valida stock disponible
   - Crea movimientos de inventario
   - Actualiza el estado del pedido

### 8.3 Estados de Entrega

- **Borrador**: En creación
- **Confirmada**: Lista para procesar
- **Procesada**: Entrega completada
- **Cancelada**: Entrega cancelada

---

## 9. Gestión de Devoluciones

### 9.1 Crear Devolución

#### Desde Entrega
1. En el detalle de la entrega, haga clic en **"Crear Devolución"**
2. Seleccione los productos a devolver
3. Especifique la cantidad y motivo

#### Devolución Manual
1. Ventas → Devoluciones → Nueva Devolución
2. Asocie con pedido y entrega
3. Complete la información

### 9.2 Tipos de Devolución

- **Defecto de Producto**: Producto con fallas
- **Error de Entrega**: Producto incorrecto
- **Arrepentimiento**: Cliente cambia de opinión
- **Otros**: Otros motivos

### 9.3 Procesar Devolución

1. Aprobar la devolución
2. El sistema:
   - Crea movimientos de stock de retorno
   - Actualiza inventario
   - Genera nota de crédito (opcional)

---

## 10. Gestión de Notas de Crédito

### 10.1 Crear Nota de Crédito

#### Desde Factura
1. En el detalle de la factura, haga clic en **"Crear Nota de Crédito"**
2. Seleccione las líneas a anular
3. Especifique el motivo

#### Nota de Crédito Manual
1. Ventas → Notas de Crédito → Nueva Nota
2. Asocie con factura y pedido
3. Complete la información

### 10.2 Aplicar Nota de Crédito

1. En el detalle de la nota, haga clic en **"Aplicar"**
2. Seleccione la factura donde aplicar
3. El sistema ajusta los montos automáticamente

---

## 11. Configuración

### 11.1 Listas de Precios

#### Crear Lista de Precios
1. Ventas → Configuración → Listas de Precios
2. Complete:
   - Nombre de la lista
   - Moneda
   - Fechas de vigencia
   - Productos y precios

#### Gestionar Items de Lista
- Agregar productos específicos
- Definir precios por cantidad
- Configurar descuentos
- Establecer códigos promocionales

### 11.2 Condiciones de Pago

#### Crear Condición de Pago
1. Ventas → Configuración → Condiciones de Pago
2. Defina:
   - Nombre de la condición
   - Descripción
   - Líneas de pago (porcentajes y días)

#### Ejemplos de Condiciones
- **Contado**: 100% al momento
- **30 días**: 100% a 30 días
- **50/50**: 50% al momento, 50% a 30 días

---

## 12. Reportes

### 12.1 Dashboard de Reportes

**Acceso**: Ventas → Reportes

#### Reportes Disponibles
- **Resumen de Ventas**: Ventas por período
- **Análisis de Clientes**: Rendimiento por cliente
- **Rendimiento de Productos**: Productos más vendidos

### 12.2 Resumen de Ventas

#### Filtros
- Período de tiempo
- Sucursal
- Vendedor
- Cliente
- Estado del pedido

#### Métricas
- Total de ventas
- Cantidad de pedidos
- Promedio por pedido
- Productos más vendidos

### 12.3 Análisis de Clientes

- Ventas por cliente
- Frecuencia de compra
- Valor promedio por cliente
- Clientes con mayor crecimiento

### 12.4 Rendimiento de Productos

- Productos más vendidos
- Margen por producto
- Rotación de inventario
- Productos con bajo rendimiento

---

## 13. Integración con Inventario

### 13.1 Validación Automática de Stock

El sistema valida automáticamente la disponibilidad de stock:

#### Al Confirmar Pedido
- Verifica stock disponible en la sucursal
- Reserva automáticamente el stock
- Previene ventas sin stock

#### Al Entregar Pedido
- Crea movimientos de stock automáticamente
- Actualiza inventario en tiempo real
- Mantiene trazabilidad completa

### 13.2 Estados de Stock

#### Disponible
- Stock físico disponible para venta
- No reservado para otros pedidos

#### Reservado
- Stock reservado para pedidos confirmados
- No disponible para nuevas ventas

#### En Tránsito
- Stock en proceso de entrega
- Pendiente de confirmación

### 13.3 Alertas de Stock

#### Stock Bajo
- Alerta cuando el stock está por debajo del mínimo
- Notificación automática al confirmar pedidos

#### Sin Stock
- Bloqueo automático de ventas
- Sugerencia de reposición

---

## 14. Flujos de Trabajo

### 14.1 Flujo Completo de Venta

#### 1. Crear Cliente
- Registrar información del cliente
- Establecer límite de crédito
- Agregar contactos

#### 2. Crear Pedido
- Seleccionar cliente
- Agregar productos
- Aplicar precios y descuentos

#### 3. Confirmar Pedido
- Validar stock disponible
- Reservar stock automáticamente
- Cambiar estado a "Confirmado"

#### 4. Procesar Pedido
- Preparar productos
- Cambiar estado a "En Proceso"

#### 5. Entregar
- Crear orden de entrega
- Procesar entrega
- Actualizar inventario

#### 6. Facturar
- Crear factura desde pedido
- Enviar al cliente

#### 7. Cobrar
- Registrar pago
- Actualizar saldos

### 14.2 Flujo de Devolución

#### 1. Crear Devolución
- Asociar con entrega
- Especificar productos y cantidades
- Indicar motivo

#### 2. Aprobar Devolución
- Validar información
- Procesar retorno de stock

#### 3. Crear Nota de Crédito
- Generar nota de crédito
- Aplicar a factura correspondiente

---

## 15. Solución de Problemas

### 15.1 Errores Comunes

#### "Stock Insuficiente"
**Problema**: No hay suficiente stock para confirmar el pedido
**Solución**:
1. Verificar stock en inventario
2. Reponer productos faltantes
3. Ajustar cantidades del pedido

#### "Límite de Crédito Excedido"
**Problema**: El pedido supera el límite de crédito del cliente
**Solución**:
1. Revisar límite de crédito del cliente
2. Solicitar autorización para override
3. Ajustar montos del pedido

#### "Pedido No Se Puede Editar"
**Problema**: No se puede modificar un pedido confirmado
**Solución**:
1. Cancelar el pedido actual
2. Crear nuevo pedido con correcciones
3. O solicitar cambio de estado a borrador

### 15.2 Validaciones del Sistema

#### Validaciones de Pedido
- Cliente debe estar activo
- Stock debe estar disponible
- Límite de crédito debe ser respetado
- Precios deben ser válidos

#### Validaciones de Factura
- Pedido debe estar entregado
- Montos deben coincidir
- Información fiscal debe ser correcta

#### Validaciones de Pago
- Factura debe existir
- Monto no debe exceder saldo
- Fecha debe ser válida

### 15.3 Contacto de Soporte

Para problemas técnicos o consultas:
- **Email**: soporte@synap.com
- **Teléfono**: +54 11 1234-5678
- **Horario**: Lunes a Viernes 9:00 - 18:00

---

## Anexos

### A. Glosario de Términos

- **Pedido de Venta**: Documento que registra la intención de compra del cliente
- **Factura**: Documento fiscal que respalda la venta
- **Entrega**: Proceso físico de entrega de productos
- **Reserva de Stock**: Bloqueo temporal de inventario para un pedido
- **Movimiento de Stock**: Registro de entrada/salida de productos
- **Nota de Crédito**: Documento que anula total o parcialmente una factura

### B. Atajos de Teclado

- **Ctrl + N**: Nuevo pedido
- **Ctrl + C**: Nuevo cliente
- **Ctrl + F**: Buscar
- **Ctrl + S**: Guardar
- **Esc**: Cancelar operación

### C. Códigos de Estado

- **DRAFT**: Borrador
- **CONFIRMED**: Confirmado
- **IN_PROCESS**: En Proceso
- **READY_TO_DELIVER**: Listo para Entregar
- **DELIVERED**: Entregado
- **INVOICED**: Facturado
- **PAID**: Pagado
- **COMPLETED**: Completado
- **CANCELLED**: Cancelado

---

*Manual de Usuario - Módulo de Ventas v1.0*
*Sistema Synap - Todos los derechos reservados* 