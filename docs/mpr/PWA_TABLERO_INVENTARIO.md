# PWA Tablero KPIs e Inventario MPR

**Estado:** implementado  
**Permiso:** `mpr.ver` (mixins `MprLoginRequiredMixin` + `MprEscritorioVerMixin`)

## Objetivo

Ofrecer dos pantallas MPR optimizadas para dispositivos móviles (PWA), siguiendo el mismo patrón que **Mi parte** (`parte_operario`): selector de template vía `get_template_for_device`, shell `base_app.html`, Alpine inline y render SSR.

## Rutas

| Pantalla | URL | Vista | Template desktop | Template mobile |
|----------|-----|-------|------------------|-----------------|
| Tablero KPIs | `/mpr/` (`mpr:tablero`) | `TableroView` | `mpr/tablero.html` | `mpr/mobile/tablero.html` |
| Inventario MPR | `/mpr/inventario/` (`mpr:inventario`) | `InventarioMprView` | `mpr/inventario.html` | `mpr/mobile/inventario.html` |

## Patrón técnico (paridad `parte_operario`)

1. Vista basada en `TemplateView` con `get_template_names()` → `get_template_for_device(request, "mpr/<nombre>.html")`.
2. Mobile bajo `mpr/templates/mpr/mobile/`.
3. Extiende `base_app.html` (no `base_mpr.html` en móvil).
4. Clase contenedora con `pb-32` para dejar espacio al bottom nav y a la status bar del shell.
5. Sin diálogos nativos (`alert` / `confirm` / `prompt`).

## Tablero KPIs (móvil)

- Header compacto «Tablero KPIs» + toggle **Docenas | Pares** (`?presentacion=`, sesión `mpr_presentacion_cantidad`).
- Cards KPI: pedidos, componentes, Resta, PED resta, packs con brecha.
- Orden de tablas: **Packs pendientes** primero, luego **Componentes**.
- Packs: columnas alineadas Artículo | St. | Resta | Pedido (antes «PED»).
- Componentes: columnas alineadas Artículo | Resta | Pedido.
- Totales en pie de cada lista.
- **Landscape:** sin `max-w-lg` (ancho completo); KPIs en 5 columnas; Packs y Componentes lado a lado.
- Reutiliza el contexto ya armado por `TableroView` (`construir_resumen_tablero_kpi` + `enriquecer_resumen_tablero_kpi_presentacion`).

## Inventario MPR

- **Fuente de datos:** `stock.services.inventario_tabla` (`parse_inventario_filtros`, `consultar_inventario_tabla`, `preparar_filas_inventario_presentacion`).
- **Presentación:** alineada con `resolver_modo_presentacion_operativa` (misma sesión que tablero MPR).
- **Filtros móvil (GET):** Fabricados | Terminados, Docenas | Pares, Con stock | Todos.
- **Búsqueda:** Alpine client-side sobre filas SSR (sin filtro SQL por tecla).
- **Escritorio:** `mpr/inventario.html` con shell `base_mpr.html`, viewport fijo y grilla reutilizando `stock/inventario/_tabla.html`. Enlace opcional «Ver en Stock» → `/stock/inventario/` (`stock:inventario`).

Errores de esquema MPR (`MprSchemaError`) y fallos de consulta muestran mensaje en español en pantalla.

## Navegación inferior compartida

Include: `mpr/includes/mobile_nav_mpr.html`

- Posición: `fixed bottom-8`, `z-20`, `max-w-lg` centrado (sobre status bar).
- Ítems: **KPIs** (`mpr:tablero`, `current=kpis`) e **Inventario** (`mpr:inventario`, `current=inventario`).
- Tercer ítem **Mi parte** (`mpr:parte_movil_operario`) si la vista pasa `mostrar_parte_movil=True` (usuario con `mpr.parte_operario`).

Helper en vista: `_context_nav_movil_mpr(request)`.

## Menú escritorio

Ítem en `core/utils/utils.py` → Producción diaria:

- **Tablero de control (KPIs)** → `mpr:tablero`, icono `dashboard`, permiso `mpr.ver`, `menu_item_id=mpr_prod_kpis`
- **Inventario** → `mpr:inventario`, icono `inventory_2`, permiso `mpr.ver`, `menu_item_id=mpr_prod_inventario`

## Menú PWA Nivel A y hub dashboard

En dispositivos móviles, el módulo **Producción (MPR)** aparece en el menú principal si el usuario lo tendría visible en escritorio (`usuario_tiene_mpr_en_menu`, vía `apps_visibles_sin_filtro_pwa`). Solo se muestran los submenús PWA:

| `menu_item_id` | Etiqueta | Ruta |
|----------------|----------|------|
| `mpr_prod_kpis` | Tablero de control (KPIs) | `/mpr/` |
| `mpr_prod_inventario` | Inventario | `/mpr/inventario/` |

Constantes en `core/pwa_nivel_a.py`: `PWA_MENU_APP_IDS` incluye `"mpr"`, `PWA_MPR_MENU_ITEM_IDS`, `PWA_MPR_DEEP_LINKS`.

En **`/core/dashboard/`**, usuarios con permiso `mpr.ver` (o admin) ven:

- **Hero** (mismo formato que Command Center, gradiente violeta): **Tablero KPIs** → `/mpr/`.
- **Action-card** (mismo formato que Reports): **Inventario** → `/mpr/inventario/`.

Visibles en desktop y móvil.

Sidebar contextual en MPR móvil: `menu_context` aplica `filtrar_submenus_mpr_para_pwa_movil` cuando `current_app_id == "mpr"`.

## Tests

```bash
docker exec Synap_app python manage.py test mpr.tests.test_pwa_tablero_inventario --keepdb
```

Archivo: `mpr/tests/test_pwa_tablero_inventario.py`

## Referencias

- [CARGA_MOVIL_OPERARIO.md](./CARGA_MOVIL_OPERARIO.md) — patrón PWA Mi parte
- [NAVIGACION_MPR_ETAPA11.md](./NAVIGACION_MPR_ETAPA11.md) — flujo MPR escritorio
- [../stock/INVENTARIO_TABLA_MPR.md](../stock/INVENTARIO_TABLA_MPR.md) — servicio compartido de inventario
