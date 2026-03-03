# Inventario y migración de formularios (AdministraNET → Synap)

## 1. Regla de proyecto

Antes de comenzar la migración de cada formulario VB6/AdministraNET solicitado:

1. Realizar un **inventario completo** de los artefactos/componentes del formulario origen.
2. Reproducir cada componente en la UI de Synap con la equivalencia indicada más abajo.
3. Cuando el componente es **checkbox** (o Sí/No binario mostrado como combo en VB6), en Synap usar **botón Activo/Inactivo** (toggle), no un `<select>` Sí/No ni un checkbox nativo.
4. Documentar el inventario y la **comparación** (origen vs Synap) en un archivo como `INVENTARIO_FORMULARIO_<nombre>.md` o en esta guía.

---

## 2. Tipos de componente (VB6 → Synap)

| Tipo en VB6 / AdministraNET | Equivalente en Synap | Notas |
|-----------------------------|----------------------|--------|
| **Label** | `<label for="...">` con clases (ej. `block text-xs font-medium`) | Siempre asociado al control con `for` e `id`. |
| **TextBox** (una línea) | `<input type="text" name="..." id="...">` con clases de formulario | Placeholder opcional. |
| **TextBox** (solo lectura) | `<input type="text" ... readonly>` con estilo gris (`bg-gray-100`, `text-gray-600`) | Para Empresa, datos de solo lectura. |
| **Password** | `<input type="password" name="..." id="...">` | Sin mostrar valor; placeholder solo en edición ("Dejar vacío para no cambiar"). |
| **ComboBox / Dropdown** | `<select name="..." id="..."><option value="">...</option>...</select>` | Incluir opción vacía "— Ninguno —" o "Seleccionar..." cuando sea opcional. |
| **ComboBox Sí/No** (binario) | Si es **estado activo/inactivo** (Anulado, Activa, etc.): **toggle** (hidden + botón Activo/Anulado). Si es **permiso o flag** (Supervisor venta, Vendedor ecommerce, Reportes localmente): `<select>` con Sí/No. | Ver regla: checkbox o estado binario → toggle. |
| **Number / Spinner** | `<input type="number" name="..." id="..." min="..." step="...">` | pvc, fuente_tamano, zoom_reportes. |
| **Checkbox** | **Botón de estado Activo/Inactivo** (toggle): `<input type="hidden" name="...">` + `<button type="button">` que alterna valor (Si/No) y estilo (verde Activo / rojo Anulado). | Patrón: ver `branch_form.html` (Estado sucursal) y `usuarios_editar.html` (Estado usuario). No usar `<input type="checkbox">` para estos casos. |
| **Botón de acción** (ej. explorar carpeta, "@") | Botón "Seleccionar carpeta" que dispara un `<input type="file" webkitdirectory directory multiple>` oculto; en el evento `change` se toma la ruta (input.value) o el nombre de carpeta (primer archivo de `webkitRelativePath`) y se escribe en el campo de texto de ruta. | Ver formulario usuario: panel Rutas y archivos. Compatible con Chrome, Edge, Safari; en Firefox usar atributo `directory`. |
| **Botón Aceptar / Guardar** | `<button type="submit">` con icono e texto. | |
| **Botón Cancelar** | Enlace o `<a href="...">` a la lista/vista anterior. | |

---

## 3. Criterios de comparación

Tras implementar el formulario en Synap, verificar:

- **Campo migrado:** Cada campo del formulario origen tiene un control en Synap que envía el mismo `name` (o el mapeo esperado en el backend).
- **Tipo correcto:** TextBox → input text; ComboBox → select; Password → input password; Checkbox/Anulado → toggle.
- **Opciones/Sí-No:** Los select con opciones fijas (Sí/No, Incluye texto/Exacto) tienen las mismas opciones y valores.
- **Solo lectura / deshabilitado:** Los campos que en origen son readonly o deshabilitados (ej. Empresa, o todo menos contraseña en usuario Supervisor) se reproducen con `readonly`, `disabled` o sin `name` según corresponda.
- **Gaps aceptados:** Documentar explícitamente si algún componente no se migra (ej. botón explorar carpeta) y el motivo.

---

## 4. Ejemplo: Modificar usuario (CargaUsuario.frm)

El inventario y la comparación detallada del formulario "Modificar usuario" están en **[INVENTARIO_FORMULARIO_MODIFICAR_USUARIO.md](INVENTARIO_FORMULARIO_MODIFICAR_USUARIO.md)**. Sirve como referencia para futuros formularios.

Resumen del resultado de la comparación:

- Todos los campos de datos tienen equivalente en Synap (Perfil, Operación y ventas, Cajas, Rutas y archivos, Apariencia).
- **Anulado** se migró como **toggle Activo/Anulado** (no como combo Sí/No), conforme a la regla.
- **Selector de carpeta:** Los tres campos de ruta (Reportes localmente, Certificados localmente, Carpeta documentos) tienen botón "Seleccionar carpeta" que abre el diálogo del sistema vía `<input webkitdirectory>` y rellena el campo con la ruta o nombre de carpeta que exponga el navegador.
