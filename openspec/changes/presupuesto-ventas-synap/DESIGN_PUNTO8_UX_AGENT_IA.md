# Punto 8 — Entrada, hub y cliente: decisiones (UX + Agent IA)

Documento de apoyo al `design.md` del cambio **presupuesto-ventas-synap**.

---

## Decisiones de producto (cerradas — actualización)

| # | Tema | Decisión |
|---|------|----------|
| **1** | Shell VB6 multi-comprobante | **Solo PRE** en Synap hasta que existan los flujos Pedido/Remito en Synap. Documentado como **fase 2:** `FASE2_VENTAS_HUB_COMPROBANTES.md`. |
| **2** | Volumen de clientes | Objetivo explícito: **buscar entre muchos clientes** — búsqueda **servidor** (paginación/filtros), no depender de cargar todo el universo en el navegador. |
| **3** | Pantalla de entrada a Presupuesto | **Lista primero** (patrón UX: **ver documentos con su estado**, **crear uno nuevo** y **filtrar/buscar** sin depender de otra pantalla). **No** se trata de imitar un producto concreto; la implementación visual sigue **TPV/MPR/Synap**. Al entrar al módulo se listan presupuestos existentes con **columna Estado**; botón **Nuevo presupuesto**. La lista debe permitir **buscar/filtrar** por **cliente** y por **cualquier campo relevante** para identificar el movimiento (p. ej. número de comprobante, fecha, `CodigoMovimiento`, sucursal según negocio). |
| **4** | Módulo Cliente | Ver **§ Módulo cliente en Synap y buenas prácticas** más abajo. |

---

## Principios transversales (humanos y agentes)

0. **VB6 no es estándar de UX:** los formularios `administranet_vb6` describen **flujo y datos**; si la densidad, el MDI o el hub único **friccionan** o son antipatrón en web, la UI Synap **se rediseña** (SPEC §1.4). Persistencia y validaciones siguen alineadas al SPEC funcional.

1. **URLs nominales:** un recurso lógico por ruta (`lista`, `nuevo`, `/<id>`); evitar que el estado crítico viva solo en pestañas sin URL propia.
2. **API como contrato:** toda acción relevante tiene equivalente **HTTP + JSON** documentado; la UI es cliente del mismo contrato que usaría un agente (no reglas solo en JS).
3. **Servidor como fuente de verdad:** validación y defaults en backend; el agente no puede “saltarse” reglas confiando en el cliente.
4. **Errores estructurados:** respuestas `{ "code", "message" }` (mensajes en español) para parsing fiable en automatización.
5. **Idempotencia y reintentos:** donde sea posible (p. ej. consultas GET, borradores con token); reduce fallos en ejecuciones largas de agente.
6. **Evitar wizards opacos:** si hay pasos, cada paso debe poder reproducirse vía API o query params documentados.
7. **Documentación para herramientas:** tabla de endpoints en `docs/` o OpenAPI; facilita codegen y “skill” de agente sobre Synap.

---

## Por subpunto (sintetizado con decisiones anteriores)

### 1 — Entrada “nuevo PRE”: shell multipropósito vs PRE-only

| Criterio | Decisión |
|----------|----------|
| **v1** | **Solo PRE.** Sin hub `CargaComprobantesPed` hasta que Pedido/Remito existan en Synap. |
| **Fase 2** | Hub multi-comprobante documentado en **`FASE2_VENTAS_HUB_COMPROBANTES.md`**. |
| **Agent IA** | URLs claras: lista PRE → nuevo → detalle; sin simular menú SmartMenu VB6. |

### 2 — Selección de cliente (muchos registros)

| Criterio | Decisión |
|----------|----------|
| **Recomendación** | **API de búsqueda** con **paginación** y query `q` (y filtros adicionales si hace falta); **entrada por código** validada en servidor; debounce en UI; límites altos solo en servidor con índice/Búsqueda LIKE acotada. Patrón base: `core.services.administranet_stock.get_clientes` **extendido** para volumen (no cargar miles en una sola respuesta sin paginar). |
| **Agent IA** | `GET` con parámetros documentados (`q`, `page`, `page_size`); respuesta JSON estable. |

### 3 — Consulta / listado de PRE vs alta (lista como home)

| Criterio | Decisión |
|----------|----------|
| **Recomendación** | **Ruta principal** = **listado** de PRE con **estado** visible (`Estado` en `comp_ped`, etc.). Botón **Nuevo**. **Filtros/búsqueda global** en lista: cliente (nombre/código), número comprobante, fechas, y otros identificadores acordados (documentar en contrato API). **Alta** en ruta dedicada (`…/nuevo/`). **Detalle/edición** `…/<codigo_movimiento>/`. |
| **Agent IA** | `GET /api/.../presupuestos/?...` con mismos filtros que la UI; `POST` crear; `GET/PATCH` por id. |

### 4 — Sistema vs talonario

Sin cambio respecto al diseño previo: cabecera del formulario PRE + campo explícito en JSON validado en servidor.

### 5 — Acciones laterales (CC, ABM cliente, domicilios)

Enlaces profundos al dominio que exista; ver siguiente sección para **cliente**.

---

## Módulo cliente en Synap y buenas prácticas (respuesta punto 4)

**Situación actual:** los **clientes comerciales AdministraNET** viven en MySQL tabla **`cliente`** y se acceden desde servicios legacy (p. ej. `get_clientes` en `core/services/administranet_stock.py`). No hay en este repo una **app “Ventas → ABM Cliente”** completa equivalente al VB6 unificada bajo `ventas/`; en **PostgreSQL** existe el modelo **`Contact`** (`core/contacts`) para contactos genéricos — **no sustituye** al cliente legacy para reglas PRE sin un mapeo explícito.

**Buenas prácticas UX para PRE:**

1. **Búsqueda de cliente en emisión:** autocomplete + servidor para **muchos clientes**; mostrar código + nombre + dato útil (p. ej. CUIT si existe en consulta).
2. **No bloquear el flujo** si no hay ficha Synap: el usuario confirma cliente desde resultados de **`cliente`** MySQL.
3. **Enlace “Ver / editar cliente”:** si aún no hay pantalla Synap de ABM, usar **enlace documentado** (roadmap) o **solo lectura** de datos ya resueltos en cabecera PRE; evitar duplicar formulario completo dentro del PRE.
4. **Consistencia:** cuando exista módulo cliente Synap dedicado a legacy, unificar ahí CC/domicilios y enlazar desde PRE con **URL estable** (`?codigo=` o slug acordado).

---

## Checklist implementación (PRE)

- [ ] Lista PRE como **home** del módulo con columna **Estado** y filtros acordados.
- [ ] API lista PRE con los mismos filtros que la UI (cliente, número, fechas, …).
- [ ] API búsqueda cliente **paginada** para alto volumen.
- [ ] Cada acción crítica con ruta/endpoint documentado.
- [ ] Guardado PRE con **tipo sistema/talonario** explícito en JSON.

---

**Pendientes globales del cambio:** puntos **10** (plantillas reporte) y **13** (feature flag) en `design.md`.
