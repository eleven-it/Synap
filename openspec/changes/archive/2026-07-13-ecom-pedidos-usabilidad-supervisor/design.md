# Design: Usabilidad pedidos mayorista + supervisor operativo

**Change:** `ecom-pedidos-usabilidad-supervisor` · **Fecha:** 13/07/2026

## Enfoque técnico

Corte vertical A→E. Núcleo: un **resolver único** de viajante efectivo (`cod_viajante_operativo`) reutilizado por checkout, masivo y relay de clientes; sobre él se apoyan VCM en simple, descuentos transparentes, lista RO y barrido visual slate/sky. Totales **siempre** backend (`serializar_carrito` / preview masivo). Referencias: proposal §Scope A–E, exploración §Recommendation, canon `05-design-system-pedidos.md` y `ui-fuente-verdad-reportes-mpr`.

## Spike — origen de `vendedor_a_cargo` (RESUELTO)

En `administraNET-ecom/control.php` (L472–507) `vendedor_a_cargo` **NO tiene fuente MySQL**: es un `array()` **hardcodeado** por `id_usuario` dentro de un `switch`, gateado por `permiso_supervisor_venta=="Si"`.

```php
if($campo->permiso_supervisor_venta=="Si"){
  switch($campo->id_usuario){ case 16: $arrVendaCargo=array(10,49,46,54); break; }
}
$_SESSION["vendedor_a_cargo"] = $arrVendaCargo;   // L703
```

**Conclusión:** no existe tabla legacy a consultar; la cartera se mantenía manualmente en código PHP por cliente (chapini user 16 → [10,49,46,54]; ibero comentado). **Resolución en Synap:** persistir el mapeo supervisor→vendedores en `configuracion_ecom` (tabla legacy existente, sin DDL) con clave `ecom_vendedores_a_cargo_<CodViajante>` y valor JSON `[10,49,46,54]`, hidratado en `mayoristapp_sesion_contexto` cuando `supervisor_venta=Si`. Fallback si no hay fila: cartera = `[cv]` (solo su propio viajante). Migración opcional a tabla `ecom_supervisor_vendedor` vía `core/services/legacy_mysql_schema/catalog.py` si se requiere ABM (fuera de v1).

## Decisiones de arquitectura

| Decisión | Elección | Alternativa rechazada | Racional |
|---|---|---|---|
| Viajante efectivo | Clave `mayoristapp.cod_viajante_operativo` (default `id_vendedor_usr`) + resolver único | Impersonación global de sesión | Acotado a pedidos; no altera permisos ni identidad; rollback trivial |
| Fuente cartera | `configuracion_ecom` JSON por supervisor | Tabla nueva con DDL / hardcode Synap | Sin DDL, editable por base; paridad con hardcode PHP sin acoplar código |
| VCM en simple | Reusar ternas (`listar_clientes_con_ternas`, marcas de terna) cuando operativo≠null | Filtro por `cliente.CodViajante` | Paridad con masivo; cumple REQ-VCM-04 |
| Lista precios | Badge RO + link PDF desde `cliente.ListaPrecio` | Selector override | Producto fijó RO; evita inconsistencia de precio |
| Descuentos simple | Columna % renglón→PATCH; `descPie` precargado; totales por `setCart` | Recalcular en front | Una sola fuente de verdad (backend) |
| Masivo precios | `price_rules_engine` por fila + endpoint preview agregado | Mantener `Precio1V` referencial | Precio real y transparencia antes de confirmar |
| Fix `_session_cod_viajante` | Leer viajante operativo vía resolver | Parche puntual `id_vendedor_usr` | Corrige bug y unifica |

## Arquitectura de datos / flujo

```
                 ┌──────────── SESIÓN mayoristapp ────────────┐
login → contexto │ id_vendedor_usr · supervisor_venta          │
control.php par. │ vendedor_a_cargo(JSON cfg) · cod_viajante_op │
                 └───────────────┬────────────────────────────┘
                                 │  resolver_viajante_operativo(sess)
        ┌────────────────────────┼───────────────────────────┐
   cliente_relay            checkout_relay              pedido_masivo
   (VCM ternas)          (_session_cod_viajante)    (matriz + preview)
        └── clientes/catálogo ── PED con CodViajante correcto ─┘
```

`resolver_viajante_operativo` (nuevo `ecom/services/vendedor_operativo.py`): devuelve `cod_viajante_operativo` si está seteado y pertenece a `{cv} ∪ vendedor_a_cargo`; si no, `id_vendedor_usr`. Único punto que consumen los 3 relays.

## IA / wireframes

**Pedido simple `/venta/` (B2B order-entry inspirado en TPV mayorista):**

```
┌ HERO slate · Pedido de venta ── [Toggle PED|PRE|DEV] ─────────────┐
├ ORDER HEADER (sticky) ────────────────────────────────────────────┤
│ [Buscar cliente ▾]  Operando como: ‹Vendedor X ▾›  (banner sky)   │
│ Cliente: NOMBRE   Lista: L1 [RO] [PDF↗]   Desc.pie: [ 5 %]        │
├ CATÁLOGO (VCM) ───────────┬ CARRITO (workspace sticky) ───────────┤
│ búsqueda ↑↓/Enter (ternas)│ Prod·UOM·Cant·%Desc·P.unit·Total·[x]  │
│                           │ Subtot · Desc · Neto · IVA · TOTAL    │
│                           │ [Confirmar PED] (sky, no purple)      │
└───────────────────────────┴───────────────────────────────────────┘
```

**Pedido masivo `/pedido-masivo-sucursales/` (matriz sucursales × artículos):**

```
┌ HERO slate + breadcrumb (sky) ────────────────────────────────────┐
│ Cliente ‹ternas›   Operando como: ‹Vendedor X›   Lista L1 [RO]     │
├ MATRIZ ────────────────────────────────────────────────────────────┤
│  Artículo \ Sucursal │ Suc A │ Suc B │ %Desc fila │ P.real │ Σ fila │
│  ART 1 (P.real)      │  [2]  │ [ ]   │   [ 5 ]     │  $..   │  $..   │
│  + agregar artículo (autocomplete ternas)                          │
├ Desc. pie lote [ 3 %] ─────────── PREVIEW: Neto·IVA·TOTAL lote ────┤
│                                   [Confirmar lote] → modal canon    │
└────────────────────────────────────────────────────────────────────┘
```

## Mapa de componentes (includes)

| Componente | Acción | Rol |
|---|---|---|
| `includes/pedidos_selector_vendedor.html` | Crear | Dropdown cartera + banner "Operando como" (hidden input + botón, patrón usuarios/sucursales) |
| `includes/pedidos_lista_badge.html` | Crear | Badge lista RO + link PDF |
| `includes/pedidos_lineas_tabla.html` | Modif | Columna `%Desc` editable → PATCH |
| `includes/pedidos_order_summary.html` | Modif | Precarga `descPie`; tokens |
| `includes/pedidos_breadcrumb.html` | Modif | Quitar `variant="purple"` |
| `includes/pedidos_page_styles.html` | Modif | Tokens `.pedidos-btn-modo-*`, `.pedidos-input-qty`; sin purple salvo `.pedidos-btn-gradient` |
| `pedido_masivo_sucursales.html` | Modif | Extraer JS a `pedido_masivo_app.mjs`; columnas desc; preview; modal `pedidos_modal.html` |
| `compra_mayorista.html` | Modif | Insertar selector + badge; slate/sky |

## Contratos / APIs

| Método | Ruta | Body/Resp |
|---|---|---|
| GET | `/ecom/api/mayoristapp/vendedores-cartera/` | `→ {vendedores:[{cod_viajante,nombre}], operativo}` |
| POST | `/ecom/api/mayoristapp/vendedor-operativo/` | `{cod_viajante} → {ok, operativo}` (valida ∈ cartera) |
| PATCH | `…/carrito/items/<id>/` | `{porcentaje_descuento}` (ya existe) |
| POST | `…/pedido-masivo/preview/` | `{draft_id, desc_pie_pct} → {sucursales:[{neto,iva,total}], total_lote}` |
| POST | `…/pedido-masivo/confirmar/` | + `descuento_cliente`, `desc_pie_pct` |

## Tokens (visual)

Sustituir `text-purple-*`, `bg-purple-*`, `focus:ring-purple-*/40`, `variant="purple"` por `.pedidos-*` / sky (`sky-600` primario, `sky-500` hover, anillo `rgba(14,165,233,.25)`). Selección de fila `bg-sky-100 border-sky-500`. Modal canon reemplaza `confirm()` (masivo L539). Prohibido purple genérico (anti-patrón §14).

## Estrategia de pruebas

| Capa | Qué | Cómo |
|---|---|---|
| Unit | resolver operativo (default/validación cartera); spike JSON cfg; `_session_cod_viajante` | `docker exec Synap_app python manage.py test ecom` |
| Integración | VCM simple ternas; PATCH desc renglón; preview masivo totales | mock `mysql_cursor` |
| E2E/manual | Supervisor elige vendedor → PED con `CodViajante` correcto; masivo N sucursales + rollback | entorno Synap |

## Migración / rollout

Sin DDL: cartera vive en `configuracion_ecom`. Seed manual JSON por supervisor. Oleadas A→E revertibles: default operativo=`id_vendedor_usr`; masivo fallback `confirm()`+Precio1V; visual revert CSS. Actualizar `SPEC_MAYORISTAPP_FUNDACIONES.md` (hoy afirma hidratación completa; no la implementa).

## Preguntas abiertas

- [ ] ¿Poblar `ecom_vendedores_a_cargo_*` desde el hardcode PHP conocido o esperar datos por base?
- [ ] ¿`price_rules_engine` soporta lote sin degradar latencia? (límite de filas en preview).
