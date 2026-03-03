# Avances de migración: menú Archivo (Empresa / Sucursales)

Documento de avances en la migración de funcionalidades del menú Archivo de AdministraNET (VB6) a Synap. Referencia: [MIGRACION_ADMINISTRANET_VB6_ANALISIS.md](MIGRACION_ADMINISTRANET_VB6_ANALISIS.md), [PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md](PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md).

**Última actualización:** febrero 2026.

---

## 1. Datos de la empresa (Empresa.frm → Synap)

### Implementado

| Aspecto | Detalle |
|--------|---------|
| **Una empresa por base** | En AdministraNET solo hay una empresa por base de datos (DatosEmpresa, id_empresa=1). Ver [EMPRESA_UNA_POR_BASE_ADMINISTRANET.md](EMPRESA_UNA_POR_BASE_ADMINISTRANET.md). |
| **Flujo en Synap** | Ruta "Datos empresa" (`core:empresa_listar`): si existe empresa en la base activa → redirección directa a detalle/edición; si no → estado vacío con "Crear primera empresa". No se muestra lista de tarjetas. |
| **Vista detalle/edición** | Formulario alineado con Empresa.frm: Denominación, País, Provincia, Departamento, Domicilio, Condición IVA, CUIT, CP, Teléfono, Email, Fax, Nro. Ingresos Brutos, Nro. Establecimiento, Inicio Actividades, Sede Timbrado, WhatsApp, Facebook mess, Twitter, URL empresa, URL ecom cli/vend, Rubro/Canal, Actividad, Observaciones. Campos opcionales (redes y URLs) sin validación obligatoria. |
| **Guardado** | Servicio `guardar_empresa` en `core/services/administranet_empresas.py`. Escribe en la base de la sesión (`base_empresa`); verificación con `SELECT DATABASE()` para asegurar que no se escribe en otra DB. |
| **Compatibilidad con VB6** | Se actualiza **DatosEmpresa** y, si existe, **datosempresa2** (Empresa.frm puede usar cualquiera de las dos). Campos `actividad` y `rubro_canal` se guardan como texto (vacío → '-'). Tipos normalizados con `core.utils.administranet_types`. |
| **Lectura** | `obtener_empresa`: usa `SELECT *` y resolución de nombre de tabla (mayúsculas/minúsculas); normalización de claves para templates. Comando diagnóstico: `python manage.py diagnostico_empresa_adminet [--base NOMBRE]`. |

### Documentación relacionada

- [EMPRESA_UNA_POR_BASE_ADMINISTRANET.md](EMPRESA_UNA_POR_BASE_ADMINISTRANET.md): una empresa por DB; datos en base_empresa.
- [TIPOS_DATOS_ADMINISTRANET.md](TIPOS_DATOS_ADMINISTRANET.md): compatibilidad Empresa.frm y datosempresa2.

---

## 2. Sucursales (ABMSucursal / CargaSucursal → Synap)

### Implementado

| Aspecto | Detalle |
|--------|---------|
| **Lista** | Vista `core:branch_list` (`empresas/1/sucursales/`). Búsqueda por nombre, provincia, empresa o descripción. Sin botón "Eliminar". |
| **Estado Activa/Anulada** | Las sucursales no se eliminan; se desactivan (Anulado=Si/No). En la lista, la columna **Estado** es un botón que envía POST a `core:branch_toggle_estado` y alterna entre Activa y Anulada. Servicio `toggle_anulado_sucursal` en `administranet_sucursales.py`. |
| **Edición** | Formulario en **tabs**: **Datos** (Empresa, Nombre, Descripción, País, Provincia, Domicilio, CP, Nro. Establecimiento, Teléfono, Email, Estado con un solo botón Activa/Anulada), **COT**, **Envíos**, **Tipo de cobro por envío**, **Geolocalización Google Maps**, **Opciones Generales**, **Agente percepción / retención**, **Impresoras de etiquetas**, **Opciones de DNF**. En la cabecera: CTA "Volver a sucursales" y título "Editar Sucursal [nombre]" (nombre en color del botón Guardar). Ver [CONVENCIONES_UX.md](CONVENCIONES_UX.md). |
| **Guardado** | `actualizar_sucursal` persiste datos principales y, en un segundo UPDATE opcional, campos COT, geo y activa_calculo_envios; si la tabla no tiene esas columnas, se ignora sin fallar. |
| **Menú** | Entrada "Sucursales" en menú Archivo → Parámetros apunta a `core:branch_list` (empresas/1/sucursales/). |

### URLs

- Lista: `core:branch_list` → `/core/empresas/1/sucursales/`
- Nueva: `core:branch_create` → `/core/empresas/1/sucursales/nueva/`
- Editar: `core:branch_edit` → `/core/empresas/1/sucursales/<id>/editar/`
- Toggle estado: `core:branch_toggle_estado` (POST) → `/core/empresas/1/sucursales/<id>/toggle-estado/`
- La ruta `branch_delete` redirige a la lista (no se usa eliminación física).

### Documentación relacionada

- [tablas/sucursales.md](tablas/sucursales.md): schema y columnas (anulado, cot_*, geo_*, activa_calculo_envios).

---

## 2.1 Avances recientes: formulario Sucursal (tabs, Estado, Geolocalización, Envíos)

### Tabs

El formulario de alta/edición de sucursal se organiza en ocho pestañas (paridad con CargaSucursal.frm + pestaña Sucursal de Configuración en AdministraNET):

**Datos** | **COT** | **Envíos** | **Tipo de cobro por envío** | **Geolocalización Google Maps** | **Opciones Generales** | **Agente percepción / retención** | **Impresoras de etiquetas** | **Opciones de DNF**

### Estado (pestaña Datos)

- **Antes:** Checkbox "Activa (Anulado=No)" y luego dos botones Activa/Inactiva.
- **Ahora:** Un solo botón que alterna entre **Activa** (verde) y **Anulada** (rojo), igual que en la columna Estado del listado de sucursales. Clic para activar o desactivar. El valor se envía en el campo oculto `anulado` (No/Si). Ver [CONVENCIONES_UX.md](CONVENCIONES_UX.md).

### Geolocalización para Google Maps

- **Obtener geolocalización:** Botón que construye la dirección a partir del domicilio y código postal (pestaña Datos), llama a la API de geocodificación y rellena Latitud y Longitud.
  - Endpoint Synap: `GET /core/api/geocode/?address=...&key=...` (parámetro `key` opcional; si no se envía se usa `GOOGLE_GEOCODING_API_KEY` de settings). Paridad con CargaSucursal.frm (Google Geocoding API).
- **Ver en mapa:** Enlace visible cuando hay latitud y longitud; abre Google Maps con esas coordenadas.
- **Formularios VB6 que utilizan geolocalización (para cuando se migren):**
  - **CargaSucursal.frm:** ApiKey desde sucursales, obtiene coords desde domicilio y "Ver en mapa".
  - **Carga_ClienteDomicilio.frm:** geo_latitud/geo_longitud en cliente_domicilio; obtiene coords con ApiKey de sucursal.
  - **Geolocalizacion_Comprobante.frm**, **Geolocalizacion_Cliente.frm:** visualización de clientes/comprobantes en mapa (geo_api_key_javascript).
  - **Pedido_Avanzado.frm**, **ConsultaComprobante.frm:** lectura de geo_latitud/geo_longitud para mostrar ubicación.

### Tipo de cobro por envío (tab + modal)

- **Paridad AdministraNET:** ABM_Sucursal_Envio.frm (listado) y CargaSucursal_Envio.frm (alta/modificación). En VB6 el id de sucursal se pasa al abrir el modal: `CargaSucursal_Envio.id_sucursales_envios = ABMSucursal.DataSucursal.Recordset.Fields!id_sucursal` y al guardar se escribe `rs.Fields!id_sucusal = id_sucursales_envios`. Tabla **sucursales_envios**: FK a sucursal en columna **id_sucusal** (VB6); algunas bases tienen además **id_sucursal**. Synap prefiere **id_sucusal** para INSERT (paridad VB6) y filtra el listado por la sucursal en edición.
- **Comportamiento:** La pestaña solo se usa al **editar** una sucursal. El listado muestra **solo** los tipos de envío de esa sucursal (filtro por id_sucursal/id_sucusal según existan). El botón **Agregar tipo de envío** abre un modal; al guardar se crea el registro asociado a la **misma sucursal que se está editando** (branch_id de la URL). En la columna Acciones cada fila tiene iconos **Editar** (lápiz) y **Eliminar** (papelera) con tooltip. Así se mantiene la regla de AdministraNET: cada registro pertenece a una sucursal concreta.
- **API:** `GET/POST /core/api/sucursales/<id_sucursal>/tipos-envio/` (id_sucursal = branch en edición), `PUT/DELETE .../tipos-envio/<id_tipo_envio>/`, `GET /core/api/sucursales/zonas/`. Servicio: `core/services/administranet_sucursales.py`.

### Envíos: artículo para facturación de envío

- **Campo:** `id_articulo_fact_envio` (tabla `sucursales`). En la pestaña Envíos se muestra un input numérico y, en edición, el nombre del artículo (desde `articulo.NombreArticulo`) cuando existe ID.
- **En VB6 (CargaSucursal.frm):** El botón de búsqueda abre el formulario **"Selección de artículo"** (ABMArticulo_seleccion.frm o ABMArticulo_seleccion_simple.frm) con `Accion = "CargaSucursal"`. El usuario busca por texto, tipo de búsqueda y lista; al aceptar un artículo del grid "Artículos y Precios", se asigna:
  - `CargaSucursal.id_articulo_fact_envio = DataABMArt.Recordset.Fields!IDArt`
  - `CargaSucursal.Articulo = DataABMArt.Recordset.Fields!NombreArticulo`
- **Uso en el proyecto:** Ese artículo se usa como referencia para la facturación o cálculo de envío asociado a la sucursal. La búsqueda con modal "Selección de artículo" se implementará en Synap cuando se migre el ABM / selector de artículos (menú Archivo → Productos o equivalente).

### Configuración Sucursal (tabs migrados desde Configuración → Sucursal en AdministraNET)

En AdministraNET, la ventana **Configuración** tiene un tab **Sucursal** con cuatro secciones. Esas secciones se migraron como cuatro tabs adicionales en el formulario de sucursal en Synap:

| Tab en Synap | Contenido (campos en `sucursales`) |
|--------------|-------------------------------------|
| **Opciones Generales** | Vendedor (vendedor_defecto), Límite consultas (limite_consulta), Ruta informes servidor/comprobantes (ruta_reporte_servidor, ruta_reporte_comprobante), Cantidad renglones (cant_renglon_venta), Salida sin existencia (salida_sin_stock), Días venc. presup/pedidos (dias_venc_presup, dias_venc_pedido), Impuestos en precio de venta (tipo_calculo_precios_impuesto_venta), Límite redondeo TPV (lim_redondeo_tpv). |
| **Agente percepción / retención** | Agente Ret. Ing. Brutos (agente_retib), Agente Ret. Ganancias (agente_retg), Agente Ret. IVA (agente_reti), Agente Percepciones (agente_percep), Agente Percep RG AFIP 5329/2023 (agente_percep_resol_afip_5329_iva). Valores Si/No. |
| **Impresoras de etiquetas** | Tipo impresora default (tipo_impresora), Impresora default (nombre_impresora), Puerto (puerto_impresora), Impresión doble etiqueta (doble_imp_etiqueta). |
| **Opciones de DNF** | DNF factura venta (dnf_vta), Tipo de DNF (dnf_tipo), Texto libre 1/2/3 DNF (dnf_texto, dnf_texto2, dnf_texto3). |

La persistencia se hace en un segundo `UPDATE` sobre `sucursales` tras el de COT/geo/envíos; si alguna columna no existe en la base, ese UPDATE se ignora sin afectar al resto.

---

## 2.2 Administración de usuarios (core/usuarios/)

Gestión de usuarios contra la base de administraNET (tabla `usuarios`). Paridad con **CargaUsuario.frm** (alta/edición) y **ABMUsuarios.frm** (listado). Servicio: `core/services/administranet_users.py`; vistas: `core/views/views_usuarios.py`.

| Aspecto | Detalle |
|--------|---------|
| **Lista** | `core:usuarios` → `/core/usuarios/`. Filtro por **id_empresa** de la sesión (solo usuarios de la empresa activa). Búsqueda por nombre, apellido o **cod_usuario**; filtro "Solo activos" (baja_usuario <> 'Si'). Columnas: Código, Nombre, Apellido, Empresa, Sucursal, Puesto, Estado (Activo/Inactivo), Acciones (iconos Editar / Eliminar). Orden: nombre_usuario. |
| **Crear** | `core:crear_usuario` → `/core/usuarios/crear/`. Campos: cod_usuario (obligatorio, se guarda en minúsculas), nombre_usuario, apellido_usuario, contraseña (AES_ENCRYPT con clave igual a VB6), puesto (puestos no anulados), sucursal (sucursales no anuladas). Si no se elige sucursal, se asigna la primera sucursal activa (id_sucursal NOT NULL en tabla). CTA y título según [CONVENCIONES_UX.md](CONVENCIONES_UX.md). |
| **Editar** | `core:editar_usuario` → `/core/usuarios/<id>/editar/`. Mismos campos; contraseña opcional (vacío = no cambiar). **id_sucursal** no se envía NULL: si el formulario viene vacío se mantiene el valor actual (NOT NULL en tabla). Usuario Supervisor (id=1): solo se permite cambiar contraseña. CTA y título con nombre en púrpura. |
| **Eliminar** | Dar de baja: `UPDATE usuarios SET baja_usuario = 'Si'`. No se elimina físicamente; no se permite baja del usuario id=1 (Supervisor). |
| **Validar integridad** | `core:validar_integridad_usuarios` → comprueba usuarios y puestos en administraNET. |
| **Alineación VB6** | Contraseña: AES_ENCRYPT con misma clave que CargaUsuario.frm. Listados de puestos y sucursales: solo registros con anulado <> 'Si'. JOINs con puestos (idpuesto), sucursales, datosempresa para nombres. |

---

## 3. Menú Archivo en Synap

| Ítem menú (Archivo → Parámetros) | URL Synap | Estado |
|----------------------------------|-----------|--------|
| Datos empresa | `core:empresa_listar` (redirige a detalle si hay empresa) | Vista implementada |
| Sucursales | `core:branch_list` (empresas/1/sucursales/) | Vista implementada; menú con `url_kwargs` para branch_list |
| Administrador de usuario | core:usuarios, crear, editar | Ya existente |
| Puesto / Permiso en menú / Permiso en sistema | core:listar_roles, permisos_sistema, listar_permisos | Ya existente |

La resolución de URLs del menú con parámetros (p. ej. `empresa_id=1` para branch_list) se hace en `core/utils/utils.py` mediante `url_kwargs` en los ítems de submenú y `reverse(item["url"], kwargs=item.get("url_kwargs") or {})`.

---

## 4. Resumen de archivos tocados

| Área | Archivos principales |
|------|----------------------|
| Empresa | core/views/views.py (empresa_listar_view, empresa_detalle_view), core/services/administranet_empresas.py, core/templates/core/system_config/empresa_list.html, empresa_detail.html, core/utils/administranet_types.py, core/management/commands/diagnostico_empresa_adminet.py |
| Sucursales | core/views/views.py (branch_*), core/services/administranet_sucursales.py, core/templates/core/system_config/branch_list.html, branch_form.html, core/urls.py, core/api/views.py (geocode_api), core/api/urls.py (geocode) |
| Usuarios | core/views/views_usuarios.py, core/services/administranet_users.py, core/templates/core/usuarios_admin.html, usuarios_crear.html, usuarios_editar.html, usuarios_admin_tabla.html, usuarios_validacion.html |
| Menú | core/utils/utils.py (APPS_CON_MODULOS: Archivo submenus, url_kwargs para branch_list) |
| Documentación | docs/general/EMPRESA_UNA_POR_BASE_ADMINISTRANET.md, TIPOS_DATOS_ADMINISTRANET.md, AVANCES_MIGRACION_ARCHIVO.md (este doc) |
