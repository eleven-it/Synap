# Alta de movimiento de stock — mejoras de UX (Synap)

**Plantilla:** `stock/templates/stock/alta_movimiento.html`  
**Objetivo:** Mejor jerarquía visual, menos ruido y alineación con el acento violeta del shell Synap, **sin cambiar** lógica Alpine.js, `id` de campos, envíos ni validaciones.

## Cambios aplicados

1. **Cabecera de página**  
   - Título con tracking ajustado y texto de ayuda breve (flujo: cabecera → pestaña artículos).

2. **Pestañas**  
   - Acento **purple** (coherencia con navbar Synap).  
   - `min-h-10`, `rounded-t-lg`, anillos de foco visibles (`focus-visible:ring-purple-500`).

3. **Panel “Datos del movimiento”**  
   - El título visible duplicado respecto al tab se reemplazó por **`<h2 class="sr-only">`** para accesibilidad sin ruido visual.  
   - **Fecha** integrada en la misma franja flexible que motivo, depósitos y vendedor (`xl:flex-row xl:items-end`), con altura uniforme de controles (`h-11`, `rounded-xl`).  
   - Card con `rounded-2xl`, borde slate suave y sombra ligera.

4. **Referencia y detalle**  
   - Mismo patrón de foco (anillo violeta).  
   - Texto auxiliar bajo **Referencia** aclarando que es lista parametrizada (opcional).

5. **Panel “Artículos”**  
   - Título visible duplicado → **`sr-only`**: “Artículos del movimiento”.  
   - Misma envoltura visual que el panel de datos.  
   - Hint de E/S actualizado a “primera pestaña” en lugar de repetir el nombre del tab.

6. **Pie de acciones**  
   - Separador superior (`border-t`).  
   - En **móvil**, `flex-col-reverse`: **Continuar / Confirmar** arriba, **Cancelar** abajo.  
   - En **`sm+`**, `justify-between`: cancelar a la izquierda, acción principal a la derecha.  
   - **Continuar:** `purple-600`; **Confirmar movimiento:** `emerald-600` (acción de guardado).  
   - **Cancelar:** estilo secundario con borde (menos peso que antes).

7. **Acentos en la pantalla**  
   - Sustitución de clases **indigo** por **purple** en enlaces, botones secundarios, escáner, tabla, modales y sugerencias de búsqueda de esta misma plantilla.

## Ajuste posterior — PEDI

- El bloque **“Pedidos internos a depósito”** vive en un `grid` de tres columnas; si era el único campo visible, el botón quedaba en ~1/3 del ancho. El contenedor usa **`md:col-span-3`** y el botón **`w-full`** con contenido centrado, alineado visualmente con campos de ancho completo (p. ej. Detalle).

## No modificado (a propósito)

- Handlers `@click`, `@change`, `x-model`, `x-show`, IDs de tabs/paneles y atributos ARIA esenciales.  
- Backend, formularios Django y URLs.

## Referencia visual / auditoría

- Objetivo alineado con reducción de títulos redundantes, rejilla más compacta en cabecera y CTAs con jerarquía clara en móvil y escritorio.
