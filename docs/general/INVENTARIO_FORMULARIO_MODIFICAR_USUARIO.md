# Inventario y comparación: formulario Modificar usuario (CargaUsuario.frm → Synap)

**Formulario origen:** CargaUsuario.frm (AdministraNET VB6) — ventana "Modificar usuario".  
**Formularios Synap:** `core/templates/core/usuarios_editar.html`, `usuarios_crear.html`.  
**Metodología:** [INVENTARIO_MIGRACION_FORMULARIOS.md](INVENTARIO_MIGRACION_FORMULARIOS.md).

---

## 1. Inventario completo en AdministraNET (VB6)

Listado de artefactos en el orden y agrupación del formulario origen (dos columnas bajo "Datos").

| # | Etiqueta (Label) | Componente VB6 | Nombre campo / valor | Observaciones |
|---|------------------|----------------|----------------------|---------------|
| 1 | Empresa | TextBox (solo lectura) | nombre_empresa / datosempresa | Solo lectura. |
| 2 | Sucursal | ComboBox | id_sucursal | Lista sucursales. |
| 3 | Usuario | TextBox | cod_usuario | Código de usuario. |
| 4 | Nombre | TextBox | nombre_usuario | |
| 5 | Apellido | TextBox | apellido_usuario | |
| 6 | Puesto | ComboBox | id_puesto | Lista puestos. |
| 7 | Contraseña | Password | password_usuario | Enmascarado. |
| 8 | Valid. Contraseña | Password | confirmación | Enmascarado. |
| 9 | Tipo Búsqueda | ComboBox | tipo_busq | Ej. "Tipeo Directo". |
| 10 | Búsqueda defecto | ComboBox | tipo_busqueda_defecto | Ej. "Incluye texto", "Exacto". |
| 11 | Supervisor venta | ComboBox Sí/No | permiso_supervisor_venta | |
| 12 | Vendedor de ecommerce | ComboBox Sí/No | vendedor_web | |
| 13 | Reportes localmente | ComboBox Sí/No + TextBox (ruta) + Botón @ | utiliza_reporte_local, ruta_reporte_local | Botón para explorar carpeta. |
| 14 | Certificados localmente | ComboBox Sí/No + TextBox (ruta) + Botón @ | utiliza_certificado_local, ruta_certificado_local | Botón para explorar carpeta. |
| 15 | Carpeta documentos | TextBox + Botón @ | carpeta_documentos | Botón para explorar carpeta. |
| 16 | Entrega default | ComboBox | entrega_defecto | Ej. "Envía por despacho". |
| 17 | Punto de Venta | ComboBox / numérico | id_punto_venta / pv | Lista punto_venta. |
| 18 | Nro Suc. Cob | Numérico (spinner) | pvc | |
| 19 | Anulado | ComboBox Sí/No | baja_usuario | Estado activo/inactivo → en Synap debe ser **toggle**. |
| 20 | Vendedor | ComboBox | CodViajante | Lista viajantes, opción —Ninguno—. |
| 21 | Depósito general | ComboBox | id_deposito | Lista deposito. |
| 22 | Caja efectivo cobranza | ComboBox | id_caja | Lista caja_abm filtrada por tipo (véase abajo). |
| 23 | Caja efectivo rendición | ComboBox | id_caja_deposito | Mismo RecordSource que id_caja en VB6. |
| 24 | Caja cheque cobranza | ComboBox | id_caja_cheque | tipo_caja = 'Cheque'. |
| 25 | Caja cheque rendición | ComboBox | id_caja_cheque_deposito | tipo_caja = 'Acumulativa Cheque'. |
| 26 | Caja tarjeta cobranza | ComboBox | id_caja_tarjeta | tipo_caja IN ('Tarjeta', 'Acumulativa Tarjeta'). |
| 27 | Caja tarjeta rendición | ComboBox | id_caja_tarjeta_deposito | Mismo RecordSource que id_caja_tarjeta en VB6. |
| 28 | Resolución Principal | ComboBox | resol_principal | Ej. "1024x768". |
| 29 | Tipo de fuente | ComboBox | fuente_nombre | Ej. "Arial". |
| 30 | Tamaño fuente | Numérico / ComboBox | fuente_tamano | Ej. 8. |
| 31 | Color formulario | ComboBox | color_formulario | Ej. "Tiza 1". |
| 32 | Botón formulario | ComboBox | tipo_boton | Ej. "14 - KDE 2". |
| 33 | Zoom reportes | Numérico / texto % | zoom_reportes | Ej. 100. |
| — | Aceptar / Guardar | Botón | submit | |
| — | Cancelar | Botón | cancel | |

**Total campos de datos:** 33. **Botones de acción en campos:** 3 (botones "@" en Reportes localmente, Certificados localmente, Carpeta documentos).

---

## 2. Inventario en Synap (usuarios_editar / usuarios_crear)

Controles presentes en las plantillas, por panel (tabs).

| # | Etiqueta | Componente Synap | name / id | Panel |
|---|----------|------------------|-----------|--------|
| 1 | Empresa | input text readonly | (sin name), valor desde contexto | Perfil |
| 2 | Sucursal * | select | id_sucursal | Perfil |
| 3 | Usuario (código) * | input text | cod_usuario | Perfil |
| 4 | Nombre * | input text | nombre_usuario | Perfil |
| 5 | Apellido | input text | apellido_usuario | Perfil |
| 6 | Puesto | select | id_puesto | Perfil |
| 7 | Contraseña | input password | password | Perfil |
| 8 | Valid. Contraseña | input password | confirmar_password | Perfil |
| 9 | Estado | **Toggle** (hidden + botón) | baja_usuario | Perfil |
| 10 | Punto de Venta | select | id_punto_venta | Operación y ventas |
| 11 | Nro Suc. Cob | input number | pvc | Operación y ventas |
| 12 | Vendedor (viajante) | select | CodViajante | Operación y ventas |
| 13 | Depósito general | select | id_deposito | Operación y ventas |
| 14 | Entrega default | input text | entrega_defecto | Operación y ventas |
| 15 | Supervisor venta | select Sí/No | permiso_supervisor_venta | Operación y ventas |
| 16 | Vendedor de ecommerce | select Sí/No | vendedor_web | Operación y ventas |
| 17 | Tipo Búsqueda | input text | tipo_busq | Operación y ventas |
| 18 | Búsqueda defecto | select | tipo_busqueda_defecto | Operación y ventas |
| 19–24 | 6 Cajas | select cada una | id_caja, id_caja_deposito, id_caja_cheque, id_caja_cheque_deposito, id_caja_tarjeta, id_caja_tarjeta_deposito | Cajas |
| 25 | Reportes localmente | select Sí/No + input text (ruta) | utiliza_reporte_local, ruta_reporte_local | Rutas y archivos |
| 26 | Certificados localmente | select Sí/No + input text (ruta) | utiliza_certificado_local, ruta_certificado_local | Rutas y archivos |
| 27 | Carpeta documentos | input text | carpeta_documentos | Rutas y archivos |
| 28 | Resolución Principal | input text | resol_principal | Apariencia |
| 29 | Tipo de fuente | input text | fuente_nombre | Apariencia |
| 30 | Tamaño fuente | input number | fuente_tamano | Apariencia |
| 31 | Color formulario | input text | color_formulario | Apariencia |
| 32 | Botón formulario | input text | tipo_boton | Apariencia |
| 33 | Zoom reportes (%) | input number | zoom_reportes | Apariencia |
| — | Guardar / Cancelar | button submit, enlace | — | Pie del formulario |

---

## 3. Comparación campo a campo (origen → Synap)

| Campo origen | Componente origen | Componente Synap | Estado | Nota |
|--------------|-------------------|------------------|--------|------|
| Empresa | TextBox readonly | input text readonly | OK | Sin name (solo lectura). |
| Sucursal | ComboBox | select | OK | |
| Usuario | TextBox | input text | OK | |
| Nombre | TextBox | input text | OK | |
| Apellido | TextBox | input text | OK | |
| Puesto | ComboBox | select | OK | |
| Contraseña | Password | input password | OK | |
| Valid. Contraseña | Password | input password | OK | |
| Tipo Búsqueda | ComboBox | input text | OK | Valor por defecto "Tipeo Directo"; en web puede ser texto o luego select si se fijan opciones. |
| Búsqueda defecto | ComboBox | select (Incluye texto / Exacto) | OK | |
| Supervisor venta | ComboBox Sí/No | select Sí/No | OK | Flag/permiso, no estado global → se mantiene select. |
| Vendedor de ecommerce | ComboBox Sí/No | select Sí/No | OK | |
| Reportes localmente | Combo Sí/No + TextBox + Botón @ | select Sí/No + input text + **botón «Seleccionar carpeta»** | OK | Botón abre `<input webkitdirectory>` y rellena la ruta (nombre de carpeta o valor que exponga el navegador). |
| Certificados localmente | Combo Sí/No + TextBox + Botón @ | select Sí/No + input text + **botón «Seleccionar carpeta»** | OK | Igual. |
| Carpeta documentos | TextBox + Botón @ | input text + **botón «Seleccionar carpeta»** | OK | Igual. |
| Entrega default | ComboBox | input text | OK | En VB6 puede ser combo con opciones; en Synap texto libre. |
| Punto de Venta | ComboBox | select | OK | |
| Nro Suc. Cob | Numérico | input number | OK | |
| **Anulado** | **ComboBox Sí/No** | **Toggle Activo/Anulado** | OK | Regla: estado binario → botón activo/inactivo. |
| Vendedor | ComboBox | select | OK | |
| Depósito general | ComboBox | select | OK | |
| 6 Cajas | ComboBox cada una | select cada una | OK | |
| Resolución Principal | ComboBox | input text | OK | |
| Tipo de fuente | ComboBox | input text | OK | |
| Tamaño fuente | Numérico | input number | OK | |
| Color formulario | ComboBox | input text | OK | |
| Botón formulario | ComboBox | input text | OK | |
| Zoom reportes | Numérico | input number | OK | |
| Aceptar / Cancelar | Botones | button submit + enlace | OK | |

---

### 3.1 Combos de caja (filtrado por tipo_caja)

En CargaUsuario.frm cada combo de caja usa un RecordSource filtrado por `tipo_caja` en `caja_abm`. Synap replica este comportamiento:

| Combo Synap | Contexto template | tipos_caja (caja_abm) |
|-------------|-------------------|------------------------|
| Caja efectivo cobranza | cajas_efectivo_cobranza | Acumulativa, Punto de Venta, Fondo Fijo |
| Caja efectivo rendición | cajas_efectivo_rendicion | Idem (mismo RecordSource que efectivo cobranza en VB6) |
| Caja cheque cobranza | cajas_cheque_cobranza | Cheque |
| Caja cheque rendición | cajas_cheque_rendicion | Acumulativa Cheque |
| Caja tarjeta cobranza | cajas_tarjeta_cobranza | Tarjeta, Acumulativa Tarjeta |
| Caja tarjeta rendición | cajas_tarjeta_rendicion | Idem (mismo RecordSource que tarjeta cobranza en VB6) |

Servicio: `AdministraNETUserService.obtener_cajas_usuario_formulario()` en `core/services/administranet_users.py`; vistas pasan las seis listas en el contexto.

---

## 4. Resumen de la comparación

- **Total campos de datos:** 33 en origen, 33 en Synap. Todos tienen correspondencia.
- **Checkbox / estado binario (Anulado):** Migrado correctamente como **toggle Activo/Anulado** (hidden `baja_usuario` + botón que alterna Si/No y estilo), según regla de proyecto.
- **Componentes Sí/No que no son “estado”:** Supervisor venta, Vendedor ecommerce, Reportes localmente, Certificados localmente se mantienen como `<select>` Sí/No (son flags/opciones, no el estado global del usuario).
- **Botones "Seleccionar carpeta":** Implementados junto a cada campo de ruta (Reportes localmente, Certificados localmente, Carpeta documentos). Al hacer clic se abre el diálogo de selección de carpeta del sistema (`<input type="file" webkitdirectory>`); la ruta o el nombre de la carpeta seleccionada se escribe en el campo de texto (el navegador puede exponer una ruta tipo `C:\fakepath\NombreCarpeta` o solo el nombre de carpeta según `webkitRelativePath`).
- **Orden y agrupación:** En Synap los campos están en 5 pestañas (Perfil, Operación y ventas, Cajas, Rutas y archivos, Apariencia); dentro de Perfil el orden es Col1: Empresa, Usuario, Nombre, Apellido; Col2: Sucursal, Puesto, Contraseña, Valid. Contraseña, Estado (toggle).

**Conclusión:** El formulario Modificar usuario (crear y editar) está migrado correctamente respecto al inventario de componentes. El único componente no reproducido son los botones de explorar carpeta, documentado como gap aceptado para el entorno web.
