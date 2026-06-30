# SDD — Armado unificado 1ra/2da e imputación supervisor

**Nombre del change:** `armado-unificado-imputacion-1ra`  
**Estado:** propuesto (17/06/2026)  
**OpenSpec:** `openspec/changes/armado-unificado-imputacion-1ra/`  
**Depende de:** [SDD_ARMADO_SURTIDO_MVP.md](SDD_ARMADO_SURTIDO_MVP.md), [SDD_ARMADO_SURTIDO_MULTI_LOTE.md](SDD_ARMADO_SURTIDO_MULTI_LOTE.md) (implementados)

## 1. Objetivo

Unificar en Synap el armado de packs en **dos modos operativos independientes de OPT**, reutilizando la UX POS + carrito + lote ya validada en armado surtido:

| Modo UI | Origen | Destino | Packs | Composición |
|---------|--------|---------|-------|-------------|
| **Armado 1ra** | Semi elaborado | Terminado (SKU 1.ª) | `ensamblado = 'Si'` + BOM | Fija (`en_abm_formula`) |
| **Armado 2da** | 2.ª selección | Terminado (SKU 2.ª) | `tipo_art_fab = 'Fabricado 2da'` | Libre |

**Armado 2da** no se imputa a pedidos (venta oportunista posterior; SKU distinto al de 1.ª).  
**Armado 1ra** puede ejecutarse sin OPT; un **supervisor** imputa cada **MSTOCK** a la demanda de pedidos (agrupación en UI por **lote de armado**).

## 2. Decisiones de producto (cerradas)

| ID | Decisión | Valor acordado |
|----|----------|----------------|
| **D1** | Entrada canónica | Menú MPR **Armado 1ra** / **Armado 2da**; no recomendar armado desde `opt_detail` ni wizard paso 4 |
| **D2** | Lote | Un lote = un solo modo; **no mezclar** 1ra y 2da en el mismo carrito/ejecución |
| **D3** | OPT y armado 2da | Sin gates `opt_puede_armado_surtido`; `?id_lista=` opcional solo trazabilidad histórica, sin bloqueos |
| **D4** | Pedidos y 2da | Packs 2.ª **no** asocian pedido; no hay imputación supervisor para 2da |
| **D5** | SKU | Artículo 2.ª es **otro IDArt**; demanda 1.ª no se cruza con stock 2.ª |
| **D6** | Imputación 1ra | Por **movimiento MSTOCK**; UI agrupa por **lote de armado** ejecutado |
| **D7** | Quién imputa | Rol **supervisor** (permiso dedicado); operario solo arma |
| **D8** | Cierre OPT | `puede_cerrar` cuando **pendiente OPP = 0**; no exige armado previo en la OPT |
| **D9** | Naming UI | «Armado 1ra» / «Armado 2da» (evitar surtido/OPA/BOM en piso) |
| **D10** | MSTOCK | Un comprobante por pack exitoso (igual multi-lote actual) |

## 3. Alcance por fases

### Fase A — Armado unificado (P0)

| Incluido | Excluido |
|----------|----------|
| Ruta `/mpr/armado/?modo=1ra\|2da` (alias temporal `/mpr/armado-surtido/` → `modo=2da`) | Imputación supervisor |
| Toggle modo; vaciar carrito al cambiar | Refactor total `services.py` |
| Armado 2da: paridad funcional actual sin gates OPT | |
| Armado 1ra: BOM + carrito multi + validación stock semi | |
| Modelo `MprArmadoLote` + `modo` en movimientos Synap | |
| Quitar tarjetas armado en `opt_detail.html` | |
| Redirect `opt/<id>/armado/` → `/mpr/armado/?modo=1ra` | |
| Deprecar wizard paso 4 (enlace al menú) | |

### Fase B — Imputación supervisor 1ra (P0)

| Incluido | Excluido |
|----------|----------|
| Pantalla `/mpr/imputacion-armado-1ra/` | Imputación 2da |
| Lista MSTOCK Armado 1ra con `estado_imputacion = pendiente` | Asignación automática sin confirmación |
| Sugerencia FIFO por `id_articulo` sobre demanda abierta | |
| Confirmación por movimiento (o selección múltiple misma regla) | |
| Tabla `MprImputacionArmado` | |
| Permiso `mpr.imputar_armado_1ra` (o equivalente) | |
| Actualización `lista_produccion_detalle` / agrupada y `estado_pedido_opt` | |

### Fase C — OPT y reportes (P1)

| Incluido | Excluido |
|----------|----------|
| `estado_acciones_opt`: `puede_cerrar` solo OPP | |
| KPI tablero: «MSTOCK 1ra sin imputar» | |
| Informe producción 2da del día (opcional) | |

### Fase D — Documentación y limpieza (P1)

- [MANUAL_USUARIO_MPR.md](MANUAL_USUARIO_MPR.md) § armado
- [GLOSARIO_MPR.md](GLOSARIO_MPR.md)
- Eliminar código muerto: `opt_puede_armado_surtido`, `ArmadoOptView` tras periodo redirect

## 4. Modelo funcional

### 4.1 Flujo operativo

```text
PLANIFICACIÓN (sin armado en OPT)
  Demanda 1.ª → OPT → OPP → stock Semi / 2.ª

ARMADO (libre)
  Menú → Armado 1ra | Armado 2da
       → POS + carrito (modo fijo por lote)
       → Ejecutar lote → N × MSTOCK

POST-ADMIN (solo 1ra)
  Supervisor → Imputación armado 1ra
            → por cada MSTOCK: asignar a pedido/demanda (FIFO sugerido)
```

### 4.2 Cabecera e ítem de lote

Reutilizar estructuras de [SDD_ARMADO_SURTIDO_MULTI_LOTE.md](SDD_ARMADO_SURTIDO_MULTI_LOTE.md) añadiendo:

```python
{
  "modo": "1ra" | "2da",  # obligatorio; inmutable durante el lote
  "deposito_origen": int,  # semi (1ra) o 2.ª (2da) — validado vs modo
  "deposito_destino": int,  # terminado destino coherente con modo
  "id_operario": int,
  "detalle": str | None,
  "id_lote_armado": uuid | int,  # asignado al ejecutar
}
```

**Ítem lote 1ra:** composición desde BOM (solo lectura en UI; editable cantidad packs).  
**Ítem lote 2da:** composición libre (reglas R-M1…R-M10 actuales).

### 4.3 Reglas de negocio nuevas

| Regla | Descripción |
|-------|-------------|
| R-U1 | `modo=1ra` → origen = depósito Semi MPR; packs con BOM; componentes según `en_abm_formula` |
| R-U2 | `modo=2da` → origen = depósito 2.ª MPR; packs `tipo_art_fab = 'Fabricado 2da'` |
| R-U3 | Cambiar modo con ítems en carrito → confirmar y vaciar |
| R-U4 | Un lote no mezcla modos ni orígenes distintos al del modo |
| R-U5 | Armado 1ra exitoso → `estado_imputacion = pendiente` en registro Synap del MSTOCK |
| R-U6 | Armado 2da exitoso → sin cola de imputación |
| R-U7 | Imputación: `Σ cantidad_imputada ≤ cantidad_armada` del MSTOCK |
| R-U8 | Imputación reduce demanda en `lista_produccion_detalle` (pendiente) del pedido asignado |
| R-U9 | FIFO sugerido: pedidos con demanda abierta del mismo `id_articulo`, orden fecha/antigüedad |
| R-U10 | Cerrar OPT: `SUM(cantidad_pendiente_prod) = 0` en líneas OPT; ignorar armado |

### 4.4 Deprecaciones

| Artefacto actual | Acción |
|------------------|--------|
| `ArmadoOptView` (`/mpr/opt/<id>/armado/`) | Redirect + deprecar |
| Tarjetas armado en `opt_detail.html` | Eliminar CTAs |
| `opt_puede_armado_surtido` | Eliminar gates GET/POST |
| Wizard paso 4 armado | Enlace «Ir a Armado 1ra» |
| `?id_lista=` bloqueante en armado 2da | Opcional en POST; no validar OPP |
| `hay_restante_armar` en `puede_cerrar` | Quitar de condición de cierre |

## 5. Modelo de datos Synap (Django)

### 5.1 Evolución tablas existentes

| Modelo actual | Evolución propuesta |
|---------------|---------------------|
| `MprArmadoSurtidoMovimiento` | Renombrar o extender → `MprArmadoMovimiento` con `modo` (`1ra`/`2da`), `id_lote_armado` FK |
| `MprArmadoSurtidoLinea` | → `MprArmadoLinea` (sin cambio semántico) |
| `MprArticuloArmadoSurtido` | Mantener legacy; catálogo 2da sigue `tipo_art_fab` |

### 5.2 Nuevas tablas

**`MprArmadoLote`**

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID/PK | Identificador de sesión de ejecución |
| `base_empresa` | str | |
| `modo` | `1ra` \| `2da` | |
| `id_operario` | int | |
| `id_usuario` | int | Quien ejecutó |
| `deposito_origen` / `deposito_destino` | int | |
| `ejecutado_en` | datetime | |
| `cantidad_items` / `cantidad_exitosos` / `cantidad_fallidos` | int | Resumen post-lote |

**`MprImputacionArmado`**

| Campo | Tipo | Notas |
|-------|------|-------|
| `codigo_movimiento` | int | MSTOCK Armado 1ra (único por imputación parcial si aplica) |
| `id_articulo_pack` | int | |
| `cantidad` | int | Unidades imputadas en esta fila |
| `codigo_movimiento_pedido` | int | `comp_ped.CodigoMovimiento` |
| `id_lista_detalle` | int nullable | Si esquema lo permite |
| `origen_regla` | `FIFO` \| `MANUAL` | |
| `id_usuario_supervisor` | int | |
| `imputado_en` | datetime | |
| `notas` | str opcional | Ajuste manual |

Índice único sugerido: evitar doble imputación total del mismo MSTOCK (`codigo_movimiento` + suma cantidades).

### 5.3 Legacy MySQL

- Sin `ALTER` obligatorio en `lista_produccion_*` para Fase A.
- Imputación (Fase B) usa tablas existentes AdministraNET vía `services.py` y tipos `administranet_types`.

## 6. UI

### 6.1 Menú MPR

```text
Armado 1ra          → /mpr/armado/?modo=1ra
Armado 2da          → /mpr/armado/?modo=2da
Imputación armado 1ra → /mpr/imputacion-armado-1ra/   (solo supervisor)
```

Patrón visual: [FUENTE_VERDAD_UI_REPORTES_MPR.md](../general/FUENTE_VERDAD_UI_REPORTES_MPR.md) — reutilizar `armado_surtido.html` / includes.

### 6.2 Armado unificado

- **Selector modo** persistente (tabs o segmented control) con colores distintos 1ra vs 2da.
- Misma estructura: cabecera lote → formulario pack → carrito → ejecutar → modal resultado.
- **Armado 1ra:** selector pack filtra `ensamblado=Si`; al elegir pack, tabla componentes BOM (solo lectura); validar `max_packs` vs stock semi (lógica `get_lineas_armado_opt` / `armado_opt` reutilizada sin `id_lista`).
- **Armado 2da:** comportamiento actual.

### 6.3 Imputación supervisor

```text
┌─ Filtros ─────────────────────────────────────────┐
│ Fecha | Operario | Solo pendientes | Pack (búsqueda)│
└────────────────────────────────────────────────────┘

┌─ Lotes recientes (agrupación) ──────────────────────┐
│ Lote UUID | Fecha | Operario | # MSTOCK | Pendientes│
│ [Expandir] → lista MSTOCK del lote                  │
└────────────────────────────────────────────────────┘

┌─ MSTOCK pendiente ──────────────────────────────────┐
│ Comprobante | Pack | Cant. | Fecha | Operario       │
│ Sugerencia FIFO: Pedido 4521 — 10 u.                │
│ [Confirmar] [Ajustar manualmente]                   │
└────────────────────────────────────────────────────┘
```

## 7. Servicios y APIs

| Función / endpoint | Responsabilidad |
|--------------------|-----------------|
| `ejecutar_lote_armado(base_empresa, lote, modo)` | Generaliza `ejecutar_lote_armado_surtido` |
| `_ejecutar_armado_1ra_tx` | BOM fija; entrada pack terminado 1.ª |
| `listar_packs_armado_1ra` | Catálogo packs BOM |
| `listar_mstock_pendientes_imputacion` | MSTOCK modo 1ra sin imputación completa |
| `sugerir_imputacion_fifo` | Propuesta por `id_articulo` |
| `confirmar_imputacion_armado` | Persiste `MprImputacionArmado` + actualiza demanda |
| `POST /mpr/api/armado/validar-item-lote/` | Extiende API actual con `modo` |

## 8. Permisos y seguridad

| Permiso | Rol típico |
|---------|------------|
| Acceso MPR armado (existente) | Operario, supervisor |
| `mpr.imputar_armado_1ra` (nuevo) | Supervisor |

Validar `base_empresa` de sesión en todas las operaciones (patrón actual MPR).

## 9. Criterios de aceptación

### Armado unificado (Fase A)

| ID | Escenario | Resultado esperado |
|----|-----------|-------------------|
| AC-A1 | Ejecutar lote 2da desde menú sin `id_lista` | N MSTOCK; sin error OPT/OPP |
| AC-A2 | Intentar mezclar pack 1ra y 2da en carrito | Rechazo al cambiar modo o al agregar |
| AC-A3 | Armado 1ra pack sin stock semi | Ítem en fallidos; parcial si aplica |
| AC-A4 | `opt_detail` | Sin tarjetas «Armado desde OPT» |
| AC-A5 | GET `/mpr/opt/5/armado/` | Redirect a Armado 1ra |
| AC-A6 | Modal post-lote | Mismas columnas éxito que hoy (pack, saldos, comprobante) |

### Imputación (Fase B)

| ID | Escenario | Resultado esperado |
|----|-----------|-------------------|
| AC-B1 | MSTOCK 1ra pendiente visible para supervisor | Lista con comprobante y pack |
| AC-B2 | Confirmar FIFO | `MprImputacionArmado` + baja pendiente detalle |
| AC-B3 | Operario sin permiso | 403 en imputación |
| AC-B4 | Imputar cantidad > armada | Rechazo validación |
| AC-B5 | MSTOCK 2da | No aparece en cola imputación |

### OPT (Fase C)

| ID | Escenario | Resultado esperado |
|----|-----------|-------------------|
| AC-C1 | OPT con OPP completo, sin armado | `puede_cerrar = true` |
| AC-C2 | OPT con pendiente OPP > 0 | `puede_cerrar = false` |

## 10. Riesgos y mitigación

| Riesgo | Mitigación |
|--------|------------|
| MSTOCK 1ra sin imputar acumulados | KPI tablero + reporte supervisor |
| Usuarios con bookmarks legacy | Redirects 6 meses + manual |
| Divergencia stock vs demanda hasta imputar | Comunicar en capacitación; «Actualizar pedidos» sigue usando stock terminado |

## 11. Plan de rollback

1. Revert merge o flag `MPR_ARMADO_UNIFICADO=false`.
2. Restaurar rutas `armado-surtido` y `armado_opt`.
3. Tablas Synap nuevas no afectan legacy; opcional truncar `MprImputacionArmado`.

## 12. Referencias

- Iteración de producto: conversación 17/06/2026 (armado libre, SKU distintos, supervisor).
- [ARTICULO_PACK_COMPONENTE_MPR.md](ARTICULO_PACK_COMPONENTE_MPR.md)
- [SDD_ARMADO_SURTIDO_MULTI_LOTE.md](SDD_ARMADO_SURTIDO_MULTI_LOTE.md)
- OpenSpec: `openspec/changes/armado-unificado-imputacion-1ra/proposal.md`

## 13. Siguiente paso SDD

```text
/sdd-continue armado-unificado-imputacion-1ra
```

→ **spec** (`openspec/changes/.../specs/`) + **design.md** + **tasks.md**
