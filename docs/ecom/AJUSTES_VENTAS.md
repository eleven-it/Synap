# Ajustes de ventas (ecom)

**Ruta:** `/ecom/mayoristapp/ajustes-ventas/`  
**Permiso:** `ecom.config_ajustes_ventas`  
**Fecha:** 16/07/2026

## Propósito

Pantalla tipo Odoo para parámetros del flujo de pedidos mayorista.

| Parámetro | Key MySQL `configuracion_ecom` | Default |
|-----------|-------------------------------|---------|
| Validar stock al confirmar pedidos | `ecom_validar_stock_pedidos` | **Si** |
| Enviar mail al confirmar pedido | `ecom_enviar_mail_confirmar_pedido` | **Si** |
| Workflow jerarquía comercial (master) | `ecom_workflow_jerarquia_comercial` | **No** |
| Aprobación comercial de pedidos (subflag) | `ecom_aprobacion_pedidos_activa` | **No** |
| Umbral monto aprobación | `ecom_aprobacion_umbral_monto` | vacío (regla inactiva) |
| Umbral descuento pie (%) | `ecom_aprobacion_umbral_desc_pie` | vacío |
| Umbral descuento renglón (%) | `ecom_aprobacion_umbral_desc_renglon` | vacío |
| Atajo objetivos en hub pedidos | `ecom_objetivos_en_pedidos` | **No** |
| Atajo backorder en hub pedidos | `ecom_backorder_en_pedidos` | **No** |

## Comportamiento

### Validación de stock

- **Si (Activo):** comportamiento legacy — el carrito y el checkout PED validan stock disponible; el preview masivo **no** valida stock (solo calcula totales).
- **No (Inactivo):** se permiten pedidos simple y masivo sin bloqueo por stock en carrito y commit; el faltante puede cubrirse fabricando vía MPR.

### Mail de confirmación al confirmar PED

- **Si (Activo):** tras confirmar un pedido (PED), si el checkout incluye `enviar_mail_cliente` y el cliente tiene email, se encola mail en `EcomMailQueue`.
- **No (Inactivo):** no se encola mail automático al confirmar (sigue disponible el encolado manual desde la UI de comprobantes).
- Requiere **AND** con el flag del checkout `enviar_mail_cliente` y SMTP configurado (`core.services.outbound_email`).

### Workflow comercial

- **Master OFF:** paridad actual — carteras JSON legacy, alcance propio, sin aprobación comercial efectiva aunque el subflag diga Sí en DB.
- **Master ON:** alcance vía organigrama G→S→V (`alcance_viajantes_comercial`); ABM jerarquía en la misma pantalla (permiso `ecom.jerarquia.editar`).
- **Subflag aprobación:** solo tiene efecto con master ON; umbrales vacíos = regla inactiva (comportamiento conservador).
- **Atajos hub:** toggles independientes para enlaces objetivos/backorder desde el hub de pedidos (`pedidos_hub.html`).

Servicio de lectura/escritura: `ecom.services.ecom_config_mysql` (`pedidos_validan_stock`, `pedidos_envian_mail_confirmacion`, `workflow_jerarquia_comercial_activo`, `aprobacion_pedidos_activa`, `guardar_config_workflow_comercial`, `escribir_valor_configuracion_ecom`).

## API

| Método | Path | Body |
|--------|------|------|
| GET | `/ecom/api/mayoristapp/ajustes-ventas/` | — |
| POST | `/ecom/api/mayoristapp/ajustes-ventas/` | `{ "validar_stock_pedidos": true \| false, "enviar_mail_confirmar_pedido": true \| false }` (al menos uno) |
| GET | `/ecom/api/mayoristapp/ajustes/workflow/` | — |
| POST | `/ecom/api/mayoristapp/ajustes/workflow/` | `{ "workflow_jerarquia_comercial": bool, "aprobacion_pedidos_activa": bool, "objetivos_en_pedidos": bool, "backorder_en_pedidos": bool, "umbral_monto": string, "umbral_desc_pie": string, "umbral_desc_renglon": string }` |
| GET/POST | `/ecom/api/mayoristapp/jerarquia/nodos/` | ABM árbol (permiso `ecom.jerarquia.editar`) |
| GET | `/ecom/api/mayoristapp/jerarquia/usuarios/?q=` | Búsqueda predictiva de usuarios con `CodViajante` para el ABM |

## Seed de parámetros

Provider global MySQL:

1. **`vendedores_asignacion`** — inserta `ecom_validar_stock_pedidos` y el resto de claves en `_ECOM_AJUSTES_VENTAS_CONFIG`.
2. **`ecom_jerarquia_aprobacion`** — además asegura las claves de workflow/aprobación/atajos al aplicar DDL de jerarquía.

Inserta filas en `configuracion_ecom` y `configuracion_ecom_conf` si no existen.

**UI:** Archivo → **Migración esquema MySQL (legacy)** → proveedor correspondiente sobre la base empresa.

## UI (cards)

Orden de las tarjetas en `ecom/ajustes_ventas.html` (canon slate/sky, toggles Activo/Inactivo):

1. **Validación de stock** — toggle `validar_stock_pedidos`.
2. **Correo al confirmar pedido** — toggle `enviar_mail_confirmar_pedido`. Nota UI: al confirmar un PED, si el cliente tiene email se encola el comprobante; requiere correo saliente configurado y el worker `process_ecom_mail_queue`. Se guarda junto a `validar_stock_pedidos` en el mismo POST a `api_ajustes_ventas`.
3. **Workflow comercial** — flags/umbrales de aprobación y atajos del hub.
4. **Jerarquía comercial** — ABM G→S→V como **árbol anidado** con **alta contextual** (permiso `ecom.jerarquia.editar`). Reemplaza el layout anterior de 3 pickers fijos + botones `Vincular G→S` / `Vincular S→V` / `Actualizar árbol`.

   **Zona 1 — Header + banner de workflow.** Título *Jerarquía comercial* y subtítulo *"Definí quién reporta a quién. Esta estructura se usa para el alcance y la aprobación de pedidos cuando el flujo de trabajo está activo."* Debajo, un banner que depende de `workflowJerarquia`:
   - **OFF** (borde `sky`, ícono `info`): *"El flujo de trabajo de pedidos está desactivado. Podés configurar con tranquilidad: los cambios se guardan, pero todavía no afectan pedidos."*
   - **ON** (borde `emerald`, ícono `check_circle`): *"Flujo de trabajo activo. Los pedidos siguen esta jerarquía. Los cambios se aplican de inmediato."*

   **Zona 2 — Árbol anidado.** El getter Alpine `arbolAnidado` deriva de la respuesta `{ vinculos_gs, vinculos_sv, etiquetas }` la estructura `{ gerentes:[{ cod, etiqueta, supervisores:[{ cod, etiqueta, vendedores:[{ cod, etiqueta }] }] }], sinGerente:[…] }`. Cada nivel se indenta con borde izquierdo (`border-l-2`) e ícono: gerente `badge` (sky), supervisor `supervisor_account` (indigo), vendedor `storefront` (amber). Acciones por nodo: gerente → *Agregar supervisor*; supervisor → *Agregar vendedor* + *Quitar* (desactiva G→S vía `cod_supervisor`); vendedor → *Quitar* (desactiva S→V vía `cod_vendedor`). Los supervisores que aparecen en `vinculos_sv` pero no tienen padre en `vinculos_gs` se listan en un grupo aparte **"Supervisores sin gerente"** (sin botón *Quitar*, ya que son raíz). El header del árbol tiene un botón sutil *Actualizar* (`refresh`, recarga `cargarJerarquia()`). El árbol se refresca solo con la respuesta `arbol` tras cada acción.
   - **Empty state:** título *"Todavía no hay jerarquía comercial"*, cuerpo *"Empezá agregando un gerente y su primer supervisor. Después vas a poder colgar más supervisores y vendedores."* y CTA primario *Agregar gerente*.

   **Zona 3 — Panel de alta (modal `altaJerarquia`).** Un único picker activo (`pick.panel`) según el modo:
   | modo | título | picker (`rol`) | al confirmar |
   |------|--------|----------------|--------------|
   | `gerente` | Agregar gerente (paso 1 de 2) | usuario `gerente` | guarda gerente y pasa a `supervisor_bajo_nuevo` (botón *Siguiente*) |
   | `supervisor_bajo_nuevo` | Agregar supervisor bajo {gerente} | usuario `supervisor` | POST `vincular_gerente_supervisor` |
   | `supervisor` | Agregar supervisor bajo {gerente} | usuario `supervisor` | POST `vincular_gerente_supervisor` (padre = gerente del nodo) |
   | `vendedor` | Agregar vendedores bajo {supervisor} | viajantes `vendedor` | POST `vincular_supervisor_vendedor` con `cod_vendedores` (padre = supervisor del nodo) |

   El **primer alta** siempre crea un G→S (no existe nodo gerente suelto): el modo `gerente` es un asistente de 2 pasos. Botones del panel: *Cancelar* / *Confirmar* (o *Siguiente* en el paso 1). Si la persona elegida **ya tiene padre** en otra rama, se pide confirmación para **mover** (`mover: true` en el POST) en lugar de fallar.

   En modo `vendedor`, el picker permite seleccionar uno o más viajantes: cada click alterna un chip y *Confirmar* crea vínculos S→V para todos, sin mover ni quitar vínculos de otros supervisores. Un vendedor puede reportar a varios supervisores activos para cobertura de vacaciones o turnos. Quitar un vendedor desde un nodo desactiva únicamente el par Supervisor→Vendedor de ese nodo. En el árbol, cada fila de vendedor tiene checkbox; con más de un vendedor aparecen *Seleccionar todos* / *Deseleccionar* y el botón *Quitar seleccionados (N)* (POST `desactivar_supervisor_vendedor` con `cod_vendedores[]`).

   **Identidad de gerente/supervisor:** los vínculos se identifican por el
   `id_usuario` elegido (`id_usuario_gerente` e `id_usuario_supervisor`).
   `CodViajante` es solo un snapshot compatible. En particular, el código `1`
   es un placeholder de usuario: varios supervisores distintos pueden usarlo
   bajo un mismo gerente. Los vendedores se seleccionan exclusivamente desde
   `viajantes` con código mayor a `1`.

   **Quitar:** modal Synap de confirmación (overlay slate, ícono `link_off`, Cancelar / Quitar rojo) en lugar de `window.confirm`; cubre quitar individual y *Quitar seleccionados*.

   Gerente/Supervisor: búsqueda de **usuarios** con puesto **Supervisor**, **Administrador**/**Administración** o **Ventas** (chip *Usuario*, ícono `badge`). Vendedor: catálogo **viajantes** (chip *Viajante*, ícono `storefront`); se excluyen nombres vacíos, `-Ninguno-` o solo guiones/placeholders.
   - **Autocomplete:** la etiqueta (dropdown e input seleccionado) muestra **solo nombre y apellido** (usuarios) o el **Nombre del viajante** (vendedor), nunca `@cod` ni `· vía. N`. Los nombres tipo `Vendedor 1`, `Vendedor 2`, … `Vendedor 10` se ordenan de forma natural ascendente; los restantes se ordenan alfabéticamente sin distinguir mayúsculas. La **flecha abajo** (o el chevron `expand_more`) lista **todos** los resultados (`q=''`, `limit=50`); flecha arriba navega o abre la lista completa. Accesible con `role="combobox"`, `aria-expanded`, `aria-activedescendant` y scroll al ítem resaltado.

## Menú

Ventas → sección **Ajustes** → **Ajustes de ventas**.
