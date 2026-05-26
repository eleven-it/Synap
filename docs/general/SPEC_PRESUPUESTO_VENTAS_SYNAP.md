# Especificación: Presupuesto de ventas en Synap (paridad de proceso y persistencia MySQL)

**Versión:** 1.12  
**Fuente de verdad comportamiento legacy:** `administranet_vb6/Formularios/Presupuesto.frm`, `Visualiza_Presupuesto.frm`, `CargaComprobantesPed.frm`, `Modulos/Visualiza.bas`, `Principal.frm` (menú y utilidades).  
**Esquema tablas:** `docs/general/tablas/comp_ped.md`, `stockp.md`, `cuerpostockpe.md`, etc.

---

## 1. Objetivo y alcance

### 1.1 Objetivo

Permitir en Synap el circuito **Presupuesto de cliente** (tipo **`PRE`** en `comp_ped`), con **misma lógica de negocio esencial** y **mismos valores persistidos** en MySQL AdministraNET que AdministraNET VB6, para convivencia con VB6, reportes y procesos posteriores (pedido, facturación, stock).

### 1.2 Alcance funcional

| Incluido | Excluido (este documento) |
|----------|---------------------------|
| Selección de cliente y apertura de emisión de PRE | Paridad visual 1:1 con formularios VB6 — la UI Synap puede reorganizarse |
| Ingreso de cabecera (fechas, CV, vendedor, totales, texto libre, etc.) según reglas legacy | **CRM:** pantallas `Crm_*`, botón llamada, workflows comerciales CRM |
| Ingreso/edición de renglones vía equivalente a `cuerpostockpe` → `stockp` | Crystal Reports u otros `.rpt` en Synap (ver §9: **módulo Reportes** propio) |
| Informe PDF de **Presupuesto** en el **módulo Reportes** (`reports`), como **documento operativo** (impresión/envío al cliente), alineado a otros comprobantes | Paridad visual 1:1 con el `.rpt` de VB6 |
| Numeración PRE por **sistema** (talonario automático) o **talonario manual** | Impresión física idéntica al VB6 (puede ser fase 2) |
| Guardado transaccional alineado a `Guardar` / ramas de modificación | Duplicar contraseñas u OCX del cliente |
| Permisos por **puesto** (`permisos_sistema` + sesión) aplicados a validaciones y pantalla | **Módulo ERP proyecto:** tablas `erp_proyecto`, campos `ID_Proyecto` / `erp_estado_pre` en cabecera, `UPDATE` proyecto en `Guardar` / `modificacion_comp`; bloques de informe solo-proyecto del VB6 (ver §1.5) |
| Modificación de PRE existente (flujo `Visualiza_Presupuesto` + permisos) | |

### 1.3 Principio de persistencia

**Todos los campos de `comp_ped`, `stockp`, `cliente_datos_adicionales` (cuando aplique), `percep_cli`, `codmov`, `talonarios` y actualizaciones relacionadas** que VB6 escribe en alta o modificación deben poder generarse desde Synap con **los mismos tipos, formatos y semántica** (fechas, decimales, strings `'Si'`/`'No'`, códigos de comprobante `PRE`, etc.). Usar siempre `core.utils.administranet_types` al implementar.

### 1.4 Principio de experiencia de usuario frente al VB6

La interfaz de **administranet_vb6** es **referencia de flujo y de qué datos intervienen**, no un mandato de usabilidad. Si un patrón del legado (ventanas MDI, densidad de controles, orden de tabulación, un solo “hub” para varios comprobantes, exceso de clics, flujos crípticos) **no es buena práctica hoy** o **fricciona** con una experiencia clara en web, el equipo **debe repensar** la UI de Synap. Se mantiene la **paridad de reglas de negocio, permisos y persistencia** en MySQL; se priorizan **claridad, accesibilidad, coherencia con TPV/MPR** y el resto del producto. Documentar en diseño las desviaciones significativas respecto al orden visual VB6 cuando existan.

### 1.5 Fuera de alcance: módulo ERP proyecto

En instalaciones con **`activ_proyecto`**, VB6 puede asociar el PRE a un proyecto (`ID_Proyecto`, `erp_estado_pre`), ejecutar **`UPDATE erp_proyecto`** tras guardar o en **`modificacion_comp`**, y mostrar lógica/UI adicional. **Synap no implementa en esta especificación** escrituras ni lecturas orientadas a proyecto: no se persiste ni reconcilia `erp_proyecto`, no se exige paridad en campos de proyecto en `comp_ped`, y el **documento de Presupuesto** en el módulo Reportes no incluye requisitos de bloques solo-proyecto del VB6. Si una empresa necesita ese vínculo, puede seguir usando VB6 para ese subflujo o se abre una fase posterior acotada.

---

## 2. Actores y proceso de negocio (resumen)

### 2.1 Actores

- Usuario con permisos de menú **Ventas → Presupuesto** (`keyPre`).
- Sesión con `codSucursal`, `idUsuario`, `id_punto_venta`, parámetros de empresa/sucursal cargados como en VB6 (`Principal.*`).

### 2.2 Flujo principal (alta)

1. **`Menu_Presupuesto_Venta`** → **`CargaComprobantesPed`** (`Caption = " Presupuestos"`).
2. Usuario selecciona cliente activo en grilla → **`keyPRE`**.
3. Se pasan al formulario de emisión: código cliente, nombre, IVA del cliente, lista de precio, descuentos, CV por defecto, viajante, tipo comprobante **Sistema** o **Talonario** (`tipo_comp_carga`), etc.
4. **`Presupuesto.Inicial`**: limpia temporales (`cuerpostockpe` / `percep_cli_temp` con `visualiza='No'`), inicializa pie, CV, vencimiento (`Principal.dias_venc_presup`), grillas, permisos.
5. Usuario carga renglones en **`cuerpostockpe`** (origen datos `CuerpoStock` / grid).
6. **`Guardar`**: validaciones → transacción **`codmov`** → (opcional CRM en VB6, **omitido en Synap según §7**) → **`cliente_datos_adicionales`** → **`comp_ped`** → líneas **`stockp`** → **`UPDATE cuerpostockpe`** asignando `CodigoMovimiento` → (en VB6: Crystal; en Synap: **emisión opcional del PDF** vía **módulo Reportes**, §9) → commit → cierre formulario → **`Elimina_Temporal`**.

### 2.3 Flujo consulta / edición

- **`Visualizar_PRE`** (`Visualiza.bas`) o **`Principal.Visualizar_Presupuesto`**: carga cabecera desde **`comp_ped`**, copia **`stockp`** → **`cuerpostockpe`** con `visualiza='Si'`; valida edición concurrente en red.
- **`Modificar_Click`** / **`Aceptar_*`** en **`Visualiza_Presupuesto`**: si **`Principal.mod_item_pre_ped = "Si"`**, actualiza **`comp_ped`** por `CodigoMovimiento`, reconcilia **`stockp`** (DELETE líneas huérfanas, INSERT/UPDATE por `id_stock`), actualiza **`cliente_datos_adicionales`**, percepciones, etc.

### 2.4 Flujo solo cambio número/fecha (talonario desde consulta)

- **`ModTalonario = "Si"`** → **`modificacion_comp`**: valida período fiscal abierto; actualiza **`stockp.Fecha`**, **`stockp.NroComprobante`**; actualiza **`comp_ped`** (fecha, número, `NroCompBusq`, `id_pv`, detalle). Sin ramas **`erp_proyecto`** en Synap (§1.5).

### 2.5 Permisos de sistema y por puesto (`permisos_sistema`)

La autorización funcional del PRE no depende solo del menú **`keyPre`**: VB6 combina **una fila en `permisos_sistema` por `IDPuesto`** (cargada en login, equivalente a **`Principal.idpuesto`**) con variables de sesión/empresa. Para Synap se debe respetar **la misma semántica** que ya existe para otros comprobantes legacy.

**Fuente en MySQL:** `SELECT * FROM permisos_sistema WHERE IDPuesto = :id_puesto` (una fila por puesto). En VB6 muchos campos se copian a **`Principal.*`** en **`IngresoUsuario`**; otros límites se releen con consultas puntuales (p. ej. `lim_desc_pie`, `lim_desc_renglon`).

**Servicios y vistas ya previstos en Synap:** lectura por puesto vía `AdministraNETPermisosSistemaService.obtener_permisos_puesto` (`core/services/administranet_permisos_sistema.py`); ABM/gestión en `core/views/views_permisos_sistema.py` (incluye flags como **`mod_item_pre_ped`**). La implementación del PRE debe **reutilizar** ese diccionario de permisos en sesión o contexto de request, sin duplicar reglas contradictorias.

**Columnas típicas de `permisos_sistema` con impacto directo en PRE** (la lista puede ampliarse si el `.frm` consulta más campos; mantener paridad con la fila del puesto):

| Columna (legacy) | Rol en PRE / Visualiza |
|-------------------|-------------------------|
| `lim_desc_pie`, `lim_desc_renglon` | Tope numérico descuentos pie/renglón vs supervisor (validaciones V5 y equivalentes en renglón) |
| `cambia_cv` | Restricción cambio condición de venta (V4) |
| `mod_descuento_pie`, `mod_descuento_renglon` | Habilitación UI y guardado de descuentos |
| `mod_lista_de_precio` | Cambio de lista en emisión |
| `modifica_vendedor`, `obliga_cambvendedor` | Selección obligatoria o editable del vendedor (V3) |
| `mod_item_pre_ped` | Si **`No`**, no se permite la modificación de ítems en **`Visualiza_Presupuesto`** (solo otras ramas permitidas) |
| `utiliza_lista_oficial` | Control de precios según lista oficial (V10) |
| `factura_importe_cero` | Permitir o bloquear precios/importes en cero (V9) |
| `carga_comp_ped`, `acceso_comp_ventas_talonario`, `modifica_comp_talonario` | Entrada desde hub y uso de talonario manual |
| `plantillas` | Uso de plantillas en informes |
| `visualiza_aviso` | Avisos al cliente en `CargaComprobantesPed` |

**Nota:** flags como **`agente_percep`**, **`utiliza_embalaje`**, **`dias_venc_presup`** pueden provenir además de **`datosempresa`**, sucursal u otras tablas de configuración; la UI debe cargarlos con los **mismos criterios** que el resto de Synap para ventas, pero las reglas **netamente por puesto** deben basarse en **`permisos_sistema`**.

---

## 3. Tablas y operaciones (matriz)

| Tabla | Alta PRE (`Presupuesto.Guardar`) | Modificación ítems (`Visualiza_Presupuesto`, `mod_item_pre_ped`) | Notas |
|-------|-----------------------------------|------------------------------------------------------------------|------|
| `codmov` (`codigo=1`) | `CodigoMovimiento` +1 (transacción aparte commit antes del resto) | No nuevo contador | PK lógica del movimiento |
| `comp_ped` | `AddNew`, `TipoComprobante='PRE'`, `Estado='Pendiente'`, totales, CV, vendedor, etc. | `UPDATE` por `CodigoMovimiento` | Ver §4 |
| `cliente_datos_adicionales` | `AddNew` con `id_datos_adicionales=1` en VB6 (fila plantilla) | `UPDATE` por `CodigoMovimiento` si existe | Logística, domicilio, contacto, origen |
| `stockp` | `AddNew` por renglón desde `cuerpostockpe` | DELETE si línea quitada; INSERT si nueva (`id_stock` nulo); UPDATE si existe | Ver §5 |
| `stock_deposito` | Asegura fila saldo por artículo/depósito; en **modificación** puede ajustar `saldo_pedido_cliente` | Igual en flujo Visualiza | Coherente con VB6 |
| `cuerpostockpe` | Tras grabar líneas: `UPDATE ... SET codigomovimiento = :contador WHERE Codusuario = :u AND visualiza='No'` | Trabajo con `visualiza='Si'` | Buffer usuario |
| `talonarios` | Si numeración **sistema**: incrementa `Nro` para `TipoComprobante='PRE'` e `id_punto_venta` | — | |
| `percep_cli` | Desde `percep_cli_temp` → nuevas filas `tipo_comp='PRE'` | `UPDATE` filas existentes por `codigo_movimiento` desde temp | Si `agente_percep` |
| `percep_cli_temp` | Limpiado en `Elimina_Temporal` / al editar | Usado en modificación | |

**Fuera de alcance Synap:** `crm_pre_llamada` (VB6 hace `UPDATE` al obtener `CodigoMovimiento`) — §7; **`erp_proyecto`** y campos de proyecto en cabecera — §1.5.

---

## 4. Cabecera `comp_ped` — campos escritos en alta (`Presupuesto.Guardar`)

Referencias explícitas en código (no exhaustivo de columnas nunca tocadas en este flujo). Implementación Synap debe mapear 1:1 cuando el dato exista en pantalla o cálculo interno.

| Campo (VB6) | Origen / regla |
|-------------|----------------|
| `Fecha` | `Format(Fecha, "short date")` |
| `TipoComprobante` | `"PRE"` |
| `codSucursal` | `Principal.codSucursal` |
| `idUsuario` | `Principal.idUsuario` |
| `NroComprobante` | Numeración sistema: `Nro.Caption` compuesto; talonario manual: `num` de `NroSuc`+`NroFact` |
| `NroCompBusq` | Numérico búsqueda (`NroBusq`) |
| `id_pv` | Sistema: `Principal.id_punto_venta`; Talonario: `Principal.ID_PV_Manual(NroSuc)` |
| `Detalle` | Texto si no vacío |
| `ImporteVenta` | Total formato `##,###.00` |
| `ImporteVentaL` | `Principal.ESCRITO(ImporteVenta)` |
| `Iva1`, `Iva2`, `Alicuota1`, `alicuota2` | Labels/cálculo pie |
| `Exento`, `Exento_interes` | Si exento 0 o importe + interés exento |
| `impuesto_interno_total`, `impuesto_interno_interes` | Pie impuesto interno |
| `anulado` | `"No"` |
| `Subtotal1`, `Subtotal2`, `SubtotalGral` | Pie |
| `PorDesc1`, `ImpDesc1`, `ImpDesc2`, `SubTotalDesc1`, `SubTotalDesc2`, `SubtotalDesc` | Descuentos |
| `Codigo` | `CodigoCliente` |
| `CondVenta`, `id_condventa` | Combo CV |
| `CodigoMovimiento` | `contador` de `codmov` |
| `Estado` | `"Pendiente"` |
| `Vencimiento` | `Format(VencFact, "short Date")` |
| `CodViajante` | Selección vendedor |
| `Tipopedido` | `tipo_comp_carga` (**Sistema** / **Talonario**) — nombre campo legacy |
| `id_deposito_despacho`, `FechaEntrega`, `FormaEntrega` | Datos entrega |
| `id_transporte`, `id_repartidor`, `operador_logistico` | Si aplica |
| `fecha_control` | `DATE_FORMAT(NOW(),...)` vía recordset |
| `comp_supervisor` | Si login supervisor |
| `total_percep` | Si percepciones y `agente_percep` |
| `id_plantilla` | Si `plantillas` y combo seleccionado |
| `CotiDolar` | `Principal.cotizacion` |
| `interes`, `interes_porcentaje` | Cálculo CV |
| `tpv_*_ocasional` | Cliente ocasional si variables cargadas |

**VB6 con módulo proyecto:** puede persistir `ID_Proyecto`, `erp_estado_pre`; **Synap no los incluye en esta especificación** (§1.5).

**Modificación cabecera ítems** (`Visualiza_Presupuesto`): actualiza subconjunto de totales, CV, vencimiento, percepciones, `comp_supervisor`, sin regenerar `CodigoMovimiento`.

---

## 5. Renglones `stockp` — campos en alta (desde `cuerpostockpe`)

Por cada renglón del cuerpo temporal (resumen desde bucle `Presupuesto.Guardar`):

| Campo | Notas |
|-------|------|
| `Fecha` | Igual cabecera |
| `CodigoArticulo`, `Descripcion`, precios (`PrecioVentaxU`, costo, IVA, bruto, neto, renglón) | Copia desde temporal |
| `Cantidad`, `Salida` | Ajuste **bulto/display** multiplicando cantidad |
| `impuesto_interno`, `impuesto_interno_subtotal` | |
| `CodigoMovimiento` | `contador` |
| `CodDeposito`, `IDArt`, `orden`, `CodViajante`, `CodLaboratorio` | |
| `CodigoCP` | `CodigoCliente` |
| `Tipo` | `"Cliente"` |
| `TipoComp` | `"Presupuesto"` |
| `Comprobante` | `"PRE"` |
| `NroComprobante` | Mismo string que cabecera |
| `anulado` | `"No"` |
| `Lista_Precio`, flags `promocion*` | |
| `Detalle` | Detalle renglón |
| `codSucursal`, `idUsuario` | |
| `multiplicador_*`, presentaciones, `cantidad_uni` | Si `utiliza_embalaje` |
| `coti_dolar`, `id_cotizacion` | Función cotización artículo |
| `unidad_art_peso` | Si `usa_multiplica_bulto_promedio` |
| `nro_despacho` | Si aplica |
| `tipo_unidad`, `cantidad_dividir`, etc. | Bulto/display |

**Modificación:** lógica INSERT/UPDATE dinámica en `Visualiza_Presupuesto`; elimina de `stockp` líneas cuyo `id_stock` ya no está en `cuerpostockpe`.

---

## 6. Validaciones obligatorias (replicar o equivalente)

| ID | Condición | Mensaje / acción VB6 |
|----|-----------|----------------------|
| V1 | `ImporteTotal` vacío o 0 | Error, abortar |
| V2 | Talonario: `NroSuc` / `NroFact` obligatorios | Error |
| V3 | `obliga_cambvendedor`: debe seleccionar vendedor | Forzar foco |
| V4 | `cambia_cv = No`: no elegir CV tipo **Cta Cte** distinta de la del cliente | MsgBox |
| V5 | Límite descuento pie: `PorDesc1` vs `permisos_sistema.lim_desc_pie` y `Principal.lim_desc_pie` | Si no supervisor |
| V6 | **Talonario manual:** `Validacion_Comp` — no duplicar `NroComprobante` para `TipoComprobante='PRE'` y `Anulado='No'` | |
| V7 | **Período fiscal** en `modificacion_comp`: mes/año abierto y no vencido | |
| V8 | Renglón: cantidad > 0 (`AceptarStock`) | |
| V9 | Precios en cero según `factura_importe_cero` | |
| V10 | Lista oficial según `utiliza_lista_oficial` | |
| V11 | Precio < costo según flags supervisor / `Mod_Precio_Fact` | (continúa en `.frm`) |

La especificación de implementación debe aplicar los permisos como en **§2.5** (`permisos_sistema` por **`IDPuesto`**, más variables de empresa/sesión ya alineadas en Synap).

---

## 7. Exclusiones CRM y coexistencia

- **No** se implementan en Synap: botón llamada, formularios `Crm_Presupuesto_Llamada`, ni sincronización UX con `crm_pre_llamada`.
- En VB6, tras incrementar `codmov`, se ejecuta  
  `UPDATE crm_pre_llamada SET CodigoMovimientoPre = :CodMov WHERE CodigoMovimientoPre = 0`.  
  **Decisión:** Synap **no** ejecuta esta sentencia. Si en una instalación aún se usa CRM solo desde VB6, el vínculo CRM queda allí. Si en el futuro hiciera falta paridad, se añade detrás de flag de configuración.

---

## 8. Temporales y concurrencia

| Recurso | Uso |
|---------|-----|
| `cuerpostockpe` | `Codusuario`, `visualiza` (`No` emisión, `Si` edición consulta) |
| `Elimina_Temporal` | `DELETE cuerpostockpe ... visualiza='No'` y `percep_cli_temp ... visualiza='No'` |
| Edición concurrente | `Visualizar_PRE`: si otro usuario tiene `cuerpostockpe` con mismo `CodigoMovimiento` y distinto `CodUsuario`, bloquear |

Synap debe reproducir el modelo (p. ej. filas temporales por usuario/sesión o equivalente con mismos criterios de limpieza).

---

## 9. Informes e impresión (módulo Reportes Synap)

**Synap no utiliza Crystal Reports.** La salida en papel/PDF de comprobantes se implementa en el **módulo de Reportes propio** (app Django **`reports`**: definiciones por empresa, consultas sobre MySQL legacy, exportación típica Excel/PDF — ver `docs/reports/` y `ReportDefinition`).

### 9.1 Tipología: documento operativo vs gerencial

En el mismo módulo pueden coexistir informes **analíticos o gerenciales** (ventas, KPI, cuadros) e informes que son **documentos de operación**: lo que en papel acompaña la operación comercial (**presupuesto**, **factura**, **remito**, etc.). El **Presupuesto de ventas** pertenece a esta segunda categoría: es un **documento para la operación** (cliente, vendedor, logística), no un cuadro de gestión.

### 9.2 Obligación de implementación en Synap

Si el flujo de Presupuesto expone “imprimir” / “ver PDF” (equivalente a `Lista_Informes_Click` o `reporte_plantilla` en VB6), debe existir una **definición de reporte** en el módulo Reportes (dataset desde `comp_ped` / `stockp` / datos cliente alineados al SPEC), con el mismo criterio que otros **documentos comerciales** ya resueltos en Synap. **No** se portan archivos `.rpt`; se **crea** el reporte en el stack Synap.

### 9.3 Referencia legacy (solo contexto)

En VB6: Crystal `comp_presupuesto.rpt` o plantilla `reporte_plantilla` cuando `plantillas='Si'`. Esa referencia sirve para **completitud de campos y reglas de negocio** mostrados al cliente, no para reproducir el motor Crystal.

### 9.4 Criterio de paridad

- **Sí:** contenido de negocio coherente con los datos persistidos en MySQL (`comp_ped`, `stockp`, etc.) y permisos (`plantillas`, §2.5).
- **No bloqueante del guardado:** diseño gráfico idéntico al `.rpt` legacy.

### 9.5 Implementación Synap (documento operativo v1)

- **`ReportDefinition`** global (`empresa=null`): slug estable **`documento-presupuesto-ventas`**, categoría **operational**, `refresh_interval` **realtime**. Dataset vía `reports.services.presupuesto_ventas_runner` (cabecera `comp_ped` + renglones `stockp`, mismo criterio que `ventas/services/presupuesto_mysql.py`).
- **Payload de ejecución / export:** `filters.base_empresa`, `filters.codigo_movimiento` (entero). Opcional `filters.nro_comprobante_archivo` para nombre de archivo al exportar.
- **Salida actual:** exportación **Excel** (`.xlsx`) con bloque de cabecera y tabla de renglones (`ExportService`). La pantalla de detalle PRE ofrece **Descargar Excel** (`GET /ventas/presupuestos/<codigo_movimiento>/exportar-xlsx/`), sometida al mismo control de sucursal que la vista de detalle.
- **API de reportes:** misma definición invocable con `POST` estándar del módulo `reports` (tipo `xlsx`) si el usuario tiene permisos operativos de reportes.
- **PDF:** pendiente de iteración; el contrato de slug y payload permanece para añadir plantilla PDF/HTML sin cambiar el identificador lógico del documento.

Documentación técnica del contrato: `docs/reports/DOCUMENTO_PRESUPUESTO_VENTAS_REPORT.md`.

### 9.6 API HTTP lectura (JSON)

Misma sesión y permiso Synap **`ventas.presupuesto.ver`** que las vistas HTML.

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/ventas/api/presupuestos/` | Listado paginado (filtros `q`, `fecha_desde`, `fecha_hasta`, `page`, `page_size` 5–100, `todas=1` para ver todas las sucursales). Respuesta: `ok`, `results`, `total`, `page`, `page_size`, `total_pages`, `filtros`. Fechas en cada ítem en ISO; `fecha_fmt` en español para referencia. |
| GET | `/ventas/api/presupuestos/<codigo_movimiento>/` | Cabecera + renglones (`stockp`). Query opcional `incluir_lineas=0` para solo cabecera. Campo `aviso_sucursal` si el PRE es de otra sucursal que la sesión. |
| POST | `/ventas/api/presupuestos/crear/` | Alta PRE (JSON). Permiso `ventas.presupuesto.editar` + `carga_comp_ped` o supervisor. Ver cuerpo documentado en §9.6 y código `api_presupuesto_crear`. |

**Alta MVP (iteración actual):** `POST /ventas/presupuestos/nuevo/` (formulario con **varios renglones** vía campos repetidos `linea_*`) y `POST /ventas/api/presupuestos/crear/` (JSON con array `lineas`). Permiso `ventas.presupuesto.editar` y, salvo usuario **supervisor**, flag **`carga_comp_ped`** del puesto. Persistencia: transacción única `codmov` + talonario **PRE** + `comp_ped` + `stockp` (numeración **sistema**; sin temporales `cuerpostockpe` ni percepciones en esta entrega). Detalle técnico: `ventas/services/presupuesto_guardado.py`, `_construir_lineas_desde_post` en `ventas/views_presupuesto.py`.

Los **PATCH** de modificación y **POST** talonario manual completos siguen según roadmap.

---

## 10. Arquitectura objetivo en Synap (diseño)

### 10.1 Capas

1. **Presentación:** vistas Django/HTML o SPA; **no** copia visual VB6 obligatoria; agrupación libre si los datos enviados al backend cubren §4–§5 (principio UX §1.4).
2. **Aplicación:** validaciones V1–V11; orquestación de pasos de §2; sin escrituras MySQL fuera del commit.
3. **Legacy / persistencia:** servicio(s) transaccionales que ejecutan el mismo orden lógico: `codmov` → `cliente_datos_adicionales` → `comp_ped` → `stockp` → temporales → `talonarios` → `percep_cli`.

### 10.2 Endpoints sugeridos (conceptual)

- `POST /api/ventas/presupuestos/` — alta (cuerpo = cabecera + líneas + flags sesión).
- `PATCH /api/ventas/presupuestos/{codigo_movimiento}/` — modificación autorizada.
- `PATCH /api/ventas/presupuestos/{codigo_movimiento}/numeracion-talonario/` — solo fecha/número (`modificacion_comp`).
- `GET` para cargar cliente, CV, talonario, borrador temporal.

(URLs finales según convención del proyecto.)

### 10.3 Tipos AdministraNET

Aplicar `to_int_or_none`, `to_decimal_or_none`, `to_date_or_none`, `str_or_default` según `TIPOS_DATOS_ADMINISTRANET.md` y columnas en `docs/general/tablas/`.

---

## 11. Criterios de aceptación (extracción)

1. Tras guardar un PRE desde Synap, un **SELECT** en `comp_ped` con `TipoComprobante='PRE'` muestra **mismos campos obligatorios** que un PRE equivalente guardado desde VB6 (misma sucursal/PV/cliente).
2. **`stockp`** tiene una fila por renglón con `Comprobante='PRE'` y `CodigoMovimiento` igual al de `comp_ped`.
3. Numeración **sistema** incrementa `talonarios.Nro` una vez por guardado exitoso.
4. Numeración **manual** rechaza duplicados con misma regla que `Validacion_Comp`.
5. Modificación con líneas agregadas/borradas deja **`stockp`** consistente con el cuerpo (misma idea que DELETE/INSERT VB6).
6. Sin filas en `cuerpostockpe` del usuario tras commit (limpieza).
7. **No** se llama a endpoints CRM; **no** es obligatorio ejecutar `UPDATE crm_pre_llamada` desde Synap.
8. Validaciones y habilitación de controles respetan **`permisos_sistema`** del puesto del usuario (§2.5); **no** se escribe en **`erp_proyecto`** ni se exige proyecto en cabecera (§1.5).
9. Si la pantalla ofrece imprimir o PDF de Presupuesto, el resultado es una definición del **módulo Reportes** (`reports`), categoría **documento operativo** (§9); sin Crystal.

---

## 12. Trazabilidad documental

- Inventario arquitectónico: `INVENTARIO_PRESUPUESTO_VENTAS_ADMINISTRANET_VB6.md`
- Esta especificación reemplaza la necesidad de “pasadas” sueltas para cerrar diseño funcional y contrato de datos.
- **OpenSpec (SDD):** requisitos formales y diseño técnico del cambio en `openspec/changes/presupuesto-ventas-synap/` (`proposal.md`, `specs/ventas-presupuesto/spec.md`, `design.md`, **`tasks.md`** checklist de implementación).
- **Licenciamiento SaaS, entitlement y desactivación remota** (instalaciones en infra del cliente): diseño en `openspec/changes/presupuesto-ventas-synap/DESIGN_PUNTO13_ENTITLEMENT_Y_DESACTIVACION_REMOTA.md`. **Servidor de tokens y panel de control:** proyecto separado del monorepo Synap — ver `docs/general/SERVICIO_LICENCIAS_PROYECTO_SEPARADO.md`.

---

## 13. Seguimiento / implementación pendiente

| Ítem | Responsable sugerido |
|------|----------------------|
| Mock de payload JSON alineado a cada campo §4–§5 | Backend |
| Matriz test integración MySQL (fixture `comp_ped`+`stockp`) | QA |
| Definición del reporte **Presupuesto** en módulo Reportes (documento operativo), dataset y plantilla **PDF** (Excel operativo ya registrado, slug `documento-presupuesto-ventas`) | Producto + Backend reports |
| Servicio global de licencia / heartbeat (si aplica al producto), integración con vistas PRE | Plataforma / Backend |

### Implementado en Synap (iteración lista / lectura)

- Rutas: `/ventas/presupuestos/` (listado con filtros y paginación), `/ventas/presupuestos/<codigo_movimiento>/` (cabecera solo lectura + **renglones `stockp`**), `/ventas/presupuestos/<codigo_movimiento>/exportar-xlsx/` (documento Excel operativo), `/ventas/presupuestos/nuevo/` (**alta MVP**: cliente + primer renglón → `codmov` / talonario PRE / `comp_ped` / `stockp`).
- Reportes: `documento-presupuesto-ventas` (`ReportDefinition` operational; runner `presupuesto_ventas_runner`; export Excel desde detalle y vía `ExportService`).
- API JSON: `GET /ventas/api/presupuestos/clientes/buscar/?q=` (autocomplete); `GET /ventas/api/presupuestos/` (listado); `GET /ventas/api/presupuestos/<codigo_movimiento>/` (detalle + líneas).
- Permisos `permisos_sistema` del puesto expuestos en contexto UI vía `ventas/services/presupuesto_permisos.py` (`mod_item_pre_ped`, `plantillas`, etc.).
- Permisos Synap: `ventas.presupuesto.ver`, `ventas.presupuesto.editar`; menú VB6 `keyPre` mapea a `ventas.presupuesto.ver` (`core/constantes_permisos.MAPEO_MENU_A_PERMISO`).
- Servicios: `ventas/services/presupuesto_mysql.py` (`comp_ped`, `cliente`, `stockp`); permisos: `AdministraNETPermisosSistemaService`.

---

**Fin del documento.**
