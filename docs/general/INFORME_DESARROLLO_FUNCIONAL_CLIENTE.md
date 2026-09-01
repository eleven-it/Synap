# Informe de desarrollo funcional — Synap

**Fecha:** 2026-08-21  
**Destinatario:** Cliente (justificación de alcance y horas facturadas)  
**Producto:** Synap — plataforma operativa sobre AdministraNET (Django + MySQL legacy)  
**Alcance de este documento:** descripción funcional de lo desarrollado en Stock, MPR, Ventas, Reportes y Migración BEST.  
**Premisa:** Desktop web + experiencia PWA Nivel A (conteo / operario), con permisos granulares por rol.

---

## 1. Resumen ejecutivo

En el período cubierto se construyó y puso en operación un conjunto de frentes críticos del negocio mayorista / manufactura:


| Frente                                         | Estado funcional         | Valor para el negocio                                           |
| ---------------------------------------------- | ------------------------ | --------------------------------------------------------------- |
| Stock — ingreso de movimientos                 | Operativo                | Paridad con AdministraNET VB6 + trazabilidad y anulación        |
| Stock — inventario por etapa                   | Operativo                | Visibilidad Fabricados vs Terminados alineada a MPR             |
| Stock — campañas y conteo (Desktop + PWA Sync) | Operativo                | Inventario físico con conteo ciego offline y aplicación a stock |
| MPR (Producción)                               | Operativo (flujo diario) | Tablero → parte → calidad → armado → reportes + móvil operario  |
| Ventas — pedidos y masivos                     | Operativo                | Hub comercial + matriz multi-sucursal                           |
| Ventas — VCM                                   | Operativo                | Gobernanza vendedor · cliente · marca                           |
| Ventas — precios y evolución                   | Operativo                | Actualización masiva + histórico de variaciones                 |
| Ventas — cola de crédito                       | Operativo                | Control financiero pre-pedido / aprobación                      |
| Reportes                                       | Operativo                | Command Center gerencial + informes de marcas/licenciatarios    |
| Migración BEST                                 | Operativo con gate       | Cutover controlado; bloqueo de pedidos hasta paridad            |


Este documento describe **qué hace cada frente**, no el detalle técnico interno. Al final se incluye una **revisión de cobertura**: ítems desarrollados que conviene mencionar aunque no estuvieran en el listado original del pedido de informe.

---



## 2. Stock



### 2.1 Ingreso de movimientos

**Objetivo:** registrar altas y bajas de stock con la misma lógica operativa que AdministraNET (módulo histórico `CargaMovStock`), desde Synap.

**Funcionalidades entregadas:**

- Pantalla de **alta de movimiento** con motivo, depósitos origen/destino, sentido E/S y renglones.
- Búsqueda de artículos / código, consulta de **lotes**, **series** y **saldo**.
- Asociación a **pedidos pendientes (PEDI)** y proyectos cuando corresponde.
- Confirmación del comprobante y limpieza de temporales de carga.
- **Consultas y anulaciones** de movimientos ya emitidos.
- Emisión de **PDF** del comprobante.
- ABM de **referencias / motivos** de movimiento de stock.
- Manual de usuario incluido en el módulo.

**Beneficio:** el depósito opera el movimiento diario en Synap sin perder paridad con el legado, con consulta y anulación auditables.

---



### 2.2 Inventario

**Objetivo:** consultar el stock por etapa de producción (no solo un saldo “plano”).

**Funcionalidades entregadas:**

- Vista **Inventario / Inventario por etapa** con saldos MPR (Fabricados vs Terminados).
- Presentación en **pares / docenas** según la unidad del negocio.
- Filtros por marca, stock, ámbito y búsqueda de artículos.
- Consulta avanzada con posibilidad de abrir ajuste desde la búsqueda.
- Integración con el informe de **inventario por depósito / artículo** del módulo Reportes.

**Beneficio:** gerencia y depósito ven el stock con la misma lógica de etapas que usa Producción (MPR), evitando desvíos entre “lo que hay” y “dónde está en el proceso”.

---



### 2.3 Campañas de inventario físico y conteo (Desktop + PWA con Sync)

**Objetivo:** ejecutar inventarios físicos formales: planificar la campaña, contar en planta (incluso sin conexión) y aplicar diferencias al stock.

#### Gestión Desktop (supervisor)

Flujo de estados de campaña:

`Borrador → EnConteo → EnRevisión → Autorizado → Aplicado` (o `Anulado`)

- Alta de campaña con depósitos (ámbito **terminados** o **fabricados**, sin mezclar), contadores asignados y marcas.
- **Monitor de progreso** de conteo.
- **Analizador de diferencias** vs snapshot.
- Override de ajuste, recálculo post-snapshot, marcar no contados en cero.
- Control de movimientos posteriores al snapshot.
- **Export Excel**.
- Autorización que **aplica movimientos de stock (MSTOCK)**.



#### Conteo PWA / móvil (operario)

- Landing **“Mis conteos”** y pantalla por campaña (solo campañas en conteo asignadas al usuario).
- Conteo **ciego** (el operario no ve saldos del sistema).
- Escáner EAN + ingreso manual.
- **Cola offline** con sincronización por lotes (aceptado / conflicto / rechazado).
- Prefetch de catálogo para trabajar sin red estable.
- Templates adaptados Desktop / Mobile.

**Beneficio:** se cierra el ciclo completo de inventario físico —de la orden de campaña al ajuste de stock— con operación de planta en celular y control supervisor en escritorio.

---



## 3. MPR completo (Manufactura / Producción)

**Objetivo:** digitalizar el día a día de fábrica sobre Synap: qué se produce, quién lo produce, cómo se clasifica y cómo se arma el pedido.

### 3.1 Flujo diario de producción

- **Tablero de producción:** enviar a producción, seguimiento de envíos, anulación.
- Asignación de artículo a máquina.
- **Parte de producción** (registro operativo + ajustes) con cupo de fabricando.
- Consulta de partes y bandeja de **partes pendientes** (supervisor).
- **Control de calidad / clasificación de producción**.
- **Planificación de turnos** (roster, carga masiva, override por línea).
- Tablero KPI de producción.
- Inventario MPR (desktop + vista mobile).



### 3.2 Armado y stock de fábrica

- Armado unificado (1ª / 2ª).
- Imputación de pedido (Armado 1ra).
- Reclasificación.
- APIs de packs / BOM / stock origen para soporte operativo.



### 3.3 Configuración maestra

Turnos, depósitos tipo MPR, operarios, líneas, máquinas (incluye planilla de control), mapeo operario↔usuario y línea habitual.

### 3.4 Reportes propios de MPR

- **Producción:** resumen diario, por operario, mensual, por máquina, cadena, pendiente de componentes.
- **Demanda:** brecha de pack, pedidos por estado, stock, inventario depósito, bajo mínimo.
- **Trazabilidad:** timeline, movimientos, conciliación, kardex.
- Exportación CSV / XLSX selectiva.



### 3.5 Móvil del operario

Acceso `/mpr/mi-parte/` con landing por rol (operario puede cargar parte sin necesitar el menú completo de MPR).

### 3.6 Nota de alcance

Además del flujo diario priorizado en menú, el sistema conserva capacidades históricas de **OPT / OP / BOM / ventana pack** (listados, alta, detalle, trazabilidad, PDF). El menú operativo actual prioriza el circuito tablero → parte → calidad → armado; las pantallas legacy permanecen disponibles para continuidad.

**Beneficio:** fábrica opera punta a punta en Synap, con trazabilidad y reportes propios, y el operario trabaja desde el celular.

---



## 4. Migración BEST (cutover)

**Objetivo:** migrar el universo BEST a Synap con control de paridad, evitando liberar pedidos si los maestros críticos no están alineados.

**Hub:** Migración BEST dentro de MPR.


| Dominio migrado                                       | Rol en el cutover                      |
| ----------------------------------------------------- | -------------------------------------- |
| Artículos terminados (match / validación / inferidos) | Bloquea gate de pedidos                |
| Artículos fabricados (BOM / PP)                       | Migrados (no bloquean gate)            |
| Clientes                                              | Bloquea gate                           |
| Depósitos / tipificación MPR                          | Migrados                               |
| Stock inicial + carga                                 | Migrados                               |
| Stock reserva (MCSS)                                  | Migrados                               |
| Operarios / tejedores                                 | Migrados                               |
| Pedidos (ensayo + confirmación con gate)              | Migrados con control                   |
| Unidades (par / docena)                               | Pendiente de cierre formal             |
| Reinicio de staging                                   | Disponible para reintentos controlados |


**Gate de pedidos:** la confirmación de migración de pedidos permanece bloqueada hasta alcanzar la paridad definida (artículos terminados + clientes, entre otros chequeos de huérfanos / inconsistencias).

**Beneficio:** el cutover no es un “import a ciegas”: hay checklist por dominio, reintentos y un freno explícito antes de contaminar la operación comercial.

---



## 5. Ventas



### 5.1 Pedidos y pedidos masivos

**Objetivo:** tomar y gestionar pedidos comerciales (simple y multi-sucursal) desde Synap / portal mayorista.

**Funcionalidades entregadas:**

- Hub de pedidos con vistas **Lista / Kanban**, detalle, PDF y KPIs.
- Gestión de drafts; migración / archivo de carritos legacy.
- **Pedido simple** y **Pedido masivo por sucursales**:
  - matriz multi-columna,
  - edición por celda,
  - descuentos por fila / pie,
  - preview y confirmación (proceso asistido),
  - plantilla Excel import/export,
  - anulación,
  - múltiplos de empaque,
  - respeto de territorio VCM y créditos en UI.
- Circuito de **aprobación comercial** de pedidos / lotes.
- **Presupuestos** (vendedor) con conversión a pedido; presupuestos PRE también en app Ventas.

**Beneficio:** el vendedor carga un pedido de muchas sucursales en una sola operación, con reglas comerciales y financieras aplicadas antes de confirmar.

---



### 5.2 VCM (Vendedor · Cliente · Marca)

**Objetivo:** gobernar qué vendedor puede operar qué cliente / sucursal / marca.

**Funcionalidades entregadas:**

- Configuración de la cuaterna **vendedor → cliente → sucursal → marca**.
- Altas / bajas y catálogos de apoyo.
- Filtrado efectivo en pedido masivo, catálogo y carrito.
- Pantalla relacionada de **asignación de vendedor** en Ventas.

**Beneficio:** se evita venta fuera de territorio comercial y se alinea catálogo / pedido con la política comercial del cliente.

---



### 5.3 Actualización de precios

**Objetivo:** mantener listas de precios de productos terminados de forma masiva y controlada.

**Funcionalidades entregadas:**

- Pantalla de **precios terminados** con tabla multi-lista.
- Filtros por marca, rubro, subrubro y proveedor.
- Guardado unitario y **cambio masivo** (preview → aplicar).
- Acceso al historial del artículo desde la misma UI.

**Beneficio:** cambios de lista masivos sin planillas sueltas ni riesgo de inconsistencia entre listas.

---



### 5.4 Evolución de precios

**Objetivo:** auditar y analizar cómo se movieron los precios en el tiempo.

**Funcionalidades entregadas:**

- Ranking de variaciones.
- Filtros por lista, fechas, marcas, rubros.
- Recorte a universo Synap cuando corresponde.
- Clasificación por tipo de modificación.

**Beneficio:** comercial y gerencia pueden explicar un cambio de precio con evidencia histórica, no con “memoria de planilla”.

---



### 5.5 Cola de crédito

**Objetivo:** frenar o liberar pedidos según política de crédito, con intervención de Finanzas.

**Funcionalidades entregadas:**

- **Cola de crédito** (Finanzas): aprobar / rechazar.
- Políticas y plantillas de aviso.
- Pre-check en la toma de pedido / presupuesto.
- Resumen de exposición del cliente.
- Configuración operativa en ajustes de ventas / workflow.
- Flag de activación del circuito de crédito en pedidos.

**Beneficio:** el riesgo crediticio se controla en el momento de la venta, no después de facturar.

---



## 6. Reportes

**Objetivo:** dar a gerencia y operación una capa analítica sobre los mismos datos vivos de Synap / AdministraNET.

### 6.1 Command Center gerencial

Tablero orquestado con áreas:

- Ventas  
- Inventario  
- Compras  
- Manufactura (MPR)  
- Demanda pendiente  
- Tesorería  
- Ventas por cobro

Visibilidad configurable (incl. control supervisor de áreas habilitadas).

### 6.2 Informes operativos y de negocio

Entre otros con UI propia / relay:

- Resumen ejecutivo de ventas  
- Clientes sin ventas  
- Cobranzas por vendedor  
- Utilidad gerencial  
- Pedidos pendientes  
- Remitos no facturados  
- Ventas netas  
- Flujos de caja / consolidado operativo



### 6.3 Informes de marcas / licenciatarios (universo Best Sox y afines)

- Ventas marcas mensual  
- Ventas mensuales licenciatarios (+ matching Excel)  
- Ventas marca / superartículo  
- Ventas BOM docenas  
- Inventario depósito-artículo



### 6.4 Plataforma de reporting

Catálogo, workspace, builder, data-map, APIs de consulta / KPI / exportación y control de visibilidad por usuario.

**Beneficio:** deja de dependerse de extracciones manuales; gerencia opera sobre un command center y un set de informes de negocio ya cableados al dato operativo.

---


|                                                    | Por qué importa                                                                                      |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **Presupuestos de venta**                          | Circuito comercial previo al pedido (app Ventas + ecom).                                             |
| **Objetivos de venta**                             | Metas por período / vendedor; no es “solo precio”.                                                   |
| **Aprobación comercial de pedidos**                | Complementa pedidos masivos y crédito.                                                               |
| **Portal / hub mayorista (ecom)**                  | Clientes, catálogo, remitos, cuenta corriente, FE NC: es la carcasa donde viven pedidos/VCM/crédito. |
| **Permisos granulares + PWA Nivel A**              | Sin esta matriz, Stock conteo / MPR operario / Finanzas no se despliegan por rol.                    |
| **Demanda pendiente y Tesorería (Command Center)** | Ya están como áreas gerenciales; si se mostró el Command Center, van en el alcance.                  |




### 7.2 Incluir solo si formaron parte del mismo contrato / facturación


| Ítem                                                             | Evidencia de desarrollo en plataforma                          |
| ---------------------------------------------------------------- | -------------------------------------------------------------- |
| **Compras** (remito, factura, NC/ND, OP, cta cte, captura móvil) | Módulo `compras` + captura                                     |
| **Logística / entregas y preparación de pedidos**                | `logistica` + estado de preparación ecom                       |
| **Facturación electrónica AFIP**                                 | `fe_afip` / pyafipws                                           |
| **Self-checkout / TPV**                                          | `self_checkout`                                                |
| **Auditoría contable / cotización**                              | `contabilidad_audit`                                           |
| **Integraciones TiendaNube / Mercado Pago**                      | apps propias                                                   |
| **Migración Odoo / Mtrix**                                       | distinto de BEST; no mezclar salvo que el contrato lo unifique |




### 7.3 Limitaciones honestas (conviene declararlas)

1. **Unidades (par/docena) en Migración BEST** — dominio aún pendiente de cierre formal.
2. **OPT/BOM legacy** — disponibles en código; el menú diario prioriza el circuito nuevo.
3. Este informe describe **funcionalidad implementada en producto**; no sustituye un timesheet ni un acta de UAT firmada.
4. La adopción real en producción y el porcentaje de uso por rol deben respaldarse con evidencia operativa del cliente (capacitaciones, tickets, actas).

---



## 8. Mapa rápido de valor (para la presentación)

```
STOCK          →  Movimientos diarios + inventario por etapa + inventario físico (Desktop/PWA)
MPR            →  Producción diaria + calidad + armado + reportes + móvil operario
BEST           →  Cutover controlado con gate de pedidos
VENTAS         →  Pedidos/masivos + VCM + precios/evolución + crédito
REPORTES       →  Command Center + informes de negocio / licenciatarios
PLATAFORMA     →  Permisos, PWA, hub mayorista (habilitan todo lo anterior)
```

---



## 9. Conclusión

El desarrollo entregado no es un conjunto de pantallas aisladas: es un **circuito operativo cerrado**

1. se produce y clasifica (MPR),
2. se controla y ajusta el stock (Stock + campañas),
3. se migra el universo BEST con freno de seguridad,
4. se vende con reglas comerciales y de crédito,
5. se mide en Reportes / Command Center.

Esa cadena —más la capa de permisos, PWA y hub mayorista que la hace usable por rol— es lo que justifica el volumen de horas frente al cliente.

---



## 10. Anexos sugeridos (opcional para la reunión)

- Anexo A: capturas por módulo (1–2 pantallas clave c/u).  
- Anexo B: glosario (VCM, PEDI, MSTOCK, gate BEST, conteo ciego, PWA Sync).  
- Anexo C: matriz de roles (Supervisor Stock, Contador, Operario MPR, Vendedor, Finanzas, Gerencia).  
- Anexo D: pendientes declarados (unidades BEST; eventual formalización de OPT/BOM en menú).

---

*Documento preparado a partir del estado funcional del producto Synap. No incluye valuación horaria por commit; esa valuación debe cruzarse con el registro de horas del proyecto.*