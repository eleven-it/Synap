# Impacto de los últimos cambios en el template y comportamiento del kiosco (Self-Checkout)

**Fecha:** 2025-01-31

---

## Resumen de los 5 últimos cambios y su impacto

| # | Cambio | Archivo(s) | Impacto en template/comportamiento |
|---|--------|------------|-----------------------------------|
| 1 | **Tailwind CDN solo en debug** | `theme/templates/base.html`, `base_app.html` | **Sí.** El kiosco extiende `base_app.html`. Cuando `debug` es falso (producción o IP fuera de INTERNAL_IPS), el script `cdn.tailwindcss.com` **no se carga**. Los estilos dependen solo de `{% static 'css/dist/styles.css' %}`. Las clases que se aplican **solo por Alpine.js con `:class`** no están en el HTML estático, así que el build de Tailwind (que escanea `theme/templates/**`) **no las incluye** en `styles.css`. Resultado: elementos que usan solo `:class` pueden quedar **sin estilos** (p. ej. botón “Pagar” invisible o como rectángulo gris). |
| 2 | **Botón “Pagar” siempre visible** (primera versión) | `self_checkout/templates/self_checkout/kiosco.html` | **Sí.** Se cambió el botón a `:class` dinámico (estilo gris cuando disabled, gradiente cuando enabled). Eso **empeoró** el problema del punto 1: cuando el CDN no se carga, esas clases no existen en el CSS compilado y el botón podía verse vacío o sin contraste. |
| 3 | **Mensaje de error Mercado Pago (400)** | `self_checkout/templates/self_checkout/kiosco.html` | **Comportamiento.** Solo se mejoró el mensaje mostrado al usuario cuando `/api/mercadopago/create-payment/` devuelve 400 (texto más claro y uso de `dataMp.detail`). No afecta la visibilidad del botón. |
| 4 | **Menú: KIOSCO → AUTOSERVICIO** | `core/utils/utils.py` | **No.** Cambia solo las etiquetas del menú lateral (sección “Autoservicio”, “Acceder al autoservicio”, “Configuración”). No toca el template del kiosco ni su lógica. |
| 5 | **FE antes de commit / no finalizar sin CAE** | `confirmation_service.py`, `api_views.py` | **No.** Afecta solo el flujo de confirmación en backend. No modifica el HTML ni el JS del kiosco. |

---

## Causa del botón “Pagar” que no se veía

1. **CDN condicional:** Sin CDN, solo aplican las clases que están en `styles.css`.
2. **Build de Tailwind:** El `tailwind.config.js` del theme usa `content: ["./templates/**/*.html"]` (relativo a `theme/`), por lo que **no** escanea `self_checkout/templates/`. Las clases que solo aparecen en el kiosco (sobre todo las usadas en `:class`) no se incluyen en el build.
3. **Botón con `:class`:** Al pintar el botón con clases solo vía `:class`, esas clases no existen en el CSS cuando el CDN no se carga → el botón queda sin fondo/color y parece que “no está”.

---

## Corrección aplicada

En el template del kiosco se reemplazó el **único botón con `:class`** por **dos botones**:

- **Botón “deshabilitado”:** visible cuando `estado === 'paying' || !items || items.length === 0 || !!stockBlocked`, con **clases estáticas** + **estilos inline** de respaldo (`background-color`, `color`) para que siempre se vea aunque falle Tailwind.
- **Botón “habilitado”:** visible cuando hay ítems y no hay bloqueo, con clases estáticas + **inline** de gradiente y color, y `x-on:click="irAPago()"`.

Así el botón “Pagar” se ve siempre (con o sin CDN, con o sin esas clases en el build) y el comportamiento (cuándo se puede pagar) se mantiene.

---

## Recomendación a futuro

Para que el kiosco no dependa del CDN ni de builds parciales:

- Incluir las plantillas del kiosco en el **content** de Tailwind al generar `styles.css`, por ejemplo en el config del theme o del proyecto que construya el CSS:

  ```js
  content: [
    "./templates/**/*.html",
    "../../self_checkout/templates/**/*.html",  // o la ruta que corresponda
    // ...
  ]
  ```

- O bien seguir usando **inline styles** en elementos críticos (como el botón “Pagar”) para que la visibilidad no dependa del build ni del CDN.
