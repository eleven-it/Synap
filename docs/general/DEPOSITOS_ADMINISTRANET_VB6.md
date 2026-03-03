# Depósitos en AdministraNET (VB6) — Análisis completo

Documento de referencia para la tabla **`deposito`** y todo lo que en el sistema depende de depósitos: estructura, ABM, asignación a usuarios, uso en stock y movimientos, y tablas relacionadas.

---

## 1. Estructura de la tabla `deposito`

Según la consulta `SELECT * FROM deposito` y el uso en VB6:

| Campo           | Tipo / Uso        | Descripción |
|----------------|--------------------|-------------|
| **CodDeposito** | PK (numérico)      | Identificador del depósito. En alta se hace `AddNew` sin setearlo; la base (MySQL) asigna el valor (autoincrement o similar). |
| **NombreDeposito** | Texto            | Nombre mostrado (ej. "Deposito Central", "Ecommerce", "Suc - Av. Cab 1915", "Roturas"). |
| **Descripcion** | Texto (opcional)   | Descripción adicional; en muchos casos vacío. |
| **anulado**     | 'Si' / 'No'        | Baja lógica. Solo se consideran activos los registros con `anulado = 'No'` (o `IS NULL` en algunos reportes). |

**Ejemplo de datos:**

| CodDeposito | NombreDeposito   | Descripcion | anulado |
|-------------|------------------|-------------|---------|
| 1           | Deposito Central |             | No      |
| 2           | Ecommerce        |             | No      |
| 3           | Suc - Av. Cab 1915|            | No      |
| 4           | Roturas          |             | No      |

En informes y filtros se usa siempre la condición `(anulado IS NULL OR anulado = 'No')` para listar solo depósitos activos.

---

## 2. ABM de depósitos (quién escribe en `deposito`)

### 2.1 Alta y modificación — CargaDeposito.frm

- **Alta:** Se abre un recordset con `"SELECT * FROM deposito WHERE CodDeposito=0"` (ninguna fila), se hace **AddNew** y se asignan:
  - `Nombredeposito` = Nombre.Text  
  - `Descripcion` = Descripcion.Text  
  - `anulado` = anulado.Text  
  Luego **Update**. El `CodDeposito` lo asigna la base.  
  Acto seguido, por **cada artículo** existente en `articulo`, se hace **AddNew** en **stock_deposito** con:
  - `id_deposito` = rs_deposito.Fields!CodDeposito (el recién creado)
  - `id_articulo` = artículo
  - `Saldo` = 0  
  Así el nuevo depósito queda con una fila por artículo en `stock_deposito` (saldo inicial 0).

- **Modificación:** Se abre el registro por `CodDeposito` y se hace **Update** de `Nombredeposito`, `Descripcion`, `anulado`. No se borran ni crean filas en `stock_deposito` al modificar.

### 2.2 Listado / selector — ABMDeposito.frm

- **Solo lectura** sobre `deposito`:  
  `DataDeposito.RecordSource = "SELECT * FROM deposito ORDER BY NombreDeposito"`  
  Desde ahí se abre CargaDeposito para alta o modificación.

**Conclusión:** La única escritura directa en la tabla `deposito` está en **CargaDeposito.frm** (AddNew y Update). No hay DELETE físico; la baja es lógica mediante `anulado = 'Si'`.

---

## 3. Tabla `deposito_usr` (asignación usuario – depósito)

- **Estructura lógica:** Relación N:M entre usuarios y depósitos. Campos típicos: `id_deposito` (= deposito.CodDeposito), `id_usuario`.
- **Quién escribe:**
  - **CargaUsuario.frm:** Al crear usuario puede insertar en `deposito_usr` (id_deposito, id_usuario).
  - **AsigUsrDeposito.frm:** Asignar depósitos a un usuario: **INSERT** (id_deposito, id_usuario) y **DELETE** por `id_Deposito_usr` para quitar asignaciones.
- **Uso:** Si el sistema tiene restricción por depósito (`Principal.cambia_deposito` u otro permiso), en varios formularios se cargan solo los depósitos permitidos para el usuario logueado:
  - `SELECT * FROM deposito INNER JOIN deposito_usr ON (deposito_usr.id_deposito = deposito.CodDeposito) WHERE deposito_usr.id_usuario = Principal.idUsuario AND deposito.anulado = 'No' ORDER BY CodDeposito`
  - Si el usuario no tiene permiso para cambiar depósito, se usa solo el depósito asignado: `Principal.id_deposito`.

Formularios que usan esta lógica (depósito origen/destino o selector de depósito): CargaMovStock, Remito, PRemito, NotaCred, NotaCred_SinCompO, PNotaCred, Pedido_Avanzado, Pedido_Interno, Articulo, ArticuloProv, Exportacion, Inventario, etc.

---

## 4. Uso de `deposito` y `CodDeposito` / `id_deposito` en el sistema

### 4.1 Stock por depósito — `stock_deposito`

- **stock_deposito** tiene `id_deposito` = `deposito.CodDeposito` y `id_articulo`. Cada fila es el saldo de un artículo en un depósito.
- Al **alta de depósito** (CargaDeposito) se crean filas en `stock_deposito` para todos los artículos con Saldo = 0.
- En **movimientos de stock** (CargaMovStock, Remito, Factura, TPV, NotaCred, PRemito, PFactura, etc.) se actualiza `stock_deposito.Saldo` (y a veces `saldo_pedido_cliente` o `saldo_pedido_proveedor`) para el `id_deposito` del movimiento.  
  Referencia: **STOCK_VB6_PROCEDIMIENTOS_GUARDADO.md**, **STOCKP_VB6_PROCEDIMIENTOS_GUARDADO.md**.

### 4.2 Movimientos de stock — `stock`, `stockp`, `movimiento_stock`

- En **stock** y **stockp** el campo **CodDeposito** indica el depósito del renglón (venta, pedido, OC, remito compra, movimiento manual, etc.).
- En **movimiento_stock** (cabecera de movimientos, p. ej. Pedido Interno “A deposito”, CargaMovStock transferencias) existen **deposito_origen** y **deposito_destino**, ambos referenciando `deposito.CodDeposito`. En ConsultaComprobante y Visualiza se hace JOIN con `deposito AS origen` y `deposito AS destino` para mostrar nombres.

### 4.3 CargaMovStock.frm — Origen y destino

- **Depósito origen:** Combo cargado desde `deposito` (con o sin filtro por `deposito_usr` según permiso). Todas las salidas/entradas/transferencias usan `DepositoOrigen.BoundText` (CodDeposito).
- **Depósito destino:** Solo para **transferencias**. Combo: `SELECT * FROM deposito WHERE anulado = 'No' AND CodDeposito <> <origen>`. Se guarda en `stock.CodDeposito` y en `movimiento_stock.deposito_destino`.

### 4.4 Inventario.frm

- Trabaja por depósito; usa `Principal.id_deposito` o selector de depósito y consultas que JOIN `stock_deposito` con `deposito` por `deposito.CodDeposito = stock_deposito.id_deposito`.

### 4.5 Cliente — depósito de despacho

- **cliente_datos_adicionales.id_deposito_despacho** puede guardar el depósito por defecto de despacho del cliente (FK a `deposito.CodDeposito`). En ConsultaComprobante, Visualiza, adm_felectronicas, Principal se hace `LEFT JOIN deposito ON deposito.CodDeposito = cliente_datos_adicionales.id_deposito_despacho` para mostrar el nombre del depósito.

### 4.6 Reposición por depósito — `deposito_reposicion`

- Tabla **deposito_reposicion**: por (id_articulo, id_deposito) se definen stock_minimo, stock_maximo, etc.
- Se usa en Remito, FacturaA, FacturaB, TPV (y TPV_2) para obtener el depósito de reposición del artículo. Visualiza_Pedido y Funciones.bas también referencian stock_deposito + deposito + deposito_reposicion para datos de stock por depósito.

---

## 5. Reportes e informes (Synap / Django)

- **BO vs Stock vs Facturación:**  
  - Cuenta depósitos con `SELECT COUNT(*) FROM deposito WHERE (anulado IS NULL OR anulado = 'No')`.  
  - Si hay más de uno, se agrega nota: stock y reservado se muestran agregados por artículo (todos los depósitos).  
  - Para el tooltip “Stock por depósito” se listan `deposito.CodDeposito`, `NombreDeposito` y por cada artículo el `stock_deposito.saldo` por `id_deposito`.
- **Validación saldo stock:** Usa `stock_deposito` (id_articulo, id_deposito, saldo); no filtra por depósito en la reconciliación global (suma por artículo).
- **verify_reservado_por_deposito:** JOIN `deposito` con `stock_deposito` y con `stockp` (CodDeposito) para verificar reservado por depósito.
- **Self Checkout / Kiosk:** Configuración puede incluir `id_deposito`; se valida contra `deposito` (CodDeposito).

---

## 6. Resumen de tablas y conceptos

| Tabla / concepto            | Relación con `deposito` |
|-----------------------------|--------------------------|
| **deposito**                | Maestro: CodDeposito, NombreDeposito, Descripcion, anulado. |
| **deposito_usr**            | id_deposito = deposito.CodDeposito; restringe qué depósitos ve cada usuario. |
| **stock_deposito**          | id_deposito = deposito.CodDeposito; una fila por (id_articulo, id_deposito); Saldo, saldo_pedido_cliente, saldo_pedido_proveedor. |
| **stock / stockp**          | CodDeposito indica el depósito del movimiento/renglón. |
| **movimiento_stock**        | deposito_origen, deposito_destino = deposito.CodDeposito. |
| **deposito_reposicion**     | id_deposito = deposito.CodDeposito; stock min/max por artículo y depósito. |
| **cliente_datos_adicionales** | id_deposito_despacho = deposito.CodDeposito (depósito de despacho por defecto). |
| **lote_stock**              | id_deposito = deposito.CodDeposito para stock por lote por depósito. |

---

## 7. Scrap / descarte / depósitos que no deben contabilizarse como disponible

### 7.1 Situación actual en VB6 y en la base

- La tabla **`deposito`** solo tiene: **CodDeposito**, **NombreDeposito**, **Descripcion**, **anulado**. No existe ningún campo que indique “scrap”, “descarte”, “no contabilizar en disponible” o “excluir de stock disponible”.
- Un depósito con nombre tipo **"Roturas"** (ej. CodDeposito 4) es un depósito más: tiene filas en `stock_deposito` y se trata igual que los demás en todos los cálculos de stock y en los informes.
- En **CargaMovStock**, **"Rotura"** es un **motivo de movimiento** (TipoComp), no un tipo de depósito: se usa al registrar una **salida** de stock por rotura desde el depósito que el usuario elija (origen). Ese origen puede ser Deposito Central, Ecommerce o Roturas; no hay lógica que excluya un depósito por nombre o por código.

### 7.2 Cómo se usa el stock en informes (Synap)

- **BO vs Stock vs Facturación:**  
  `stock_actual` = `SUM(stock_deposito.saldo)` por **id_articulo**, sumando **todos** los depósitos (sin filtrar por CodDeposito ni por nombre).  
  **disponible** = `GREATEST(0, stock_actual - stock_reservado)`.  
  Por tanto, el saldo del depósito "Roturas" (y el de cualquier otro) **sí se incluye** en disponible y en stock actual.
- **Reconciliación saldo stock:**  
  Columna A = `SUM(stock_deposito.saldo)` por artículo, también **sin excluir** ningún depósito.
- **Tooltip “Stock por depósito” (BO):**  
  Lista todos los depósitos activos y el saldo por artículo en cada uno; no hay exclusión.

### 7.3 Conclusión

**No hay en AdministraNET VB6 ni en los reportes de Synap ningún tratamiento específico de scrap o descarte** que excluya depósitos del “disponible” o del stock a considerar. Si un depósito (p. ej. Roturas) no debe contabilizarse como disponible, hay que implementarlo, por ejemplo:

1. **Campo en `deposito`:** Añadir algo como `no_contabilizar_disponible` ('Si'/'No') o `tipo_deposito` ('Normal'/'Scrap'/'Descarte') y, en los informes que calculan stock_actual o disponible, excluir esos depósitos (p. ej. `JOIN deposito d ON d.CodDeposito = sd.id_deposito AND (d.no_contabilizar_disponible IS NULL OR d.no_contabilizar_disponible = 'No')`).
2. **Lista configurable:** En configuración del reporte o en parámetros de empresa, mantener una lista de CodDeposito a excluir del cálculo de disponible y aplicarla en las consultas.
3. **Exclusión por nombre:** Filtrar por nombre (ej. excluir si `NombreDeposito LIKE '%Rotura%'`) es frágil ante cambios de nombre o nuevos depósitos de descarte con otro nombre.

---

## 8. Consultas útiles

- **Depósitos activos (todos; hoy ninguno se excluye de disponible):**  
  `SELECT * FROM deposito WHERE (anulado IS NULL OR anulado = 'No') ORDER BY CodDeposito;`
- **Cantidad de depósitos activos:**  
  `SELECT COUNT(*) FROM deposito WHERE (anulado IS NULL OR anulado = 'No');`
- **Stock por depósito (por artículo):**  
  `SELECT sd.id_articulo, sd.id_deposito, d.NombreDeposito, sd.saldo FROM stock_deposito sd INNER JOIN deposito d ON d.CodDeposito = sd.id_deposito WHERE (d.anulado IS NULL OR d.anulado = 'No');`
- **Depósitos asignados a un usuario:**  
  `SELECT deposito.* FROM deposito INNER JOIN deposito_usr ON deposito_usr.id_deposito = deposito.CodDeposito WHERE deposito_usr.id_usuario = <id_usuario> AND (deposito.anulado IS NULL OR deposito.anulado = 'No');`

- **Stock por artículo excluyendo depósitos “no disponible” (cuando exista el campo):**  
  Hoy no aplica. Si se agrega `no_contabilizar_disponible` en `deposito`, sería algo como:  
  `SELECT sd.id_articulo, SUM(sd.saldo) FROM stock_deposito sd INNER JOIN deposito d ON d.CodDeposito = sd.id_deposito WHERE (d.no_contabilizar_disponible IS NULL OR d.no_contabilizar_disponible = 'No') GROUP BY sd.id_articulo;`

---

*Elaborado a partir del análisis de administranet_vb6 (Formularios y Modulos) y de reports (query_runner, reconciliation, verify_reservado_por_deposito, self_checkout).*
