# Inventario: Presupuesto de ventas (AdministraNET VB6 → Synap)

**Ámbito:** circuito **Presupuesto de cliente** (tipo **PRE** en `comp_ped`), **no** confundir con **Presupuesto de compra** (`PPresupuesto.frm` / menú Compras `keyPreCompra`).

**Código fuente:** `administranet_vb6/` en el repositorio Synap (revisión incluyendo subdirectorios principales).

**Relacionado:** `docs/general/tablas/*.md` (uso SQL por formulario), `docs/self_checkout/STOCKP_VB6_PROCEDIMIENTOS_GUARDADO.md` (persistencia `stockp`).

**Especificación cerrada** (proceso, tablas, validaciones, exclusiones CRM y ERP proyecto, permisos por puesto, módulo Reportes sin Crystal): [SPEC_PRESUPUESTO_VENTAS_SYNAP.md](SPEC_PRESUPUESTO_VENTAS_SYNAP.md).

---

## 1. Estructura relevante del árbol `administranet_vb6`

| Ruta | Contenido |
|------|-----------|
| `Formularios/` | Formularios `.frm`/`.frx` del ERP (incluye copias `* 3.frm`, carpetas `Copia Codigos Formularios`, `Informes`, `Restauracion`, `Formulario Base`, etc.). |
| `Modulos/` | `.bas` compartidos; **`Visualiza.bas`** (`VB_Name = Visualiza_Reimprime`) centraliza visualización/reimpresión y **`Visualizar_PRE`**. |
| `Modulos de clase/` | Clases `.cls` (menú ListView, etc.). |
| `Formularios Gestión de Clientes/` | Proyecto satélite `GestionClientes_administraNET.vbp` (alcance aparte). |
| `Plantillas my.ini/` | Plantillas servidor MySQL (no lógica PRE). |
| `administraNET.vbp` / `administraNET 2.vbp` | Proyecto VB6: referencias a `Presupuesto.frm`, `CargaComprobantesPed.frm`, `Visualiza_Presupuesto.frm`. |

**Nota:** coexisten archivos duplicados (`Presupuesto 3.frm`, etc.). La referencia del proyecto principal es `Formularios\Presupuesto.frm` en `administraNET.vbp`.

---

## 2. Punto de entrada en menú (shell MDI)

**Archivo:** `Formularios/Principal.frm`

| Clave menú | Procedimiento | Efecto |
|-------------|---------------|--------|
| `keyPre` (Gestión → Ventas → Presupuesto) | `Menu_Presupuesto_Venta` | `Control_Sesiones`, `Control_Fecha`, abre **`CargaComprobantesPed`** con `Caption = " Presupuestos"` y visibilidad de ítems de menú: Comprobantes visible, **Presupuesto** visible, Pedido/Remitos/Parte diario ocultos según índices SmartMenu. |
| `General_Consulta_Presupuestos` (atajo/config) | `Menu_Consultas_Presupuestos` | Abre **`ConsultaComprobante`** en modo ventas, filtra comprobante **PRE**, ejecuta búsqueda. |

**Separación explícita compras:** `keyPreCompra` → `Menu_Presupuesto_Compra` usa **`CargaComprobantesP`** y **`PPresupuesto`**, no este flujo.

---

## 3. Hub de carga: `CargaComprobantesPed.frm`

**Caption por defecto:** `Presupuestos / Pedidos / Remitos` (el `Principal` lo fuerza a `" Presupuestos"` solo en modo presupuesto).

**Control principal:** `MenuPrincipal` (SmartMenuXP), `GridTodos` (clientes), `DataCliente`, búsqueda, `TipoComprobante` (Sistema/talonario).

**Menú cuando `Caption = " Presupuestos"`** (resumen):

- **Archivo:** copiar celda, salir.
- **Comprobantes:** `keyPRE` Presupuesto (F2), `keyPED` Pedido, `keyREM` Remito, `keyFactPedPend` remito por pedidos pendientes, `keyPED_PD` pedido desde parte diario.
- **Acciones:** cuenta corriente cliente, ABM cliente / rápido / editar rápido, domicilios.
- **Informes:** `keyInfCobranza` visualizar.

**`MenuPrincipal_Click` → `Case "keyPRE"`** (Presupuesto ventas):

- Valida cliente seleccionado (`GridTodos`) y estado **Activo**.
- Evita tener **Pedido** y **Presupuesto** abiertos a la vez (mensaje y `Unload`).
- Asigna a **`Presupuesto`**: `CodigoCliente`, `Cliente`, `ID_Cat_Contribuyente`, datos de carga (`id_cliente_carga`, `tipo_comp_carga`, `id_cv_carga`, descuentos, lista de precio), viajante desde `Viajantes`, `Visualizar_Comprobante = "No"`.
- Opcional: modal **`Avisos`** si `Principal.visualiza_aviso` y cliente con aviso.
- **`Presupuesto.Inicial`** → **`Presupuesto.Show`**.

**Otros modos del mismo form:** con `Caption = " Pedidos"` o `" Remitos de Venta"` se muestran/ocultan ítems (misma shell, distinta operativa).

---

## 4. Formulario de emisión: `Presupuesto.frm`

**Caption:** `Presupuesto`.

**OCX / controles típicos:** `tidate8`, `senxpctl` (OsenXPButton), `SmartMenuXP`, `TAB32X30`, `MSADODC`, `todg8` (TrueOleDBGrid80), `MSDATLST`, `MSCOMCTL`.

**Procedimientos públicos / piezas clave** (lista no exhaustiva; el `.frm` supera 10k líneas):

| Procedimiento | Rol |
|---------------|-----|
| `Inicial` | Arranque de pantalla, datos de sesión, grillas, permisos. |
| `Elimina_Temporal` | Limpieza buffers usuario (`cuerpostockpe`, etc.). |
| `Guardar` / `Aceptar_Click` / `AceptarStock_Click` | Persistencia del comprobante (vía `stockp` / cabecera según diseño documentado en STOCKP). |
| `CalculoTotales`, `Sub_Total_0`, `Calculo_descuento_importe` | Totales e impuestos. |
| `Menu` / `MenuPrincipal_Click` | Menú interno del formulario (informes, cotizador, etc.). |
| `btnLlamada_Click` | CRM / llamada comercial (relacionado con `crm_pre_llamada`). |
| `Modificar_Click`, `modificacion_comp` | Flujo modificación comprobante ya emitido. |
| `Validacion_Comp`, `Validacion_Descuento_*` | Reglas de negocio. |
| `ReglaPrecio`, `RPrecioM`, `RPrecioG` | Listas y políticas de precio. |
| `Calculo_Stock_Actual`, `Calculo_Pedido_Cliente_Pendiente`, `Calculo_Disponible` | Stock y disponibilidad. |
| `Cambia_Display_Bulto`, `tipo_unidad_bulto_*` | Bulto cerrado / display (flags `Principal.utiliza_bulto_cerrado`, etc.). |

**Integración listas:** `Lista_Articulo_Cliente` con `Formulario_Origen = "Presupuesto"` (en `Pedido.frm` también se usa origen Presupuesto para búsqueda de artículos).

---

## 5. Formulario de visualización / modificación: `Visualiza_Presupuesto.frm`

Misma familia de controles que `Presupuesto.frm`. Incluye **`Trazabilidad_Click`**, **`Guardar`**, **`Inicial`**, **`Elimina_Temporal`**, totales, grillas, menú, permisos de renglón, etc.

**Uso:** consulta y, si permisos y estado lo permiten, modificación de un PRE ya grabado (sincronización `stockp` ↔ `cuerpostockpe` documentada en Synap).

---

## 6. Módulo `Modulos/Visualiza.bas` (`Visualiza_Reimprime`)

**`Public Sub Visualizar_PRE(CodMov As Double, accion_menu As String)`**

- Lee cabecera desde **`comp_ped`** + **`cliente`** + **`usuarios`** por `CodigoMovimiento`.
- Según `accion_menu` (**Visualizar** / **Modificar**): fija `Visualiza_Presupuesto.ModTalonario`; si **Modificar**, valida estado **Facturado** (solo detalle), borra `cuerpostockpe`/`percep_cli_temp` del usuario con `visualiza = 'Si'`, y **bloquea si otro usuario** tiene renglones en `cuerpostockpe` para el mismo `CodigoMovimiento`.
- Copia líneas de **`stockp`** hacia **`cuerpostockpe`** (marcando `Visualiza = 'Si'`), con lógica de bulto/display, embalaje, impuesto interno, cotización dólar, marca, etc.
- Abre **`Visualiza_Presupuesto`** (flujo continúa en el propio `.bas` tras el fragmento citado).

**Otros callers de `Visualizar_PRE`:** `ConsultaComprobante.frm` (`Visualizar_PRE_PED`), `trz_trazabilidad.frm`, `Crm_CargaLlamada.frm`.

**`Principal.Visualizar_Presupuesto`** (en `Principal.frm`): variante que usa `DataConsulta` ya cargado y lógica equivalente (duplicación parcial respecto a `Visualiza.bas`; migración a Synap debe unificar criterios).

---

## 7. Consultas y anulaciones: `ConsultaComprobante.frm`

- Soporta **`Tipo_Menu = "Ventas"`** y **`"PRE-PED"`**.
- Comprobante **PRE:** visualización vía `Visualizar_PRE` / `Visualizar_PRE_PED`, anulación **`Anular_PRE_PED`**, reglas distintas si el menú es compras (`Visualizar_CompPRE` para PRE proveedor).

---

## 8. CRM

**`Formularios/Crm_Presupuesto_Llamada.frm`** — Caption: *Vinculación relación comercial y presupuesto*; grillas y datos CRM vinculados al PRE (tablas `crm_*` documentadas en `docs/general/tablas/crm_pre_llamada.md`, etc.).

**`Crm_CargaLlamada.frm`** puede invocar **`Visualizar_PRE`** desde una llamada (`CodigoMovimientoPre`).

---

## 9. Integración con Pedido

**`Pedido.frm`:** al generar pedido desde presupuesto, actualiza estado del presupuesto y graba relación en **`ped_presup`** (p. ej. `SELECT * FROM ped_presup WHERE id_ped_presup = 0` antes de `AddNew`) y uso de **`cuerpostockpe`** (comentarios y bloques ~4613–4737 según versión del `.frm`). **`tipo_busqueda = "Presupuesto"`** abre **`Lista_Comp_Gral`** con `TipoComprobante = "Presupuestos"` para elegir PRE.

**Permiso:** `Principal.modifica_pedido_presupuesto` controla visibilidad de **`Pedido.FrameBotones`** (botones que enlazan con presupuesto antes del pedido).

---

## 10. Trazabilidad

**`trz_trazabilidad.frm`:** incluye **`Visualizar_PRE_PED`** y llamadas a **`Visualizar_PRE`** para navegar el PRE desde la cadena de trazabilidad.

---

## 11. Informes en VB6 (Crystal) y equivalencia Synap

**Legacy (VB6):** **`Presupuesto.frm`:** `Lista_Informes_Click`, **`reporte_plantilla`** (`tipo_plantilla = 'Presupuesto'`); Crystal `comp_presupuesto.rpt` u otros según `Principal.RutaInformes`.

**Synap:** **no** se usa Crystal. Los PDF/imprimibles de comprobantes se implementan en el **módulo Reportes** (`reports`): definiciones por empresa, datos desde MySQL legacy. El Presupuesto es un **documento operativo** (como factura o remito), **no** un informe gerencial; debe **crearse** en ese módulo cuando el flujo lo requiera. Ver **§9** de `SPEC_PRESUPUESTO_VENTAS_SYNAP.md`.

**Aclaración:** `Principal.Reimprimir_PREP` actúa sobre **preparación de pedido** (`ped_prep`, reporte `comp_prepp_total.rpt`), **no** sobre el formulario Presupuesto ventas como tal (nombre engañoso).

---

## 12. Tablas MySQL núcleo (referencias en código)

| Tabla | Uso |
|-------|-----|
| `comp_ped` | Cabecera PRE/PED (join con `cliente` en consultas). |
| `stockp` | Renglones persistidos del movimiento. |
| `cuerpostockpe` | Buffer por usuario; `CodigoMovimiento = 1` en carga temporal; bandera `visualiza`. |
| `ped_presup` | Relación pedido ↔ presupuesto (cuando aplica). |
| `Viajantes` | Vendedor asignado al cliente. |
| `permisos_sistema` | Límites descuento, etc. |
| `percep_cli_temp` | Limpieza al editar PRE en modo modificación (`Visualiza.bas`). |
| `crm_pre_llamada` | CRM asociado al movimiento. |

Detalle de columnas y más tablas en `docs/general/tablas/` (búsqueda por `Presupuesto.frm` / `Visualiza_Presupuesto.frm`).

---

## 13. Registro en proyecto VB6

En **`administraNET.vbp`** (y variantes):

```text
Form=Formularios\CargaComprobantesPed.frm
Form=Formularios\Presupuesto.frm
Form=Formularios\Visualiza_Presupuesto.frm
```

**Compras (referencia cruzada):** `PPresupuesto.frm`, `Visualiza_PPresupuesto.frm` — **fuera del alcance** de este inventario salvo impacto en `comp_ped`/`TipoComprobante` en consultas globales.

---

## 14. Implicaciones para Synap

1. **Paridad de proceso:** selección cliente → cabecera PRE → renglones temporales → commit a `stockp` / `comp_ped`; visualización/edición vía copia a `cuerpostockpe` y controles de concurrencia (mismo `CodigoMovimiento`).
2. **Unificar** lógica duplicada entre **`Visualiza.bas`** y **`Principal.Visualizar_Presupuesto`** en un solo servicio Django si se migra.
3. **Permisos (prioridad alta):** reglas por **puesto** desde **`permisos_sistema`** (`IDPuesto` en sesión, equivalente a VB6), alineado con `AdministraNETPermisosSistemaService` y validaciones V1–V11 del SPEC; incluye `mod_item_pre_ped`, límites `lim_desc_*`, `cambia_cv`, listas, talonario, vendedor, etc.
4. **Sin módulo ERP proyecto en alcance Synap** para esta migración: no `erp_proyecto` ni campos de proyecto en cabecera como requisito de paridad (ver §1.5 del SPEC).
5. **UX:** la UI VB6 es referencia de flujo y datos, no de usabilidad obligatoria; ver **§1.4** del SPEC si conviene repensar pantallas.
6. **Informes:** en Synap el PDF/imprimible es una definición del **módulo Reportes** (documento operativo); no Crystal. Crear reporte Presupuesto según SPEC §9.

### 14.1 Formulario «Nuevo presupuesto» en Synap (HTML)

- Pantalla `ventas/presupuesto_nuevo.html`: **una sola hoja** continua (cabecera compacta + líneas + pie). **Cabecera de datos:** rejilla **3×2** (`sm:grid-cols-3`): fila 1 **Fecha \| Cliente \| Vendedor**; fila 2 **Vencimiento \| Lista de precio \| Cond. venta** (en pantallas estrechas se apila en una columna). **Paridad visual con informe VO** (`ventas-objetivos-vs-bo`): **Fecha** y **vencimiento** usan las mismas clases que `reports/includes/filters_period_bo_dual.html` (`bo-date-input synap-input`, píldora `rounded-full`, `min-w-[148px]`, `h-9`, `text-xs`, foco `ring-sky-400`). **Cliente**, **vendedor**, **lista de precio** y **cond. venta** usan el **mismo patrón y la misma lógica** que los filtros por etiquetas del dashboard de reportes: módulo compartido `reports/static/reports/js/tags_filter.mjs` (`initializeTagsFilter`), estructura `tags-filter-container` + `tags-chips` + `tags-input` + `tags-dropdown` (equivalente a `filters_bo_punto_venta_sucursales_depositos_clientes.html` y al detalle del dashboard). Cada campo tiene un `<select multiple>` oculto con opciones servidas por Django y un **hidden** para el valor único del POST: cliente → `codigo_cliente` (`#pre-cli-cod`); vendedor → `cod_viajante` (`#pre_viajante_hid`, opción vacía «Predeterminado (sesión)»); lista de precio → `lista_precio_ui` (`#pre_lista_hid`, opciones 0–6 costo / lista oficial / listas 1–5); cond. venta → `id_condventa` (`#pre_cond_hid`). **Cliente:** búsqueda remota vía API (`api_presupuesto_clientes_buscar`, ≥ 2 caracteres). **Vendedor** y **cond. venta:** opciones desde `viajantes` y `condiciones_venta` en contexto (sin JSON auxiliar). **Pie:** **observaciones** a la **izquierda** del bloque **Resumen** de importes (dos columnas desde `lg`). En la columna **Descuento** (y en descuento global del resumen), el conmutador **% \| $** y el valor comparten un único contorno **`.pre-dto-group`** (misma altura y `text-sm` que el resto de celdas). Tabla de líneas: **`table-fixed`** + `<colgroup>` (aprox. código 11 %, descripción 33 %, cantidad 6 %, precio unitario 9 %, descuento con toggle **%**|**$** 14 %, IVA % 5 %, IVA 8 %, subtotal 10 %, acción 4 %; `min-w-[48rem]`). Cabeceras de columnas: **CODIGO**, **DESCRIPCION**, **CANTIDAD**, **PRECIO UNITARIO**, **DESCUENTO**, **IVA %**, **IVA**, **SUBTOTAL**. Impuesto interno por ítem no tiene columna propia (sigue en `dataset` / totalización). **Depósito** oculto por fila = **1**. La vista **consulta** (`presupuestos/<id>/`) usa la **misma plantilla** en modo solo lectura (`solo_lectura`), con datos de `comp_ped` / `stockp` y sin JS de edición.
- **Modal de espera** (`#pre-busy-modal`): se muestra al buscar clientes, al buscar artículos por código y al enviar **Guardar** (textos en español).
- **Resumen** (pie compacto): **Importe base**; **Descuento global** con toggle **%** / **$** y campo visible — POST **`desc_global_pct_1`** oculto (porcentaje equivalente; modo `$` convierte desde importe); **`desc_global_pct_2`** oculto vacío; filas **IVA** / **impuestos internos** dinámicas (solo si hay importe; escalado si hay dto. global); bloque **percepciones** reservado oculto hasta motor; **Descuentos totales** (renglón + global); **Total**.
- Lectura de renglones PRE en Synap (`listar_lineas_presupuesto_stockp`): además de ``CodigoMovimiento`` del PRE, deben resolverse líneas ya pasadas a pedido vía ``stockp.codmov_presupuesto`` y/o ``ped_presup`` (movimiento pedido ↔ presupuesto); si no, un PRE «En Pedido» puede mostrar cabecera con importe y tabla vacía.
- API `GET /core/api/articulos/search/` (`_buscar_articulos_con_precios`): parámetro opcional **`lista_precio`** (0–6: costo, lista oficial, listas 1–5); devuelve **`PrecioLista`** y columnas de precio. También **`ImpuestoInterno`** (`articulo.impuesto_interno`).
- POST: `_construir_lineas_desde_post` (`linea_*`) y `desc_global_pct_*`, más `linea_detalle` oculto por fila.

---

## 15. Próximos documentos sugeridos

- **Inventario de controles** campo a campo para `Presupuesto.frm` / `Visualiza_Presupuesto.frm` según `INVENTARIO_MIGRACION_FORMULARIOS.md`.
- **Flujo de secuencia** (diagrama) desde `Menu_Presupuesto_Venta` hasta guardado y hasta `Pedido`.

**Última actualización:** elaborado a partir del código en `administranet_vb6/` disponible en el repositorio Synap. Última revisión de §14.1 (formulario Synap): **06/05/2026** (cabecera: fechas `filters_period_bo_dual`; filtros cabecera con `initializeTagsFilter` / `tags_filter.mjs` compartido con reportes).
