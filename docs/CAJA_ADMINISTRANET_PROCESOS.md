# Procesos de caja en administraNET

Documento que describe cómo se dan de alta las cajas, qué tablas intervienen y cómo se relacionan con el resto del sistema (VB6 y Synap).

---

## 1. Tablas principales

### 1.1 `caja_abm` (maestro de cajas)

Define cada **caja** como entidad: nombre, tipo, sucursal, límites, cuentas contables.

| Campo / uso en VB6 | Descripción |
|--------------------|-------------|
| `id_caja` | PK, identificador único de la caja |
| `nombre_caja` | Nombre (ej. "Caja 1", "Caja Autoservicio") |
| `tipo_caja` | Tipo funcional (ver abajo) |
| `id_sucursal` | FK a `sucursales`; la caja pertenece a una sucursal |
| `id_pc` / `id_pc_dolares` | Cuentas contables (plan contable) en $ y US$ |
| `anulado` | 'Si' / 'No' |
| `activa_limite_efectivo` | Si aplica límite de efectivo |
| `limite_efectivo` | Monto límite |

**Tipos de caja** (usados en filtros y reglas):

- **Acumulativa** – Caja general (efectivo)
- **Punto de Venta** – Caja de usuario de PV/TPV
- **Fondo Fijo**
- **Cheque** – Caja de cheques
- **Acumulativa Cheque**
- **Tarjeta** – Caja para pagos con tarjeta
- **Acumulativa Tarjeta**
- **Otro Medio de Cobro** / **Acumulativa Otro Medio de Cobro**

En Synap (MercadoPago) se listan para el dropdown las cajas con `anulado = 'No' OR anulado IS NULL`.

---

### 1.2 `caja_saldo` (saldos por caja y moneda)

Un registro por combinación **caja + moneda**: saldo actual y última actualización.

| Campo | Descripción |
|-------|-------------|
| `id_caja_saldo` | PK |
| `id_caja` | FK a `caja_abm.id_caja` |
| `Moneda` | 'Pesos' / 'Dolar' |
| `Saldo` | Saldo actual |
| `id_usuario` / `cod_sucursal` | Auditoría |

Al **alta de una caja** en VB6 se crean uno o dos registros en `caja_saldo`: uno en Pesos y, si la caja es Acumulativa o Punto de Venta, otro en Dolar, con Saldo = 0.

---

### 1.3 `caja` (movimientos de caja)

Cada fila es un **movimiento** (ingreso/egreso) en una caja, vinculado a comprobantes, cobros, pagos, movimientos entre cajas, cierres, etc.

| Campo relevante | Descripción |
|-----------------|-------------|
| `id_caja` | PK del movimiento (no confundir con id_caja de caja_abm) |
| `codigo_movimiento` | Número de movimiento (compartido con otros módulos: factura, recibo, etc.) |
| `fecha_control` / `Fecha` | Fecha del movimiento |
| `tipo_comprobante` | Ej. 'MCAJ' (mov. caja), 'TARJ', 'CHEQ', tipo factura, etc. |
| `Tipo` | Texto del concepto: 'Factura Contado TPV', 'Tarjeta', 'Cobranza Efectivo', 'Mov Caja', 'Cierre de Caja - Usuario de PV', etc. |
| `ingreso` | Monto que **entra** a la caja |
| `egreso` | Monto que **sale** de la caja |
| `id_caja_abm_origen` | FK a `caja_abm.id_caja` – caja donde se origina el movimiento (egreso o transferencia) |
| `id_caja_abm_destino` | FK a `caja_abm.id_caja` – caja destino (transferencias, cierre a caja supervisor) |
| `cod_sucursal` | Sucursal |
| `codigo_cliente` / `codigo_prov` | Cliente o proveedor si aplica |
| `tipo_cp` | Ej. 'Cliente', 'Mov Caja' |
| `nro_comprobante` / `nro_comp_busq` | Número de comprobante |
| `anulado` | 'Si' / 'No' |
| `id_cierre_caja` | Cierre de caja al que pertenece (PV/supervisor) |
| `id_usuario` / `id_usuario_destino` | Usuario que registra / destino en mov. entre usuarios |
| `cod_vendedor` | Vendedor |
| Otros | `cod_gasto`, `id_chequetercero`, `importe_fisico`, `importe_diferencia`, `arqueo_cerrado`, etc. |

Los reportes de “flujo de caja” en Synap (reports) filtran por `c.id_caja_abm_origen` y/o `c.id_caja_abm_destino` y hacen JOIN con `caja_abm` para mostrar nombre y tipo de caja.

---

## 2. Alta y modificación de cajas (VB6)

### 2.1 Pantallas

- **ABMCajas** – Listado de cajas (grid) y acceso a alta/edición.
- **CargaCajas** – Formulario de **alta** y **edición** de una caja.

### 2.2 Alta de una caja (CargaCajas – nuevo)

1. Se valida que no exista ya una caja con el mismo `nombre_caja` en la misma `id_sucursal`.
2. Se abre un recordset sobre `caja_abm` con `id_caja = 0`, se hace **AddNew** y se completan:
   - `nombre_caja`, `tipo_caja`, `id_sucursal`, `id_pc`, `id_pc_dolares`, `anulado`, `activa_limite_efectivo`, `limite_efectivo`.
3. **Update** en `caja_abm` (el motor asigna `id_caja`).
4. Se crea al menos un registro en **caja_saldo**:
   - `id_caja` = el `id_caja` recién creado, `Moneda` = 'Pesos', `Saldo` = 0.
   - Si `tipo_caja` es **Acumulativa** o **Punto de Venta**, se agrega otro con `Moneda` = 'Dolar', `Saldo` = 0.

Todo se hace dentro de una transacción (BeginTrans / CommitTrans).

### 2.3 Modificación de una caja (CargaCajas – edición)

Se carga el registro de `caja_abm` por `id_caja` (seleccionado en ABMCajas) y se actualizan nombre, tipo, sucursal, cuentas contables, anulado, límites. No se crean nuevos `caja_saldo`; los saldos existentes se siguen usando.

### 2.4 Filtro en listados VB6

En ABMCajas y CargaCajas se filtran tipos de caja operativos, por ejemplo: Acumulativa, Punto de Venta, Cheque, Fondo Fijo, Tarjeta, Acumulativa Cheque, Acumulativa Otro Medio de Cobro, Otro Medio de Cobro, Acumulativa Tarjeta.

---

## 3. Relación con usuarios (VB6 y Synap)

### 3.1 Tabla `usuarios` (MySQL administraNET)

Cada usuario puede tener asignadas varias cajas por rol:

| Campo | Uso |
|-------|-----|
| `id_caja` | Caja principal (efectivo / Punto de Venta) |
| `id_caja_deposito` | Caja de depósito o rendición |
| `id_caja_tarjeta` | Caja donde se registran pagos con tarjeta |
| `id_caja_tarjeta_deposito` | Caja de depósito de tarjeta |
| `id_caja_cheque` | Caja de cheques |
| `id_caja_cheque_deposito` | Caja de depósito de cheques |

En **CargaUsuario** (VB6) se asignan estas cajas mediante combos vinculados a `caja_abm` (filtrando por `tipo_caja` según el rol: Acumulativa/Punto de Venta/Fondo Fijo para caja principal, Cheque para caja cheque, Tarjeta/Acumulativa Tarjeta para caja tarjeta).

Al **loguearse** (IngresoUsuario), VB6 carga en **Principal** los IDs de caja del usuario:

- `Principal.id_caja`, `Principal.id_caja_deposito`, `Principal.id_caja_tarjeta`, `Principal.id_caja_cheque`, etc.

Esa “caja del usuario” se usa en TPV, FacturaA/B, ReciboCobro, OrdenPago, CargaMovCaja (origen/destino por defecto), etc.

En **Synap**, el login administraNET (`login/administranet_auth.py`, `core/services/administranet_users.py`) lee `usuarios.id_caja` (y resto de datos de usuario) y los expone en sesión/API; no se usa directamente para escribir movimientos de caja desde Synap, pero el modelo de “usuario con caja asignada” es el mismo.

---

## 4. Procesos que escriben en `caja` (movimientos)

### 4.1 Movimientos manuales de caja – CargaMovCaja

- **Movimiento entre cajas**: egreso en `id_caja_abm_origen`, ingreso en `id_caja_abm_destino`; actualiza `caja_saldo` de origen y destino.
- **Ingreso a caja**: solo `id_caja_abm_origen`, `ingreso`; actualiza saldo de esa caja.
- **Egreso / retiro**: solo `id_caja_abm_origen`, `egreso`; actualiza saldo.
- **Cierre a caja de supervisor**: usa `Clave_Supervisor.id_caja_supervisor` como `id_caja_abm_destino`.
- **Cobro cheque efectivo**: vincula con `id_chequetercero`, `tipo_comp_cheq` = 'CHEQ'.

En todos los casos se genera un nuevo `codigo_movimiento` (tabla de contadores), `nro_comprobante` (MCAJ + número), y se actualiza el registro de `caja_saldo` correspondiente (Saldo ± importe).

### 4.2 TPV / Factura contado (TPV.frm, FacturaA, FacturaB)

- Al confirmar venta en efectivo: se inserta en `caja` con `id_caja_abm_origen = Principal.id_caja`, `Tipo` = 'Factura Contado TPV', `ingreso` = monto, `codigo_movimiento` = el de la factura, `tipo_cp` = 'Cliente'.
- Tarjeta: `id_caja_abm_origen = Principal.id_caja_tarjeta`, tipo 'Tarjeta'.
- Cheque: `id_caja_abm_origen = Principal.id_caja_cheque`.
- Se actualiza `caja_saldo` de la caja correspondiente (Saldo += ingreso).

Anulaciones: se marca `caja.anulado = 'Si'` y se ajusta el saldo de la caja (restar el importe que se había sumado).

### 4.3 Recibo de cobro (ReciboCobro.frm)

- Cobranza efectivo: `id_caja_abm_origen = Caja.BoundText` (caja elegida en el formulario, acotada a la caja del usuario), `ingreso`, `Tipo` = 'Cobranza Efectivo'.
- Cheque: `id_caja_abm_origen = caja_abm_cheque.BoundText`.
- Tarjeta: `id_caja_abm_origen = Principal.id_caja_tarjeta`.
- Otros medios: según configuración (ej. `id_caja_ingreso` en medios de cobro).
- Siempre se actualiza `caja_saldo` de la caja usada.

### 4.4 Orden de pago (OrdenPago.frm)

- Pago efectivo: egreso en caja con `id_caja_abm_origen` = caja seleccionada, `Tipo` = 'Pago Efectivo'.
- Entrega a proveedor / cheques: caja cheque correspondiente.
- Se actualizan saldos en `caja_saldo`.

### 4.5 Cierre de caja (CargaMovCaja, Caja_Arqueo)

- Movimiento tipo “Cierre de Caja - Usuario de PV” (o “Usuario Supervisor”): egreso de la caja del usuario (`id_caja_abm_origen`) e ingreso en la caja de destino (`id_caja_abm_destino`, ej. caja supervisor o caja acumulativa).
- Se asigna `id_cierre_caja` a todos los movimientos incluidos en ese cierre.
- En **Caja_Arqueo** se compara saldo físico con saldo sistema y se pueden registrar `importe_fisico`, `importe_diferencia`, `arqueo_cerrado` en el movimiento de cierre.

### 4.6 Consulta / anulación de comprobantes (ConsultaComprobante, TPV, etc.)

Al anular facturas, recibos, etc., se localizan los movimientos en `caja` por `codigo_movimiento` (y a veces por `Tipo`), se marcan como anulados y se revierte el saldo en `caja_saldo` (restar lo que se había sumado o sumar lo que se había restado).

---

## 5. Otros formularios y reportes

- **Caja.frm** – Consulta de movimientos de caja con filtros por fecha, moneda, caja, etc. (solo lectura / análisis).
- **Caja_Arqueo** – Arqueo de caja de efectivo (conteo físico vs. sistema, cierre).
- **Caja_Control_Sucursales** / **Caja_Control_Sucursales_Rend** – Control de cajas por sucursal (reportes/consulta).
- **Info_Caja** – Información de caja.
- **ABM_Cajas_MP** – “Administración de cajas de Mercado Pago” en VB6 (configuración/credenciales MP por caja; no es la tabla `caja_abm`).
- **CargaDNF_Caja** / **CargaExtraccion** – Otros movimientos (egresos, extracciones) que también escriben en `caja` y actualizan `caja_saldo`.
- **Informes.bas** / reportes Crystal – Filtros por `caja.Fecha`, `caja.tipo`, `caja_abm.tipo_caja` para reportes de ventas, cierres, etc.

---

## 6. Uso en Synap: MercadoPago y Self-Checkout

### 6.1 Configuración MercadoPago – “ID Caja (administraNET)”

En la configuración de MercadoPago (SmartPoint) en Synap se puede elegir opcionalmente un **ID Caja (administraNET)**. Corresponde a `caja_abm.id_caja`.

- En el formulario se muestra un **dropdown** con las cajas activas de la base MySQL de la empresa (`caja_abm`, `anulado = 'No' OR anulado IS NULL`), con etiqueta nombre (y tipo).
- Si se deja en “Ninguna”, los pagos MP no generan movimiento en caja.

### 6.2 Escritura de movimiento al aprobar pago MP

Cuando un pago de Mercado Pago se aprueba, el servicio `write_caja_ingreso` (mercadopago/services/payment_service.py) puede registrar un **movimiento en la tabla `caja`** de administraNET:

- `id_caja_abm_origen` = ID de caja configurado en MercadoPago (`id_caja_abm` de la config).
- `codigo_movimiento` = el del comprobante generado por el autoservicio (factura/venta).
- `ingreso` = monto cobrado; `egreso` = 0 (igual que en VB6 para Factura Contado TPV / Tarjeta / Cobranza).
- `cod_sucursal`, `nro_comprobante`, `tipo_cp` = 'Cliente', `anulado` = 'No'.
- `tipo` = por defecto "Tarjeta" (configurable en código).

Así el cobro por MP queda registrado en la caja elegida y es coherente con el flujo de caja que usa el resto de administraNET (reportes de caja, arqueos, control por sucursal). No se actualiza `caja_saldo` en el código actual de Synap; en VB6 esa actualización se hace al insertar en `caja` en algunos flujos; si se requiere saldo al día para cajas que reciben solo MP, podría añadirse una actualización de `caja_saldo` en Synap o dejarse para cierre/arqueo en VB6.

---

## 7. Resumen de relaciones

```
caja_abm (1) ──< caja_saldo     (saldo por caja y moneda)
caja_abm (1) ──< caja           (id_caja_abm_origen / id_caja_abm_destino)
sucursales (1) ──< caja_abm     (cada caja pertenece a una sucursal)
usuarios (N) ──> caja_abm       (id_caja, id_caja_tarjeta, id_caja_cheque, etc.)

Factura/TPV/ReciboCobro/OrdenPago/CargaMovCaja
  → insertan en caja y actualizan caja_saldo
  → usan codigo_movimiento compartido con comprobantes
```

- **Alta de caja**: ABMCajas + CargaCajas → `caja_abm` + `caja_saldo` (Pesos y opcionalmente Dolar).
- **Uso**: TPV, facturas, recibos, órdenes de pago, movimientos manuales, cierres y arqueos leen/escriben `caja` y `caja_saldo` usando `caja_abm.id_caja`.
- **Synap**: listado de cajas desde `caja_abm` para el dropdown; escritura en `caja` (opcional) al aprobar pago MP con `id_caja_abm` configurado.
