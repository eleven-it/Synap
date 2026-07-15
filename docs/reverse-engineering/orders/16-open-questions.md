# Preguntas abiertas — Ingeniería inversa pedidos eCom

**Estado:** Pendientes de validación con producto, operaciones o runtime MySQL.  
**Confianza respuestas:** NO VERIFICADO salvo indicación.

---

## 1. Datos y convivencia histórica

### OQ-001 — ¿Existen pedidos `TipoPedido='Web'` en producción post-migración eCom?

**Contexto:** Filtro listado usa `Web` pero alta actual escribe `Ecom vendedor`.  
**Impacto:** Reportes y filtros BI.  
**Acción sugerida:** Query §5 `read-only-inspection.sql`.

### OQ-002 — ¿Conviven `Web cliente` y `Ecom cliente` en la misma base?

**Contexto:** Synap escribe `Ecom cliente`; PHP escribe `Web cliente`.  
**Impacto:** Filtros unificados Synap/PHP.

### OQ-003 — ¿Valores reales de `comp_ped.Estado` con/sin tilde?

**Contexto:** `En preparación` vs `En preparacion`.  
**Referencia:** `docs/reports/VALIDACION_PEDIDOS_PENDIENTES.md`.  
**Acción:** `SELECT DISTINCT Estado FROM comp_ped`.

---

## 2. Autorización y crédito

### OQ-004 — ¿Quién y cuándo escribe `autorizacion_web`?

**Contexto:** Leída en listados eCom; no escrita en alta PHP.  
**Hipótesis INFERIDA:** Workflow VB6 o backoffice.

### OQ-005 — ¿El flag `arrCliente['exceso']` usa la misma lógica que Synap `mayorista_credito`?

**Impacto:** Paridad autorización entre sistemas.

### OQ-006 — ¿Pedidos `No Autorizado` bloquean preparación en VB6?

**Contexto:** eCom permite alta siempre; campo informativo en PHP.

---

## 3. Stock y depósito

### OQ-007 — ¿`saldo_pedido_cliente` tiene techo o validación en VB6 al preparar?

**Contexto:** PHP puede sobre-reservar sin SQL check.

### OQ-008 — ¿Qué ocurre con `saldo_pedido_cliente` al pasar a remito/facturado?

**Hipótesis INFERIDA:** VB6 decrementa reserva al despachar.

### OQ-009 — ¿Permiso `permiso-sin-stock` se configura por usuario o empresa?

**Evidencia parcial:** `carrito.js` — origen sesión no trazado.

---

## 4. Anulación

### OQ-010 — ¿Operadores anulan pedidos desde VB6 exclusivamente hoy?

**Contexto:** eCom no expone botón; AJAX existe.

### OQ-011 — ¿Anulación VB6 sí anula `percep_cli`?

**Impacto:** Definir si gap PHP es bug o paridad VB6.

### OQ-012 — ¿`ajax-comprobante.php` valida ownership del `codMovP` por sesión?

**Riesgo:** IDOR — NO VERIFICADO en auditoría estática.

---

## 5. Mail y comprobantes

### OQ-013 — ¿Flujo mail PED post-alta se usa en producción o está roto?

**Contexto:** `fin-comprobante` case PED con break vacío; PDF no generado.

### OQ-014 — ¿`relay-comprobante-a-mail.php` se invoca tras cada alta PED eCom?

**Evidencia:** Alta redirect a `alta_pedido.php`, no siempre a fin-comprobante.

### OQ-015 — ¿Existe PDF servidor para PED fuera de `ver_pedido` modal?

---

## 6. Numeración y concurrencia

### OQ-016 — ¿Frecuencia de huecos en `codmov` por fallos rollback?

**Acción:** Métrica operativa en sandbox.

### OQ-017 — ¿Alta concurrente misma empresa satura loop `codmov`?

**Contexto:** Optimistic lock sin backoff documentado.

---

## 7. Logística y entrega

### OQ-018 — ¿`cant_dias_entrega` y `arr_dias_no_laborables` son por empresa o sucursal?

### OQ-019 — ¿`hoja_ruta` obligatoria cuando `activ_logistica=Si`?

**Evidencia PHP:** Acepta NULL si POST vacío (bug L313 posible: `!isset && == ""`).

### OQ-020 — ¿Domicilio obligatorio bloquea commit PHP o solo UI jCart?

---

## 8. Migración Synap

### OQ-021 — ¿Producto acepta convivencia indefinida `Web cliente` / `Ecom cliente`?

### OQ-022 — ¿Se requiere ETL normalización `TipoPedido` histórico?

### OQ-023 — ¿Portal cliente legacy sigue apuntando a PHP en algún tenant?

**Referencia:** Relay `frm=0` → Synap documentado en SPEC.

---

## 9. Priorización de cierre

| ID | Prioridad | Responsable sugerido |
|----|-----------|---------------------|
| OQ-001, OQ-002 | Alta | Datos / BI |
| OQ-003 | Media | DBA |
| OQ-011, OQ-012 | Alta | Seguridad / VB6 |
| OQ-013, OQ-014 | Media | Producto |
| OQ-021, OQ-022 | Alta | Producto migración |

---

## 10. Cómo cerrar cada pregunta

1. Ejecutar `sql/read-only-inspection.sql` en copia DB (solo lectura).
2. Entrevista operador depósito (VB6 preparación/remito).
3. Comparar con `mayorista_credito` y tests Synap.
4. Registrar resolución en este archivo o `docs/ecom/`.
