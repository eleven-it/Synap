# Spec: Informe cobranzas por vendedor

**Change:** `informe-cobranzas-por-vendedor`
**Artifact Type:** delta spec (capability `reports-cobranzas-vendedor`)
**Fuente PHP:** `listado-cobranzas-vendedor.php`, `informes-json/cobranza_lista_vendedor_resumen.php`
**Target Synap:** `reports/` (servicio + relay API + ReportDefinition `cobranzas-por-vendedor`)

---

## ADDED Requirements

### REQ-COB-001: Universo de comprobantes de cobranza

El sistema **MUST** considerar únicamente filas de `cuentacliente` con `TipoComprobante IN ('REC','FA','FB','FM','FE','FC')`, `Anulado='No'`, `CodigoMovimiento <> 0`, `CondVenta IN ('Contado','-')` y `Fecha` dentro del rango `[fechaDesde, fechaHasta]`.

**Acceptance Scenarios:**

```gherkin
Escenario: Recibo contado dentro del período se incluye
  DADO un REC no anulado, CondVenta 'Contado', con CodigoMovimiento distinto de 0 en el período
  CUANDO se ejecuta el informe
  ENTONCES ese comprobante suma en el período correspondiente
```

```gherkin
Escenario: Comprobante anulado o de cuenta corriente se excluye
  DADO un comprobante anulado, o con CondVenta 'Cuenta Corriente'
  CUANDO se ejecuta el informe
  ENTONCES ese comprobante NO suma en ningún período
```

---

### REQ-COB-002: Fechas obligatorias y parametrizadas

El sistema **MUST** exigir `fechaDesde` y `fechaHasta` (formato `YYYY-MM-DD`), responder 400 si faltan o son inválidas, y enviarlas a MySQL como parámetros vinculados (nunca concatenadas).

**Acceptance Scenarios:**

```gherkin
Escenario: Falta fechaDesde
  DADO una petición sin fechaDesde
  CUANDO se procesa
  ENTONCES el sistema responde 400 y no ejecuta la consulta
```

---

### REQ-COB-003: Agregados por medio de pago

Para cada período el sistema **MUST** calcular:
- **Efectivo** = `SUM(IF(TipoComprobante='REC', TotalEfectivoP, ImporteVenta))`
- **Dólares** = `SUM(TotalEfectivoD)`
- **Cheques** = `SUM(TotalCheque)`
- **Transferencias** = `SUM(total_trans)`
- **Percepciones** = `SUM(total_percep)`
- **Total** = `SUM(IF(TipoComprobante='REC', ImporteCobro, ImporteVenta))`

Los montos **MUST** calcularse con precisión decimal (sin pérdida por float).

**Acceptance Scenarios:**

```gherkin
Escenario: Efectivo distingue REC de factura
  DADO un REC con TotalEfectivoP=100 y una FA con ImporteVenta=50 en el mismo período
  CUANDO se calcula el efectivo del período
  ENTONCES el efectivo del período es 150
```

```gherkin
Escenario: Total distingue REC (ImporteCobro) de factura (ImporteVenta)
  DADO un REC con ImporteCobro=120 y una FB con ImporteVenta=80 en el período
  CUANDO se calcula el total del período
  ENTONCES el total del período es 200
```

---

### REQ-COB-004: Modos de período (mensual / totalizado)

El sistema **MUST** soportar dos modos:
- `mes` (por defecto): una fila por mes, etiquetada como `"<Mes> <Año>"` (mes en español), ordenada cronológicamente.
- `totalizado`: una sola fila con etiqueta `"<dd/MM/yyyy> al <dd/MM/yyyy>"` que suma todo el rango.

**Acceptance Scenarios:**

```gherkin
Escenario: Modo mensual agrupa por mes
  DADO cobros en enero y febrero de 2026
  CUANDO se ejecuta el informe en modo mes
  ENTONCES hay una fila "Enero 2026" y otra "Febrero 2026"
```

```gherkin
Escenario: Modo totalizado devuelve una sola fila
  DADO cobros en varios meses del rango 01/01/2026 a 31/03/2026
  CUANDO se ejecuta el informe en modo totalizado
  ENTONCES hay una única fila etiquetada "01/01/2026 al 31/03/2026"
```

---

### REQ-COB-005: Totales generales (pie)

El sistema **MUST** devolver una fila de totales generales que sume cada columna de montos a lo largo de todos los períodos del resultado.

**Acceptance Scenarios:**

```gherkin
Escenario: El pie suma todas las filas
  DADO un resultado con 2 filas cuyos totales son 100 y 250
  CUANDO se calcula el pie
  ENTONCES el total general de la columna Total es 350
```

---

### REQ-COB-006: Control de acceso por vendedor

El sistema **MUST** restringir el resultado según el rol:
- Usuario operativo (no gerencial): solo cobranzas de su propio `CodViajante` de sesión; **MUST NOT** poder ver otros vendedores manipulando el parámetro `codViajante`.
- Usuario gerencial: puede ver todos los vendedores o filtrar por uno (`codViajante=<id>` o `todos`).

**Acceptance Scenarios:**

```gherkin
Escenario: Operativo solo ve sus cobranzas
  DADO un vendedor operativo con CodViajante=7
  CUANDO ejecuta el informe (incluso enviando codViajante=99)
  ENTONCES la consulta se restringe a CodViajante=7
```

```gherkin
Escenario: Gerencial filtra por vendedor
  DADO un usuario gerencial y codViajante=10
  CUANDO ejecuta el informe
  ENTONCES el resultado corresponde solo al vendedor 10
```

```gherkin
Escenario: Gerencial ve todos
  DADO un usuario gerencial y codViajante=todos (o ausente)
  CUANDO ejecuta el informe
  ENTONCES el resultado no se restringe por vendedor
```

---

### REQ-COB-007: Acceso vía informe canónico

El sistema **MUST** exponer el informe como `ReportDefinition` slug `cobranzas-por-vendedor`, accesible en `/reports/dashboard/cobranzas-por-vendedor/`, categoría operativo, sección legacy `listados`, con UI canónica de Synap (no las pantallas de `ventas/`).

**Acceptance Scenarios:**

```gherkin
Escenario: Informe listado en el catálogo
  DADO un usuario con permiso de reportes operativos
  CUANDO abre el catálogo
  ENTONCES ve la tarjeta "Cobranzas por vendedor" y puede abrir su dashboard con filtros de período y vendedor
```

---

## Implementation Constraints

- SQL 100% parametrizado (`cursor.execute(sql, params)`); `CodViajante` normalizado a `int`.
- Montos con `Decimal`; totales acumulados en `Decimal`.
- Conexión legacy vía `core.mysql_pool`; tipos con `core.utils.administranet_types`.
- UI conforme a `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`.
- Español; fechas dd/MM/yyyy; montos con formato es-AR en la UI.

---

## Size Budget

**Palabras:** ~650 · **Escenarios:** 11 · **Estado:** Completa

## Metadata

- **Created:** 02/07/2026
- **Status:** draft
