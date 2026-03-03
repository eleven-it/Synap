# Mapeo menú "Archivo" – AdministraNET VB6

Menú principal definido en **Principal.frm** (sub `AltaMenu` con control SmartMenuXP). Todo lo que cuelga de **Archivo** y la acción/formulario que dispara cada ítem.

---

## Estructura general

| Ítem en pantalla | Clave menú | Acción / Formulario |
|------------------|------------|----------------------|
| **Archivo** | (raíz) | — |
| Empresa | keyPar | Submenú "Parametros" (mismo que menú &Parametros) |
| Entidades | keyTabla | Submenú entidades |
| Productos | keyArticulos | Submenú productos/artículos |
| Variables | keyVariable | Submenú variables (impositivas, administrativas, etc.) |
| Procesos | keyProceso | Submenú procesos |
| Exportación | keyExportacion | Submenú exportaciones |
| Configuración | keyConf | `VerConfiguracion` |
| — | (separador) | — |
| Salir | keySalir | `MenuSalir` |

---

## 1. Empresa (keyPar) → submenú Parametros

| Ítem | Clave | Acción |
|------|--------|--------|
| Datos | keyEmpresa | `Empresa.Show` |
| Sucursal | keySucursal | `ABMSucursal.Show` |
| Administrador de usuario | keyNuevoUsuario | `Nuevo_Usuario` (proc) |
| Puesto | keyPuesto | Submenú |
| Administrador de sesión | keyAdmSesiones | `Adm_Sesion.Show` |

### 1.1 Puesto (keyPuesto)

| Ítem | Clave | Acción |
|------|--------|--------|
| Permiso en menú | keyPuestoMenu | `ABMPuesto.Show` |
| Permiso en sistema | keyPuestoSistema | `ABMPermiso_Sistema.Show` (CargaPermiso_Sistema_Puesto, permisos por puesto) |

---

## 2. Entidades (keyTabla)

| Ítem | Clave | Acción |
|------|--------|--------|
| Cliente | keyCliente | `Menu_ABM_Cliente` |
| Proveedor | keyProveedor | `Menu_ABM_Proveedor` |
| Banco | keyABMBanco | `Menu_ABM_Banco` |
| Vendedor | keyViajantes | `Menu_ABM_Vendedor` |
| Depósito | keyDeposito | `ABMDeposito.Show` |
| Laboratorio | keyLaboratorio | `ABMLaboratorio.Show` |

---

## 3. Productos (keyArticulos)

| Ítem | Clave | Acción |
|------|--------|--------|
| Rubro | keyRubros | `ABMRubro.Show` |
| Sub rubro | keySubRubros | `ABMSubRubro.Show` |
| Categoria rubro | keyABMRubroCategoria | `ABMRubroCategoria.Show` |
| Artículo | keyABMArticulo | `Menu_ABM_Articulo` |
| Presentación de artículo | keyPresArticulo | `ABMPresentacion.Show` |
| Campos especiales | keyArticuloCE | `Articulo_ce.Show` |
| Marca y modelo | keyModelo | `ABMModelo.Show` |
| Categoría de artículo | keyCategoria_Articulo | `ABMArticulo_Categoria.Show` |
| Unidades de medida | keyUM | `ABMUniMed.Show` |
| Asignación de proveedores a artículo | keyAsigProvArt | `AsigProvArt.Show` |
| Actualización de precios | keyCambioPrecio | `ActPrecio.Show` (VariacionPrecio) |
| Actualización de descuentos en venta | keyCambioDescuento | `ActDescuento.Show` |
| Consulta avanzada de artículos | keyConsulta_Avanzada_Articulo | `Menu_Stock_Consulta_Avanzada` |
| Descuento de proveedor | keyDescuento_Proveedor | `ABM_Descuento_Proveedor.Show` |
| Actualización de descuentos de proveedor | keyDescuento_Proveedor_Act | `ActDescuento_Prov.Show` |
| Actualización masiva de datos de artículo | keyActualizacion_Datos_Art | `ActDatos_Articulo.Show` |
| Reglas de precios | keyRprecios | `Rprecios_abm.Show` |
| Asignación de artículos a tipo de cliente | keyAsigArtTipo | `Articulo_tipo_cliente.Show` |
| Armado / Desarmado de artículos | keyDesarmeArt | `En_abm.Show` (modo Armado/desarmado) |
| Programa de descuentos y voucher | keyPrograma_Descuentos | `Programa_Descuentos.Show` |
| Consulta de precios | keyConsulta_Precios | `Menu_Consulta_Articulo` → `Consulta_Precio_Articulo_Usr.Show` |

---

## 4. Variables (keyVariable)

### 4.1 Impositivas (keyImpositiva)

| Ítem | Clave | Acción |
|------|--------|--------|
| Impuesto | keyImpuesto | `ABMImpuestos.Show` |
| Alícuota IVA | keyImpuestos | `ABMIVA.Show` |
| Alícuota ingresos brutos | keyIngBrutos | `ABMIngBrutos.Show` |
| Retención | keyRet | Submenú (Proveedor: keyTipoRetProI/G/IVA; Cliente: keyTipoRetCli) |
| Percepciones | KeyPercep | Submenú (Proveedor keyPerPro; Cliente keyPerCli → keyTipoPerc, keyTipoPercTipo) |
| Impuestos internos | keyImpuestoInterno | `ABM_ImpuestoInterno.Show` |
| Año y período de vencimiento fiscal | keyABMPeriodos | `ABMPeriodos.Show` |
| Configuración de Factura electrónica (C.A.E.A) | keyConfCompElect | `adm_felectronicas_caea.Show` |

**Retención (keyRet):**  
- Proveedor: keyTipoRetProI → `ABMRetProv.Show`, keyTipoRetProG → `ABMRetProvG.Show`, keyTipoRetProIVA → `ABMRetProvIVA.Show`  
- Cliente: keyTipoRetCli → `ABMRetCli.Show`

**Percepciones (KeyPercep):**  
- Proveedor keyPerPro → `ABMPercepciones.Show`  
- Cliente keyPerCli: keyTipoPerc → `ABMPercepcionesCli.Show`, keyTipoPercTipo → `ABMPercepcionesCliTipo.Show`

### 4.2 Administrativas (keyAdministrativa)

| Ítem | Clave | Acción |
|------|--------|--------|
| Punto de venta y talonario de cobro | keyPV | `ABMPV.Inicial` + `ABMPV.Show` |
| Talonario | keyTalon | `ABMTalonario.Inicial` + `ABMTalonario.Show` |
| Condición venta/compra | keyCondventa | `ABMCondVenta.Show` |
| Cotización Moneda extranjera | keycotizacion | `Menu_Cotizacion_Moneda` |
| Grupo de gasto | keyGastos_Grupo | `ABMGastos_Grupo.Show` |
| Gasto | keyGastos | `ABMGastos.Show` |
| Descuentos recibo / orden de pago | keyDescRec | `ABMDescuentoREC.Show` |
| Caja | keyABMCajas | `ABMCajas.Show` |
| Tarjeta de crédito / débito / billeteras virtuales | keyABMTarjetasCredito | `ABMTarjetaC.Show` |
| Plan de tarjeta... | keyABMPlanes_TarjetasCredito | `ABMPlantc.Show` |
| Referencia de movimiento de stock | KeyABMref_movstock | `ABMref_movstock.Show` |
| Transporte | keyABMTransporte | `ABMTransporte.Show` |
| Tipo de medio de cobro / pago | keyTipoMedioCP | `ABM_medio_cobpag_tipo.Show` |
| Medio de cobro / pago | keyMedioCP | `ABM_medio_cobpag.Show` |
| Ingreso | keyIngreso | `ABM_ingreso.Show` |
| Deuda | keyDeuda | `ABMDeuda.Show` |

### 4.3 Bancarias (keyBancarias)

| Ítem | Clave | Acción |
|------|--------|--------|
| Gasto bancario | keyGastoB | `ABMGastoBancario.Show` |
| Cuenta bancaria y chequera | keyChequeras | `ABMChequera.Show` |

### 4.4 Generales (keyGeneral)

| Ítem | Clave | Acción |
|------|--------|--------|
| Tipo de cliente | keyTC | `ABMTipoCliente.Show` |
| Grupo de cliente | keyGrupo_Cliente | `ABM_Cliente_Grupo.Show` |
| País / Provincia / Departamento / distrito | keyDep | `ABMDpto.Show` |
| Zona | keyZona | `ABMZona.Show` |
| Configuración de impresora fiscal | keyConfImpFiscal | `Proceso_Fiscal_Conf.Show` |
| Configuración de báscula | keyConfiguracion_Carga_Bascula | `Configuracion_Carga_Bascula.Show` |
| Administración de publicidades | keyPublicidades | `ABM_Publicidad.Show` |

### 4.5 Ecommerce (keyEcommerce)

| Ítem | Clave | Acción |
|------|--------|--------|
| Plantilla de característica de artículo | keyEcom_Plantilla_Caract | `ecom_caract_plantilla.Show` |

---

## 5. Procesos (keyProceso)

| Ítem | Clave | Acción |
|------|--------|--------|
| Anulacion de numeración de comprobantes | keyAnulComp | `Control_Fecha` + `AnulaComp.Show` |
| Liquidación de comisiones | keyAnulCheq | `Liq_ABM_Viajante.Show` |
| Liquidación de comisiones avanzadas | keyComisiones_Avanzadas | `Menu_Comisiones_Avanzadas` |

---

## 6. Exportación (keyExportacion)

| Ítem | Clave | Acción |
|------|--------|--------|
| Sistemas externos | keyExSIAP | `Control_Fecha` + `Exportacion.Show` |

El formulario **Exportacion.frm** genera archivos de salida (REGINFO, SIFERE, Citi, Sicore, WooCommerce, balanzas, etc.) en `C:\administraNET\Archivos` o `App.Path & "\Archivos"`.

---

## 7. Configuración y Salir

| Ítem | Clave | Acción |
|------|--------|--------|
| Configuración | keyConf | `VerConfiguracion` (abre pantalla de configuración principal) |
| Salir | keySalir | `MenuSalir` (cierre de sesión/salida) |

---

## Resumen de formularios (.frm) referenciados desde Archivo

- **Empresa, ABMSucursal, Adm_Sesion, ABMPuesto**, CargaPermiso_Sistema_Puesto (**ABMPermiso_Sistema**)
- **Cliente/Proveedor/Banco/Vendedor**: vía `Menu_ABM_*` (formularios ABM correspondientes)
- **ABMDeposito, ABMLaboratorio**
- **ABMRubro, ABMSubRubro, ABMRubroCategoria, ABMPresentacion, Articulo_ce, ABMModelo, ABMArticulo_Categoria, ABMUniMed, AsigProvArt, ActPrecio** (VariacionPrecio), **ActDescuento, ABM_Descuento_Proveedor, ActDescuento_Prov, ActDatos_Articulo, Rprecios_abm, Articulo_tipo_cliente, En_abm** (armado/desarmado), **Programa_Descuentos, Consulta_Precio_Articulo_Usr**
- **ABMImpuestos, ABMIVA, ABMIngBrutos, ABMRetProv, ABMRetProvG, ABMRetProvIVA, ABMRetCli, ABMPercepciones, ABMPercepcionesCli, ABMPercepcionesCliTipo, ABM_ImpuestoInterno, ABMPeriodos, adm_felectronicas_caea**
- **ABMPV, ABMTalonario, ABMCondVenta, ABMGastos_Grupo, ABMGastos, ABMDescuentoREC, ABMCajas, ABMTarjetaC, ABMPlantc, ABMref_movstock, ABMTransporte, ABM_medio_cobpag_tipo, ABM_medio_cobpag, ABM_ingreso, ABMDeuda**
- **ABMGastoBancario, ABMChequera**
- **ABMTipoCliente, ABM_Cliente_Grupo, ABMDpto, ABMZona, Proceso_Fiscal_Conf, Configuracion_Carga_Bascula, ABM_Publicidad**
- **ecom_caract_plantilla**
- **AnulaComp, Liq_ABM_Viajante** (+ menú comisiones avanzadas)
- **Exportacion**
- **VerConfiguracion** → formulario de configuración principal

---

**Origen:** `administranet_vb6/Formularios/Principal.frm`, procedimiento `AltaMenu` (SmartMenuXP) y manejador de clic de menú (Select Case por clave).  
**Última revisión:** a partir del código VB6 en el repositorio.

---

**Análisis para migración:** cada ítem de este menú está siendo analizado en profundidad (tablas, formularios, reglas de negocio, Synap actual y recomendación) en [MIGRACION_ADMINISTRANET_VB6_ANALISIS.md](MIGRACION_ADMINISTRANET_VB6_ANALISIS.md).
