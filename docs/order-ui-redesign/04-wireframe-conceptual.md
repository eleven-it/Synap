# 04 · Wireframe conceptual — OrderShell

- **Fecha:** 10/07/2026
- **Pantalla:** `/ecom/mayoristapp/compra/`
- **Base de layout:** `ecom/templates/ecom/base_pedidos.html` + tokens `pedidos_page_styles.html`
- **Objetivo:** definir la estructura visual "OrderShell" sin cambiar backend ni el contrato Alpine `compraMayorista()`.

> Estos wireframes son conceptuales (estructura y jerarquía). El detalle de tokens está en `05-design-system-pedidos.md` y el mapeo a includes/Alpine en `06-componentes.md`.

### Criterio de layout (decisión 10/07/2026)

No se elige layout por semejanza a “ERP” o “carrito”. Se elige lo que hace más **dinámica** la carga para vendedores:

1. **Captura continua** (búsqueda + teclado) como gesto principal.
2. **Líneas del pedido** como superficie de edición (no un mini-carrito de tienda).
3. **Contexto comercial** (cliente, crédito, modo, total) siempre visible sin interrumpir la carga.
4. **Confirmar** a un toque cuando el pedido está listo.
5. Lenguaje de UI orientado al trabajo (“pedido”, “líneas”, “confirmar”); evitar “carrito” como metáfora dominante.

---

## 1. Estructura OrderShell

El OrderShell reorganiza la pantalla en cinco zonas con responsabilidad única:

1. **Header sticky** — cliente + modo (PED/PRE/DEV) + acciones (vaciar, repetir, nuevo).
2. **Captura de productos** — búsqueda dominante estilo TPV + filtros (marcas, promo) + resultados.
3. **Líneas del pedido** — tabla en desktop / tarjetas en mobile.
4. **Resumen sticky** — totales + confirmar (lateral en desktop, bottom bar en mobile).
5. **Secciones secundarias colapsables** — entrega y observaciones.

```mermaid
flowchart TB
    subgraph OrderShell
        direction TB
        HEADER["HEADER STICKY\n[Cliente ▾]  [ PED | PRE | DEV ]  [Repetir] [Vaciar] [Nuevo]"]
        subgraph MAIN[" "]
            direction LR
            subgraph LEFT["ZONA PRODUCTOS + LÍNEAS"]
                direction TB
                SEARCH["Búsqueda dominante TPV\n(código de barras / código / nombre)\n↑↓ mover · Enter agregar   [Solo promo]"]
                RESULTS["Resultados (tabla): Código · Nombre · Stock · Precio"]
                LINES["Líneas del pedido\n(tabla desktop / cards mobile)"]
                SECOND["▸ Entrega y observaciones (colapsable)"]
            end
            subgraph RIGHT["RESUMEN STICKY (lateral)"]
                direction TB
                CREDITO["Crédito / cuenta cliente"]
                TOTALS["Neto · IVA · Imp. int · Desc. pie %\nTOTAL"]
                CTA["[ Revisar y confirmar {tipo} ]"]
            end
        end
        HEADER --> MAIN
    end
```

---

## 2. Layout desktop (≥1024px)

```mermaid
flowchart LR
    subgraph VP["Viewport desktop"]
      direction TB
      H["≡ HEADER STICKY  ·  Cliente: Acme SA (#123) ▾  ·  [PED] PRE DEV  ·  Repetir | Vaciar | Nuevo"]
      subgraph B["Cuerpo (grid 12 col)"]
        direction LR
        L["PRODUCTOS (col 1–8)\n┌───────────────────────────┐\n│ [ Buscar / escanear …    ]│\n│ [Solo promo]              │\n│ Cód · Nombre · Stock · $ │\n│ ─ resultados ─           │\n├───────────────────────────┤\n│ LÍNEAS (tabla)            │\n│ Prod · UOM · Cant · $ · × │\n├───────────────────────────┤\n│ ▸ Entrega / Observaciones │\n└───────────────────────────┘"]
        R["SUMMARY STICKY (col 9–12)\n┌───────────────┐\n│ Crédito cta.  │\n│ Neto     $    │\n│ IVA      $    │\n│ Imp.int  $    │\n│ Desc pie [%]  │\n│ ─────────────│\n│ TOTAL    $    │\n│ [ CONFIRMAR ] │\n└───────────────┘"]
      end
      H --> B
    end
```

- **Proporción sugerida:** productos ~66% / summary ~33% (revisando la compresión actual del carrito; ver diagnóstico §5). El summary es **`position: sticky; top: <alto header>`**.
- Los **pedidos recientes** y el **bloque de éxito** se muestran como banda superior contextual, no como card de ancho completo que empuje el área de trabajo.

---

## 3. Layout tablet (768–1023px)

```mermaid
flowchart TB
    HT["HEADER STICKY compacto\nCliente ▾ · [PED|PRE|DEV] · ⋯"]
    ST["Búsqueda dominante TPV"]
    RT["Resultados"]
    LT["Líneas (tabla condensada o cards)"]
    CT["▸ Entrega / Observaciones (colapsable)"]
    BB["BOTTOM BAR STICKY\nTOTAL $ ·····  [ Confirmar {tipo} ]"]
    HT --> ST --> RT --> LT --> CT --> BB
```

- Una sola columna; el summary se transforma en **bottom bar sticky**.
- Toque en el TOTAL de la bottom bar → expande desglose (neto/IVA/imp.int/desc).

---

## 4. Layout mobile (<768px)

```mermaid
flowchart TB
    HM["HEADER STICKY mini\n[👤 Acme SA ▾]  [PED|PRE|DEV]  [⋯]"]
    SM["🔍 Buscar / escanear  (dominante)"]
    RM["Resultados (lista)"]
    subgraph CARDS["Líneas — cards"]
      C1["▢ Producto A\n$ c/u · IVA · Embalaje\n[−] 2 [+]        $ total  ×"]
      C2["▢ Producto B\n$ c/u · IVA\n[−] 1 [+]        $ total  ×"]
    end
    SEC["▸ Entrega / Observaciones (sheet)"]
    BOT["⎯⎯ BOTTOM BAR STICKY ⎯⎯\nTOTAL $12.340,00   [ Confirmar pedido ]"]
    HM --> SM --> RM --> CARDS --> SEC --> BOT
```

- **Header mini sticky**: chip de cliente (abre selector), segmented de modo, menú "⋯" para acciones secundarias (repetir, vaciar, nuevo, hub).
- **Líneas como `OrderLineMobileCard`**: cantidad con stepper táctil, precio unitario, total, quitar.
- **Bottom bar sticky** siempre visible: total + confirmar. Un toque abre el modal resumen.
- Entrega/observaciones como *sheet* inferior colapsable, no intercalado con las líneas.

---

## 5. Header sticky — anatomía

```mermaid
flowchart LR
    subgraph HEADER["HEADER STICKY"]
      direction LR
      CL["CLIENTE\n[input predictivo ▾]\n(crédito resumido)"]
      MO["MODO\n( PED | PRE | DEV )\ncolor semántico"]
      AC["ACCIONES\nRepetir · Vaciar · Nuevo"]
    end
    CL --- MO --- AC
```

- El header **fija** el contexto operativo (a quién, qué tipo) mientras el usuario scrollea productos/líneas.
- El color del borde/acento del shell cambia según modo (sky/amber/rose), reutilizando `.compra-modo-*`.
- En scroll, el header puede condensarse (altura reducida) manteniendo cliente + modo visibles.

---

## 6. Zona de productos — dominante

```mermaid
flowchart TB
    SB["BÚSQUEDA (input grande, foco al cargar)\nplaceholder: código de barras / código / nombre\nhint: ↑↓ mover · Enter agregar"]
    FT["FILTROS: [Marcas ▾]  [Solo promociones]"]
    RG["RESULTADOS (listbox)\nrole=option · aria-selected · fila resaltada"]
    SB --> FT --> RG
```

- La búsqueda es el **elemento de mayor peso** de la zona de trabajo (tamaño, contraste, foco inicial).
- Resultados conservan navegación por teclado (contrato: `selectedSearchIndex`, `$refs.busquedaDropdownList`).
- Al agregar, el input se limpia y **recupera foco** (flujo de captura continua para operadores intensivos).

---

## 7. Líneas — tabla desktop vs cards mobile

**Desktop (tabla):**

| Producto | UOM | Cant. | P. unit. | Total | |
|---|---|---|---|---|---|
| Producto A | Unidad ▾ | [ 2 ] | $1.200,00 | $2.400,00 | × |
| Producto B | Bulto ▾ | [ 1 ] | $9.940,00 | $9.940,00 | × |

- Nueva columna **UOM** (selector Unidad/Bulto/Display) alimentada por `presentacion.opciones` (hoy oculta; ver diagnóstico §1.3). Sin cambio de backend: el API ya acepta `tipo_unidad` + `multiplicador`.

**Mobile (card):**

```
┌─────────────────────────────┐
│ Producto A                  │
│ $1.200,00 c/u · 21% IVA     │
│ UOM: Unidad ▾   Promo       │
│ [ − ]  2  [ + ]     $2.400  │
│                        Quitar│
└─────────────────────────────┘
```

---

## 8. Summary sticky — desktop lateral / mobile bottom bar

```mermaid
flowchart TB
    subgraph DESK["Desktop: summary lateral sticky"]
      D1["Neto      $"]
      D2["IVA       $"]
      D3["Imp. int  $ (si > 0)"]
      D4["Desc. pie [ % ]"]
      D5["TOTAL     $ (dominante)"]
      D6["[ Revisar y confirmar {tipo} ]"]
      D1-->D2-->D3-->D4-->D5-->D6
    end
    subgraph MOB["Mobile: bottom bar sticky"]
      M1["TOTAL $12.340,00   ▲ desglose"]
      M2["[ Confirmar pedido ]"]
      M1-->M2
    end
```

- **Totales siempre del backend** (`serializar_carrito`): el summary solo formatea con `money()`.
- El botón de confirmar hereda color por modo (PED sky / PRE amber / DEV rose).
- En mobile, "▲ desglose" expande neto/IVA/imp.int/desc sin abandonar la vista.

---

## 9. Secciones secundarias colapsables

```mermaid
flowchart TB
    TT["▸ Entrega y observaciones (colapsado por defecto)"]
    OP["▾ Expandido:\n· Punto de venta [Sesión ▾]\n· Forma de entrega [texto]\n· Observaciones [textarea]"]
    TT -->|toggle| OP
```

- Fuera del camino crítico: no compiten con líneas ni con confirmar.
- Punto de venta se mantiene como selector (contrato `puntosVenta`, `pv`).

---

## 10. Modal resumen (pre-confirmación)

```mermaid
flowchart TB
    OV["Overlay (bg-slate-900/50)"]
    subgraph DLG["Dialog (role=dialog, aria-modal, focus-trap)"]
      T["Resumen — {tipo}"]
      SUB["N renglón(es) · Total $"]
      LI["Lista de líneas (cant × precio)"]
      BT["[ Volver ]   [ Confirmar ]"]
    end
    OV --> DLG
```

- Reutiliza el modal existente (líneas 216–234 de `compra_mayorista.html`) **añadiendo** semántica a11y (`role="dialog"`, `aria-modal`, focus trap, cierre con `Esc`, retorno de foco).
- El mismo patrón cubre: cambio de modo con carrito, y vaciar carrito (reemplazando `confirm()` nativo).

---

## 11. Breakpoints (resumen)

| Breakpoint | Ancho | Layout | Summary |
|---|---|---|---|
| `base` (mobile) | < 640px | 1 columna, header mini, cards | Bottom bar sticky |
| `sm` | ≥ 640px | 1 columna, inputs táctiles | Bottom bar sticky |
| `md` | ≥ 768px | 1–2 columnas (tabla condensada) | Bottom bar o lateral estrecho |
| `lg` | ≥ 1024px | 2 columnas (productos + summary) | Lateral sticky |
| `xl` | ≥ 1280px | 2 columnas holgadas | Lateral sticky |

> Nota: hoy el grid usa `md:grid-cols-3` (2/3+1/3). La propuesta sugiere pasar el summary a **sticky** y reservar el layout de dos columnas para `lg+`, dejando `md` en una columna con bottom bar para evitar la compresión del carrito descrita en el diagnóstico §5.

---

## 12. Zonas de scroll

```mermaid
flowchart TB
    HS["Header sticky (no scrollea)"]
    BODY["Cuerpo scrollea:\nproductos → líneas → secundarias"]
    SS["Summary sticky:\ndesktop lateral fijo / mobile bottom bar fija"]
    HS --- BODY --- SS
```

- Se elimina el **scroll interno del carrito** (`compra-carrito-scroll max-height: 46vh`) en favor de scroll natural del documento con summary sticky, evitando "scroll dentro de scroll".

El mapeo de cada zona a componentes reales (includes + Alpine) está en `06-componentes.md`.
