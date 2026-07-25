# Spec: Checkout mayorista — alta de pedido/presupuesto

**Change:** `catalogo-carrito-checkout-mayorista`
**Artifact Type:** delta spec
**Fase:** P2 (escritura legacy MySQL controlada — **riesgo ALTO**) + P4 (percepciones IIBB, REQ-CHK-009)
**Target:** `ecom/` (portal mayorista). Confirma el carrito P1 dando de alta un comprobante en AdministraNET (MySQL).
**Legacy:** `administraNET-ecom/mayoristapp/{alta_pedido_confirmado.php, alta_presupuesto_confirmado.php}`.
**Alcance de esta fase:** **PED** (pedido, baja stock comprometido) y **PRE** (presupuesto, no toca stock). **DEV** (devolución) queda para P3.

---

## ADDED Requirements

### REQ-CHK-001: Confirmación transaccional atómica del carrito

Al confirmar un carrito borrador, el sistema **MUST** ejecutar todas las escrituras legacy dentro de **una única transacción MySQL** (autocommit off, `COMMIT`/`ROLLBACK`), escribiendo: cabecera `comp_ped`, renglones `stockp` (uno por ítem), `cliente_datos_adicionales`, `percep_cli` (una por percepción) y —solo para PED— `UPDATE stock_deposito.saldo_pedido_cliente`. Si cualquier paso falla, **MUST** hacer `ROLLBACK` completo y no dejar comprobante parcial. Ninguna escritura legacy **MUST** ocurrir fuera del acto de confirmar (el carrito borrador nunca escribe en MySQL).

**Acceptance Scenarios:**

```gherkin
Escenario: Alta de pedido exitosa
  DADO un carrito borrador con 2 ítems, cliente y punto de venta válidos
  CUANDO el vendedor confirma el pedido (PED)
  ENTONCES se crea una cabecera comp_ped con Estado 'Pendiente'
  Y se crean 2 renglones stockp con el mismo CodigoMovimiento
  Y se actualiza saldo_pedido_cliente en stock_deposito por cada artículo
  Y el carrito queda en estado 'confirmado' con el CodigoMovimiento y NroComprobante generados
```

```gherkin
Escenario: Rollback ante fallo en un renglón
  DADO un carrito en confirmación con la cabecera ya insertada
  CUANDO falla el INSERT de un renglón stockp
  ENTONCES la transacción hace ROLLBACK completo
  Y no queda ninguna fila comp_ped/stockp/percep_cli/cliente_datos_adicionales con ese CodigoMovimiento
  Y el carrito permanece en estado 'borrador'
```

```gherkin
Escenario: El borrador no escribe en MySQL
  DADO un carrito con ítems agregados (fase P1)
  CUANDO el vendedor agrega/quita ítems sin confirmar
  ENTONCES no se realiza ninguna escritura en comp_ped/stockp/stock_deposito
```

---

### REQ-CHK-002: Numeración segura bajo concurrencia

El sistema **MUST** generar el `CodigoMovimiento` desde `codmov` y el número de comprobante desde `talonarios` (por `id_punto_venta` + `TipoComprobante`) de forma **segura ante concurrencia**, corrigiendo el bug del PHP legacy (que actualiza `talonarios.Nro` sin lock). En Synap **MUST** usarse `SELECT ... FOR UPDATE` (o lock optimista con reintento acotado) dentro de la transacción, de modo que dos confirmaciones simultáneas **NO** obtengan el mismo número. El `NroComprobante` **MUST** formatearse `PV(4)-Nro(8)` con ceros a la izquierda; `NroCompBusq` guarda el `Nro` sin formato.

**Acceptance Scenarios:**

```gherkin
Escenario: Dos confirmaciones concurrentes no duplican número
  DADO dos vendedores confirmando pedidos en el mismo punto de venta simultáneamente
  CUANDO ambas transacciones toman número de talonarios
  ENTONCES cada comprobante recibe un Nro distinto y consecutivo
  Y talonarios.Nro queda incrementado exactamente en 2
```

```gherkin
Escenario: Formato de número de comprobante
  DADO un punto de venta PV=3 con talonarios.Nro=57
  CUANDO se confirma el pedido
  ENTONCES NroComprobante = '0003-00000057'
  Y NroCompBusq = 57
  Y talonarios.Nro pasa a 58
```

---

### REQ-CHK-003: Validación de stock disponible en el commit (solo PED)

Para **PED**, el sistema **MUST** revalidar el stock **disponible** en el momento del commit (no confiar en la validación del carrito) mediante un `UPDATE` condicionado que sólo aplique si `saldo − saldo_pedido_cliente ≥ cantidad`. Si el `UPDATE` no afecta filas (stock insuficiente), la transacción **MUST** hacer `ROLLBACK` y devolver un error en español indicando el artículo. Para **PRE** no se valida ni modifica stock.

**Acceptance Scenarios:**

```gherkin
Escenario: Stock se consumió entre carrito y checkout
  DADO un ítem con 3 disponibles al agregar al carrito
  Y que otro proceso consumió stock dejando 1 disponible
  CUANDO el vendedor confirma el pedido de 3 unidades
  ENTONCES la confirmación falla con "Stock insuficiente" indicando el artículo
  Y no se crea el comprobante
```

```gherkin
Escenario: Presupuesto no valida stock
  DADO un ítem con 0 disponibles
  CUANDO el vendedor confirma un presupuesto (PRE) con ese ítem
  ENTONCES el presupuesto se crea correctamente sin tocar stock_deposito
```

---

### REQ-CHK-004: Validación de crédito y autorización

El sistema **MUST** calcular la **autorización** del comprobante mediante el evaluador unificado de `ecom-credito-pedidos` cuando `ecom_credito_pedidos_activa` está ON: MUST considerar política por cliente/canal, exposición Balance+All (capas ON/OFF), monto y mora en días; MUST persistir snapshot de evaluación (motivos, capas, totales) junto al alta. Si `cliente.Credito=0`, MUST NOT rechazar por tope monetario. Con flag OFF MUST mantener evaluación legacy solo-días. Un pedido originado por **cliente** (autogestión) **MUST** quedar siempre `'No Autorizado'`. El exceso de crédito MUST NOT bloquear el alta; MUST registrarse el estado correspondiente y, en fase B, activar hold de preparación cuando aplique.

**Acceptance Scenarios:**

```gherkin
Escenario: Cliente al día autorizado
  DADO un cliente sin comprobantes vencidos más allá de su límite de días y exposición dentro de cupo
  CUANDO el vendedor confirma el pedido
  ENTONCES comp_ped.autorizacion_sistema = 'Autorizado'
  Y MUST persistir snapshot de evaluación cuando flag crédito ON
```

```gherkin
Escenario: Cliente con atraso excede límite
  DADO un cliente con credito_limite_dias = 30 y un comprobante impago de hace 45 días
  CUANDO el vendedor confirma el pedido
  ENTONCES el pedido se crea con autorizacion_sistema = 'No Autorizado'
  Y MUST registrarse motivo por días en snapshot
```

```gherkin
Escenario: Exceso de exposición monetaria
  DADO flag crédito ON, cliente con cupo $ finito y exposición + total pedido superan límite
  CUANDO el vendedor confirma PED
  ENTONCES MUST crearse comprobante con autorizacion_sistema = 'No Autorizado'
  Y MUST NOT abortar la transacción de alta por crédito
  Y MUST incluir motivo por monto en snapshot
```

```gherkin
Escenario: Flag crédito OFF — solo días
  DADO ecom_credito_pedidos_activa desactivado
  CUANDO se confirma pedido
  ENTONCES MUST evaluarse únicamente mora en días según reglas legacy
  Y MUST NOT persistir snapshot de exposición $
```

---

### REQ-CHK-005: Idempotencia (evita doble alta)

El sistema **MUST** ser idempotente frente a un doble envío: si el carrito ya está `confirmado`, una nueva confirmación **MUST** devolver el resultado existente (mismo `CodigoMovimiento`/`NroComprobante`) sin crear un segundo comprobante. La verificación del estado del carrito **MUST** ocurrir dentro de la transacción antes de numerar/insertar.

**Acceptance Scenarios:**

```gherkin
Escenario: Doble submit no duplica el comprobante
  DADO un carrito ya confirmado con CodigoMovimiento X
  CUANDO se vuelve a llamar a confirmar el mismo carrito
  ENTONCES no se crea un nuevo comprobante
  Y la respuesta devuelve el CodigoMovimiento X existente
```

---

### REQ-CHK-006: Precio como autoridad del motor en el commit

En el commit, el sistema **MUST** recalcular los precios de cada renglón con el motor único (`price_rules_engine`) según lista/cliente vigentes, **sin confiar** en los importes persistidos del carrito P1. Los importes escritos en `comp_ped`/`stockp` (netos, IVA 21/10,5, exento, impuesto interno, descuentos, percepciones, total) **MUST** derivar de ese recálculo, garantizando consistencia con el catálogo y el carrito.

**Acceptance Scenarios:**

```gherkin
Escenario: Cambio de precio antes de confirmar
  DADO un carrito con un ítem preciado a 100 en la lista
  Y que la lista cambió el precio a 110 antes de confirmar
  CUANDO el vendedor confirma el pedido
  ENTONCES los importes de comp_ped/stockp reflejan el precio 110 recalculado
```

---

### REQ-CHK-007: Selección de punto de venta (fiscal / no fiscal)

El sistema **MUST** determinar el punto de venta activo desde la sesión mayorista para numerar el comprobante. Si no hay punto de venta válido para el `TipoComprobante`, la confirmación **MUST** fallar con un mensaje en español, sin escribir nada.

**Acceptance Scenarios:**

```gherkin
Escenario: Sin punto de venta configurado
  DADO un vendedor sin punto de venta activo en sesión
  CUANDO intenta confirmar un pedido
  ENTONCES la confirmación falla indicando que falta seleccionar punto de venta
  Y no se realiza ninguna escritura legacy
```

---

### REQ-CHK-008: Cálculo de fecha de entrega (solo PED)

Para **PED**, el sistema **MUST** calcular `FechaEntrega` sumando los días de entrega configurados y evitando días no laborables (paridad legacy). El resultado **MUST** persistirse en `comp_ped.FechaEntrega` y `cliente_datos_adicionales.fechaEntrega`. Para **PRE** la fecha de entrega no aplica.

**Acceptance Scenarios:**

```gherkin
Escenario: Fecha de entrega salta día no laborable
  DADO días de entrega = 2 y que el día resultante es no laborable
  CUANDO se confirma el pedido
  ENTONCES FechaEntrega se corre al siguiente día hábil según la configuración
```

---

### REQ-CHK-009: Percepciones de Ingresos Brutos (IIBB) — configurable por implementación (Fase P4)

El cálculo de percepciones de IIBB **MUST** ser una **opción configurable según la implementación del cliente**: se activa cuando la sucursal del cliente es agente de percepción (`sucursales.agente_percep = 'Si'`, paridad legacy — flag ya cargado en sesión por `control.php`). Cuando está **desactivado**, `comp_ped.total_percep` **MUST** persistirse en `0` y no se insertan filas en `percep_cli`.

Cuando está **activado**, para **PED** y **PRE**, el sistema **MUST**:
- Tomar como **base imponible** el neto gravado con descuento (renglón + pie) del comprobante (equivalente al `subtotal_neto` del carrito; paridad `jcart.php` `totalNetoPer`).
- Leer los tipos de percepción del cliente en `percep_cli_param WHERE id_cliente = <cliente>`.
- Por cada tipo, leer `percep_cli_tipo.alicuota_percep_cli_tipo` y calcular `importe = base × alícuota / 100` (paridad legacy: **sin** aplicar `importe_minimo`).
- Insertar **una fila por tipo** en `percep_cli` (`id_percep_cli_tipo`, `alicuota_percep_cli`, `importe_percep_cli`, `codigo_movimiento`, `id_cliente`, `tipo_comp`) dentro de la **misma transacción** del alta.
- Acumular el total en `comp_ped.total_percep`.

Si `agente_percep = 'Si'` pero el cliente **no** tiene tipos configurados en `percep_cli_param`, el sistema **MUST** abortar la confirmación con un mensaje claro en español (paridad legacy: no se genera un comprobante fiscalmente incompleto), haciendo `ROLLBACK`.

Para **DEV** (devolución) las percepciones quedan **fuera de alcance** de esta fase (`total_percep = 0`).

**Acceptance Scenarios:**

```gherkin
Escenario: Sucursal no agente de percepción → sin IIBB
  DADO un cliente cuya sucursal tiene agente_percep = 'No'
  CUANDO se confirma un pedido (PED)
  ENTONCES comp_ped.total_percep se persiste en 0
  Y no se inserta ninguna fila en percep_cli
```

```gherkin
Escenario: Sucursal agente de percepción con tipos configurados → calcula e inserta IIBB
  DADO un cliente cuya sucursal tiene agente_percep = 'Si'
  Y el cliente tiene 1 tipo de percepción con alícuota 3% en percep_cli_param/percep_cli_tipo
  Y una base imponible (neto con descuento) de 1000
  CUANDO se confirma el pedido (PED)
  ENTONCES se inserta 1 fila en percep_cli con importe 30 y alícuota 3
  Y comp_ped.total_percep se persiste en 30
```

```gherkin
Escenario: Agente de percepción sin tipos configurados para el cliente → bloquea
  DADO un cliente cuya sucursal tiene agente_percep = 'Si'
  Y el cliente NO tiene filas en percep_cli_param
  CUANDO se intenta confirmar el pedido
  ENTONCES la confirmación falla con un mensaje en español
  Y se hace ROLLBACK sin dejar comp_ped/stockp/percep_cli
```

---

## Implementation Constraints

- **Transacción:** conexión MySQL del pool con `autocommit(False)`, `COMMIT`/`ROLLBACK`; `SELECT ... FOR UPDATE` en `codmov` y `talonarios`. Reutilizar patrones de `self_checkout.services.confirmation_service` y `talonarios_service`.
- **Escritura controlada:** SQL **parametrizado** siempre; normalización con `core.utils.administranet_types` (INT/DATE/VARCHAR/DECIMAL) para paridad AdministraNET.
- **Sin ORM en MySQL:** las tablas legacy se acceden por `core.mysql_pool` (no Django ORM). El carrito origen vive en Postgres (P1).
- **Columnas reales confirmadas** (schema): `comp_ped` (TipoComprobante, NroComprobante, NroCompBusq, Codigo, CodigoMovimiento, ImporteVenta, IVA1, IVA2, Alicuota1, Alicuota2, Exento, SubTotal1, SubTotal2, SubTotalGral, PorDesc1/2, ImpDesc1/2, SubTotalDesc1/2, SubtotalDesc, impuesto_interno_total, total_percep, autorizacion_sistema, Estado, Vencimiento, FechaEntrega, FormaEntrega, id_pv, id_deposito_despacho, CodViajante, CodSucursal, IdUsuario, CotiDolar, geo_latitud, geo_longitud); `stockp` (IDArt, CodigoArticulo, CodigoMovimiento, Salida, Cantidad, Precio*xU/xR, Alicuota, imp_alicuota_iva, PorDesc, ImpDesc, promocion*, Orden, Comprobante, TipoComp, NroComprobante, CodDeposito, lista_precio, tipo_unidad); `talonarios` (id_punto_venta, TipoComprobante, Nro, PV); `codmov` (codigo=1, CodigoMovimiento).
- **Idempotencia:** por estado del carrito Postgres (`estado='confirmado'` + `codigo_movimiento` persistido en `EcomCart`).
- **Autorización:** consulta a `cuentacliente` (comprobantes N/Canc, no anulados) y `cliente.credito_limite_dias`.
- **Idioma/fechas:** mensajes en español; fechas al usuario dd/MM/yyyy; fechas a MySQL en formato de columna (DATE).
- **Percepciones IIBB (P4):** `mayorista_percepciones.py` (lectura `sucursales.agente_percep`, `percep_cli_param`, `percep_cli_tipo`; INSERT `percep_cli` parametrizado dentro de la transacción). Base = `subtotal_neto` del carrito. Configurable por sucursal (agente de percepción).
- **Fuera de alcance P2/P4:** factura electrónica/CAE (el pedido nace `Pendiente`), medios de pago/caja; percepciones en **DEV** (devolución) quedan diferidas.

---

## Size Budget

**Escenarios:** 13 · **Estado:** draft

## Metadata

- **Author role:** SDD (agente principal)
- **Created:** 2026-07-03
- **Status:** draft

---

## Extensions — pedido masivo lote (2026-07-13)

### REQ-CHK-MAS-01 — Batch multi-PED
El sistema MUST exponer un servicio/API de confirmación de pedido masivo que cree N comprobantes PED reutilizando la lógica de checkout mayorista, uno por `id_cliente_domicilio` con líneas agregadas de esa columna.

### REQ-CHK-MAS-02 — Integridad del lote
Si cualquier alta del lote falla tras haber creado otras, el sistema MUST compensar (anular) las altas de esa corrida y MUST reportar el error sin marcar el borrador como CONFIRMADO.

#### Scenario: Compensación
- **GIVEN** el lote creó PED #1 OK y falla PED #2
- **WHEN** se aplica la política de lote
- **THEN** PED #1 MUST quedar anulado (o no persistido) y el borrador MUST seguir editable

---

## Extensions — viajante operativo (2026-07-13)

### REQ-CHK-010 — CodViajante operativo en alta PED

Al confirmar checkout mayorista (PED), el sistema MUST persistir en `comp_ped.CodViajante` el **viajante efectivo** resuelto por el helper único (`cod_viajante_operativo` con fallback `id_vendedor_usr`). MUST NOT usar atributos obsoletos `user.cod_viajante` / `codViajante` si difieren de `id_vendedor_usr`.

#### Scenario: Vendedor directo confirma pedido

- **GIVEN** vendedor con `id_vendedor_usr=42` y `cod_viajante_operativo=42`
- **WHEN** confirma PED
- **THEN** `comp_ped.CodViajante` MUST ser `42`

#### Scenario: Supervisor confirma en nombre de vendedor

- **GIVEN** supervisor con `cod_viajante_operativo=21`
- **WHEN** confirma PED
- **THEN** `comp_ped.CodViajante` MUST ser `21`, no el `id_vendedor_usr` del supervisor

---

### REQ-CHK-011 — Fix resolución sesión CodViajante

La función `_session_cod_viajante` (y equivalentes) MUST leer `id_vendedor_usr` de la sesión mayoristapp como fuente primaria de `CodViajante`, alineada con `cod_viajante_desde_sesion_usuario`. MUST integrar viajante operativo cuando esté definido.

#### Scenario: Sesión solo con id_vendedor_usr

- **GIVEN** sesión con `id_vendedor_usr=55` sin campos legacy `cod_viajante`
- **WHEN** checkout resuelve CodViajante
- **THEN** MUST devolver `55`, no null

#### Scenario: Bug legacy corregido

- **GIVEN** sesión donde antes `_session_cod_viajante` devolvía null
- **WHEN** confirma PED tras el fix
- **THEN** `comp_ped.CodViajante` MUST NOT quedar null si el usuario tiene viajante válido

---

### REQ-CHK-012 — CodViajante operativo en lote masivo

La confirmación batch masiva (`REQ-CHK-MAS-01`) MUST usar el mismo viajante efectivo que checkout simple para todos los PED del lote.

#### Scenario: Lote masivo con supervisor operativo

- **GIVEN** supervisor operando como vendedor 21 confirma lote de 3 sucursales
- **WHEN** se crean los 3 PED
- **THEN** los tres MUST tener `CodViajante=21`
