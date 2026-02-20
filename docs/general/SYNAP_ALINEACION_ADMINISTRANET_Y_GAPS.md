# Synap vs AdministraNET: alineación, GAPs y deuda técnica

Documento de estado: qué está implementado en Synap y alineado con AdministraNET (VB6/MySQL), qué gaps existen y qué deuda técnica conviene abordar.

**Referencias:** [MIGRACION_ADMINISTRANET_VB6_ANALISIS.md](MIGRACION_ADMINISTRANET_VB6_ANALISIS.md), [AVANCES_MIGRACION_ARCHIVO.md](AVANCES_MIGRACION_ARCHIVO.md), [ADMINISTRANET_VB6_MENU_ARCHIVO.md](ADMINISTRANET_VB6_MENU_ARCHIVO.md), [CAJA_AUTOSERVICIO_ANALISIS_Y_GAPS.md](../self_checkout/CAJA_AUTOSERVICIO_ANALISIS_Y_GAPS.md), [AUDITORIA_PERMISOS_ADMINISTRANET_SELF_CHECKOUT.md](../self_checkout/AUDITORIA_PERMISOS_ADMINISTRANET_SELF_CHECKOUT.md).

---

## 1. Resumen ejecutivo

| Área | Alineado con AdministraNET | GAPs principales | Deuda técnica |
|------|----------------------------|------------------|----------------|
| **Login / Auth** | Sí (MySQL usuarios, sesión, empresas, puestos, permisos) | Multi-empresa por base; sesión única | Permisos en MySQL; usuario “supervisor” hardcodeado para reports |
| **Core (empresa, sucursal, usuarios, puestos)** | Parcial (servicios + vistas Datos empresa y Sucursales) | Resto de ABM Archivo (Entidades, Productos, etc.) en VB6 | Ver [AVANCES_MIGRACION_ARCHIVO.md](AVANCES_MIGRACION_ARCHIVO.md): vistas operativas para Datos empresa y Sucursales |
| **Reportes** | Sí (solo lectura MySQL; mismos datos que VB6) | Filtros por sucursal/pv/caja según permisos; no todos los informes VB6 existen | query_runner grande; slug ventas_netas vs ventas-netas |
| **Self Checkout** | Sí (codmov, talonarios, cuentacliente, stock, stock_deposito, caja si MP) | Caja solo con MercadoPago instalado; FE depende de fe_afip | MercadoPago comentado en settings → caja no se registra si no hay MP |
| **ABM Archivo (VB6)** | Parcial (Datos empresa y Sucursales con vistas en Synap) | Entidades, Productos, Variables, Procesos, Exportación, Configuración siguen en VB6 | Ver [AVANCES_MIGRACION_ARCHIVO.md](AVANCES_MIGRACION_ARCHIVO.md), MIGRACION_ADMINISTRANET_VB6_ANALISIS.md |

---

## 2. Lo que Synap tiene y está alineado con AdministraNET

### 2.1 Autenticación y sesión

| Funcionalidad | Implementación | Tablas MySQL | Alineación |
|---------------|----------------|--------------|------------|
| Login | `login/administranet_auth.py` (AdministraNETAuth) | usuarios, sesion, empresas (base 'empresas') | Mismo modelo que VB6: usuario por empresa/sucursal/puesto. |
| Selección de empresa | Listado desde base `empresas`; sesión con base_empresa (DB_NAME) | empresas (lista de bases), datosempresa (datos por base) | Alineado. |
| Permisos por puesto | Carga desde permiso_sistema + permiso_sistema_puesto (MySQL) en middleware | permiso_sistema, permiso_sistema_puesto, puestos | Mismo criterio que VB6 (valor_permiso 'Si'). |
| Cierre de sesión | Logout; sesión Django + posible baja en sesion MySQL | sesion | Alineado. |

### 2.2 Servicios Core (lectura/escritura MySQL)

| Servicio | Archivo | Tablas | Uso |
|----------|---------|--------|-----|
| Empresa | core/services/administranet_empresas.py | DatosEmpresa | Obtener/actualizar datos empresa (nombre, CUIT, etc.). |
| Sucursales | core/services/administranet_sucursales.py | sucursales, datosempresa, provincia | Listar, crear, editar sucursales. |
| Usuarios | core/services/administranet_users.py | usuarios | CRUD usuarios (clave AES como VB6). |
| Puestos | core/services/administranet_puestos.py | puestos | Listar/CRUD puestos. |
| Permisos sistema | core/services/administranet_permiso_sistema.py | permiso_sistema, permiso_sistema_puesto | Listar, crear, actualizar permisos y asignación por puesto. |
| Permisos menú | core/services/administranet_permisos_menu.py | permiso_sistema, permiso_sistema_puesto | Menú lateral según permisos del usuario. |

Todos usan la misma conexión MySQL (settings.DATABASES['mysql']) y base por empresa. **Alineación:** Mismo esquema y reglas que VB6. **Vistas expuestas:** Datos de empresa (`core:empresa_listar` → detalle/edición) y Sucursales (`core:branch_list`, alta/edición, toggle estado Activa/Anulada) bajo menú Archivo → Parámetros; ver [AVANCES_MIGRACION_ARCHIVO.md](AVANCES_MIGRACION_ARCHIVO.md).

### 2.3 Reportes

| Funcionalidad | Implementación | Tablas MySQL (lectura) | Alineación |
|---------------|----------------|-------------------------|------------|
| Catálogo de reportes | reports (PostgreSQL ReportDefinition; slug, config, empresa) | — | Definición en Django; datos desde MySQL. |
| Ejecución de reportes | reports/services/query_runner.py (connection_pool MySQL) | cuentacliente, caja, caja_abm, caja_saldo, sucursales, punto_venta, articulo, stock, codmov, etc. | Consultas alineadas con estructura VB6 (JOINs sucursales, caja, filtros por id_sucursal, id_punto_venta, id_caja_abm). |
| Filtros por permiso | Sucursal, punto de venta, caja según puesto/usuario | Mismas tablas | Mismo concepto que VB6 (restricción por sucursal/pv/caja). |
| Exportación Excel | reports (descarga) | — | Solo lectura; no escribe en MySQL. |

Reportes existentes (ej. ventas netas, total consolidado, BO stock facturación, validaciones) leen las mismas tablas que los informes VB6. **Alineación:** Paridad de datos; no paridad de “pantallas” (no existe en Synap el árbol de informes de VB6).

### 2.4 Self Checkout (kiosco / autoservicio)

| Funcionalidad | Implementación | Tablas MySQL | Alineación |
|---------------|----------------|--------------|------------|
| Carrito | self_checkout_cart, self_checkout_cart_item (MySQL) | self_checkout_* (propias) + articulo, stock_deposito (lectura) | Mismo articulo/depósito que TPV VB6. |
| Stock disponible | StockService: saldo - saldo_pedido_cliente en stock_deposito | stock_deposito | Mismo criterio que VB6. |
| Confirmación | ConfirmationService.confirmar() | codmov, talonarios, cuentacliente, stock, stock_deposito, serie_entrada, resumen_venta_cv, tc_comprobante, self_checkout_cart, self_checkout_audit_log | Flujo atómico alineado con TPV: numeración, comprobante, salida de stock, series si aplica. |
| Factura electrónica | fe_afip (CAE/CAEA); actualización cuentacliente (fe_cae, fe_vto_cae, fe_comp, fe_transmitido) | cuentacliente | Mismo modelo que VB6 (FE sobre cuentacliente). |
| Caja | write_caja_ingreso_with_cursor (desde mercadopago.services.payment_service) llamada en confirmar() | caja, caja_saldo | Registro de ingreso por efectivo/tarjeta; id_caja_abm e id_usuario_autoservicio por config. **Condición:** Solo si MercadoPago está instalado y config tiene id_caja_abm. |
| Permisos Self Checkout | permiso_sistema (self_checkout.kiosk, .supervisor, .admin); sync_self_checkout_permissions | permiso_sistema, permiso_sistema_puesto | Mismo esquema que resto de permisos AdministraNET. |
| Kiosco / PV / Depósito | self_checkout_kiosk (id_sucursal, id_punto_venta, id_deposito) | punto_venta, sucursales, deposito | Misma relación que TPV (un kiosco = un PV por sucursal/depósito). |

**Alineación:** Flujo de venta (numeración, comprobante, stock, FE, auditoría) alineado con AdministraNET. Caja alineada cuando existe módulo MercadoPago y configuración de caja por kiosco.

### 2.5 Integración con tablas compartidas

Synap **escribe** en MySQL en:

- **Login/sesión:** sesion (alta/baja al iniciar/cerrar sesión).
- **Self Checkout:** codmov, talonarios, cuentacliente, stock, stock_deposito, serie_entrada, resumen_venta_cv, tc_comprobante, self_checkout_*, caja, caja_saldo (si caja habilitada).
- **Talonarios:** Nro = Nro + 1 (mismo que VB6).
- **Punto de venta:** pv_service puede crear punto_venta/reporte_comprobante en alta de PV.
- **Cliente:** cliente_administranet_service actualiza nombre_cliente (ej. desde self checkout).
- **Permisos:** permiso_sistema (sync_self_checkout_permissions, sync_synap_permissions_to_adminet).

Todo lo anterior es compatible con el uso simultáneo de VB6 (mismas tablas y convenciones).

---

## 3. GAPs (lo que falta o no está alineado)

### 3.1 Funcionalidad

| Gap | Descripción | Impacto | Prioridad |
|-----|-------------|---------|-----------|
| **ABM menú Archivo en Synap** | Datos empresa y Sucursales ya tienen vistas en Synap (Archivo → Parámetros). Falta: Entidades (Cliente, Proveedor, etc.), Productos, Variables, Procesos, Exportación, Configuración. | Operadores pueden usar Synap para empresa y sucursales; el resto en VB6. | Media; seguir migrando ítems según PLAN. |
| **Caja sin MercadoPago** | Si el módulo `mercadopago` no está en INSTALLED_APPS, la importación de `get_config_for_kiosk` / `write_caja_ingreso_with_cursor` falla o no se ejecuta; las ventas del kiosco no se registran en `caja` ni en `caja_saldo`. | Reportes de caja y arqueos no incluyen ventas autoservicio cuando no hay MP. | Alta si hay kioscos sin MP (ej. solo efectivo). |
| **Actualización caja_saldo** | Según doc CAJA_AUTOSERVICIO_ANALISIS_Y_GAPS, en un momento la función solo hacía INSERT en `caja` y no actualizaba `caja_saldo`. Si aún es así, el saldo de la caja queda desactualizado. | Arqueos y saldos por caja incorrectos. | Alta (verificar implementación actual de write_caja_ingreso_with_cursor). |
| **Usuario “supervisor” hardcodeado** | Permisos de reportes se agregan por cod_usuario == 'supervisor' o nombre_puesto == 'Supervisor' en base_middleware. | Dependencia de un usuario/puesto con nombre fijo; poca flexibilidad. | Media. |
| **Multi-empresa por base** | La multi-empresa es “una base MySQL por empresa” (empresas.empresa = nombre de base). No hay un único modelo Empresa en Django como fuente de verdad para todas. | Consistencia con VB6 pero limita modelos Django centrales. | Baja si se mantiene modelo actual. |
| **Informes VB6 no replicados** | No todos los informes de VB6 (Gestión, Banco, Stock, etc.) existen como reportes en Synap. | Usuarios siguen usando VB6 para ciertos listados. | Media. |
| **Exportación (REGINFO, SIFERE, etc.)** | La generación de archivos de exportación está solo en VB6 (Exportacion.frm). Synap no genera esos archivos. | Procesos batch y normativas siguen en VB6. | Baja salvo que se quiera centralizar en Synap. |

### 3.2 Datos y convenciones

| Gap | Descripción | Recomendación |
|-----|-------------|----------------|
| **Slug reportes** | Inconsistencia ventas_netas vs ventas-netas (guión) en BD y query_runner. | Estandarizar un formato y aceptar el otro en lectura (ya hay lógica de slug alternativo). |
| **Cliente código 1** | Consumidor final (codigo=1) se usa en self checkout; actualización desde Empresa.frm en VB6 puede cambiar IDIva/CUIT. | Documentar que el cliente 1 es compartido VB6/Synap; evitar conflictos de actualización. |
| **CodigoMovimiento global** | codmov tiene un solo registro (codigo=1); compartido entre VB6 y Synap. | Correcto; no cambiar sin coordinación. |

### 3.3 Permisos y seguridad

| Gap | Descripción | Recomendación |
|-----|-------------|----------------|
| **Permisos solo en MySQL** | Los permisos efectivos vienen de MySQL (permiso_sistema_puesto); no hay réplica en PostgreSQL para lógica Django. | Mantener; documentar que la fuente de verdad es MySQL. |
| **Self Checkout sin MercadoPago** | Si mercadopago no está instalado, la ruta de pago/confirmación puede no registrar caja ni usar “usuario cajero autoservicio”. | Definir flujo explícito para “solo efectivo” (TPV en kiosco) con escritura en caja sin depender de MP. |

---

## 4. Deuda técnica

### 4.1 Código y arquitectura

| Deuda | Descripción | Estado / Ubicación |
|-------|-------------|---------------------|
| **Connection pool MySQL** | Patrón único: pool en `core/mysql_pool.py`; reports y self_checkout consumen desde core. Ver [DEUDA_TECNICA_FASE1_MYSQL.md](DEUDA_TECNICA_FASE1_MYSQL.md). | **Resuelto** |
| **Duplicación de lógica de permisos** | Única fuente: `core/services/administranet_permisos_usuario.py`; middleware y self_checkout delegan ahí. | **Resuelto** |
| **Módulo MercadoPago comentado** | mercadopago está comentado en INSTALLED_APPS; la integración de caja en confirmación depende de ese módulo. | django_project/settings.py, self_checkout/services/confirmation_service.py |
| **query_runner muy grande** | query_runner.py concentra muchas consultas y filtros; difícil de mantener y testear. | reports/services/query_runner.py |
| **Servicios administranet_* sin vistas** | Empresa y Sucursales ya tienen vistas (empresa_listar, branch_list, branch_edit, branch_toggle_estado). Usuarios, puestos y permisos siguen con vistas existentes bajo Archivo. Resto de ítems Archivo (Entidades, Productos, etc.) sin pantalla en Synap. | core/services/administranet_*.py, core/views/views.py |

### 4.2 Configuración y despliegue

| Deuda | Descripción |
|-------|-------------|
| **Dos bases de datos** | PostgreSQL (Django default: core, auth, report definitions) y MySQL (administraNET). Migraciones y backups deben contemplar ambas. |
| **Charset MySQL** | Uso de latin1 en varios sitios (administranet_auth, empresas) y utf8mb4 en otros (sucursales); puede afectar caracteres especiales. |
| **Firebase deshabilitado** | Código y rutas de Firebase siguen en el repo pero no se usan; documentado en FIREBASE_DESHABILITADO.md. |

### 4.3 Documentación y pruebas

| Deuda | Descripción |
|-------|-------------|
| **Tests de integración MySQL** | Pocos tests que golpeen MySQL; la mayoría asume mocks o SQLite. |
| **Documentación de APIs** | Endpoints de reports y self_checkout no están todos documentados (OpenAPI/Swagger). |
| **Mapa de tablas escritas por Synap** | No hay un único documento que liste todas las tablas MySQL que Synap escribe y en qué flujo; este doc y el de migración lo cubren parcialmente. |

---

## 5. Matriz de alineación por capacidad

| Capacidad | VB6 (AdministraNET) | Synap | Alineado | Notas |
|-----------|---------------------|--------|----------|--------|
| Login / sesión | IngresoUsuario, sesion | AdministraNETAuth, sesión Django + MySQL | Sí | |
| Empresa (datos) | Empresa.frm, DatosEmpresa | Vista Datos empresa + administranet_empresas (MySQL DatosEmpresa/datosempresa2) | Sí | Ver AVANCES_MIGRACION_ARCHIVO |
| Sucursales | ABMSucursal, CargaSucursal | Vista Sucursales (branch_list, toggle estado) + administranet_sucursales | Sí | Sin eliminación; estado Activa/Anulada; formulario COT/Geo/Envíos |
| Usuarios / Puestos / Permisos | CargaUsuario, ABMPuesto, CargaPermiso_Sistema | Servicios core (sin UI) | Parcial | Solo servicios |
| Menú según permisos | Principal + permiso_sistema_puesto | base_middleware + permisos_menu | Sí | Misma fuente MySQL |
| Reportes (datos) | Info_*.frm, consultas MySQL | reports query_runner, filtros por sucursal/pv/caja | Sí | No todos los informes VB6 existen |
| Ventas kiosco (flujo) | TPV confirmación | ConfirmationService (codmov, talonarios, cuentacliente, stock) | Sí | |
| Factura electrónica | FE en TPV/Facturación | fe_afip + actualización cuentacliente | Sí | |
| Caja (movimientos) | caja + caja_saldo en TPV | write_caja_ingreso_with_cursor en confirmar (si MP + config) | Condicional | Solo con MercadoPago instalado y config |
| ABM Cliente / Proveedor / Artículo / etc. | Menú Archivo completo | No existe en Synap | No | Todo en VB6 |

---

## 6. Recomendaciones prioritarias

1. **Caja sin MercadoPago:** Decidir flujo para kioscos sin MP (solo efectivo): either (a) extraer `write_caja_ingreso` y config de caja a un módulo que no dependa de mercadopago, o (b) documentar que sin MP no se registra caja y usar un proceso manual/alternativo.
2. **Verificar caja_saldo:** Confirmar que `write_caja_ingreso_with_cursor` actualiza `caja_saldo` (Saldo += importe) además del INSERT en `caja`; si no, implementar según CAJA_AUTOSERVICIO_ANALISIS_Y_GAPS.
3. **Permisos reportes:** Sustituir o complementar el “supervisor” hardcodeado por permisos en MySQL (ej. reports.view_operational asignados por puesto).
4. **Documentar tablas escritas:** Mantener en este doc (o en MIGRACION) la lista de tablas MySQL que Synap escribe y en qué flujo, para auditoría y soporte.
5. **Estandarizar slug reportes:** Un solo formato (guión o guión bajo) y aceptar el otro en compatibilidad.

---

**Última actualización:** Febrero 2025. Incluye avances de migración Archivo: vistas Datos empresa y Sucursales operativas (AVANCES_MIGRACION_ARCHIVO). Código: core, login, reports, self_checkout; docs: CAJA_AUTOSERVICIO_ANALISIS_Y_GAPS, AUDITORIA_PERMISOS_ADMINISTRANET_SELF_CHECKOUT.
