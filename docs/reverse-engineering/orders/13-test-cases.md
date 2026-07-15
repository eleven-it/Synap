# Casos de prueba — Pedidos eCom (AS-IS)

**Propósito:** Validar paridad comportamiento legacy y regresión Synap.  
**Ejecución PHP:** manual en entorno eCom; **Synap:** `docker exec Synap_app python manage.py test ecom`.  
**SQL inspección:** `sql/read-only-inspection.sql`  
**SQL mutación:** solo `sql/sandbox-tests.sql` en DEV/SANDBOX.

---

## 1. Alta de pedido

### TC-PED-001 — Alta vendedor feliz path (CONFIRMADO)

| Campo | Valor |
|-------|-------|
| Precondición | Vendedor logueado, cliente con crédito OK, carrito 2 ítems |
| Pasos | Seleccionar cliente → alta_pedido → agregar ítems → confirmar |
| Resultado esperado | Redirect `cartel=0&ped=PV-NNNNNNNN`; `comp_ped.Estado=Pendiente`; `TipoPedido=Ecom vendedor`; `Anulado=No` |
| SQL verify | Query §2 `read-only-inspection.sql` por `NroComprobante` |

### TC-PED-002 — Alta cliente web (CONFIRMADO)

| Campo | Valor |
|-------|-------|
| Precondición | `tipousuario=cliente` |
| Pasos | Carrito → confirmar → `confOperacion=ok` |
| Resultado | `TipoPedido=Web cliente`; `autorizacion_sistema=No Autorizado` (rama cliente pura) |

### TC-PED-003 — Carrito vacío (CONFIRMADO)

| Pasos | Confirmar sin ítems |
| Resultado | Redirect `alta_pedido.php?cartel=1`; sin filas nuevas en `comp_ped` |

### TC-PED-004 — Cliente no seleccionado (CONFIRMADO)

| Pasos | Acceder `alta_pedido.php` sin sesión cliente |
| Resultado | Redirect `listado-clientes.php?cartel=1` |

### TC-PED-005 — Cliente exceso crédito vendedor (CONFIRMADO)

| Precondición | `arrCliente['exceso']=1` |
| Resultado | Alta permitida; `autorizacion_sistema=No Autorizado` |

---

## 2. Stock y cantidades

### TC-PED-010 — Reserva stock_deposito (CONFIRMADO)

| Pasos | Alta con artículo qty=5 |
| Verificar | `saldo_pedido_cliente` incrementó 5 vs valor previo |

### TC-PED-011 — Validación JS stock insuficiente (CONFIRMADO)

| Precondición | `permiso-sin-stock` desactivado, saldo < cantidad |
| Resultado | Alert JS "Sin STOCK disponible"; no agrega al carrito |

### TC-PED-012 — Bypass permiso sin stock (INFERIDO)

| Precondición | Permiso sin stock activo |
| Resultado | Alta persiste aunque saldo JS < cantidad |

### TC-PED-013 — Sin validación SQL stock (CONFIRMADO)

| Pasos | Simular POST directo a confirmado sin pasar JS |
| Resultado | PHP acepta y suma `saldo_pedido_cliente` (prueba solo SANDBOX) |

---

## 3. Numeración y transacciones

### TC-PED-020 — Unicidad CodigoMovimiento (CONFIRMADO)

| Verificar | Cada PED nuevo tiene `CodigoMovimiento` distinto y mayor al anterior |

### TC-PED-021 — Formato NroComprobante (CONFIRMADO)

| Verificar | Regex `^\d{4}-\d{8}$` |

### TC-PED-022 — Rollback parcial (CONFIRMADO)

| Pasos | Forzar error en INSERT stockp (sandbox) |
| Resultado | ROLLBACK; DELETE compensatorio; posible codmov consumido |

---

## 4. Cálculos

### TC-PED-030 — Totales cabecera vs jCart (CONFIRMADO)

| Verificar | `ImporteVenta` = subtotal jCart con imp interno; `Iva1+Iva2+SubTotalDesc` coherentes |

### TC-PED-031 — Descuento al pie (CONFIRMADO)

| Precondición | Cliente con `descPie>0` |
| Verificar | `PorDesc1/2` y netos descontados en cabecera |

### TC-PED-032 — Percepciones agente (CONFIRMADO)

| Precondición | `agente_percep=Si`, params cliente configurados |
| Verificar | Filas `percep_cli` + `total_percep` en cabecera |

### TC-PED-033 — Unidad Display/Bulto (CONFIRMADO)

| Verificar | `stockp.tipo_unidad`, `Cantidad` coherente con `cantidadMinimaContada` |

---

## 5. Listado y consulta

### TC-PED-040 — Listado vendedor cartera (CONFIRMADO)

| Precondición | `todos_clientes=No` |
| Verificar | Solo pedidos `CodViajante` del vendedor |

### TC-PED-041 — Filtro Tipo Web Vendedor (CONFIRMADO — bug)

| Pasos | Filtrar "Web Vendedor" (`value=Web`) tras alta eCom vendedor |
| Resultado esperado legacy | **0 resultados** (desalineación); pedido tiene `Ecom vendedor` |

### TC-PED-042 — Ver detalle modal (CONFIRMADO)

| Pasos | Click verComprobante |
| Resultado | AJAX `ver_pedido.php` devuelve HTML con renglones |

---

## 6. Anulación

### TC-PED-050 — Anulación AJAX feliz (CONFIRMADO)

| Precondición | PED Pendiente sin remito/factura |
| Request | `ajax-comprobante.php?tipoComp=PED&codMovP={cod}` |
| Resultado | `anulado=Si`; stock revertido; mensaje éxito |

### TC-PED-051 — Bloqueo por remito (CONFIRMADO)

| Precondición | `rem_ped` activo |
| Resultado | Mensaje remito; sin cambios |

### TC-PED-052 — Bloqueo por factura (CONFIRMADO)

| Precondición | `ped_fact` activo |
| Resultado | Mensaje factura; sin cambios |

### TC-PED-053 — percep_cli persiste (CONFIRMADO gap)

| Pasos | Anular PED con percepciones |
| Verificar | Filas `percep_cli` siguen activas (no anuladas) |

### TC-PED-054 — Sin botón UI anulación (CONFIRMADO)

| Pasos | Revisar HTML listado vendedor |
| Resultado | No hay control que llame ajax-comprobante |

---

## 7. Mail

### TC-PED-060 — fin-comprobante PED post-mail (CONFIRMADO)

| Pasos | Enviar mail PED exitoso |
| Resultado | Sin redirect automático (break vacío) |

### TC-PED-061 — Sin mail vendedor (CONFIRMADO)

| Precondición | Credenciales SMTP vacías |
| Resultado | Redirect `cartel=7` |

---

## 8. Regresión Synap (paridad TO-BE)

| ID Synap | Equivalente PHP | Servicio |
|----------|-----------------|----------|
| TC-SYN-001 | TC-PED-001 | `mayorista_checkout_service` |
| TC-SYN-010 | TC-PED-050 | `anular_pedido_relay` + reversa stock |
| TC-SYN-011 | TC-PED-053 | Verificar anulación `percep_cli` en Synap ✅ |

Ejecutar: `docker exec Synap_app python manage.py test ecom.tests.test_pedido_gestion ecom.tests.test_compra_mayorista_cliente`

---

## 9. Matriz trazabilidad regla → test

| Regla | Test |
|-------|------|
| PED-RN-001 | TC-PED-003 |
| PED-RN-005 | TC-PED-001, TC-PED-002 |
| PED-RN-020 | TC-PED-010 |
| PED-RN-021 | TC-PED-011, TC-PED-013 |
| PED-RN-060/061 | TC-PED-051, TC-PED-052 |
| PED-RN-063 | TC-PED-053 |
| PED-RN-081 | TC-PED-041 |
| PED-RN-090 | TC-PED-060 |
