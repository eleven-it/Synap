# Campos del formulario de usuario: módulos AdministraNET y propuesta de tabs en Synap

**Origen:** Formulario "Modificar usuario" (CargaUsuario.frm en VB6). Todos los campos se editan en ese único formulario; en VB6 cada campo es consumido después por distintos módulos (TPV, Caja, Reportes, etc.).

**Objetivo:** Asignar cada opción al módulo/funcionalidad que la utiliza en AdministraNET (según referencias en formularios VB6 y tablas) y proponer una separación en pestañas en Synap para mejorar la UX.

---

## 1. Asignación campo → módulo en AdministraNET (VB6)

Basado en [tablas/usuarios.md](tablas/usuarios.md), referencias a CargaUsuario.frm, caja_abm, deposito, punto_venta, viajantes, y docs de self_checkout/reports.

| Campo (tabla `usuarios`) | Formulario(s) VB6 que lo consumen / uso | Módulo funcional |
|--------------------------|------------------------------------------|-------------------|
| **Empresa** (id_empresa / nombre) | CargaUsuario (solo lectura), datosempresa | Organización |
| **Sucursal** (id_sucursal) | CargaUsuario, Logi_Gestion, CargaMovCaja, TPV, punto_venta_usr | Organización / TPV / Caja |
| **Usuario** (cod_usuario) | Login, ABMUsuarios, todos los que filtran por usuario | Identidad / Permisos |
| **Nombre / Apellido** | ABMUsuarios, mensaj_carga, listados | Perfil |
| **Puesto** (id_puesto) | ABMUsuarios, permisos por puesto (menurapido, CargaPermiso) | Permisos / Perfil |
| **Contraseña** | Login, CargaUsuario (AES_ENCRYPT) | Seguridad |
| **Tipo Búsqueda** (tipo_busq) | Comportamiento de búsqueda en grillas (productos, clientes) | Comportamiento UI / Búsqueda |
| **Búsqueda defecto** (tipo_busqueda_defecto) | Mismo: criterio por defecto (incluye texto, exacto) | Comportamiento UI / Búsqueda |
| **Supervisor venta** (permiso_supervisor_venta) | Ventas, autorizaciones, supervisión de operaciones | Ventas / Permisos |
| **Vendedor de ecommerce** (vendedor_web) | Módulo e-commerce (pedidos web, publicaciones) | E-commerce |
| **Reportes localmente** (utiliza_reporte_local, ruta_reporte_local) | Reportes (Crystal u otro), ruta local de generación/almacenamiento | Reportes |
| **Certificados localmente** (utiliza_certificado_local, ruta_certificado_local) | Facturación electrónica (AFIP), certificados .crt/.key | FE AFIP |
| **Carpeta documentos** (carpeta_documentos) | Almacenamiento de documentos del usuario | Documentos / Archivos |
| **Entrega default** (entrega_defecto) | Pedidos, remitos (forma de entrega por defecto: "Envía por despacho", etc.) | Logística / Pedidos |
| **Punto de Venta** (id_punto_venta, pv) | TPV.frm, punto_venta_usr, Caja, comprobantes | TPV / Comprobantes |
| **Nro Suc. Cob** (pvc) | Cobranza / sucursal de cobranza | TPV / Cobranza |
| **Anulado** (baja_usuario) | Login (no lista bajas), ABMUsuarios, filtros | Estado del usuario |
| **Vendedor** (CodViajante) | Cliente.frm, Info_Venta, CuentaCliente, comp_ped, Visualiza_TPV, facturas, NC, liquidación comisiones | Ventas / Viajantes / Comisiones |
| **Depósito general** (id_deposito) | Stock, deposito_usr, pedidos, remitos, CargaArticulo | Stock / Depósitos |
| **Caja efectivo cobranza** (id_caja) | CargaMovCaja, Caja_Control_Sucursales, TPV (caja del cajero) | Caja / TPV |
| **Caja efectivo rendición** (id_caja_deposito) | Movimientos de caja, rendición a caja central | Caja |
| **Caja cheque cobranza** (id_caja_cheque) | Caja (cheques) | Caja |
| **Caja cheque rendición** (id_caja_cheque_deposito) | Caja (cheques) | Caja |
| **Caja tarjeta cobranza** (id_caja_tarjeta) | Caja (tarjetas), TPV | Caja / TPV |
| **Caja tarjeta rendición** (id_caja_tarjeta_deposito) | Caja (tarjetas) | Caja |
| **Resolución Principal** (resol_principal) | Configuracion / ventana principal VB6 | UI (legacy, no aplica web) |
| **Tipo de fuente** (fuente_nombre) | Apariencia formularios VB6 | UI (reinterpretar en web) |
| **Tamaño fuente** (fuente_tamano) | Apariencia formularios VB6 | UI (reinterpretar en web) |
| **Color formulario** (color_formulario) | Tema visual formularios | UI / Tema |
| **Botón formulario** (tipo_boton) | Estilo botones VB6 | UI (legacy, no aplica web) |
| **Zoom reportes** (zoom_reportes) | Visor de reportes (Crystal) | Reportes / UI |

---

## 2. Agrupación por módulo (resumen)

| Módulo / Área | Campos |
|---------------|--------|
| **Organización** | Empresa (solo lectura), Sucursal |
| **Perfil e identidad** | Usuario (código), Nombre, Apellido, Puesto, Contraseña, Valid. Contraseña, Anulado |
| **Permisos / roles** | Puesto, Supervisor venta, Vendedor de ecommerce |
| **Búsqueda / comportamiento** | Tipo Búsqueda, Búsqueda defecto |
| **TPV / Comprobantes** | Punto de Venta, Nro Suc. Cob |
| **Ventas / Viajantes** | Vendedor (CodViajante) |
| **Stock / Depósitos** | Depósito general |
| **Caja** | Caja efectivo cobranza, Caja efectivo rendición, Caja cheque cobranza/rendición, Caja tarjeta cobranza/rendición |
| **Logística / Pedidos** | Entrega default |
| **Reportes** | Reportes localmente (Sí/No + ruta), Zoom reportes |
| **FE AFIP** | Certificados localmente (Sí/No + ruta) |
| **Documentos** | Carpeta documentos |
| **UI / Preferencias** | Resolución Principal, Tipo de fuente, Tamaño fuente, Color formulario, Botón formulario |

---

## 3. Propuesta de tabs para Synap (mejor UX)

Separar el formulario monolítico en pestañas por contexto de uso. Nombres orientados a negocio para que el administrador encuentre rápido cada bloque.

| Tab | Título sugerido | Campos incluidos | Justificación |
|-----|-----------------|------------------|---------------|
| **1** | **Perfil** | Empresa (solo lectura), Sucursal, Usuario (código), Nombre, Apellido, Puesto, Contraseña, Valid. Contraseña, Anulado | Lo que identifica al usuario y su estado; lo que se cambia con más frecuencia (nombre, contraseña). |
| **2** | **Operación y ventas** | Punto de Venta, Nro Suc. Cob, Vendedor (viajante), Supervisor venta, Vendedor de ecommerce, Depósito general, Entrega default, Tipo Búsqueda, Búsqueda defecto | Todo lo que define cómo opera el usuario: PV, vendedor asignado, depósito, entrega y comportamiento de búsqueda. |
| **3** | **Cajas** | Caja efectivo cobranza, Caja efectivo rendición, Caja cheque cobranza, Caja cheque rendición, Caja tarjeta cobranza, Caja tarjeta rendición | Asignación de fondos por tipo de medio; crítico para conciliación y TPV. |
| **4** | **Rutas y archivos** | Reportes localmente (Sí/No + ruta), Certificados localmente (Sí/No + ruta), Carpeta documentos | Rutas locales y uso de reportes/certificados; en web parte puede ser irrelevante o reemplazada por config global. |
| **5** | **Apariencia** (opcional o colapsable) | Resolución Principal, Tipo de fuente, Tamaño fuente, Color formulario, Botón formulario, Zoom reportes | Preferencias de UI; según [USUARIO_OPCIONES_OTROS_ANALISIS.md](USUARIO_OPCIONES_OTROS_ANALISIS.md) varios son legacy y en Synap solo tendrían sentido tema + quizá zoom reportes. |

**Detalles de implementación sugeridos:**

- **Tab Perfil:** Siempre visible; en edición del usuario Supervisor solo esta pestaña con contraseña editable (resto readonly).
- **Tab Operación y ventas:** Agrupa todo lo que “dónde y cómo trabaja” el usuario (PV, vendedor, depósito, entrega, búsqueda).
- **Tab Cajas:** Una sola sección “Asignación de cajas” con los seis combos; ayuda a no mezclar con datos de perfil.
- **Tab Rutas y archivos:** En entorno web se puede ocultar o simplificar (ej. solo “Carpeta documentos” si se usa; reportes/certificados pueden ser config de sucursal o servidor).
- **Tab Apariencia:** O bien se oculta y los campos se mantienen solo en DB por compatibilidad, o se muestra con etiqueta “Preferencias de interfaz (heredadas)” y solo Tema + Zoom reportes si el producto los usa.

---

## 4. Referencias

- Tabla `usuarios`: [docs/general/tablas/usuarios.md](tablas/usuarios.md).
- CargaUsuario y tablas relacionadas: [tablas/caja_abm.md](tablas/caja_abm.md), [tablas/deposito.md](tablas/deposito.md), [tablas/punto_venta.md](tablas/punto_venta.md), [tablas/viajantes.md](tablas/viajantes.md).
- Caja y usuarios: [docs/self_checkout/CAJA_ADMINISTRANET_PROCESOS.md](../self_checkout/CAJA_ADMINISTRANET_PROCESOS.md).
- Opciones “Otros” (UI): [USUARIO_OPCIONES_OTROS_ANALISIS.md](USUARIO_OPCIONES_OTROS_ANALISIS.md).
- Formularios actuales Synap: `core/templates/core/usuarios_crear.html`, `usuarios_editar.html`. **Implementación:** ambos formularios usan 5 pestañas (Perfil, Operación y ventas, Cajas, Rutas y archivos, Apariencia) con Alpine.js; roles ARIA `tablist`/`tab`/`tabpanel` para accesibilidad.
