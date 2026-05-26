# Tablero MPR — layout y densidad

**Plantilla:** `mpr/templates/mpr/tablero.html`  
**Objetivo:** más altura útil en pantallas tipo laptop; menos espacio “muerto” entre navbar, encabezado y KPIs; columnas inferiores sin altura mínima fija que deje blanco con pocas filas.

## Cambios aplicados

- **Sección:** `min-h-screen` y `py-8`/`sm:py-10` sustituidos por padding vertical más bajo (`py-4` / `sm:py-5`).
- **Encabezado:** menos margen inferior y padding bajo el borde (`mb-4`/`pb-4`, `lg:items-center`); subtítulo `text-sm` y `leading-snug`; H1 ligeramente menor en mobile (`text-xl` → `sm:text-2xl`).
- **CTA «Ver demanda»:** estilo **secundario** (borde morado, fondo claro) para no competir visualmente con el título; tamaño `min-h-9` y tipografía más compacta.
- **KPIs:** cards `rounded-xl`, menos padding (`p-3.5`/`sm:p-4`), iconos `text-2xl`, filas `items-center`, valores `text-xl` en viewport chico y `sm:text-2xl` en mayores; menos gap en la grilla.
- **Columnas «OPTs en proceso» y «Top urgencias»:** eliminado `min-h-[546px]`; añadido `max-h-[min(52vh,26rem)]` y `lg:max-h-[min(58vh,32rem)]` con scroll interno para listado y tabla. Así no queda un bloque alto vacío cuando hay pocas filas.
- **Búsqueda predictiva (OPTs en proceso):** en la misma fila del encabezado del panel (título + badge «En curso» + campo a la derecha), filtrado en cliente con Alpine (`data-search-text` + `x-show`), mismo criterio que en listados MPR (`mpr/ventana_pack.html`, `mpr/opt_list.html`). Si hay filas cargadas pero ninguna coincide, se muestra el mensaje «Ninguna OPT coincide con la búsqueda.».
- **Crear OPP:** `bg-purple-600` (antes azul) para alinear con el acento MPR; **Crear OPA** sigue en esmeralda y **Cerrar** en ámbar por semántica de acción.

## Notas

- Si hace falta aún más densidad en entornos con barra de estado Synap muy alta, valorar reducir un poco más `max-h` o el padding del `base_app` solo en esta ruta (fuera del alcance de esta plantilla).
