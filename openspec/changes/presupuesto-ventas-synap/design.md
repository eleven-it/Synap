# Design: Presupuesto de ventas (PRE) en Synap

## Technical Approach

Implementar el flujo PRE como **servicios de dominio** sobre MySQL legacy (`core.mysql_pool`, transacciones con commit intermedio de `codmov` cuando el SPEC lo exija). Exponer **API HTTP** y vistas bajo `ventas/` con el **mismo patrón de UI que TPV (`self_checkout`) y MPR**: páginas Django, vistas clase/función, JSON donde ya acostumbra el módulo de referencia, sin imponer SPA aparte. Permisos: `AdministraNETPermisosSistemaService`. PDF: módulo **`reports`** (`ReportDefinition`), documento operativo. Tipos: `core.utils.administranet_types`.

Referencia persistencia: `docs/general/SPEC_PRESUPUESTO_VENTAS_SYNAP.md`.

**UX vs VB6:** El comportamiento y datos del legado **no** obligan a copiar una interfaz que sea mala práctica o genere fricción. Synap puede **repensar** agrupación de campos, navegación y número de pasos siempre que se mantengan reglas de negocio, permisos y escritura MySQL (véase **§1.4** del SPEC).

## Decisiones de producto (cerradas)

| Tema | Decisión |
|------|----------|
| Alcance v1 | **Todo:** alta, modificación desde consulta, cambio fecha/número (`modificacion_comp`), lista/búsqueda de PRE. |
| Pedido desde PRE (`ped_presup`, etc.) | **Fase 2** (fuera de esta entrega). |
| Entrada en menú | Mismo criterio **granular** que el resto; configuración en **`/core/permisos-sistema/`** y pestaña **navbar** (`?tab=navbar`). |
| Convivencia VB6 | **Sin restricción:** PRE desde VB6 y desde Synap en paralelo. |
| Sesión | Mismo **contrato** que objetivos ventas / **core login** para desarrollos nuevos (`base_empresa`, usuario, `id_puesto`, etc.). |
| Informe PDF | **Primera versión:** replicar contenido del reporte legacy; **luego** iterar personalización. |
| Momento del PDF | Según **configuración** (empresa / preferencia; ver **`DESIGN_PUNTO10_PLANTILLAS_REPORTES.md`**). |
| Plantillas / variantes informe | **Un `ReportDefinition`** (`slug` estable, categoría **operational**); variantes vía **`config`** + payload (`codigo_movimiento`, `id_plantilla` si aplica); varias filas solo si pipelines irreconciliables. Detalle: **`DESIGN_PUNTO10_PLANTILLAS_REPORTES.md`**. |
| Percepciones | **Incluidas** en el alcance. Si el cronograma aprieta, valorar **sub-fase previa mínima** solo si bloquea el núcleo; preferencia un solo release con `percep_cli` / temporales alineados al SPEC. |
| Tests / BD | Entorno de **pruebas**; asumir **BD de test** mientras `DEBUG=True` en desarrollo (tests integración contra esa BD). |
| Licenciamiento / desactivación remota | **Capas:** entitlement → `ModuleConfig` / despliegue → menú por puesto → `permisos_sistema`. Infra del cliente: heartbeat + token firmado + gracia offline. **Servidor de tokens y panel admin SaaS = proyecto separado** (Synap solo cliente); ver **`DESIGN_PUNTO13_ENTITLEMENT_Y_DESACTIVACION_REMOTA.md`** y **`docs/general/SERVICIO_LICENCIAS_PROYECTO_SEPARADO.md`**. |

## Architecture Decisions

| Decisión | Opción elegida | Alternativas | Motivo |
|----------|----------------|--------------|--------|
| Ubicación código | App `ventas/` | Nueva app | Ya montada en URLs |
| Acceso MySQL | `mysql_cursor` / `get_connection` | ORM legacy | Estándar proyecto |
| Permisos menú | Registry + ABM `/core/permisos-sistema/` | Hardcode | Decisión explícita del equipo |
| Informe PDF | `ReportDefinition` en `reports` | Crystal / PDF suelto | Política Synap |
| Tipos columnas | `administranet_types` | Cast crudos | Regla proyecto |
| UI | Mismo criterio **TPV / MPR** | Solo API SPA | Decisión explícita |

### Supervisor, descuentos (V5) y precio vs costo (V11)

- Leer **`lim_desc_pie`**, **`lim_desc_renglon`**, **`Mod_Precio_Fact`** (y `mod_descuento_*` si aplica) desde **`permisos_sistema`** vía `obtener_permisos_puesto`.
- **Bypass** tipo VB6 “supervisor”: mismo criterio ya usado en **`ventas/views.py`** / **`reports`** — usuario AdministraNET con **`cod_usuario`** igual a **`supervisor`** (case-insensitive). Con ese usuario se omiten topes V5 y se permite V11 con **`Mod_Precio_Fact='No'`**; sin bypass, V11 sigue **`Mod_Precio_Fact`**.
- Opcional futuro: helper único “omite límites precio/descuento” si se unifica con otros campos de `usuarios`.

## Data Flow

```
UI (patrón TPV/MPR) ──HTTP──► ventas/views + APIs
       │                              │
       ▼                              ▼
 Sesión (contrato VO/login)         Servicio PRE
       │                              │
       ├── permisos_sistema (puesto)  ├── validaciones V1–V11
       └── usuario (supervisor cod)   └── MySQL: codmov → comp_ped → stockp → …
                                              │
                                              ├── percep_cli / temp (mismo alcance)
                                              └── reports → PDF (según config)
```

## File Changes (previsto)

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `ventas/services/presupuesto_legacy.py` (nombre definitivo al implementar) | Crear | Orquestación alta/modificación/numeración + percepciones |
| Servicio/listado `comp_ped` tipo PRE (filtros búsqueda) | Crear | Lista como **home** del módulo (patrón lista→detalle con estado y filtros; ver § punto 8) + API `GET` con query params |
| `ventas/views.py`, `ventas/urls.py` | Modificar | Lista PRE home, nuevo, detalle; APIs |
| `templates/ventas/...` | Crear | UI presupuesto |
| `reports/` | Crear/ajustar | `ReportDefinition` PRE (`slug` estable, operational); fixtures/migración datos catálogo; pipeline PDF según **`DESIGN_PUNTO10_PLANTILLAS_REPORTES.md`** |
| `ventas/tests/` | Crear | Integración con BD de pruebas si `DEBUG`/settings test |

## Interfaces / Contracts

- **Entrada API:** JSON cabecera §4 SPEC + líneas + flags sesión; percepciones alineadas a `percep_cli_temp` / flujo SPEC.
- **Permisos:** `obtener_permisos_puesto(base_empresa, id_puesto)` + menú granular desde core.

## Testing Strategy

| Capa | Qué | Cómo |
|------|-----|------|
| Unit | Validadores, límites desc, Mod_Precio_Fact | Tests directos |
| Integración | Secuencia MySQL PRE + percepciones | BD de pruebas, `DEBUG=True` en dev |
| API | HTTP | Cliente Django |

## Migration / Rollout

Sin migración PG obligatoria para núcleo PRE salvo **datos de catálogo** para `ReportDefinition` del PDF Presupuesto (fixtures/migración Django en `reports`). **Entitlement y kill switch remoto:** ver **§ Punto 13** (implementación transversal cuando exista servicio de licencia).

## Punto 8 — Entrada, lista y cliente (cerrado con respuestas producto)

| Respuesta | Contenido |
|-----------|-----------|
| **1** | **Solo PRE** hasta que Pedido/Remito existan en Synap. Shell tipo VB6 multi-comprobante → **fase 2:** `FASE2_VENTAS_HUB_COMPROBANTES.md`. |
| **2** | Objetivo **muchos clientes:** búsqueda **en servidor** con paginación/filtros (extender patrón `get_clientes` / API dedicada); no cargar todo el catálogo en cliente. |
| **3** | **Home del módulo = lista de presupuestos** con **columna Estado** (idea UX: documentos visibles con estado, crear nuevo desde la lista y filtrar — **sin imitar un producto concreto**); botón **Nuevo**; búsqueda/filtros por **cliente** y campos identificadores (número, fecha, `CodigoMovimiento`, etc. según contrato API). Rutas: lista → `nuevo/` → detalle `<codigo_movimiento>/`. |
| **4** | **Cliente:** datos maestros en MySQL **`cliente`** (servicios legacy); no hay módulo único Synap equivalente al ABM VB6 integrado en `ventas/`. UX: autocomplete robusto + enlace a ficha cuando exista; evitar duplicar ABM dentro del PRE (`DESIGN_PUNTO8_UX_AGENT_IA.md` § módulo cliente). |

Documentación detallada y checklist: **`DESIGN_PUNTO8_UX_AGENT_IA.md`**.

---

## Punto 10 — Plantillas e informe PDF Presupuesto (cerrado)

Resumen: **`DESIGN_PUNTO10_PLANTILLAS_REPORTES.md`** (`ReportDefinition` único operational, `config` + payload para variantes, v1 una salida con paridad de datos Crystal y permiso **`plantillas`**).

---

## Punto 13 — Entitlement, SaaS y desactivación remota (cerrado)

Documento completo: **`DESIGN_PUNTO13_ENTITLEMENT_Y_DESACTIVACION_REMOTA.md`** (incluye **proyecto aparte** para servidor de tokens + panel de control).

Resumen: mismas capas que arriba. **Emisión de tokens, API de licencia y UI de activación/revocación de clientes** se implementan **fuera del repo Synap**; este proyecto solo incorpora el **cliente** (settings, renovación, middleware). Desactivación remota en infra del cliente: HTTPS periódico, tokens firmados, gracia offline, opcional revocación publicada.

---

## Iteración pendiente

Ninguna decisión de producto pendiente para este cambio OpenSpec; la implementación del servicio de licencia es **transversal** y puede abrirse como trabajo aparte.

## Tareas de implementación

Checklist ordenado: **`tasks.md`** (incluye bloque paralelo para repositorio de licencias).
