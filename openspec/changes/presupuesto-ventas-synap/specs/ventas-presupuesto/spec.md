# Ventas — Presupuesto (PRE)

## Purpose

Comportamiento exigible del **Presupuesto de cliente** en Synap frente a MySQL AdministraNET: misma semántica de persistencia que VB6 donde el SPEC aplica, temporales por usuario, permisos por **puesto**, sin CRM ni proyecto ERP, y salida PDF solo por **módulo Reportes** (documento operativo).

## Requirements

### Requirement: Paridad de escritura legacy en alta y modificación

The system MUST escribir `comp_ped` (`TipoComprobante='PRE'`, `Estado` coherente con SPEC), `stockp`, incremento `codmov` (transacción según orden SPEC), `talonarios` cuando la numeración sea por sistema, `cliente_datos_adicionales`, `percep_cli` / temporales de percepción cuando corresponda, y `stock_deposito` según las mismas reglas que el SPEC funcional. All valores MUST normalizarse con `core.utils.administranet_types`.

#### Scenario: Numeración sistema correcta

- GIVEN punto de venta y talonario PRE configurados
- WHEN el usuario guarda un PRE nuevo con numeración sistema
- THEN `CodigoMovimiento` es consistente entre `comp_ped` y `stockp` y `talonarios.Nro` refleja un único incremento exitoso

#### Scenario: Modificación de ítems autorizada

- GIVEN `mod_item_pre_ped` permite editar ítems y un PRE existente
- WHEN el usuario confirma cambios de líneas
- THEN `stockp` refleja altas/bajas/modificaciones sin filas huérfanas respecto al cuerpo enviado

### Requirement: Talonario manual sin duplicados

The system MUST rechazar guardados con numeración manual si existe otro PRE no anulado con el mismo comprobante según la regla equivalente a `Validacion_Comp` del SPEC.

#### Scenario: Duplicado detectado

- GIVEN un PRE activo con mismo número/sucursal según criterio legacy
- WHEN se intenta guardar otro PRE manual con el mismo número
- THEN la operación falla con mensaje claro al usuario

### Requirement: Temporales `cuerpostockpe` y limpieza

The system MUST mantener líneas de trabajo en `cuerpostockpe` (y `percep_cli_temp` si aplica) con discriminación por usuario y `visualiza` equivalente al SPEC MUST eliminar temporales del usuario tras commit exitoso según el flujo documentado.

#### Scenario: Limpieza post-guardado

- GIVEN líneas temporales `visualiza='No'` del usuario
- WHEN el guardado confirma
- THEN no quedan filas temporales pendientes de ese usuario para ese flujo

### Requirement: Concurrencia en edición

The system SHOULD impedir o advertir edición concurrente cuando otro usuario tenga el mismo `CodigoMovimiento` cargado en temporal con distinto usuario, según el SPEC.

### Requirement: Permisos `permisos_sistema` por puesto

The system MUST obtener la fila de permisos por `IDPuesto` de sesión (p. ej. vía servicio existente de permisos) MUST aplicar flags relevantes al PRE (`mod_item_pre_ped`, `lim_desc_*`, `cambia_cv`, lista de precio, talonario, vendedor, `factura_importe_cero`, `utiliza_lista_oficial`, etc.) en validación y presentación.

#### Scenario: Sin permiso para modificar ítems en consulta

- GIVEN permisos indican no modificación de ítems de PRE/pedido según SPEC
- WHEN el usuario abre modificación desde consulta
- THEN no puede alterar renglones (u solo las ramas permitidas)

### Requirement: Exclusiones CRM y ERP proyecto

The system MUST NOT ejecutar `UPDATE` ni lógica sustituta de `crm_pre_llamada` desde Synap. The system MUST NOT escribir `erp_proyecto` ni exigir `ID_Proyecto` / `erp_estado_pre` para cumplir este cambio.

### Requirement: Cambio solo fecha/número (`modificacion_comp`)

The system MUST validar período fiscal abierto y actualizar `comp_ped` y `stockp` en línea con el SPEC, sin ramas de proyecto ERP.

### Requirement: Validaciones de negocio mínimas

The system MUST aplicar las validaciones V1–V11 del SPEC funcional (totales, obligatoriedad talonario manual, vendedor, descuentos vs límites y supervisor, CV, cantidades, precio cero, lista oficial, precio vs costo según permisos).

### Requirement: Documento PDF en módulo Reportes

The system MUST NOT usar Crystal Reports. The system MUST exponer la salida imprimible del Presupuesto como **documento operativo** del módulo `reports` (definición de reporte / dataset sobre `comp_ped` y `stockp` y datos de cliente). La paridad visual con el `.rpt` VB6 SHOULD NOT ser obligatoria; la paridad de datos SHOULD serlo.

#### Scenario: Generación tras guardado

- GIVEN un PRE persistido
- WHEN el usuario solicita PDF desde Synap
- THEN el PDF se obtiene vía infraestructura de Reportes con contenido coherente con las tablas legacy

### Requirement: Una definición ReportDefinition por informe lógico Presupuesto

The system MUST registrar el PDF del Presupuesto como **una** `ReportDefinition` de categoría **operational** con **slug** estable. Variantes por permiso **`plantillas`** o **`id_plantilla`** MUST resolverse mediante **`config`** de la definición y **payload** de ejecución (`codigo_movimiento`, identificador de plantilla si aplica). The system SHOULD NOT multiplicar slugs salvo pipelines de datos irreconciliables.

#### Scenario: Payload con plantilla

- GIVEN varias variantes declaradas en `config` y usuario con `plantillas` habilitado
- WHEN se solicita PDF con plantilla elegida o inferida desde cabecera PRE
- THEN la salida corresponde a esa variante sin requerir otro slug de reporte

### Requirement: Respeto del estado de licencia / instalación (plataforma)

When existe un **servicio de entitlement o licencia** activo en la instalación, the system MUST impedir operaciones de **escritura** del flujo PRE (alta, modificación, cambio fecha/número) si la instalación está **suspendida** o **revocada** según **`DESIGN_PUNTO13_ENTITLEMENT_Y_DESACTIVACION_REMOTA.md`**. The system SHOULD aplicar la misma política de bloqueo **solo lectura** o **denegación total** definida globalmente para otros módulos. When no existe dicho servicio (desarrollo o instalación sin verificación), this requirement MUST NOT aplicarse.

#### Scenario: Instalación sin derecho de uso

- GIVEN el estado de licencia indica suspensión o revocación fuera de período de gracia
- WHEN un usuario intenta guardar o modificar un PRE
- THEN la operación es rechazada con mensaje coherente con el resto de la aplicación
