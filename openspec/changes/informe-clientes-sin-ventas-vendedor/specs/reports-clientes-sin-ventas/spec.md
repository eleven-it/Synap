# Spec: Informe clientes sin ventas por vendedor

**Change:** `informe-clientes-sin-ventas-vendedor`
**Artifact Type:** delta spec (nueva capability `reports-clientes-sin-ventas`)
**Fuente PHP:** `administraNET-ecom/mayoristapp/relay-clientes-vendedor.php`, `informe-clientes-vendedor.php`
**Target Synap:** `reports/` (servicio + relay API + ReportDefinition `clientes-sin-ventas-vendedor`)

---

## ADDED Requirements

### REQ-CSV-001: Definición de "cliente sin ventas en el período"

El sistema **MUST** listar únicamente clientes con `cliente.Estado = 'Activo'` y `cliente.Codigo <> 1` que **no** tengan ningún comprobante en `cuentacliente` dentro del rango `[fechaDesde, fechaHasta]`, excluyendo notas de crédito (`TipoComprobante NOT IN ('NCA','NCB')`) y comprobantes anulados (`Anulado = 'No'`).

**Acceptance Scenarios:**

```gherkin
Escenario: Cliente sin comprobantes en el período aparece en el listado
  DADO un cliente activo sin comprobantes entre fechaDesde y fechaHasta
  CUANDO se ejecuta el informe con queInforme=sin_ventas
  ENTONCES el cliente aparece en "datos"
  Y su columna "Última compra" muestra la fecha del último comprobante histórico o "-" si nunca compró
```

```gherkin
Escenario: Cliente con comprobante en el período se excluye
  DADO un cliente activo con al menos un comprobante no anulado (distinto de NCA/NCB) dentro del período
  CUANDO se ejecuta el informe
  ENTONCES el cliente NO aparece en "datos"
```

```gherkin
Escenario: Notas de crédito no cuentan como venta
  DADO un cliente activo cuyo único movimiento en el período es una NCA o NCB
  CUANDO se ejecuta el informe
  ENTONCES el cliente SÍ aparece como "sin ventas"
```

```gherkin
Escenario: Cliente inactivo o cliente 1 nunca aparece
  DADO un cliente con Estado distinto de 'Activo' o con Codigo = 1
  CUANDO se ejecuta el informe
  ENTONCES ese cliente NO aparece en el listado bajo ninguna condición
```

---

### REQ-CSV-002: Fechas obligatorias y validadas

El sistema **MUST** exigir `fechaDesde` y `fechaHasta` (formato `YYYY-MM-DD`) para el modo `sin_ventas` y **MUST** rechazar la petición con error 400 si falta alguna o el formato es inválido. Las fechas **MUST** viajar a MySQL como parámetros vinculados, nunca concatenadas.

**Acceptance Scenarios:**

```gherkin
Escenario: Falta fechaHasta
  DADO una petición sin_ventas con fechaDesde válida y sin fechaHasta
  CUANDO se procesa la petición
  ENTONCES el sistema responde 400 con un mensaje indicando que las fechas son obligatorias
```

```gherkin
Escenario: Fecha con formato inválido
  DADO una petición con fechaDesde = "2026-13-40"
  CUANDO se procesa la petición
  ENTONCES el sistema responde 400 y NO ejecuta la consulta
```

---

### REQ-CSV-003: Modo selección de vendedores

Con `queInforme=seleccion`, el sistema **MUST** devolver la lista de vendedores (viajantes con `Anulado='No'`) como pares `{label, value}` para el filtro, respetando los permisos de sesión (un vendedor sin permiso gerencial solo se ve a sí mismo; un supervisor ve su cartera `vendedor_a_cargo`).

**Acceptance Scenarios:**

```gherkin
Escenario: Vendedor operativo solo se ve a sí mismo
  DADO un usuario sin permiso gerencial ni supervisión
  CUANDO solicita queInforme=seleccion
  ENTONCES la lista contiene únicamente su propio CodViajante
```

```gherkin
Escenario: Supervisor ve su cartera
  DADO un usuario con supervisor_venta='Si' y vendedor_a_cargo=[10,11,12]
  CUANDO solicita queInforme=seleccion
  ENTONCES la lista contiene solo los vendedores 10, 11 y 12
```

```gherkin
Escenario: Gerencial ve todos los vendedores activos
  DADO un usuario con permiso gerencial
  CUANDO solicita queInforme=seleccion
  ENTONCES la lista contiene todos los viajantes no anulados ordenados por nombre
```

---

### REQ-CSV-004: Control de acceso por permisos de sesión

El sistema **MUST** restringir los clientes visibles según los permisos de sesión cuando el usuario NO filtra por vendedores específicos:
- gerencial (`inf_gerenciales='Si'`) con `todos_clientes='Si'` → todos los clientes;
- supervisor (`supervisor_venta='Si'`) → clientes de `vendedor_a_cargo` (o el propio si la cartera está vacía);
- operativo → solo clientes de su propio `CodViajante`.

Cuando el usuario **sí** filtra por vendedores (parámetro `filtrarPor` con `vendedor|<id>`), el sistema **MUST** aplicar ese filtro validando que cada id sea entero. El relay operativo **MUST NOT** permitir a un vendedor ver clientes de otro vendedor mediante manipulación de `filtrarPor`.

**Acceptance Scenarios:**

```gherkin
Escenario: Operativo sin filtro ve solo su cartera
  DADO un vendedor operativo con CodViajante=7 y sin filtrarPor
  CUANDO ejecuta el informe
  ENTONCES todos los clientes de "datos" tienen CodViajante=7
```

```gherkin
Escenario: filtrarPor con vendedores específicos
  DADO un usuario gerencial y filtrarPor="vendedor|10|Ana|0||vendedor|11|Beto|1"
  CUANDO ejecuta el informe
  ENTONCES "datos" contiene solo clientes con CodViajante en (10, 11)
```

```gherkin
Escenario: filtrarPor con valor no numérico se ignora de forma segura
  DADO filtrarPor="vendedor|DROP TABLE|x|0"
  CUANDO ejecuta el informe
  ENTONCES el valor no numérico se descarta
  Y la consulta se ejecuta con parámetros vinculados sin alterar la sentencia
```

---

### REQ-CSV-005: Columnas, "última compra" y opción domicilio

El sistema **MUST** devolver las columnas: Código de cliente (usando `id_manual_cli` cuando `usa_id_manual='Si'`, con fallback a `Codigo`), Cliente, Última compra (dd/MM/yyyy o "-"), Vendedor (`Nombre (Cod: N)`). Cuando `incluirDomicilio=1`, el sistema **SHOULD** anexar el domicilio (calle + número del último domicilio) al nombre del cliente.

**Acceptance Scenarios:**

```gherkin
Escenario: Código manual con fallback
  DADO usa_id_manual='Si' y un cliente sin id_manual_cli
  CUANDO se arma la fila
  ENTONCES la columna "Cod. Cliente" usa cliente.Codigo como fallback
```

```gherkin
Escenario: Última compra formateada dd/MM/yyyy
  DADO un cliente cuyo último comprobante histórico es 2025-11-19
  CUANDO se arma la fila
  ENTONCES "Última compra" muestra 19/11/2025
```

```gherkin
Escenario: Cliente sin compras históricas
  DADO un cliente que nunca tuvo comprobantes
  CUANDO se arma la fila
  ENTONCES "Última compra" muestra "-"
  Y el orden lo ubica al final (fecha de orden 9999-12-31)
```

```gherkin
Escenario: Incluir domicilio
  DADO incluirDomicilio=1 y un cliente con domicilio "Av. Siempreviva 742"
  CUANDO se arma la fila
  ENTONCES el nombre del cliente se muestra como "<nombre> | Av. Siempreviva 742"
```

---

### REQ-CSV-006: Resumen por vendedor y global para gráficos

El sistema **MUST** devolver `resumenVendedores` (por vendedor: `total`, `activos` = con compra en período, `noActivos` = sin compra), `resumenGlobal` (suma de los tres) y `modoTodosVendedores` (verdadero si hay más de un vendedor en el resultado). El resumen **MUST** respetar el mismo alcance de permisos/filtro que el listado.

**Acceptance Scenarios:**

```gherkin
Escenario: Resumen coherente con un solo vendedor
  DADO un resultado restringido a un único vendedor
  CUANDO se calcula el resumen
  ENTONCES modoTodosVendedores es falso
  Y resumenGlobal.total = resumenVendedores[0].total
```

```gherkin
Escenario: Resumen con múltiples vendedores
  DADO un resultado con 3 vendedores
  CUANDO se calcula el resumen
  ENTONCES modoTodosVendedores es verdadero
  Y resumenGlobal.total = suma de total de cada vendedor
  Y resumenGlobal.noActivos = suma de noActivos de cada vendedor
```

---

### REQ-CSV-007: Acceso vía informe canónico

El sistema **MUST** exponer el informe como `ReportDefinition` con slug `clientes-sin-ventas-vendedor`, accesible en `/reports/dashboard/clientes-sin-ventas-vendedor/`, categoría de indicadores (operativo o gerencial), siguiendo la UI canónica de reportes de Synap (no las pantallas de `ventas/`).

**Acceptance Scenarios:**

```gherkin
Escenario: Informe listado en el catálogo
  DADO un usuario con permiso de reportes
  CUANDO abre el catálogo de reportes
  ENTONCES ve la tarjeta "Clientes sin ventas por vendedor"
  Y al abrirla se carga /reports/dashboard/clientes-sin-ventas-vendedor/ con filtros de período y vendedor
```

---

## Implementation Constraints

- Toda la consulta **MUST** usar parámetros vinculados (`cursor.execute(sql, params)`); prohibido concatenar `fechaDesde/fechaHasta/filtrarPor`.
- Las listas de `CodViajante` **MUST** normalizarse a `int` antes de construir cláusulas `IN`.
- Tipos legacy normalizados con `core.utils.administranet_types` (fechas, enteros).
- Conexión legacy vía `core.mysql_pool` (`get_mysql_pool().get_connection(base_empresa)`), igual que `reports/services/ventas_netas.py`.
- UI **MUST** seguir `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` y `openspec/specs/ui-fuente-verdad-reportes-mpr/spec.md`.
- Textos y fechas al usuario en español; fechas dd/MM/yyyy.

---

## Size Budget

**Palabras:** ~700 · **Escenarios:** 17 · **Estado:** Completa

## Metadata

- **Created:** 02/07/2026
- **Status:** draft
