# Manual de usuario – Módulo Compras

Este manual describe el uso del módulo Compras en Synap: **captura y expedientes** (flujo Synap con documento y API), **pantalla única de Factura de Compra** (Facturación), listado de proveedores (hub), Remito de Compra, y accesos a Cuenta Corriente e imputación. La facturación clásica y el hub replican AdministraNET (VB6) para convivencia sobre la misma base MySQL; el flujo de expedientes vive en Synap (PostgreSQL).

**Requisitos:** Usuario con permiso **compras.ver** (para Captura y expedientes, Facturación y listado) o **compras.crear** (para Remito de Compra). **Empresa activa** seleccionada en sesión. Sin empresa activa, el sistema redirige al dashboard.

**Referencias:** [MIGRACION_HUB_COMPROBANTES_STOCK.md](MIGRACION_HUB_COMPROBANTES_STOCK.md), [ORIGEN_DATOS_FACTURA_COMPRA_VB6.md](../compras/ORIGEN_DATOS_FACTURA_COMPRA_VB6.md), [CONVIVENCIA_VB6_DJANGO_LEGACY_DB.md](CONVIVENCIA_VB6_DJANGO_LEGACY_DB.md).

---

## 1. Acceso al módulo

- Desde la barra de navegación de Synap, hacer clic en **Compras**.
- Submenú:
  - **Expedientes captura** → listado de expedientes del flujo Synap filtrados por empresa activa en sesión (`/compras/captura/expedientes/`). Desde ahí podés abrir **Revisar** si tenés permiso de edición del módulo captura.
  - **Captura y expedientes** → pantalla para crear expediente, subir foto/PDF y continuar el workflow (`/compras/captura/movil/`). Requiere el mismo permiso que Facturación (**compras.ver**).
  - **Facturación** → pantalla única para cargar Factura de Compra (proveedor predictivo, origen de los datos, Ver Cuenta Corriente, Agregar Proveedor, Informes).
  - **Listado de proveedores** → listado de proveedores y acciones por fila (hub).
  - **Remito de Compra** → formulario de Remito de Compra.

Alternativa: **Stock** → **Comprobantes de compra** → **Facturación** o **Listado de proveedores**.

---

## 2. Pantalla única: Facturación (Factura de Compra)

**Ruta:** Compras → Facturación (`/compras/facturacion/`).

Pantalla principal centrada en **cargar facturas**, no en listar proveedores.

### Elementos de la pantalla

- **Barra superior:** Título "Factura de Compra", botón **Ver Cuenta Corriente** (habilitado al seleccionar proveedor), **Agregar Proveedor**, **Informes**.
- **Origen de los datos:** Selector (pills) que indica **de dónde se toman los datos** para armar la factura (no el tipo de comprobante):
  - **Manual** — usuario carga renglones a mano.
  - **Desde Remito** — datos desde remitos de compra pendientes (panel en construcción).
  - **Desde Orden de compra** — datos desde OC pendientes (panel en construcción).
  - **Desde Vale** — datos desde liquidación de vales (panel en construcción).
- **Proveedor:** Campo **predictivo** (autocomplete): al escribir se buscan proveedores por código, nombre o CUIT; al elegir uno se guarda para el flujo y se habilita Ver Cuenta Corriente.
- **Encabezado:** Fecha comprobante, fecha registro, nro. suc., nro. comprobante, detalle.
- **Cuerpo:** Renglones (tabla artículo, cantidad, precio). El guardado vía legacy_db se implementará en la siguiente iteración.
- **Pie:** Subtotal, IVA, total.

Si se accede desde el **Listado de proveedores** eligiendo la acción Factura, se redirige a esta pantalla con el proveedor ya preseleccionado.

---

## 3. Hub: Listado de proveedores

**Ruta:** Compras → Listado de proveedores (`/compras/comprobantes-proveedor/`).

### Qué muestra

- **Filtros:** Buscar (texto), tipo de búsqueda (Incluye texto / Comienza con / Finaliza con), Sucursal (si el usuario no tiene permiso para ver todas las sucursales), cantidad por página (25 / 50 / 100).
- **Tabla de proveedores:** Código, Nombre, CUIT, IVA, Saldo. Clic en el encabezado de columna para ordenar por Código, Nombre, CUIT o Saldo.
- **Acciones por fila:** botones para cada proveedor:
  - **Factura** → Factura de Compra (validación CAI y OC).
  - **NC Dev** → Nota de Crédito por devolución.
  - **NC Desc** → Nota de Crédito por descuento (exige descuentos cargados).
  - **ND** → Nota de Débito.
  - **OP Imput.** → Orden de Pago por imputación (exige facturas pendientes y que nadie más tenga la OP abierta).
  - **OP Cuenta** → Orden de Pago a cuenta.
  - **Cta Cte** → Cuenta Corriente del proveedor.
  - **Imputación** → Imputar comprobantes a Orden de Pago.
  - **Desimputación** → Desimputar comprobantes.

### Validaciones (igual que en AdministraNET)

Antes de abrir un comprobante se comprueba:

- **Factura:** CAI del proveedor vigente; si el proveedor exige Orden de Compra para factura, se muestra mensaje y no se abre.
- **Orden de Pago (imputación o a cuenta):** Que otro usuario no tenga abierta la OP del mismo proveedor; para imputación, que existan facturas para imputar.
- **NC Descuento:** Que existan descuentos cargados para el proveedor.
- **Imputación:** Que existan facturas/comprobantes para imputar.

Si alguna validación falla, se muestra un mensaje en español y no se redirige al formulario.

### Formularios en construcción

Al elegir **Factura**, se redirige a la **pantalla única Facturación** (`/compras/facturacion/`) con el proveedor preseleccionado. Al elegir OP, NC, ND, Cta Cte, Imputación o Desimputación, se abre la pantalla correspondiente (algunas en construcción). La persistencia se irá implementando con la misma lógica que en AdministraNET (tablas y reglas compartidas).

---

## 4. Remito de Compra

**Ruta:** Compras → Remito de Compra (`/compras/remito-compra/`).

Formulario operativo para cargar remitos de compra: cabecera (proveedor, depósito, fechas, importes), renglones (artículo, cantidad, depósito), y opción de importar desde Orden de Compra o Factura. Al guardar se generan los movimientos de stock según la configuración del usuario (depósito por defecto, por artículo, etc.). Requiere permiso **compras.crear** (o el asignado al ítem de menú).

---

## 5. Permisos y visibilidad del menú

| Permiso        | Uso                                                                 |
|----------------|---------------------------------------------------------------------|
| **compras.ver**   | Ver menú Compras, Captura y expedientes, Facturación (pantalla única) y Listado de proveedores (hub). |
| **compras.crear** | Registrar compras (Remito de Compra y, cuando estén implementados, Factura, OP, NC, ND). |

Si no ve el menú **Compras** en la barra:

1. Verificar que su **puesto** tenga asignado el permiso **compras.ver** (Archivo → Puesto → Permiso en sistema).
2. Si el permiso **compras.ver** no aparece en la lista al editar el puesto, ejecutar la sincronización de permisos Synap (comando `sync_synap_permissions_to_adminet` o volver a iniciar sesión si está activo el auto-sync).
3. Cerrar sesión y volver a entrar para refrescar permisos.

El módulo Compras no se activa desde Module Management; siempre está disponible si el usuario tiene el permiso correspondiente.

---

## 6. Plantillas creadas

- `factura_compra_captura/lista_expedientes.html` — Listado web de expedientes (empresa de sesión), enlace a revisión y a nueva captura.
- `factura_compra_captura/captura_movil.html` — Captura y expedientes: misma base que el resto de Synap (`base_app.html`), tarjeta y formulario alineados al módulo Compras; crear expediente y subir documento vía API.
- `compras/factura_compra.html` — Pantalla única Factura de Compra (Facturación): proveedor predictivo, origen de los datos, encabezado/cuerpo/pie.
- `compras/hub_comprobantes.html` — Listado de proveedores y acciones.
- `compras/comprobante_en_construccion.html` — Pantalla “En construcción” para Factura, OP, NC, ND, Cta Cte, Imputación, Desimputación.
- `compras/remito_compra_form.html` — Formulario Remito de Compra.
- `compras/lista_comp_remito.html` — Lista de comprobantes para importar en Remito.

---

## Referencias

- [MIGRACION_HUB_COMPROBANTES_STOCK.md](MIGRACION_HUB_COMPROBANTES_STOCK.md)
- [ORIGEN_DATOS_FACTURA_COMPRA_VB6.md](../compras/ORIGEN_DATOS_FACTURA_COMPRA_VB6.md)
- [INVENTARIO_INGENIERIA_INVERSA_CARGA_COMPROBANTES_P.md](INVENTARIO_INGENIERIA_INVERSA_CARGA_COMPROBANTES_P.md)
- [CONVIVENCIA_VB6_DJANGO_LEGACY_DB.md](CONVIVENCIA_VB6_DJANGO_LEGACY_DB.md)
