# Reglas de negocio — Pedidos eCom (AS-IS)

**Formato ID:** `PED-RN-xxx`  
**Confianza:** CONFIRMADO salvo indicación

---

## Alta y validación

### PED-RN-001 — Carrito no vacío (CONFIRMADO)

**Regla:** No se persiste pedido si `articulos` vacío o `pedidoArr['subtotal'] <= 0`.  
**Evidencia:** `alta_pedido_confirmado.php` L160, L864-871.  
**Acción:** Redirect `alta_pedido.php?cartel=1`, vaciar carrito.

### PED-RN-002 — Cliente obligatorio en sesión (CONFIRMADO)

**Regla:** Sin `$_SESSION['cliente']` → redirect `listado-clientes.php`.  
**Evidencia:** `alta_pedido.php` L30-32.

### PED-RN-003 — Estado inicial Pendiente (CONFIRMADO)

**Regla:** Todo PED eCom nuevo nace con `Estado='Pendiente'`.  
**Evidencia:** INSERT `comp_ped` L453.

### PED-RN-004 — No anulado al crear (CONFIRMADO)

**Regla:** `anulado='No'` en cabecera y renglones.  
**Evidencia:** L438, L786.

### PED-RN-005 — Tipo pedido por actor (CONFIRMADO)

| Actor | `TipoPedido` |
|-------|--------------|
| Vendedor | `Ecom vendedor` |
| Cliente web | `Web cliente` |

**Evidencia:** `alta_pedido_confirmado.php` L43; `alta_pedido_confirmado_cliente.php` L73.

### PED-RN-006 — Bifurcación confirmación cliente (CONFIRMADO)

**Regla:** Si `tipousuario=='cliente'`, redirect a `alta_pedido_confirmado_cliente.php` antes de procesar.  
**Evidencia:** L19-21 `alta_pedido_confirmado.php`.

### PED-RN-007 — Confirmación explícita cliente (CONFIRMADO)

**Regla:** Cliente requiere `POST confOperacion=ok` para commit.  
**Evidencia:** `alta_pedido_confirmado_cliente.php` L124.

---

## Autorización comercial

### PED-RN-010 — Autorización sistema vendedor (CONFIRMADO)

**Regla:** Vendedor: `Autorizado` salvo `arrCliente['exceso']==1` → `No Autorizado`.  
**Evidencia:** L174-178 `alta_pedido_confirmado.php`.  
**Nota:** No bloquea el alta; solo marca cabecera.

### PED-RN-011 — Autorización sistema cliente (CONFIRMADO)

**Regla:** Pedido cliente web siempre `No Autorizado` en rama vendedor-redirect; en `_cliente.php` depende de `arrCliente['exceso']`.  
**Evidencia:** L179-181 confirmado.php; L241-252 cliente.php.

### PED-RN-012 — autorizacion_web no se escribe (CONFIRMADO)

**Regla:** Alta eCom no popula `comp_ped.autorizacion_web`.  
**Evidencia:** INSERT sin campo; listado sí SELECT (lectura legacy).

---

## Stock y depósito

### PED-RN-020 — Reserva stock en alta (CONFIRMADO)

**Regla:** Por cada renglón, `stock_deposito.saldo_pedido_cliente += qty`.  
**Evidencia:** L526-548.

### PED-RN-021 — Validación stock solo JavaScript (CONFIRMADO)

**Regla:** PHP commit **no** valida disponibilidad SQL; `carrito.js` compara cantidad vs saldo.  
**Evidencia:** `_scripts/carrito.js` L500-513; ausencia check en PHP.

### PED-RN-022 — Permiso operar sin stock (CONFIRMADO)

**Regla:** Si `permiso-sin-stock` activo, permite cantidad > saldo.  
**Evidencia:** `carrito.js` L405-513 (INFERIDO nombre exacto flag sesión).

---

## Numeración

### PED-RN-030 — CodigoMovimiento único optimista (CONFIRMADO)

**Regla:** Loop `while($buscoCod==0)` hasta `mysqli_affected_rows=1` en update `codmov`.  
**Evidencia:** L198-227.

### PED-RN-031 — Talonario PED por PV (CONFIRMADO)

**Regla:** Numeración desde `talonarios` where `TipoComprobante='PED'` e `id_punto_venta` del vendedor.  
**Evidencia:** L237-260.

### PED-RN-032 — Formato NroComprobante (CONFIRMADO)

**Regla:** `str_pad(PV,4,'0').'-'.str_pad(Nro,8,'0')`.

---

## Entrega y logística

### PED-RN-040 — Fecha entrega calculada (CONFIRMADO)

**Regla:** Hoy + `cant_dias_entrega`; si día en `arr_dias_no_laborables`, +1 día adicional.  
**Evidencia:** L274-288.

### PED-RN-041 — Origen pedido Web en datos adicionales (CONFIRMADO)

**Regla:** `cliente_datos_adicionales.origen_pedido = 'Web'`.  
**Evidencia:** L347.

### PED-RN-042 — Domicilio entrega opcional/obligatorio (INFERIDO)

**Regla:** Controlado por `obliga_domicilio_cliente` en jCart display; PHP acepta NULL.  
**Evidencia:** jcart display + L304-309.

---

## Percepciones

### PED-RN-050 — Percepciones si agente (CONFIRMADO)

**Regla:** Si `agente_percep='Si'`, jCart calcula y alta inserta `percep_cli`.  
**Evidencia:** jcart L1063+; confirmado L369-394.

### PED-RN-051 — Percepciones sin config → error carrito (CONFIRMADO)

**Regla:** Sin filas en `percep_cli_param` → `update_subtotal` retorna error tipo `percepcion`.  
**Evidencia:** jcart L1071-1076.

---

## Anulación

### PED-RN-060 — Bloqueo por factura (CONFIRMADO)

**Regla:** Si existe `ped_fact` activo, no anula; mensaje con Nº factura.  
**Evidencia:** `ajax-comprobante.php` L21-36.

### PED-RN-061 — Bloqueo por remito (CONFIRMADO)

**Regla:** Si existe `rem_ped` activo, no anula; mensaje con Nº remito.  
**Evidencia:** L39-52.

### PED-RN-062 — Reversa stock en anulación (CONFIRMADO)

**Regla:** `saldo_pedido_cliente -= stockp.Cantidad` por renglón.  
**Evidencia:** L89-95.

### PED-RN-063 — percep_cli no se anula en PHP (CONFIRMADO)

**Regla:** Anulación eCom no marca `percep_cli`. Gap vs Synap.

### PED-RN-064 — Sin UI anulación en listado (CONFIRMADO)

**Regla:** `lista-pedidos-vendedor.php` no invoca `ajax-comprobante.php`.

---

## Modificación

### PED-RN-070 — Sin edición in-place (CONFIRMADO)

**Regla:** No existe flujo PHP eCom para UPDATE de renglones/cabecera de PED existente.  
**Evidencia:** Ausencia archivos mod_*; patrón anular + nuevo en Synap.

---

## Listado y filtros

### PED-RN-080 — Filtro vendedor por viajante (CONFIRMADO)

**Regla:** Si `todos_clientes='No'`, `CodViajante = objVendedor.CodViajante`.  
**Evidencia:** `lista-pedidos-vendedor.php` L29-31.

### PED-RN-081 — Desalineación filtro Tipo Web (CONFIRMADO)

**Regla:** UI ofrece `TipoPedido='Web'` etiquetado "Web Vendedor" pero alta guarda `Ecom vendedor`.  
**Evidencia:** L459 listado vs L43 confirmado.

### PED-RN-082 — Límite 60 registros carga inicial (CONFIRMADO)

**Regla:** `ORDER BY Fecha DESC LIMIT 60`.  
**Evidencia:** L83.

---

## Mail post-alta

### PED-RN-090 — fin-comprobante PED sin redirect éxito (CONFIRMADO)

**Regla:** Tras mail OK para `PED`, `switch` ejecuta `break` vacío — usuario queda sin navegación automática.  
**Evidencia:** `fin-comprobante.php` L152-153.

### PED-RN-091 — Mail vendedor requerido (CONFIRMADO)

**Regla:** Sin credenciales correo vendedor → redirect `listado-clientes.php?cartel=7`.  
**Evidencia:** `fin-comprobante.php` L31-35.

---

## Índice rápido

| ID | Resumen |
|----|---------|
| PED-RN-001..007 | Validación alta |
| PED-RN-010..012 | Autorización |
| PED-RN-020..022 | Stock |
| PED-RN-030..032 | Numeración |
| PED-RN-040..042 | Entrega |
| PED-RN-050..051 | Percepciones |
| PED-RN-060..064 | Anulación |
| PED-RN-070 | No edición |
| PED-RN-080..082 | Listado |
| PED-RN-090..091 | Mail |
