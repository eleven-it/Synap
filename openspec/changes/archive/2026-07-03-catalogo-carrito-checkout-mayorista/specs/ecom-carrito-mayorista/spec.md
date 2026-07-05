# Spec: Carrito mayorista (borrador en Synap)

**Change:** `catalogo-carrito-checkout-mayorista`
**Artifact Type:** delta spec
**Fase:** P1 (persistencia en Postgres `synap`, sin escritura MySQL legacy)
**Target:** `ecom/` (portal mayorista). Reutiliza `price_rules_engine.calcular_precio_articulo_row`, `self_checkout.StockService`, `mayoristapp_session`.
**Legacy:** `administraNET-ecom/mayoristapp/jcart/jcart.php` (clase `Jcart`, `$_SESSION['jcart']`).

---

## ADDED Requirements

### REQ-CAR-001: Un carrito activo por vendedor y cliente

El sistema **MUST** mantener, por combinación de empresa + usuario (vendedor), **un** carrito en estado `borrador`. El carrito **MUST** registrar el cliente seleccionado, la lista de precio, el depósito y si el IVA va incluido (tomados de la sesión mayorista). Al cambiar el cliente seleccionado, el carrito borrador **MUST** vaciarse/recrearse (paridad `session.pop("jcart")` del PHP).

**Acceptance Scenarios:**

```gherkin
Escenario: Crear u obtener el carrito activo
  DADO un vendedor autenticado con cliente y lista de precio en sesión
  CUANDO solicita su carrito activo por primera vez
  ENTONCES el sistema crea un carrito en estado borrador asociado a ese usuario y cliente
  Y devuelve el carrito vacío con totales en cero
```

```gherkin
Escenario: Cambio de cliente reinicia el carrito
  DADO un carrito borrador con ítems para el cliente A
  CUANDO el vendedor selecciona el cliente B y solicita el carrito
  ENTONCES el carrito del cliente A no se mezcla con el del cliente B
  Y el carrito devuelto para B no contiene los ítems de A
```

---

### REQ-CAR-002: Agregar ítem con precio del motor y validación de stock

Al agregar un artículo, el sistema **MUST** validar que la **cantidad total** del artículo en el carrito no supere el stock **disponible** (`max(0, saldo − saldo_pedido_cliente)`) del depósito activo (reutilizando `StockService`). El **precio del renglón MUST** calcularse con el motor único (`calcular_precio_articulo_row`) según la lista y el cliente, guardando neto unitario, alícuota IVA, impuesto interno y datos de promoción. Si el artículo ya está en el carrito, **MUST** consolidarse en un único renglón sumando cantidades.

**Acceptance Scenarios:**

```gherkin
Escenario: Agregar artículo con stock suficiente
  DADO un artículo con 100 unidades disponibles en el depósito activo
  CUANDO el vendedor agrega 10 unidades
  ENTONCES el ítem se agrega con el precio calculado por el motor para la lista del cliente
  Y los totales del carrito se recalculan
```

```gherkin
Escenario: Agregar cantidad que excede el stock disponible
  DADO un artículo con 5 unidades disponibles
  CUANDO el vendedor intenta agregar 8 unidades
  ENTONCES el sistema NO agrega el ítem
  Y devuelve un mensaje en español indicando el stock disponible
```

```gherkin
Escenario: Agregar un artículo ya presente consolida el renglón
  DADO un carrito con 3 unidades del artículo X
  CUANDO el vendedor agrega 2 unidades más del artículo X (con stock suficiente)
  ENTONCES el carrito tiene un único renglón del artículo X con cantidad 5
```

---

### REQ-CAR-003: Actualizar cantidad, descuento de renglón y quitar ítem

El sistema **MUST** permitir actualizar la cantidad de un ítem (revalidando stock), aplicar/actualizar el descuento porcentual del renglón (0–100) y quitar un ítem. Toda operación **MUST** recalcular los totales.

**Acceptance Scenarios:**

```gherkin
Escenario: Actualizar cantidad revalida stock
  DADO un ítem con 5 unidades y 5 disponibles
  CUANDO el vendedor cambia la cantidad a 10
  ENTONCES el sistema rechaza el cambio por stock insuficiente y conserva la cantidad previa
```

```gherkin
Escenario: Aplicar descuento de renglón
  DADO un ítem con neto de 1000 y alícuota 21%
  CUANDO el vendedor aplica 10% de descuento al renglón
  ENTONCES el neto del renglón pasa a 900 y el IVA se calcula sobre 900
```

```gherkin
Escenario: Quitar ítem
  DADO un carrito con 2 ítems
  CUANDO el vendedor quita uno
  ENTONCES el carrito queda con 1 ítem y los totales se recalculan
```

---

### REQ-CAR-004: Cálculo de totales con desglose por alícuota

El sistema **MUST** recalcular y exponer los totales del carrito con paridad `Jcart.update_subtotal`: neto gravado por alícuota (21% y 10,5%), IVA por alícuota, subtotal exento, impuesto interno total, descuento al pie (porcentaje e importe) y total final. El descuento al pie **MUST** aplicarse sobre el neto por alícuota antes de recalcular el IVA.

**Acceptance Scenarios:**

```gherkin
Escenario: Desglose con dos alícuotas
  DADO un carrito con un ítem gravado al 21% (neto 1000) y otro al 10,5% (neto 500)
  CUANDO se recalculan los totales
  ENTONCES el neto gravado 21% es 1000 con IVA 210
  Y el neto gravado 10,5% es 500 con IVA 52,50
  Y el total es 1762,50
```

```gherkin
Escenario: Descuento al pie
  DADO un carrito con neto gravado 21% de 1000 (IVA 210)
  CUANDO se aplica 10% de descuento al pie
  ENTONCES el neto pasa a 900 y el IVA a 189
  Y el total refleja el descuento
```

```gherkin
Escenario: Ítem exento
  DADO un ítem con alícuota 0 (exento) y neto 300
  CUANDO se recalculan los totales
  ENTONCES el subtotal exento es 300 y no genera IVA
```

---

## Implementation Constraints

- **Persistencia:** modelos Django `EcomCart` / `EcomCartItem` en la base `synap` (Postgres). **Sin** escritura a MySQL legacy en esta fase.
- **Scope multiempresa:** todo carrito **MUST** llevar `base_empresa` y `id_usuario`; las consultas **MUST** filtrar por ellos.
- **Stock:** reutilizar `self_checkout.services.stock_service.StockService` (no duplicar el cálculo de disponible).
- **Precio:** reutilizar `ecom.services.price_rules_engine.calcular_precio_articulo_row` (fuente única). El carrito guarda el neto calculado; el **checkout (P2) recalcula** para autoridad final.
- **Decimales:** usar `Decimal` (no float) en cálculos; cuantización a 2 decimales para importes.
- **Permiso:** `EcomMayoristappSessionPermission`.
- **Idioma:** mensajes en español; fechas dd/MM/yyyy en textos al usuario.

---

## Size Budget

**Escenarios:** 11 · **Estado:** draft

## Metadata

- **Author role:** SDD (agente principal)
- **Created:** 2026-07-02
- **Status:** draft
