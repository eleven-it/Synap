# Spec — Informe DABRA consolidado remitos

**Capability:** `reports-dabra-consolidado-remitos`
**Change:** `reports-dabra-consolidado-remitos`
**Slug dashboard:** `dabra-consolidado-remitos`
**Referencia sample:** `DABRA MMYYYY.xlsx` (Best Sox)

---

## Purpose

Generar mensualmente para el cliente DABRA (`Codigo=368`) un Excel de líneas de factura con remito y pedido, con preview en dashboard Synap y alarmas de integridad. MUST replicar el layout del sample Best Sox; MUST operar solo sobre FA completas en AdministraNET/Synap de la empresa de sesión.

---

## Requirements

### REQ-DABRA-001: Permiso y empresa de sesión

El sistema **MUST** registrar un permiso nuevo dedicado al informe y **MUST** ejecutar consultas únicamente contra la base MySQL (`base_empresa`) de la empresa logueada. Usuarios sin permiso **MUST NOT** acceder al dashboard, al relay ni al export.

#### Scenario: Acceso denegado sin permiso

- **DADO** un usuario autenticado sin el permiso del informe DABRA
- **WHEN** navega a `/reports/dashboard/dabra-consolidado-remitos/` o invoca el relay
- **THEN** el sistema responde con acceso denegado
- **AND** no se ejecuta consulta MySQL ni se genera Excel

#### Scenario: Consulta acotada a empresa de sesión

- **DADO** un usuario con permiso y `base_empresa=administranet89` en sesión
- **WHEN** ejecuta preview o export
- **THEN** los datos provienen exclusivamente de `administranet89`
- **AND** no se mezclan filas de otras bases

---

### REQ-DABRA-002: Universo de facturas DABRA

El sistema **MUST** incluir únicamente filas de `cuentacliente` con:
- `Codigo=368` (cliente DABRA fijo)
- `TipoComprobante='FA'`
- `Anulado='No'`
- `Fecha` (fecha de factura) dentro del mes y año seleccionados

El sistema **MUST NOT** incluir notas de crédito, notas de débito ni comprobantes anulados. El sistema **MUST NOT** parametrizar otro cliente.

#### Scenario: FA DABRA del mes incluida

- **DADO** una FA no anulada de `Codigo=368` con fecha 24/07/2026
- **WHEN** el operador filtra Mes=7, Año=2026
- **THEN** sus líneas aparecen en preview y export

#### Scenario: NC/ND y anuladas excluidas

- **DADO** una NC o una FA con `Anulado='Si'` del mismo cliente y período
- **WHEN** se ejecuta el informe
- **THEN** esos comprobantes no generan filas

#### Scenario: FA de otro cliente excluida

- **DADO** una FA no anulada de `Codigo≠368` en el mismo mes
- **WHEN** se ejecuta el informe
- **THEN** no aparece en el resultado

---

### REQ-DABRA-003: Solo datos AdministraNET/Synap con líneas

El sistema **MUST** incluir FA DABRA del período que tengan al menos una línea en `stock`. **MUST NOT** intentar paridad con FA importadas/incompletas del flujo BEST anterior (cabecera sin líneas). La ausencia de remito o de CAE **MUST NOT** excluir la FA: se informa con **alarma** en preview.

#### Scenario: FA sin líneas stock excluida

- **DADO** una FA DABRA del período sin renglones en `stock`
- **WHEN** se arma el universo del informe
- **THEN** esa FA no aporta filas al export
- **AND** el preview puede listarla en alarmas de exclusión (dato incompleto / BEST anterior)

#### Scenario: FA Synap con líneas incluida

- **DADO** una FA emitida en Synap con líneas `stock` (con o sin remito/CAE)
- **WHEN** se ejecuta el informe del mes de su fecha
- **THEN** sus líneas se incluyen
- **AND** faltantes de remito o CAE generan alarma no bloqueante

---

### REQ-DABRA-004: Filtros Mes y Año obligatorios

El dashboard y el relay **MUST** exigir filtro **Mes** (1–12) y **Año** (entero) aplicados a la **fecha de factura**. Si faltan o son inválidos, **MUST** responder error en español sin ejecutar la consulta.

#### Scenario: Filtros ausentes

- **DADO** una petición al relay sin mes o sin año
- **WHEN** se procesa
- **THEN** responde 400 con mensaje en español
- **AND** no se ejecuta SQL

#### Scenario: Período válido

- **DADO** Mes=7 y Año=2026
- **WHEN** se ejecuta preview
- **THEN** el rango efectivo es del 01/07/2026 al 31/07/2026 sobre `cuentacliente.Fecha`

---

### REQ-DABRA-005: Granularidad línea y vínculo remito–pedido

Cada fila del informe **MUST** representar una línea de factura (`stock` unida a `cuentacliente`). El sistema **MUST** resolver remito y pedido vía `rem_fact` → `comp_ped`. **MUST** emitir **una fila por remito** cuando una FA tenga varios remitos. `CompRef` y `NumeroRef` **MUST** provenir del remito vinculado.

#### Scenario: Línea con un remito

- **DADO** una línea FA con un único remito en `rem_fact`
- **WHEN** se genera la fila
- **THEN** `CompRef`/`NumeroRef` coinciden con ese remito
- **AND** hay una sola fila por esa línea-remito

#### Scenario: FA con dos remitos

- **DADO** una línea FA vinculada a dos remitos distintos
- **WHEN** se genera el informe
- **THEN** hay dos filas (una por remito) con referencias de remito diferenciadas

---

### REQ-DABRA-006: Punto de venta y número legal

`PuntoVenta` y `NumeroLegal` **MUST** parsearse desde `NroComprobante` de la cabecera FA según convención AdministraNET (PV + número legal).

#### Scenario: Parse de NroComprobante

- **DADO** una FA con `NroComprobante` que representa PV 0008 y número legal 00012345
- **WHEN** se materializa la fila
- **THEN** `PuntoVenta` es texto zero-pad 5 (`00008`) y `NumeroLegal` usa máscara 8 dígitos; el string de TOTAL FACTURAS embebe PV en 4 dígitos (`A000800012345`)

---

### REQ-DABRA-007: CAE, CUIT y DocType

El CAE y su vencimiento **MUST** tomarse de `cuentacliente.fe_cae` / `fe_vto_cae` (columnas siempre presentes en export). Si faltan, **MUST** exportar vacío y emitir **alarma** (no excluir la FA). El CUIT emisor **MUST** ser el de la empresa (`datosempresa`). `DocType` **MUST** ser `1` en todas las filas.

#### Scenario: CAE presente

- **DADO** una FA con CAE y vencimiento válidos
- **WHEN** se exporta
- **THEN** las columnas CAE del Excel contienen esos valores
- **AND** `DocType=1`

#### Scenario: CAE ausente con alarma

- **DADO** una FA con líneas y sin `fe_cae`
- **WHEN** se genera preview/export
- **THEN** la FA se incluye con CAE vacío
- **AND** hay alarma no bloqueante

#### Scenario: CUIT empresa en fila

- **DADO** empresa con CUIT configurado en sesión
- **WHEN** se genera cualquier fila
- **THEN** el CUIT emisor en export coincide con el de la empresa logueada

---

### REQ-DABRA-008: Artículo, talle y categoría

El sistema **MUST** parsear `CodArtProv` del artículo para obtener ítem y talle según reglas del sample. Si no hay categoría resoluble, **MUST** usar **`ACCESORIOS`** como valor por defecto.

#### Scenario: CodArtProv estándar

- **DADO** un artículo con `CodArtProv` parseable en ítem y talle
- **WHEN** se genera la fila
- **THEN** las columnas de ítem/talle reflejan el parseo

#### Scenario: Sin categoría explícita

- **DADO** un artículo sin categoría mapeable
- **WHEN** se genera la fila
- **THEN** la categoría exportada es `ACCESORIOS`

---

### REQ-DABRA-009: Entrega y sucursal (NroCalle)

Las columnas **Entrega** y **Suc** **MUST** llevar el texto de domicilio **`NroCalle`** del remito (texto, sin normalización adicional obligatoria en spec).

#### Scenario: Domicilio desde remito

- **DADO** un remito con `NroCalle='Av. Corrientes 1234'`
- **WHEN** se genera la fila
- **THEN** Entrega y Suc contienen `'Av. Corrientes 1234'`

---

### REQ-DABRA-010: Importes de línea

Por línea el sistema **MUST** exponer: precio bruto pre-bonificación, bonificación % de línea, alícuota IVA del artículo e importes de línea tomados/validados desde AdministraNET. **MUST NOT** recalcular ciegamente totales que contradigan cabecera o línea almacenada.

#### Scenario: Coherencia con stock

- **DADO** una línea `stock` con precio, bonificación e IVA registrados
- **WHEN** se materializa la fila
- **THEN** los importes del informe coinciden con los valores legacy normalizados
- **AND** no se inventan alícuotas distintas a las del artículo

---

### REQ-DABRA-011: Layout Excel columnas A–AW

El export **MUST** generar hoja **REPORTE** con columnas **A–AW** según sample. Columnas **O** y **P** **MUST** quedar vacías. Columnas **Y–AW** **MUST** ser `0`. `DocType=1` en todas las filas.

#### Scenario: Columnas fijas vacías/cero

- **DADO** cualquier fila exportada
- **WHEN** se inspecciona el Excel
- **THEN** O y P están vacías
- **AND** Y–AW valen 0

---

### REQ-DABRA-012: Preview vs export (columnas visibles)

El preview en dashboard **MUST** mostrar columnas **B, D, E, F, NombreArticulo, G–N, Q, R, S, U, V, X**. **`NombreArticulo` MUST** mostrarse **solo en preview** y **MUST NOT** incluirse en el Excel exportado.

#### Scenario: Preview con nombre artículo

- **DADO** un resultado con líneas
- **WHEN** el operador ve la pestaña REPORTE en preview
- **THEN** la columna NombreArticulo está visible con la descripción

#### Scenario: Export sin NombreArticulo

- **DADO** el mismo resultado
- **WHEN** se descarga `DABRA MMYYYY.xlsx`
- **THEN** no existe columna NombreArticulo en la hoja REPORTE

---

### REQ-DABRA-013: Export Excel — nombre y hojas

El export **MUST** producir un archivo `.xlsx` con **exactamente dos hojas**: **REPORTE** (líneas) y **TOTAL FACTURAS** (resumen por factura). El nombre del archivo **MUST** ser `DABRA MMYYYY.xlsx` donde `MM` es mes de dos dígitos y `YYYY` el año del filtro.

#### Scenario: Export julio 2026

- **DADO** Mes=7, Año=2026 y datos válidos
- **WHEN** el operador exporta
- **THEN** el archivo se descarga como `DABRA 072026.xlsx`
- **AND** contiene hojas REPORTE y TOTAL FACTURAS

---

### REQ-DABRA-014: Hoja TOTAL FACTURAS

La hoja **TOTAL FACTURAS** **MUST** resumir por cabecera FA los totales requeridos por el sample (identificación PV/legal, importes de cabecera y conteos alineados al período filtrado).

#### Scenario: Resumen por factura

- **DADO** tres FA DABRA distintas en el mes
- **WHEN** se exporta
- **THEN** TOTAL FACTURAS tiene una fila por cada FA incluida
- **AND** los totales coinciden con cabecera `cuentacliente`

---

### REQ-DABRA-015: Alarmas FA↔REM (no bloquean)

Desfasajes o inconsistencias entre factura y remito (fechas, referencias, vínculos faltantes parciales detectables) **MUST** mostrarse como **alarmas visibles** en preview. Esas alarmas **MUST NOT** bloquear la descarga del Excel.

#### Scenario: Desfasaje remito visible pero exportable

- **DADO** una FA incluida con fecha de remito posterior a la factura
- **WHEN** el operador consulta preview
- **THEN** ve una alarma descriptiva en español
- **AND** puede exportar el Excel igualmente

---

### REQ-DABRA-016: Validación Σ líneas vs cabecera (bloquea export)

Para cada FA incluida, la suma de importes de línea (**Σ**) **MUST** coincidir con los totales de cabecera dentro de tolerancia decimal definida en diseño. Las líneas de `stock` son **predescuento** de cabecera: el neto se compara con `SubTotal1` y el bruto con `ImporteVenta` aplicando el factor `SubtotalDesc/SubTotal1`. Si hay mismatch, el sistema **MUST** marcar **error** en preview y **MUST NOT** permitir export hasta corregir datos o excluir la FA conflictiva.

#### Scenario: Totales coherentes — export permitido

- **DADO** una FA cuya Σ líneas coincide con cabecera
- **WHEN** el operador solicita export
- **THEN** el export se genera correctamente

#### Scenario: FA con descuento de cabecera — export permitido

- **DADO** una FA con `PorDesc1`/`ImpDesc1` (ej. 20 %) donde `SubtotalDesc < SubTotal1` e `ImporteVenta` ya refleja el descuento
- **AND** Σ `Cantidad×PrecioNetoxU` = `SubTotal1` y Σ bruto × (`SubtotalDesc`/`SubTotal1`) = `ImporteVenta` dentro de tolerancia
- **WHEN** el operador solicita export
- **THEN** el sistema **MUST NOT** marcar error de consistencia
- **AND** el export se genera correctamente

#### Scenario: Mismatch Σ vs cabecera — export bloqueado

- **DADO** una FA donde Σ líneas ≠ total cabecera (incluso tras aplicar el factor de descuento)
- **WHEN** el operador solicita export
- **THEN** el sistema responde error en español
- **AND** no entrega archivo Excel

---

### REQ-DABRA-017: Dashboard UI canónica

El informe **MUST** registrarse como `ReportDefinition` slug `dabra-consolidado-remitos` y **MUST** renderizarse en `/reports/dashboard/dabra-consolidado-remitos/` siguiendo canon reportes (`dashboard_detail.html`, includes y feedback Synap). **MUST NOT** usar diálogos nativos del navegador. **MUST** ofrecer pestañas preview **REPORTE** y **TOTAL FACTURAS**.

#### Scenario: Tabs de preview

- **DADO** un operador autorizado en el dashboard
- **WHEN** ejecuta consulta con Mes/Año válidos
- **THEN** puede alternar entre pestaña REPORTE y TOTAL FACTURAS
- **AND** la UI sigue patrones del dashboard de reportes Synap

---

### REQ-DABRA-018: Relay API

El sistema **MUST** exponer relay bajo `/api/reports/dabra-consolidado-remitos/relay/` (o ruta equivalente registrada) protegido por el permiso nuevo, aceptando `mes` y `anio` y devolviendo payload para preview y export.

#### Scenario: Relay con parámetros válidos

- **DADO** usuario con permiso y `mes=7`, `anio=2026`
- **WHEN** invoca el relay
- **THEN** recibe JSON con filas REPORTE, resumen TOTAL FACTURAS y metadatos de alarmas/errores

---

## Out of Scope (explicit)

- Otros clientes distintos de DABRA (`Codigo=368`)
- NC, ND y comprobantes anulados
- Paridad con FA importadas/incompletas BEST
- Columnas UnidMed; valores distintos de cero en Y–AW salvo sample futuro
- Contenido en columnas O y P
