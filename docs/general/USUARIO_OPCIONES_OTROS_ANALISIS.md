# Análisis: opciones "Otros" del formulario de usuario (AdministraNET → Synap)

**Contexto:** La sección "Otros" del formulario de crear/modificar usuario en AdministraNET (VB6) incluye: Resolución Principal, Tipo de fuente, Tamaño fuente, Color formulario, Botón formulario y Zoom reportes. En la base de datos corresponden a las columnas de la tabla `usuarios`: `resol_principal`, `fuente_nombre`, `fuente_tamano`, `color_formulario`, `tipo_boton`, `zoom_reportes`.

**Objetivo:** Decidir qué tiene sentido mantener en Synap (stack web) y cómo reinterpretar o deprecar cada opción.

---

## 1. Uso en VB6 (AdministraNET)

En una aplicación de escritorio VB6 estas opciones servían para:

- **Resolución Principal:** Fijar el tamaño de la ventana principal del cliente (ej. 1024x768). La aplicación se abría con esa resolución fija.
- **Tipo de fuente / Tamaño fuente:** Fuente y tamaño por defecto del texto en formularios y controles de la aplicación.
- **Color formulario:** Esquema de color de los formularios (ej. "Tiza 1" = tema concreto).
- **Botón formulario:** Estilo visual de los botones (ej. "14 - KDE 2", referido a temas/estilos de controles en escritorio).
- **Zoom reportes:** Nivel de zoom por defecto al abrir reportes (Crystal Reports u otro visor dentro de la app).

---

## 2. Relevancia en Synap (stack web)

| Campo (DB)        | Uso en VB6              | ¿Tiene sentido en web? | Recomendación |
|-------------------|-------------------------|-------------------------|---------------|
| **resol_principal** | Resolución fija ventana | **No.** En web el “tamaño” lo da el navegador; el diseño debe ser responsivo. | **No mostrar en UI.** Mantener columna en DB y persistir valor por compatibilidad con AdministraNET; en Synap no usarlo para nada. Opcional: ocultar en formulario o marcar como “legacy”. |
| **fuente_nombre**   | Fuente por defecto en UI | **Parcial.** En web la tipografía se controla con CSS; una “fuente del sistema” por usuario puede ser útil para accesibilidad o temas. | **Reinterpretar o simplificar.** Si se mantiene: ofrecer pocas opciones (ej. “Por defecto”, “Serif”, “Grande”) mapeadas a clases/variables CSS, no replicar lista de fuentes del sistema. |
| **fuente_tamano**   | Tamaño de fuente en puntos | **Parcial.** Equivalente en web sería escalado de texto (accesibilidad). El valor “8” (pt) no se traduce 1:1 a `rem`/`em`. | **Reinterpretar.** Opción tipo “Texto normal / grande / muy grande” que ajuste `font-size` vía CSS (variables o clase en `<html>`). Persistir en DB como preferencia si se implementa. |
| **color_formulario** | Tema de color (ej. “Tiza 1”) | **Sí, como concepto.** En web = tema visual (claro/oscuro, paletas). | **Mantener como “Tema visual”.** Guardar en DB el identificador de tema; en front aplicar clases o variables CSS según ese valor. Los nombres legacy (“Tiza 1”) pueden mapearse a temas de Synap. |
| **tipo_boton**     | Estilo de botones (ej. “KDE 2”) | **No.** Estilo de controles VB6; en web los botones los define el CSS del proyecto. | **No mostrar en UI.** Mantener columna en DB para no romper esquema y sincronía con AdministraNET; no usar en lógica ni estilos de Synap. |
| **zoom_reportes**  | Zoom inicial en visor de reportes | **Solo si hay visor propio.** Si los reportes se abren en pestaña nueva o se descargan, el zoom lo controla el navegador. | **Evaluar.** Mantener en DB. Mostrar en UI solo si Synap implementa un visor de reportes (iframe/PDF viewer, etc.) con zoom propio; entonces usar este valor como zoom inicial. |

---

## 3. Resumen de decisiones

- **No usar en la UI de Synap (solo compatibilidad de datos):**  
  `resol_principal`, `tipo_boton`.

- **Mantener en DB y reinterpretar en UI (cuando se implemente):**  
  `color_formulario` → tema visual; opcionalmente `fuente_nombre` / `fuente_tamano` como preferencias de accesibilidad o tema.

- **Evaluar según producto:**  
  `zoom_reportes` → solo si existe un visor de reportes con zoom dentro de la aplicación.

- **Implementación actual:**  
  Los seis campos se siguen leyendo y guardando en crear/editar usuario para no romper la paridad con la base de AdministraNET. Se puede en un siguiente paso:
  - Ocultar o agrupar en “Opciones heredadas (no aplican en Synap)” los que no tengan uso en web.
  - Reemplazar etiquetas/controles por versiones “web” (ej. tema, tamaño de texto) cuando exista la lógica en front (CSS/temas).

---

## 4. Referencias

- Tabla `usuarios`: [docs/general/tablas/usuarios.md](tablas/usuarios.md).
- Formularios de usuario en Synap: `core/templates/core/usuarios_crear.html`, `usuarios_editar.html`.
- Servicio y vistas: `core/services/administranet_users.py`, `core/views/views_usuarios.py`.
