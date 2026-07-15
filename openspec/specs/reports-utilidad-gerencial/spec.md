# Especificación — Informe utilidad gerencial (Synap)

Fuente de verdad OpenSpec para el slug `utilidad-gerencial`, relays operativo/gerencial en `reports/` y servicio `get_utilidad_gerencial`.

**Origen PHP:** `relay-ventas-netas-gerencia.php` (modo `verInforme=ut` → `utilidades_totales_todos`; `uti` → `utilidades_totales_todos_inflacion`).

**Change archivado:** `informe-utilidad-gerencial` (13/07/2026).

## Requisitos

### REQ-UT-001: Universo de renglones (stock)

El sistema **MUST** calcular utilidad desde la tabla `stock` unida a `cuentacliente`, considerando solo `stock.Anulado='No'`, `stock.visualiza_ensamble='No'`, `stock.TipoComp IN ('Venta','Venta TPV','Devol - Cliente','ND Anul NC')` y `stock.Fecha` dentro del rango. El signo es positivo para `Venta`/`Venta TPV`/`ND Anul NC` y negativo para `Devol - Cliente`.

**Escenarios de aceptación:**

```gherkin
Escenario: Devolución resta venta y costo
  DADO un renglón TipoComp='Devol - Cliente' con PrecioNetoxR=100 y PrecioCostoxR=60
  CUANDO se agrega al informe
  ENTONCES resta 100 a Venta Neta y 60 a Costo del grupo
```

```gherkin
Escenario: Renglón de ensamble excluido
  DADO un renglón con visualiza_ensamble='Si'
  CUANDO se ejecuta el informe
  ENTONCES ese renglón no participa de ningún agregado
```

---

### REQ-UT-002: Columnas y fórmulas base

Por cada grupo el sistema **MUST** devolver: **Venta** = `SUM(±PrecioVentaxR)`, **Neto** = `SUM(±PrecioNetoxR)`, **Costo** = `SUM(±PrecioCostoxR)`, **Utilidad(base)** = `SUM(±(PrecioNetoxR-PrecioCostoxR))`. El **Costo MUST** usar `PrecioCostoxR` (no `PrecioCostoxU*Cantidad`). Todos los montos **MUST** calcularse con precisión decimal.

**Escenarios de aceptación:**

```gherkin
Escenario: Costo usa PrecioCostoxR
  DADO un renglón de venta con PrecioNetoxR=100 y PrecioCostoxR=60
  CUANDO se calcula el grupo
  ENTONCES Costo=60 y Utilidad base=40
```

---

### REQ-UT-003: Notas de crédito / descuentos (Desc)

El sistema **MUST** integrar notas de crédito/descuentos (columna **Desc**) solo cuando la dimensión de agrupación es `cliente`, `tipocliente`, `vendedor` o `zona` y no hay filtros de nivel artículo; en dimensiones de artículo (`articulo`, `proveedor`, `rubro`, `subrubro`, `categoria`, `marca`) Desc **MUST** ser 0 (paridad `traigoArrayNc`). El importe NC proviene de `cuentacliente` con: devolución (`TipoNC='Devolucion'`) → `ImpDesc1+ImpDesc2`; ND (`NDA/NDB/NDE/NDC/NDM`) → `SubtotalDesc`; NC (`NCA/NCB/NCE/NCC/NCM`) → `-SubtotalDesc`; facturas (`FA/FB/FE/FC/FM`) → `-(ImpDesc1+ImpDesc2)`; excluyendo `concepto_nd='Anulacion NC - Mercaderia'`.

**Escenarios de aceptación:**

```gherkin
Escenario: NC aplica por cliente
  DADO listar_por=cliente y una NC de -500 para el cliente 7
  CUANDO se calcula el grupo del cliente 7
  ENTONCES Desc=-500 y Venta Neta=Neto-500
```

```gherkin
Escenario: NC no aplica por artículo
  DADO listar_por=articulo
  CUANDO se calcula el informe
  ENTONCES Desc=0 en todas las filas
```

---

### REQ-UT-004: Venta Neta, Utilidad y Utilidad %

El sistema **MUST** devolver **Venta Neta** = `Neto + Desc`, **Utilidad** = `Utilidad(base) + Desc`, y **Utilidad %** = `(Neto + Desc) / Costo` (ratio); si `Costo=0` el ratio **MUST** ser 0.

**Escenarios de aceptación:**

```gherkin
Escenario: Utilidad % es ratio Neto/Costo
  DADO Neto=125, Desc=0, Costo=100
  CUANDO se calcula
  ENTONCES Utilidad % = 1.25
```

```gherkin
Escenario: Costo cero no rompe
  DADO Costo=0
  CUANDO se calcula Utilidad %
  ENTONCES Utilidad % = 0
```

---

### REQ-UT-005: Dimensiones de agrupación

El sistema **MUST** soportar agrupar por `cliente`, `tipocliente`, `vendedor`, `articulo`, `proveedor`, `zona`, `categoria`, `rubro`, `subrubro`, `marca`, cada una con su código y nombre, ordenado por nombre.

**Escenarios de aceptación:**

```gherkin
Escenario: Agrupar por rubro
  DADO listar_por=rubro
  CUANDO se ejecuta
  ENTONCES cada fila corresponde a un rubro con sus totales
```

---

### REQ-UT-006: Filtros, punto de venta y control de acceso

El sistema **MUST** aceptar filtros por dimensión (`filtrarPor`) y punto de venta (`pvSelec`) parametrizados, y **MUST** restringir por vendedor: usuario operativo solo su `CodViajante` de sesión (anti-bypass); gerencial/supervisor ve todos o su cartera `vendedor_a_cargo`.

**Escenarios de aceptación:**

```gherkin
Escenario: Operativo restringe a su vendedor
  DADO un usuario operativo con CodViajante=3
  CUANDO ejecuta el informe (incluso filtrando otro vendedor)
  ENTONCES la consulta se restringe a CodViajante=3
```

---

### REQ-UT-007: Variante inflación

En modo inflación el sistema **MUST** calcular un segundo rango (`tipoInflacion` `mensual` = mismo lapso desplazado, `anual` = un año antes), un **Índice** por grupo = `AVG(PrecioCostoxU rango1) / AVG(PrecioCostoxU rango2)`, y las columnas **Venta Ant** = `Neto2`, **Desc Ant**, **Venta Esp** = `(Neto2 + Desc Ant) * Índice`, **Resultado** = `Neto / ((Neto2 + Desc Ant) * Índice)` (1 si el denominador es 0).

**Escenarios de aceptación:**

```gherkin
Escenario: Índice y venta esperada
  DADO Neto2=100, Desc Ant=0, Índice=1.5
  CUANDO se calcula
  ENTONCES Venta Esp=150 y Resultado=Neto/150
```

---

### REQ-UT-008: Acceso vía informe canónico

El sistema **MUST** exponer el informe como `ReportDefinition` slug `utilidad-gerencial`, gerencial, sección legacy `gerenciales`, en `/reports/dashboard/utilidad-gerencial/` con UI canónica de Synap.

**Escenarios de aceptación:**

```gherkin
Escenario: Informe listado en catálogo gerencial
  DADO un usuario con permiso de reportes gerenciales
  CUANDO abre el catálogo
  ENTONCES ve "Utilidad gerencial" y puede abrir su dashboard con dimensión, período y filtros
```

---

## Restricciones de implementación

- SQL 100% parametrizado (`cursor.execute(sql, params)`); ids normalizados a `int`.
- Montos con `Decimal`; ratios en `float` para salida JSON.
- Conexión legacy vía `core.mysql_pool`; tipos con `core.utils.administranet_types`.
- Rango acotado ~1 mes (paridad `controlarFechas`); v1 no hace pivote por sub-período.
- UI conforme a `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`; español; montos es-AR.

## Implementación (referencia)

| Componente | Ruta |
|---|---|
| Servicio | `reports/services/utilidad_gerencial.py` |
| Relays | `reports/utilidad_gerencial_relay_views.py` |
| Rutas API | `reports/api_urls.py` (`utilidad-gerencial/relay/` y `.../gerencia/`) |
| UI | `reports/templates/reports/dashboard_utilidad_gerencial.html` |
| Migración | `reports/migrations/0035_add_utilidad_gerencial_report.py` |
| Tests | `reports/tests/test_utilidad_gerencial_relay.py` |

## Metadata

- **Creado:** 02/07/2026
- **Archivado:** 13/07/2026
- **Estado:** activo (fuente de verdad)
