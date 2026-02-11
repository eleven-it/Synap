# Análisis Principal.frm: brechas de migración, FODA y mejoras

**Plan de referencia:** migración/refactor de Principal.frm (VB6) a Synap. Todo el desarrollo relacionado con shell, sesión, TPV y caja debe ajustarse a este documento.

---

## 1. Brechas de migración / refactor (qué falta en Synap)

Comparando [Principal.frm (informe)](../reports/docs/PRINCIPAL_FRM_INFORME_DETALLADO.md) con el shell actual de Synap ([base_app.html](../theme/templates/base_app.html), [context_processors](../core/context_processors.py), [login logout](../login/views.py), [APPS_MENU](../core/utils/utils.py)):

| Responsabilidad en Principal | Estado en Synap | Acción sugerida |
| --------------------------- | --------------- | ---------------- |
| **Variables de sesión globales** (empresa, sucursal, puesto, fecha, caja, PV, id_vendedor_usr, permisos, módulos) | Parcial: `session_user`, `empresa_activa`, `branch_activa`, `permisos_usuario` en context. No hay: fecha servidor, id_caja, id_punto_venta, id_vendedor_usr, flags de licencia/módulo. | Centralizar en sesión Django o en un "session store" (por request/cache) y exponer vía context o API; opcionalmente modelo/cache por usuario. |
| **Barra de estado (StatusBar)** con Fecha, Hora, Empresa, Sucursal, Puesto, Usuario | No existe. Navbar muestra logo y menú, no fecha/hora ni datos de contexto. | Añadir barra inferior o zona en navbar con fecha/hora (servidor), empresa, sucursal, puesto, usuario (y opcional cajero si TPV). |
| **Fecha del servidor (Control_Fecha)** | No se expone. Cada reporte/consulta puede usar `NOW()` en MySQL pero no hay "fecha de trabajo" única en UI. | Endpoint o context con fecha/hora del servidor (MySQL o servidor app) y mostrarla en shell; opcional "fecha de trabajo" configurable. |
| **Menú lateral por puesto (menurapido_grupo / menurapido_item)** | No. Synap usa `APPS_MENU` estático en código + permisos; no lee tablas `menurapido_*` de MySQL. | Decisión: mantener menú en código o migrar a BD (menurapido_* o modelos Django) para que por puesto se definan grupos/ítems. |
| **Cierre de sesión completo (Salida)** | Parcial: [logout_view](../login/views.py) hace UPDATE `sesion.fechafin` en MySQL y `session.flush()`. **No** llama a Cierra_Logueo_Vendedor. | En logout, si existe `id_vendedor_usr` en sesión, ejecutar UPDATE `viajantes` SET logueado='No', detalle_logueo=NULL, ip_logueo=NULL antes de flush. |
| **Autenticación cajero al abrir TPV** (clave_caja, viajantes) | No implementada. Self-checkout tiene entrada en menú pero no flujo "clave de caja" ni sesión de cajero. | Implementar según [TPV_CAJA_AUTENTICACION_Y_OPERACIONES](../reports/docs/TPV_CAJA_AUTENTICACION_Y_OPERACIONES.md): auth-cashier, logout-cashier, sesión id_vendedor_usr. |
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
- **Optimizaciones:** Session store acotado, endpoint fecha servidor, menú en código + filtro BD, logout unificado.
- **Seguridad:** Activar cuando **ENVIRONMENT=production** (o produccion). Ver secciones 7 y 8.

---

## 6. Propuesta técnica ampliada

### 6.1 Session store acotado

- Fuente de verdad: `request.session["user"]` con opcionales `id_vendedor_usr`, `id_caja`, `id_punto_venta`, `nombre_cajero`. Helper `get_session_work_context(request)`; no exponer `id_sesion` en JSON ni barra de estado.

### 6.2 Barra de estado

- Ubicación: barra inferior en base_app o bloque en navbar. Contenido: fecha/hora vía GET `/api/core/fecha-servidor/`, empresa, sucursal, puesto, usuario, opcional "Cajero: X". Partial reutilizable (ej. `theme/templates/partials/status_bar.html`).

### 6.3 Fecha del servidor

- Endpoint `GET /api/core/fecha-servidor/` (JSON: fecha, hora, iso). Opcional inyectar en context para primera carga.

### 6.4 Logout unificado con Cierra_Logueo_Vendedor

- Flujo: leer id_sesion, base_empresa, id_vendedor_usr → si id_vendedor_usr, UPDATE viajantes (logueado='No', etc.) → UPDATE sesion.fechafin → session.flush(). Misma lógica desde navbar, timeout y APIs.

### 6.5 Auth-cashier y cierre de caja en TPV

- Auth-cashier: modal clave de caja; validar viajantes; si obliga_cierre_caja validar cierre previo. Logout-cashier: botón "Cerrar caja" → Cierra_Logueo_Vendedor y limpiar id_vendedor_usr en sesión. Movimientos de caja leen id_vendedor_usr de sesión.

### 6.6 Opcionales

- Menú desde BD (menurapido_* por id_puesto); API notificaciones; sesión única (registro y revocación); avisos configurables (banner/modal).

---

## 7. Riesgos de seguridad y mitigaciones

**Criterio de activación:** Todas las medidas de seguridad deben estar **activas cuando `ENVIRONMENT=production`** (o `produccion` en .env). En desarrollo se pueden relajar solo cookies/HTTPS; autorización y auditoría aplican en todos los entornos. Usar variable tipo `IS_PRODUCTION = (ENVIRONMENT == 'production' or os.environ.get('ENVIRONMENT') == 'produccion')`.

- **7.1 Sesión y cookies:** Con ENVIRONMENT=production: SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SECURE, SESSION_COOKIE_SAMESITE = 'Lax'. Regenerar session key tras login.
- **7.2 Identificadores sensibles:** No enviar id_sesion al cliente; base_empresa siempre desde sesión en APIs; barra de estado sin base_empresa ni IDs internos.
- **7.3 Multi-tenant (base_empresa) e IDOR:** base_empresa siempre desde sesión autenticada; query/body solo hint para UX. Helper único `get_base_empresa_for_request(request)`.
- **7.4 Clave de caja:** HTTPS; no loguear ni guardar clave; valorar hash en BD.
- **7.5 Auditoría:** Registrar logout y cierre de caja (user_id, id_sesion/id_caja, timestamp, IP).
- **7.6 Barra de estado y APIs contexto:** Devolver solo nombres (empresa, sucursal, cajero); no id_sesion, base_empresa, id_vendedor_usr en JSON frontend.
- **7.7 CSRF y XSS:** CsrfViewMiddleware y {% csrf_token %}; evitar |safe con datos de usuario; limitar @csrf_exempt.
- **7.8 Inyección SQL:** Siempre parámetros preparados (cursor.execute(sql, [params])).

---

## 8. Mejores prácticas ERP no contempladas

- **Sesión (OWASP):** Regenerar ID tras login; timeouts; re-auth para acciones críticas; límite sesiones concurrentes.
- **Multi-tenant (OWASP):** Tenant desde sesión; prefijo tenant en caché; logs con contexto tenant.
- **Caja/TPV:** Segregación de funciones (cajero vs supervisor); controles "No Sale" y anulaciones; auditoría movimientos de caja (append-only).
- **Auditoría:** Eventos críticos (login, logout, auth-cashier, cierre caja); inmutabilidad y retención; revisión accesos privilegiados.

### 8.5 Resumen de adopción

- **Criterio:** Seguridad estricta (cookies, HTTPS) cuando **ENVIRONMENT=production**.
- **Inmediato:** Logout con Cierra_Logueo_Vendedor; no exponer id_sesion/base_empresa; cookies seguras en producción; base_empresa desde sesión.
- **Corto plazo:** Helper get_base_empresa_for_request; auditoría logout/cierre caja; validación tenant en rutas MySQL.
- **Opcional:** Sesión única; re-auth cierre caja; segregación permisos caja/supervisor; audit trail; prefijo tenant en caché.
