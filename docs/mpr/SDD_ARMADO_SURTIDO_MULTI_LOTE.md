# SDD — Armado surtido multi-pack (lote / carrito)

**Nombre del change:** `mpr-armado-surtido-multi-lote`  
**Estado:** implementado (apply 26/06/2026; verify manual AC-M1…M10 pendiente)  
**Fecha:** 26/06/2026  
**Depende de:** [SDD_ARMADO_SURTIDO_MVP.md](SDD_ARMADO_SURTIDO_MVP.md) (MVP implementado)

## 1. Objetivo

Permitir **varios armados surtidos de distintos packs** en una misma sesión de pantalla (`/mpr/armado-surtido/`), mediante un **carrito (lote pendiente)**, con validación de stock **al agregar** y **al ejecutar**, grabación **parcial** si falta stock en algún ítem del lote, y **modal** informando qué no se pudo registrar.

El operario arma pack por pack, los agrega al lote, revisa el resumen de consumo y confirma. Tras ejecutar, permanece en la pantalla (formulario y lote limpios salvo ítems fallidos, según reglas §6).

## 2. Decisiones de producto (cerradas)

| ID | Decisión | Valor acordado |
|----|----------|----------------|
| **D1** | Comprobante legacy | **A)** Un **MSTOCK por pack** (un `codigo_movimiento` + `nro_comprobante` por cada armado del lote). |
| **D2** | Depósitos | **A)** **Origen y destino compartidos** para todo el lote (cabecera única). |
| **D3** | Cuándo validar stock | **C)** Al **agregar al lote** (estimación) y al **ejecutar lote** (definitivo contra MySQL). |
| **D4** | Componente en varios packs | **Sí:** demanda **agregada** por `(id_articulo, deposito_origen)` en todo el lote. |
| **D5** | Atomicidad | **Parcial:** grabar los armados que alcancen stock; **modal** con los rechazados por stock insuficiente (u otro error por ítem). |
| **UI** | Patrón | **Opción 1 — Carrito de armados** (formulario actual + tabla lote pendiente). |

## 3. Alcance

### Incluido (fase 2.1)

| Incluido | Excluido |
|----------|----------|
| Carrito en UI (Alpine) con agregar / editar / quitar | Depósitos distintos por pack |
| Cabecera lote: operario, origen, destino, detalle opcional | Un solo MSTOCK para todo el lote |
| Resumen consumo agregado por componente | Plantillas de composición (fase SDD aparte) |
| API o validación server-side de stock al agregar (opcional GET) | Acordeón multi-pack simultáneo |
| `ejecutar_lote_armado_surtido` con resultado parcial | Tabla `MprArmadoSurtidoLote` (opcional fase 2.3) |
| Modal post-ejecución: éxitos + fallos | Límite duro de N packs (definir en implementación, sugerido 20) |

### Relación con MVP

- Sigue vigente: `tipo_art_fab = 'Fabricado 2da'`, `PrecioCostoxU/R` desde `articulo.PrecioCosto`, FIFO lote, `?id_lista=` opcional.
- `ejecutar_armado_surtido` se reutiliza **por ítem del lote** (refactor interno a cursor compartido cuando el ítem entra en la misma transacción MySQL del ítem exitoso).

## 4. Modelo funcional

### 4.1 Estructuras

**Cabecera del lote (compartida):**

```python
{
  "deposito_origen": int,
  "deposito_destino": int,
  "id_operario": int,
  "detalle": str | None,
  "id_lista_produccion": int | None,
}
```

**Ítem del lote (un armado = un pack distinto):**

```python
{
  "id_articulo_pack": int,
  "cantidad_packs": int,  # >= 1
  "lineas": [
    {"id_articulo": int, "cantidad_por_pack": int},  # >= 1, sin duplicados por pack
  ],
}
```

**Lote:**

```python
{
  "cabecera": CabeceraLote,
  "armados": [ItemLote, ...],  # >= 1 para ejecutar
}
```

### 4.2 Reglas de negocio

| Regla | Descripción |
|-------|-------------|
| R-M1 | Cada ítem del lote = un pack (`tipo_art_fab = 'Fabricado 2da'`) + composición propia. |
| R-M2 | No repetir el mismo `id_articulo_pack` en dos filas del lote (editar la fila existente). |
| R-M3 | Un `IDArt` no puede ser **pack** en un ítem y **componente** en otro ítem del mismo lote. |
| R-M4 | Demanda componente `D[id] = Σ (cantidad_por_pack × cantidad_packs)` sobre todos los ítems del lote. |
| R-M5 | Al agregar/editar ítem: validar `D[id] ≤ saldo_origen` (API o cálculo cliente con saldo inicial − reservado en lote). |
| R-M6 | Al ejecutar: por cada ítem en orden de la tabla, intentar armado; si falla stock → ítem a lista `fallidos`, continuar siguiente. |
| R-M7 | Cada ítem exitoso → 1 MSTOCK + 1 `MprArmadoSurtidoMovimiento` + líneas composición (como MVP). |
| R-M8 | Tras ejecución parcial: quitar del lote los ítems **exitosos**; mantener **fallidos** para corrección o quitar manualmente. |
| R-M9 | Mensaje toast/resumen + **modal** con tabla: pack, cantidad, motivo (stock / otro). |
| R-M10 | Si `?id_lista=` presente, cada armado exitoso incluye OPT en detalle/historial (igual MVP). |

### 4.3 Orden de ejecución (D5 parcial)

Orden recomendado: **orden de filas en el lote** (FIFO de captura). El primer pack consume stock; el siguiente ve saldo ya reducido en la misma sesión de ejecución.

- Cada ítem exitoso: transacción MySQL **commit** individual (o subtransacción con savepoint por ítem).
- Ítem fallido: **rollback** solo de ese ítem; no revierte MSTOCK ya confirmados de ítems anteriores.

Alternativa descartada: una sola transacción global (todo o nada) — contradice D5.

## 5. UI — Carrito (Opción 1)

### 5.1 Layout

```
┌─ Cabecera lote ─────────────────────────────────────┐
│ Operario* | Origen* | Destino* | Detalle (opc.)    │
└─────────────────────────────────────────────────────┘

┌─ Armar pack (formulario actual) ────────────────────┐
│ Pack terminado | Cantidad packs                     │
│ Composición (búsqueda + tabla)                      │
│                    [ Agregar al lote ]  [ Limpiar ] │
└─────────────────────────────────────────────────────┘

┌─ Lote pendiente (N armados) ────────────────────────┐
│ Cód. pack | Descripción | Cant. | # comp. | Acciones│
│ Resumen consumo agregado (componente → total u.)   │
└─────────────────────────────────────────────────────┘

[ Ejecutar lote (N) ]   [ Volver tablero / OPT ]
```

### 5.2 Comportamiento Alpine

| Acción | Efecto |
|--------|--------|
| **Agregar al lote** | Valida pack + composición + stock estimado (D3); push a `lote[]`; limpia formulario pack/composición. |
| **Editar** | Carga ítem en formulario superior; quita fila del lote hasta re-agregar. |
| **Quitar** | Elimina fila del lote; recalcula resumen consumo. |
| **Ejecutar lote** | POST JSON o campos indexados; overlay loading; respuesta abre modal. |

### 5.3 Validación al agregar (cliente + servidor)

**Cliente (inmediato):**

- Saldo API por componente en origen.
- `reservadoEnLote[id] = Σ demandas de ítems ya en carrito`.
- `disponibleEstimado = saldo − reservadoEnLote`.
- Si `demandaNueva > disponibleEstimado` → toast error, no agregar.

**Servidor (opcional GET `/mpr/api/armado-surtido/validar-lote/`):**

- Recibe lote actual + ítem candidato; devuelve `{ ok, conflictos: [{ id_articulo, necesario, disponible }] }`.

### 5.4 Modal post-ejecución

Título: **Resultado del lote**

| Sección | Contenido |
|---------|-----------|
| Éxitos | Pack, cantidad, comprobante `0001-000000XX`, código movimiento. |
| No grabados | Pack, cantidad, motivo (`Stock insuficiente de …`, etc.). |
| Acciones | Cerrar (mantener fallidos en lote), opcional «Copiar detalle». |

Patrón visual: modal canon MPR (mismo estilo que comprobante OPT / wizard).

## 6. Backend

### 6.1 Nuevas funciones (`mpr/services.py`)

```python
def calcular_demanda_agregada_lote(armados: List[Dict]) -> Dict[int, Decimal]:
    """Suma consumo por id_articulo componente en todo el lote."""

def validar_item_lote_armado_surtido(
    base_empresa, deposito_origen, item_lote, demanda_previa: Dict[int, Decimal]
) -> Tuple[bool, Optional[str], Dict[int, Decimal]]:
    """Valida un ítem contra stock; devuelve demanda acumulada actualizada si ok."""

def ejecutar_lote_armado_surtido(
    base_empresa, id_usuario, cabecera, armados: List[Dict]
) -> Dict[str, Any]:
    """
    Ejecuta armados en orden. Devuelve:
    {
      "exitosos": [{"id_articulo_pack", "cantidad_packs", "codigo_movimiento", "nro_comprobante"}],
      "fallidos": [{"id_articulo_pack", "cantidad_packs", "error": str}],
    }
    """
```

Refactor recomendado: extraer núcleo de `ejecutar_armado_surtido` a `_ejecutar_armado_surtido_tx(cursor, …)` para reutilizar dentro del loop sin abrir N conexiones.

### 6.2 Vista POST

- Ruta: mismo `ArmadoSurtidoView.post`.
- Detectar payload multi: presencia de `armados` (JSON) o `lote_count > 0`.
- Si multi → `ejecutar_lote_armado_surtido`; si no → flujo MVP actual (un pack) **o** deprecar single en favor de lote de 1 ítem (decisión implementación: unificar en lote siempre simplifica).

**Recomendación implementación:** unificar siempre en «lote de 1..N ítems»; el formulario single envía `armados: [ único ]`.

### 6.3 Respuesta POST (multi)

- **HTML:** redirect a misma pantalla + flash resumen + query `?resultado=lote` y JSON en sesión para modal.
- **Preferible (fase 2.1):** POST normal + contexto `resultado_lote_json` en template si flash/session.

Alternativa fase 2.2: POST fetch JSON + modal sin reload.

## 7. Escenarios de aceptación

| ID | Escenario | Resultado esperado |
|----|-----------|-------------------|
| AC-M1 | Agregar 2 packs distintos con stock suficiente | Lote muestra 2 filas; resumen consumo correcto. |
| AC-M2 | Mismo componente en 2 packs; suma supera saldo | Bloqueo al agregar el segundo (cliente) o al ejecutar (servidor). |
| AC-M3 | Lote 3 packs; el 2.º falla por stock | 1.º y 3.º MSTOCK OK; 2.º en modal fallidos; 2.º permanece en lote. |
| AC-M4 | Ejecutar lote vacío | Error «Agregue al menos un armado al lote». |
| AC-M5 | Pack no Fabricado 2da en lote | Rechazo ítem con mensaje claro. |
| AC-M6 | Con `?id_lista=` | Armados exitosos referencian OPT en historial. |
| AC-M7 | Componente con lote FIFO en 2 packs | Consumo ordenado por ítem; sin doble reserva fantasma. |

## 8. Tareas de implementación (orden sugerido)

| # | Tarea | Archivos principales |
|---|-------|----------------------|
| T1 | `calcular_demanda_agregada_lote` + tests unitarios | `mpr/services.py`, `mpr/tests/test_armado_surtido_lote.py` |
| T2 | Refactor `_ejecutar_armado_surtido_tx` desde `ejecutar_armado_surtido` | `mpr/services.py` |
| T3 | `ejecutar_lote_armado_surtido` (parcial D5) | `mpr/services.py` |
| T4 | API validación stock lote (opcional GET) | `mpr/views.py`, `mpr/urls.py` |
| T5 | UI carrito Alpine + resumen consumo | `mpr/templates/mpr/armado_surtido.html` |
| T6 | POST parse lote + modal resultado | `mpr/views.py`, include modal |
| T7 | Tests integración servicio lote (mock MySQL) | `mpr/tests/` |
| T8 | Actualizar manual + glosario | `docs/mpr/MANUAL_USUARIO_MPR.md`, `GLOSARIO_MPR.md` |

## 9. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Saldo desactualizado entre agregar y ejecutar | Revalidar en servidor al ejecutar; modal claro. |
| Orden de ejecución favorece primeros ítems | Documentar FIFO de filas; UI muestra orden. |
| POST grande | JSON en hidden `lote_json` (max ~20 ítems). |
| Doble submit | Deshabilitar botón + overlay loading (ya existe `mpr-post-loading`). |

## 10. Referencias

- MVP: [SDD_ARMADO_SURTIDO_MVP.md](SDD_ARMADO_SURTIDO_MVP.md)
- Pack/componente: [ARTICULO_PACK_COMPONENTE_MPR.md](ARTICULO_PACK_COMPONENTE_MPR.md)
- UI canon: [FUENTE_VERDAD_UI_REPORTES_MPR.md](../general/FUENTE_VERDAD_UI_REPORTES_MPR.md)

---

*Documento de diseño acordado con producto (26/06/2026). Especificación: [SPEC_ARMADO_SURTIDO_MULTI_LOTE.md](SPEC_ARMADO_SURTIDO_MULTI_LOTE.md). Diseño técnico: [DESIGN_ARMADO_SURTIDO_MULTI_LOTE.md](DESIGN_ARMADO_SURTIDO_MULTI_LOTE.md). Tareas: [TASKS_ARMADO_SURTIDO_MULTI_LOTE.md](TASKS_ARMADO_SURTIDO_MULTI_LOTE.md).*
