# Análisis Principal.frm: brechas de migración, FODA y mejoras

**Plan de referencia:** migración/refactor de Principal.frm (VB6) a Synap. Todo el desarrollo relacionado con shell, sesión, TPV y caja debe ajustarse a este documento.

**Documentos relacionados:** Estado de alineación, GAPs y deuda técnica: [SYNAP_ALINEACION_ADMINISTRANET_Y_GAPS.md](SYNAP_ALINEACION_ADMINISTRANET_Y_GAPS.md). Árbol del menú Archivo VB6: [ADMINISTRANET_VB6_MENU_ARCHIVO.md](ADMINISTRANET_VB6_MENU_ARCHIVO.md). Análisis por ítem para migración: [MIGRACION_ADMINISTRANET_VB6_ANALISIS.md](MIGRACION_ADMINISTRANET_VB6_ANALISIS.md).

---

## 1. Brechas de migración / refactor (qué falta en Synap)

Comparando [Principal.frm (informe)](PRINCIPAL_FRM_INFORME_DETALLADO.md) con el shell actual de Synap ([base_app.html](../../theme/templates/base_app.html), [context_processors](../../core/context_processors.py), [login logout](../../login/views.py), [APPS_MENU](../../core/utils/utils.py)):

| Responsabilidad en Principal | Estado en Synap | Acción sugerida |
| --------------------------- | --------------- | ---------------- |
| **Variables de sesión globales** (empresa, sucursal, puesto, fecha, caja, PV, id_vendedor_usr, permisos, módulos) | Parcial: `session_user`, `empresa_activa`, `branch_activa`, `permisos_usuario` en context. No hay: fecha servidor, id_caja, id_punto_venta, id_vendedor_usr, flags de licencia/módulo. | Centralizar en sesión Django o en un "session store" (por request/cache) y exponer vía context o API; opcionalmente modelo/cache por usuario. |
| **Barra de estado (StatusBar)** con Fecha, Hora, Empresa, Sucursal, Puesto, Usuario | No existe. Navbar muestra logo y menú, no fecha/hora ni datos de contexto. | Añadir barra inferior o zona en navbar con fecha/hora (servidor), empresa, sucursal, puesto, usuario (y opcional cajero si TPV). |
| **Fecha del servidor (Control_Fecha)** | No se expone. Cada reporte/consulta puede usar `NOW()` en MySQL pero no hay "fecha de trabajo" única en UI. | Endpoint o context con fecha/hora del servidor (MySQL o servidor app) y mostrarla en shell; opcional "fecha de trabajo" configurable. |
| **Menú lateral por puesto (menurapido_grupo / menurapido_item)** | No. Synap usa `APPS_MENU` estático en código + permisos; no lee tablas `menurapido_*` de MySQL. | Decisión: mantener menú en código o migrar a BD (menurapido_* o modelos Django) para que por puesto se definan grupos/ítems. |
| **Cierre de sesión completo (Salida)** | Parcial: [logout_view](../../login/views.py) hace UPDATE `sesion.fechafin` en MySQL y `session.flush()`. **No** llama a Cierra_Logueo_Vendedor. | En logout, si existe `id_vendedor_usr` en sesión, ejecutar UPDATE `viajantes` SET logueado='No', detalle_logueo=NULL, ip_logueo=NULL antes de flush. |
| **Autenticación cajero al abrir TPV** (clave_caja, viajantes) | No implementada. Self-checkout tiene entrada en menú pero no flujo "clave de caja" ni sesión de cajero. | Implementar según [TPV_CAJA_AUTENTICACION_Y_OPERACIONES](../self_checkout/TPV_CAJA_AUTENTICACION_Y_OPERACIONES.md): auth-cashier, logout-cashier, sesión id_vendedor_usr. |
| **Validación "obliga_cierre_caja" antes de abrir TPV** | No. No se valida caja PV ni cierre del día anterior. | Antes de abrir vista TPV: leer caja_abm/caja_saldo/caja por usuario; si obliga_cierre_caja, exigir cierre previo o bloquear entrada. |
| **Control de sesión única (Timer_Control_Sesion, Control_Sesiones)** | No. No se impide doble login del mismo usuario en otra estación. | Opcional: al login, marcar sesión activa (por usuario o por id_sesion); middleware o polling que, si se detecta otro login, cierre o avise. |
| **Mensajería interna (Timer1, tabla mensajeria)** | No. | Opcional: job o polling que consulte mensajes no leídos y muestre notificaciones o badge en navbar. |
| **Alertas CRM (Timer1, crm_llamada fecha_prox_llamada)** | No. | Opcional: mismo mecanismo de notificaciones con filtro CRM. |
| **Avisos (Frame_Aviso, ej. vencimiento certificado FE)** | No. | Opcional: banner o modal desde configuración o regla (ej. vencimiento certificado). |
| **Lógica compartida** (Guardar_Error, Generacion_CodBarra/QR AFIP, reportes Crystal, Visualizar_PED/Presupuesto) | Parte en reports/self_checkout (FE, códigos); no hay "Principal" central. Guardar_Error puede estar en core o en cada app. | Mantener servicios por dominio; no replicar un "Principal" monolítico; unificar solo donde aporte (ej. utilidad de fecha servidor, errores globales). |

---

## 2. FODA

### 2.1 FODA de Principal.frm

**Fortalezas:** Un solo punto de entrada post-login; menú dinámico por puesto (menurapido_*); cierre ordenado (sesión BD + cierre logueo vendedor); validaciones centralizadas antes de TPV.

**Debilidades:** Formulario monolítico (~13.600 líneas); centenares de variables públicas; menú con 219+ casos en Menu_Click; timers y ActiveX en el mismo form.

**Oportunidades:** Migrar menú a datos; separar shell de lógica de negocio; unificar fecha del sistema y sesión caja/vendedor en APIs.

**Amenazas:** Cualquier cambio impacta toda la app VB6; replicar la misma estructura en Synap generaría un super controlador rígido.

### 2.2 FODA del shell actual de Synap

**Fortalezas:** Shell ligero; menú basado en permisos y APPS_MENU; logout cierra sesión en MySQL; context con empresa/sucursal.

**Debilidades:** No hay barra de estado; no hay Cierra_Logueo_Vendedor en logout; menú no proviene de menurapido_*.

**Oportunidades:** Barra de estado; auth-cashier y cierre de caja en TPV; session store acotado.

**Amenazas:** Sobrecargar contexto con todas las variables de Principal.

---

## 3. Optimizaciones viables

- **Session store acotado:** Subconjunto (empresa, sucursal, puesto, usuario, base_empresa, id_caja, id_punto_venta, id_vendedor_usr, fecha_servidor); cargar en login o middleware.
- **Fecha del servidor:** Un endpoint o context; evitar N consultas NOW().
- **Menú:** APPS_MENU en código; opcional filtro por BD (menurapido_*) sin duplicar casos.
- **Logout:** Unificar Django logout + UPDATE sesion + Cierra_Logueo_Vendedor si hay id_vendedor_usr.
- **TPV/Caja:** Solo flujos documentados (auth-cashier, cierre, arqueo) en self_checkout o módulo caja.

---

## 4. Mejoras funcionales

- Barra de estado (fecha/hora servidor, empresa, sucursal, puesto, usuario, opcional cajero).
- Cierre explícito de caja en TPV (botón "Cerrar caja" → logout-cashier y flujo cierre).
- Notificaciones (API + polling/WebSocket; icono y badge en navbar).
- Control de sesión única (opcional).
- Avisos configurables (banner/modal desde configuración).

---

## 5. Resumen ejecutivo

- **Falta en Synap:** Barra de estado; Cierra_Logueo_Vendedor en logout; auth-cashier y caja en TPV; obliga_cierre_caja; fecha servidor en contexto/API; opcional menú BD, sesión única, mensajería/CRM, avisos.
- **Compras — Factura:** El selector es **origen de datos** (Manual, Desde Remito, Desde OC, Desde Vale), no “tipo de factura”; ver 6.6 y [ORIGEN_DATOS_FACTURA_COMPRA_VB6.md](../compras/ORIGEN_DATOS_FACTURA_COMPRA_VB6.md).
- **Optimizaciones:** Session store acotado, endpoint fecha servidor, menú en código + filtro BD, logout unificado.
- **Seguridad:** Activar cuando **ENVIRONMENT=production** (o produccion). Ver secciones 8 y 9.

---

## 6. Estado de migración, orden y reglas

### 6.1 Estado de migración

| Área | Estado | Detalle |
|------|--------|---------|
| **Login** | Hecho | Autenticación contra MySQL (usuarios, sesion, empresas); login migrado al pool MySQL ([login/administranet_auth.py](../../login/administranet_auth.py)). |
| **Pool MySQL** | Hecho | Origen único en [core/mysql_pool.py](../../core/mysql_pool.py); consumido por login, reports, self_checkout. Ver [DEUDA_TECNICA_FASE1_MYSQL.md](DEUDA_TECNICA_FASE1_MYSQL.md). |
| **Permisos unificados** | Hecho | Única fuente: [core/services/administranet_permisos_usuario.py](../../core/services/administranet_permisos_usuario.py); middleware y self_checkout delegan ahí. |
| **Principal** | Pendiente | Session store acotado; fecha servidor (endpoint); barra de estado; logout con Cierra_Logueo_Vendedor. |
| **Archivo – Parametros** | Pendiente | Menú Archivo con orden VB6; Datos empresa (vista); Sucursal, Usuario, Puesto, Permisos sistema (mover desde Settings a Archivo). |
| **Archivo – Entidades** | Pendiente | Cliente, Proveedor, Banco, Vendedor, Depósito, Laboratorio (por fases). |
| **Archivo – Productos / Variables / Procesos / Export / Config** | Pendiente | Según [MIGRACION_ADMINISTRANET_VB6_ANALISIS.md](MIGRACION_ADMINISTRANET_VB6_ANALISIS.md) sección 8.2; Procesos y Exportación en VB6 salvo decisión de retiro. |

### 6.2 Orden de migración (cuatro fases)

El orden respeta dependencias y el estado actual. Referencia: [ADMINISTRANET_VB6_MENU_ARCHIVO.md](ADMINISTRANET_VB6_MENU_ARCHIVO.md), [MIGRACION_ADMINISTRANET_VB6_ANALISIS.md](MIGRACION_ADMINISTRANET_VB6_ANALISIS.md).

1. **Fase 1 — Principal (shell):** Session store acotado; endpoint fecha servidor; barra de estado; logout unificado con Cierra_Logueo_Vendedor (UPDATE viajantes si id_vendedor_usr en sesión).
2. **Fase 2 — Archivo: estructura y Parametros:** Menú "Archivo" con orden y estructura según VB6; mover a Archivo las entradas que hoy están en Settings (Empresas, Sucursales, Usuarios, Roles, Permisos); vista "Datos de empresa"; asegurar base_empresa desde sesión y pool en vistas existentes.
3. **Fase 3 — Archivo: Entidades:** Cliente, Proveedor y, según prioridad, Banco, Vendedor, Depósito, Laboratorio. Reutilizar servicios existentes (ej. cliente_administranet_service) y exponer vistas ABM bajo Archivo → Entidades.
4. **Fase 4 — Archivo: Productos, Variables, Procesos, Exportación, Configuración:** Priorizar ítems que reportes y self_checkout ya usan (artículo, PV, caja); Procesos y Exportación mantener en VB6 salvo decisión explícita; Configuración: en Synap solo parámetros que Synap consuma.

### 6.3 Reglas de reutilización y menú

- **Reutilización:** Antes de implementar cualquier ítem de Principal o Archivo, comprobar si ya existe en Synap la funcionalidad (vista, servicio, API); en ese caso, actualizar o reutilizar en lugar de duplicar.
- **Ubicación en menú:** Si la funcionalidad existe pero está en un menú distinto al de AdministraNET (p. ej. bajo "Settings"), debe moverse al menú Archivo (o equivalente) respetando el orden de [ADMINISTRANET_VB6_MENU_ARCHIVO.md](ADMINISTRANET_VB6_MENU_ARCHIVO.md). Las URLs y vistas se mantienen; solo se reorganiza el menú lateral (no duplicar entradas en Settings y Archivo).

### 6.4 Funcionalidad ya existente en Synap (reutilizar o exponer)

| Área Archivo VB6 | En Synap | Ubicación | Acción |
|------------------|----------|-----------|--------|
| Datos empresa | Vista + servicio | core/views/views.py (empresa_listar_view, empresa_detalle_view), core/services/administranet_empresas.py | ✅ Vista operativa; redirección a detalle; guardado en DatosEmpresa/datosempresa2. Ver [AVANCES_MIGRACION_ARCHIVO.md](AVANCES_MIGRACION_ARCHIVO.md). |
| Sucursal | Vista + CRUD | core/views/views.py (branch_*), core/services/administranet_sucursales.py, core/urls.py empresas/…/sucursales/ | ✅ Lista/alta/edición; toggle estado Activa/Anulada (sin eliminar); formulario COT/Geo/Envíos. Menú Archivo → Parametros. |
| Usuario | CRUD completo | core/views/views.py, views_usuarios.py, core/services/administranet_users.py | Reutilizar; mover entrada de menú a Archivo → Parametros. |
| Puesto (Roles) | CRUD completo | core/views/views_roles.py, core/services/administranet_puestos.py | Reutilizar; mover entrada de menú a Archivo → Parametros. |
| Permiso en sistema | Listar / editar por puesto / toggle | core/views/views_permisos_sistema.py, views_permisos.py, permisos-sistema/, permisos/ | Reutilizar; mover entrada de menú a Archivo → Parametros. |
| Empresas (lista) | Listar / detalle / nueva / eliminar | core/urls.py empresas/, core/views/views.py empresa_* | Reutilizar; mover a Archivo. |
| Cliente | Parcial (actualización desde self_checkout) | self_checkout/services/cliente_administranet_service.py | Ampliar a ABM completo; vista bajo Archivo → Entidades. |
| Punto de venta | Lógica en self_checkout | self_checkout/services/pv_service.py | Exponer ABM si no existe; Archivo → Variables. |
| Salir | Logout | login/views.py logout_view | Actualizar para añadir Cierra_Logueo_Vendedor; no nueva pantalla. |

### 6.5 Mapa Archivo → Synap (resumen)

| Ítem menú Archivo (VB6) | Equivalente actual en Synap | Estado |
|-------------------------|-----------------------------|--------|
| Archivo → Empresa/Parametros → Datos | core:empresa_listar (redirige a detalle/edición) | ✅ Implementado |
| Archivo → Empresa/Parametros → Sucursal | core:branch_list, branch_create, branch_edit, branch_toggle_estado (empresas/1/sucursales/) | ✅ Implementado; menú Archivo → Parametros |
| Archivo → Empresa/Parametros → Administrador de usuario | core:usuarios, crear_usuario, editar_usuario | Reutilizar; mover menú |
| Archivo → Empresa/Parametros → Puesto → Permiso en menú / Permiso en sistema | core:listar_roles, permisos_sistema, permisos (listar_permisos, toggle_valor) | Reutilizar; mover menú |
| Archivo → Entidades → Cliente / Proveedor / etc. | cliente_administranet_service (parcial); resto por implementar | Actualizar / nuevo |
| Archivo → Productos / Variables / Procesos / Exportación / Configuración | Reportes y self_checkout leen tablas; sin ABM equivalentes en menú | Según MIGRACION_ADMINISTRANET_VB6_ANALISIS.md |
| Archivo → Salir | login logout_view | Actualizar: Cierra_Logueo_Vendedor |

### 6.6 Compras — Origen de datos para Factura de Compra (no “tipo de factura”)

En VB6 el selector que abre la factura de compra **no son “tipos de factura”** sino **orígenes desde donde se toman los datos** para armar la factura. El mismo formulario PFactura se abre con `TipoComprobante` = "Factura" | "Factura Remito" | "Factura OC" | "Factura Vale"; según ese valor cambia la UI (ListaRem, ListaVales) y la lógica de guardado.

| Origen (nomenclatura Synap) | En VB6 (CargaComprobantesP) | De dónde vienen los datos | Al guardar (además de cuentaproveedor) |
|-----------------------------|-----------------------------|---------------------------|----------------------------------------|
| **Manual** (sin origen) | keyFact → TipoComprobante "Factura" | Usuario carga ítems a mano en cuerpostockp | stock, stock_deposito, op_factura |
| **Desde Remito** | keyFactRem → "Factura Remito" | Remitos pendientes (REM); renglones con codmov_remito | remp_factp, estado remito Facturado; stock vinculado |
| **Desde Orden de compra** | keyFactOC → "Factura OC" | OC pendientes; renglones desde stockp con codmov_oc | stock, stock_deposito, stockp, saldo_pedido_proveedor, pedido_factura |
| **Desde Vale** | keyFactVALE → "Factura Vale" | Vales (en_vale_viaje, en_vale_factura_temp) | en_vale_factura, en_vale_viaje.estado |

**Regla en Synap:** En la pantalla de Factura de Compra no usar “tipo de factura” para estas opciones; usar **“Origen de los datos”** (Manual, Desde Remito, Desde Orden de compra, Desde Vale) y mostrar el panel correspondiente según la opción. Documentación detallada: [ORIGEN_DATOS_FACTURA_COMPRA_VB6.md](../compras/ORIGEN_DATOS_FACTURA_COMPRA_VB6.md).

---

## 7. Propuesta técnica ampliada

### 7.1 Session store acotado

- Fuente de verdad: `request.session["user"]` con opcionales `id_vendedor_usr`, `id_caja`, `id_punto_venta`, `nombre_cajero`. Helper `get_session_work_context(request)`; no exponer `id_sesion` en JSON ni barra de estado.

### 7.2 Barra de estado

- Ubicación: barra inferior en base_app o bloque en navbar. Contenido: fecha/hora vía GET `/api/core/fecha-servidor/`, empresa, sucursal, puesto, usuario, opcional "Cajero: X". Partial reutilizable (ej. `../../theme/templates/partials/status_bar.html`).

### 7.3 Fecha del servidor

- Endpoint `GET /api/core/fecha-servidor/` (JSON: fecha, hora, iso). Opcional inyectar en context para primera carga.

### 7.4 Logout unificado con Cierra_Logueo_Vendedor

- Flujo: leer id_sesion, base_empresa, id_vendedor_usr → si id_vendedor_usr, UPDATE viajantes (logueado='No', etc.) → UPDATE sesion.fechafin → session.flush(). Misma lógica desde navbar, timeout y APIs.

### 7.5 Auth-cashier y cierre de caja en TPV

- Auth-cashier: modal clave de caja; validar viajantes; si obliga_cierre_caja validar cierre previo. Logout-cashier: botón "Cerrar caja" → Cierra_Logueo_Vendedor y limpiar id_vendedor_usr en sesión. Movimientos de caja leen id_vendedor_usr de sesión.

### 7.6 Opcionales

- Menú desde BD (menurapido_* por id_puesto); API notificaciones; sesión única (registro y revocación); avisos configurables (banner/modal).

---

## 8. Riesgos de seguridad y mitigaciones

**Criterio de activación:** Todas las medidas de seguridad deben estar **activas cuando `ENVIRONMENT=production`** (o `produccion` en .env). En desarrollo se pueden relajar solo cookies/HTTPS; autorización y auditoría aplican en todos los entornos. Usar variable tipo `IS_PRODUCTION = (ENVIRONMENT == 'production' or os.environ.get('ENVIRONMENT') == 'produccion')`. (Variable en [settings.py](../../django_project/settings.py).)

- **8.1 Sesión y cookies:** Con ENVIRONMENT=production: SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SECURE, SESSION_COOKIE_SAMESITE = 'Lax'. Regenerar session key tras login.
- **8.2 Identificadores sensibles:** No enviar id_sesion al cliente; base_empresa siempre desde sesión en APIs; barra de estado sin base_empresa ni IDs internos.
- **8.3 Multi-tenant (base_empresa) e IDOR:** base_empresa siempre desde sesión autenticada; query/body solo hint para UX. Helper único `get_base_empresa_for_request(request)`.
- **8.4 Clave de caja:** HTTPS; no loguear ni guardar clave; valorar hash en BD.
- **8.5 Auditoría:** Registrar logout y cierre de caja (user_id, id_sesion/id_caja, timestamp, IP).
- **8.6 Barra de estado y APIs contexto:** Devolver solo nombres (empresa, sucursal, cajero); no id_sesion, base_empresa, id_vendedor_usr en JSON frontend.
- **8.7 CSRF y XSS:** CsrfViewMiddleware y {% csrf_token %}; evitar |safe con datos de usuario; limitar @csrf_exempt.
- **8.8 Inyección SQL:** Siempre parámetros preparados (cursor.execute(sql, [params])).

---

## 9. Mejores prácticas ERP no contempladas

- **Sesión (OWASP):** Regenerar ID tras login; timeouts; re-auth para acciones críticas; límite sesiones concurrentes.
- **Multi-tenant (OWASP):** Tenant desde sesión; prefijo tenant en caché; logs con contexto tenant.
- **Caja/TPV:** Segregación de funciones (cajero vs supervisor); controles "No Sale" y anulaciones; auditoría movimientos de caja (append-only).
- **Auditoría:** Eventos críticos (login, logout, auth-cashier, cierre caja); inmutabilidad y retención; revisión accesos privilegiados.

### 9.5 Resumen de adopción

- **Criterio:** Seguridad estricta (cookies, HTTPS) cuando **ENVIRONMENT=production**.
- **Inmediato:** Logout con Cierra_Logueo_Vendedor; no exponer id_sesion/base_empresa; cookies seguras en producción; base_empresa desde sesión.
- **Corto plazo:** Helper get_base_empresa_for_request; auditoría logout/cierre caja; validación tenant en rutas MySQL.
- **Opcional:** Sesión única; re-auth cierre caja; segregación permisos caja/supervisor; audit trail; prefijo tenant en caché.
