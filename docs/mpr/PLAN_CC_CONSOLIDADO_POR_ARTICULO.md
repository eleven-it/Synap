# Plan — Control de calidad consolidado por artículo

**Fecha:** 20/08/2026  
**Estado:** Plan de producto e implementación (sin código aún)  
**Pantalla:** `/mpr/tablero-produccion/clasificacion-produccion/`  
**Principio rector:** el stock físico y el ledger histórico no se reescriben. El cambio es de **cómo se clasifica de ahora en más** y de **cómo se lee** lo ya guardado.

Este documento es la fuente de verdad del alcance cerrado con producto. La implementación no debe ampliarlo ni relajar los controles de saldo.

---

## Quick path

1. **No tocar** `stock_deposito` ni filas históricas de `mpr_transicion_lote`.
2. **Cambiar** la grilla, el POST de confirmación y el borrador.
3. **Confirmar** en transacción **por artículo** contra el saldo vivo de Depósito Producción (nunca best-effort mixto).
4. **Verificar** con snapshots de saldo + ledger **antes y después** en base de prueba, y con tests que cubran histórico + huérfano + 2da por operario.

Si un paso mueve stock “para acomodar el modelo”, está mal. El stock ya está bien; lo que estaba mal era la granularidad de carga.

---

## 1. Qué queda cerrado

El parte ya guarda quién fabricó qué y en qué máquina. El control de calidad **clasifica el saldo físico** de Depósito Producción; no vuelve a partir el semi por operario ni por máquina.

| Tema | Decisión |
|------|----------|
| Unidad visual | Un **bloque por artículo** (día completo). Sin columna máquina. Sin filtro Turno. |
| Columna cantidad | **Saldo disponible en Depósito Producción** de ese artículo (no parte+extra). |
| Semi elaborado | Un solo ingreso por artículo. Ledger **sin** `id_operario` ni `id_mpr_turno`. |
| 2da / desperdicio | Por **operario + turno** del parte del día. Sin máquina. |
| Artículo en parte | Lista de operarios (máquinas colapsadas: mismo operario+turno = una fila). |
| Artículo **sin** parte, **con** saldo Producción | Una fila, **solo Semi**. 2da/desperdicio deshabilitadas. |
| Tope | `semi + Σ 2da + Σ desperdicio ≤ saldo vivo Producción` del artículo. |
| Solo pendiente | Oculta artículos con saldo 0. Dentro del bloque, oculta operarios con 2da/desperdicio ya confirmado. |
| Ver roster | Default. Incluye bloques en saldo 0 (solo lectura) y operarios ya confirmados. |
| Bloqueo del parte | Solo turnos con **2da o desperdicio** nuevos. Semi no bloquea. Histórico: ver §5. |
| Histórico | **No migrar** ledger. Al leer, agregar Semi del día. |
| Borradores abiertos | **No migrar**. Incompatibles; se descartan o se piden recargar. |

---

## 2. Invariantes (no negociables)

Estas reglas valen antes, durante y después del deploy. Si un PR las rompe, no entra.

### I1 — El saldo físico es la autoridad

- Fuente del número en pantalla y del tope: `stock_deposito` del depósito con `tipo_mpr = Produccion`.
- Nunca usar el parte como tope de stock.
- Nunca “reconstruir” Producción desde el parte para mostrar la columna.

### I2 — Confirmar solo mueve lo que el usuario acaba de cargar

- El POST compara **solo el lote actual** contra el saldo **vivo** (igual que el fix del 08/07/2026: no sumar lo ya clasificado otra vez).
- `Σ clasificado_ahora(artículo) ≤ saldo_Producción(artículo)` en el momento del lock.

### I3 — El ledger histórico es de solo lectura

- Prohibido `UPDATE`/`DELETE` masivo de `mpr_transicion_lote` para “consolidar Semi”.
- Prohibido backfill de `id_operario = NULL` en filas viejas.
- Prohibido rehacer MSTOCK de días cerrados.

### I4 — Borrador no mueve stock

- Guardar borrador = solo tablas `mpr_clasificacion_borrador*`.
- Cero MSTOCK, cero `stock_deposito`, cero `mpr_transicion_lote`.

### I5 — Atomicidad por artículo al confirmar

Hoy `transferir_stock_lote` es **best-effort sin `atomic()`**: un destino puede salir y otro no, y el borrador igual se borra. En este modelo eso es inaceptable (Semi a nivel artículo + 2da por operario en el mismo guardado).

- Todas las líneas de **un mismo artículo** (Semi + 2da + scrap) entran en **una transacción**.
- Si falla cualquier destino de ese artículo: rollback de ese artículo, el resto puede seguir.
- El borrador de un artículo **no se borra** si ese artículo falló.

### I6 — 2da y desperdicio sin operario no existen

- Sin fila de parte (operario+turno) no hay POST de 2da/scrap.
- El servidor ignora y rechaza claves 2da/scrap de artículos huérfanos.

---

## 3. Modelo actual vs modelo nuevo

### 3.1 Grilla

| | Hoy | Nuevo |
|---|---|---|
| Fila | máquina × artículo × turno × operario | bloque artículo; subfilas operario+turno |
| Semi / 2da / scrap | las tres por celda | Semi del artículo; 2da/scrap por operario |
| Cantidad mostrada | parte de la celda + extra del artículo | saldo Depósito Producción |
| Universo | solo celdas del parte del día | parte del día **∪** artículos con saldo Producción > 0 **∪** (roster) CC confirmado hoy |
| Encabezado | Fecha + Turno opcional | Solo Fecha (+ buscador, Solo pendiente, Docenas\|Pares) |

### 3.2 Persistencia confirmada (`mpr_transicion_lote`)

Las **columnas no cambian**. Cambia el convenio de escritura:

| Destino | Hoy | Nuevo |
|---------|-----|-------|
| Semi | `id_operario` + `id_mpr_turno` (siempre) | `id_operario = NULL`, `id_mpr_turno = NULL` |
| 2da / Scrap | operario + turno; sin máquina | igual (operario + turno; sin máquina) |
| Huérfano | no entra (el POST exige parte) | solo Semi, sin operario ni turno |
| `cantidad_extra` | split parte vs extra por celda | altas nuevas: `0` (el tope ya no es el parte) |

### 3.3 Borrador (único DDL real)

Hoy no entra el modelo: cabecera `(fecha, turno)`, línea `(artículo, operario, máquina)` con las tres cantidades juntas, `id_operario NOT NULL`.

Nuevo (vía catálogo `mpr_core_tables`, no SQL suelto):

- Cabecera: **una por fecha** (`UNIQUE (fecha_produccion)`).
- Líneas de dos tipos:
  - Semi: `id_articulo`, `id_operario NULL`, `id_mpr_turno NULL`, `cant_semi > 0`, 2da/scrap = 0.
  - 2da/scrap: `id_articulo`, `id_operario`, `id_mpr_turno`, `cant_2da`/`cant_scrap`, `cant_semi = 0`.
- `id_mpr_maquina` deja de formar la UK (siempre 0 o se elimina de la UK).
- `id_operario` pasa a NULL.

Borradores abiertos al corte: **no se convierten**. Al abrir la grilla consolidada (o al confirmar un artículo), si existe cabecera vieja `(fecha, turno)` se **elimina** automáticamente; no se muestra aviso ni se precargan cantidades del shape legacy.

---

## 4. Cómo se lee el histórico (sin tocarlo)

### 4.1 Semi del bloque (Ver roster / solo lectura)

```text
semi_mostrar(artículo, fecha) =
    SUM(cantidad) FROM mpr_transicion_lote
    WHERE id_articulo = ?
      AND fecha_produccion = ?
      AND tipo_origen = 'Produccion'
      AND tipo_destino = 'SemiElaborado'
```

Da igual que las filas viejas tengan operario. El usuario ve **un** número en **Cargado** (docenas y pares enteros). El detalle por operario sigue en la tabla para auditoría. Los casilleros de carga nueva no se rellenan con ese histórico (evitar doble POST).

### 4.2 2da / desperdicio por operario

```text
2da/scrap(artículo, fecha, operario, turno) =
    SUM(cantidad) ... tipo_destino IN ('2daSeleccion','Scrap')
    AND id_operario = ? AND id_mpr_turno = ?
```

Esto **ya es** la clave del ledger (sin máquina). Se termina el reparto visual entre máquinas (`_consumir_desglose_contra_capacidad_maquina`) para la UI nueva.

### 4.3 Artículo “completo” (solo lectura)

Un bloque está en solo lectura cuando `saldo_Producción = 0` **y** hay CC confirmada ese día (desglose del §4.1–4.2). El extra de Producción de **otro** artículo no reabre este bloque.

### 4.4 Bloqueo del parte (compatibilidad)

Regla dual, **sin fecha de corte en datos**:

```text
turno T de fecha F queda bloqueado en el parte SI:
  A) existe fila CC de F+T con tipo_destino IN (2daSeleccion, Scrap)
  O
  B) existe fila CC de F+T con tipo_destino = SemiElaborado
     AND id_operario IS NOT NULL          -- shape viejo
```

- Semi **nuevo** (`id_operario NULL`, `id_mpr_turno NULL`) no dispara A ni B → no bloquea turnos.
- Semi **histórico** (con operario y turno) sigue bloqueando ese turno (B).
- No hace falta backfill.

---

## 5. Controles (el núcleo del cambio)

### 5.1 Antes de escribir (servidor)

Orden fijo. Si uno falla, ese artículo no entra a transferencia.

| # | Control | Qué evita |
|---|---------|-----------|
| C1 | Releer saldo Producción **en la misma transacción** (`SELECT … FOR UPDATE` de `stock_deposito` del artículo + depósito Producción) | Carrera entre dos clasificadores |
| C2 | `qty_semi + Σ qty_2da + Σ qty_scrap ≤ saldo_lock` | Sobregiro de Producción |
| C3 | Cantidades ≥ 0, enteros (pares), tipos AdministraNET (`to_int_or_none` / `to_decimal_or_none`) | Basura en DECIMAL |
| C4 | 2da/scrap solo si existe celda de parte `(artículo, operario, turno)` ese día (máquinas ya colapsadas) | Atribuir calidad a quien no fabricó hoy |
| C5 | Huérfano: rechazar cualquier 2da/scrap; exigir saldo > 0 | Inventar trazabilidad |
| C6 | Semi del POST es **una** clave por artículo (`semi_{id_articulo}`). Ignorar `semi_*_op_*` si vinieran | Clientes viejos / POST manipulado |
| C7 | No clasificar destinos con qty 0 (no insertar filas vacías) | Ledger ruidoso |
| C8 | Suma del artículo en el POST vs hidden `max` de UI: **ganar siempre el saldo de BD** | Hidden manipulable (ya existe; mantener) |

### 5.2 Durante la escritura

| # | Control | Qué evita |
|---|---------|-----------|
| C9 | `atomic()` **por artículo**: Semi + todas las 2da/scrap de ese artículo | Semi acreditado y 2da no (o al revés) con stock a medias |
| C10 | MSTOCK + `stock_deposito` + `mpr_transicion_lote` en esa misma TX (como `transferir_stock_entre_etapas`, no un best-effort suelto encima) | Ledger sin movimiento o movimiento sin ledger |
| C11 | `cantidad_extra = 0` en altas nuevas | Reintroducir el split parte/extra como tope |
| C12 | `id_usuario` = quien guardó; `id_operario` = fabricante **solo** en 2da/scrap | Contaminar Semi con operario |

### 5.3 Después de escribir

| # | Control | Qué evita |
|---|---------|-----------|
| C13 | Borrar borrador **solo** de artículos confirmados OK | Perder carga si hubo fallo parcial entre artículos |
| C14 | Recalcular saldo Producción y fallar el test si `saldo_antes − qty ≠ saldo_después` | Drift silencioso |
| C15 | `SUM(cantidad)` del lote insertado = qty del POST de ese artículo | Filas duplicadas |
| C16 | No dejar `tipo_destino = SemiElaborado` con `id_operario NOT NULL` en **altas nuevas** (assert de test) | Regresión al shape viejo |

### 5.4 Lo que el código actual hace mal y este plan corrige

1. **`transferir_stock_lote` sin atomic** + mensaje “parcial” + **borra el borrador igual**. Debe dejar de usarse así para CC.
2. **POST exige `fabricado_celda > 0`**: bloquea huérfanos. Hay que ramificar: con parte vs solo saldo.
3. **Tope por celda (`atribuible + extra pool`)** permite clasificar de más a nivel artículo si se suma mal entre filas. El tope único es el saldo lockeado.
4. **Filtro turno** en GET/POST parte el día; se elimina. El POST no acepta `turno_id` como alcance de Semi.

---

## 6. Registro de riesgos

| ID | Riesgo | Impacto | Prob. | Mitigación | Detección |
|----|--------|---------|-------|------------|-----------|
| R1 | Reescribir histórico Semi a `id_operario NULL` | Pierde auditoría de rendimiento viejo; no cambia stock si se hace mal el MSTOCK | Baja si se prohíbe | I3 + code review: cero scripts de UPDATE masivo | `COUNT(*)` Semi con operario **antes = después** del deploy |
| R2 | Double-spend de Producción (dos POST a la vez) | Saldo negativo o rechazo a destiempo | Media | C1 lock de fila `stock_deposito` | Test de concurrencia o al menos lock documentado + prueba manual |
| R3 | Best-effort: Semi OK, 2da fail | Stock en Semi, 2da no, borrador perdido | Alta hoy | C9 + C13 | Test: mock fallo en 2da ⇒ saldo Producción intacto **y** sin fila Semi |
| R4 | Usar parte como tope y dejar remanente de días previos sin clasificar | Saldo Producción “invisible” | Alta si se copia lógica vieja | I1; universo ∪ saldo > 0 | Test huérfano con stock y sin parte |
| R5 | Huérfano con 2da en POST manipulado | Scrap/2da sin fabricante | Media | C5–C6 | Test POST huérfano + seg2da ⇒ 400/mensaje, saldo igual |
| R6 | `turno_tiene_control_calidad` sigue contando Semi nuevo | Bloquea todos los turnos del día al guardar solo Semi | Alta | Regla dual §4.4 | Test: solo Semi nuevo ⇒ parte de mañana/tarde/noche **editable** |
| R7 | Regla dual mal implementada: desbloquea parte de días con CC viejo solo-Semi | Se reabre parte ya cerrado | Media | Rama B del §4.4 | Test con fixture Semi histórico (`id_operario` set) ⇒ parte bloqueado |
| R8 | Borrar borradores viejos al migrar DDL | Pérdida de carga no confirmada | Media | No migrar; aviso UI | Checklist cutover |
| R9 | Reporte rendimiento: Semi nuevo no aparece por operario | KPI de 1ra por persona cae a 0 en días nuevos | Segura (es el producto) | Documentar; el gráfico apila 2da+scrap; Semi va a un total de artículo si se necesita | Revisar `sumar_clasificado_rendimiento_operario` (`id_operario IS NOT NULL`) |
| R10 | Fabricando / acreditado usa CC por operario | Cupo del tablero desfasado | Media | Revisar `acreditado = max(stock, clasificado CC, partes)`; el clasificado CC **agregado por artículo** no cambia si se suma `cantidad` sin filtrar operario | Tests tablero existentes + uno con Semi `id_operario NULL` |
| R11 | Extra pool viejo + saldo nuevo = doble tope | Se clasifica de más o de menos | Media | Dejar de llamar `_extra_pool_clasificacion_por_articulo` / `_max_clasificable_celda` en el flujo nuevo | Test: parte 100, saldo Prod 150 → tope 150 |
| R12 | `cantidad` vs `cantidad_extra` en lecturas de “cuánto se clasificó” | Si alguien suma solo `cantidad` y extra estaba aparte… hoy `cantidad` **incluye** el total de la fila y `cantidad_extra` es desglose. No cambiar el significado de `cantidad` | Baja | Altas nuevas: `cantidad = qty`, `cantidad_extra = 0` | Assert en insert |
| R13 | Artículos con saldo Producción de **otro origen** (ajuste, traslado) entran al CC | Operación válida (producto lo pidió) pero sorprende | — | Universo explícito; Solo pendiente los muestra | QA planta |
| R14 | Planilla impresa A4 (máquinas) se interpreta como la grilla CC | Confusión de dos pantallas | Baja | Fuera de alcance; no cambiar planilla en este plan | — |

---

## 7. Impacto por tabla (qué se toca / qué no)

| Tabla | ¿DDL? | ¿Datos viejos? | Escritura nueva |
|-------|-------|----------------|-----------------|
| `stock_deposito` | No | No | Solo el movimiento normal Producción → destino |
| `movimiento_stock` / MSTOCK | No | No | Igual que hoy, dentro de la TX del artículo |
| `mpr_transicion_lote` | No (columnas ya sirven) | **No tocar** | Semi sin operario/turno; 2da/scrap con ambos |
| `mpr_parte` / `mpr_parte_linea` | No | No | Solo lectura (lista de operarios) |
| `mpr_clasificacion_borrador` | **Sí** | No migrar | Una cabecera por fecha |
| `mpr_clasificacion_borrador_linea` | **Sí** | No migrar | Semi vs 2da/scrap en tipos de línea |
| `deposito` | No | No | Lookup `tipo_mpr = Produccion` |

DDL del borrador: función dedicada o extensión de `run_mpr_core_tables_mysql` en `core/services/legacy_mysql_schema/catalog.py` + SQL en `mpr/sql/007_…sql`. No ALTER suelto en apps.

Índice recomendado (idempotente, no cambia semántica):

```sql
-- lectura Semi del día
INDEX idx_mpr_tl_fecha_art_dest (fecha_produccion, id_articulo, tipo_destino)
```

---

## 8. Flujo de guardado (confirmación)

```text
POST confirmar
  parsear:
    semi_{id_articulo}  (docenas/pares → unidades)
    seg2da_{id_articulo}_op_{id_operario}_t_{id_turno}
    scrap_{id_articulo}_op_{id_operario}_t_{id_turno}
  agrupar por id_articulo
  para cada artículo:
    BEGIN
      lock saldo Producción
      validar C2–C6
      transferir Semi (si qty>0)  → transicion_lote id_operario NULL
      transferir cada 2da/scrap   → transicion_lote con operario+turno
    COMMIT o ROLLBACK ese artículo
  borrar líneas de borrador de artículos OK
  feedback: éxito total / éxito parcial (otros artículos) / error
```

Nombres de POST viejos (`semi_{art}_op_{op}_t_{t}_m_{m}`) **no** se interpretan como Semi. Si aparecen, se ignoran (C6) para no clasificar de más.

---

## 9. UI (alcance, sin rediseño de marca)

Canon: la pantalla actual de CC (`clasificacion_produccion.html` + includes), no Objetivos de venta / Presupuestos.

- Quitar combo Turno del encabezado.
- Columna: etiqueta **Saldo producción** (o equivalente claro); un número consolidado (docenas/pares según toggle).
- Artículo con `rowspan` sobre las filas de operario.
- Semi: un control (docenas+pares) con rowspan del bloque.
- 2da/desperdicio: controles por fila de operario.
- Huérfano: una fila, Semi editable, 2da/desperdicio no editables (texto “Sin operario en el parte”).
- Sin `alert`/`confirm` nativos; mismos modales / `mprShowAviso` / overlay de espera.
- Footer: Guardar borrador / Guardar control de calidad; deshabilitar si no hay editables.

---

## 10. Reportes y Fabricando

| Consumidor | Qué hacer |
|------------|-----------|
| Rendimiento por operario | Sigue filtrando `id_operario IS NOT NULL`. Semi nuevo no entra (producto). 2da/scrap sí. Documentar en `REPORTES_MPR.md` y glosario. |
| Clasificado agregado (tablero, pendientes) | Sumar `cantidad` por artículo **sin** exigir operario. Cubrir con test un Semi `NULL`. |
| `fecha_tiene_control_calidad` | Sigue: existe cualquier fila de la fecha (Semi huérfano también cuenta). OK. |
| `turno_tiene_control_calidad` | Reemplazar por la regla dual §4.4. |
| Planilla impresa / parte analista | Fuera de alcance. |

---

## 11. Fases de implementación (orden seguro)

No implementar UI completa antes de los invariantes de saldo.

| Fase | Qué | Criterio de salida | Riesgo que cierra |
|------|-----|--------------------|-------------------|
| **0. Baseline** | Script de auditoría (solo SELECT) en base de prueba: conteos ledger, muestra de saldos Producción vs `SUM(CC)` del día | Informe guardado en `docs/mpr/` o adjunto QA | R1 |
| **1. Tests primero** | Fixtures: histórico Semi-con-operario; 2da por operario; huérfano; solo Semi nuevo no bloquea parte; POST 2da en huérfano rechazado; TX rollback si falla 2da | Rojo | R3 R5 R6 R7 |
| **2. DDL borrador** | `007` + catálogo; app lee/escribe shape nuevo; ignora borrador viejo | Tests borrador; `apply_mpr_core_tables` idempotente | R8 |
| **3. Servicio grilla** | Universo ∪ saldo; colapso máquinas; Semi agregado; Solo pendiente | Tests `construir_grilla_clasificacion_produccion` | R4 R11 |
| **4. POST confirmar** | Parser nuevo, lock, atomic por artículo, `cantidad_extra=0`, huérfanos | Tests `RegistrarClasificacionProduccionView` + saldo | R2 R3 R5 |
| **5. Bloqueo parte** | Query dual | Tests roster/parte | R6 R7 |
| **6. UI** | Encabezado, rowspan, huérfano, filtros | Tests de template / humo contenedor | — |
| **7. Reportes/docs** | Rendimiento, glosario, manual §5, `DOCENAS_…` | Docs en el mismo cambio | R9 R10 |
| **8. Verify** | `e2e_mpr_trazabilidad` + checklist §13 en empresa de prueba | Saldos fase a fase | I1 I2 |

TDD: cada fase 1–5 tiene test rojo antes del código de producción.

---

## 12. Matriz de pruebas (mínimo)

### 12.1 Saldos (obligatorio)

| Caso | Setup | Acción | Esperado |
|------|-------|--------|----------|
| S1 | Prod = 120 pares | Semi 120 | Prod 0, Semi 120, 1 fila ledger `id_operario NULL` |
| S2 | Prod = 120; parte Luis 80, Mario 40 | Semi 100 + 2da Luis 20 | Prod 0; ledger Semi 100 sin op; 2da Luis 20 |
| S3 | Prod = 120 | Semi 100 + 2da 30 | **Rechazo**; Prod sigue 120; **cero** filas nuevas |
| S4 | Huérfano Prod = 50 | Semi 50 | Prod 0; sin 2da |
| S5 | Huérfano Prod = 50 | POST 2da 10 | Rechazo; Prod 50 |
| S6 | Prod = 150; parte del día 100 | Mostrar / tope 150 | No 100 |
| S7 | Fallo inyectado en 2da tras validar | Confirmar Semi+2da | Rollback: Prod intacto, sin Semi |
| S8 | CC histórico Semi 60 con operario; Prod 0 | Abrir roster | Semi mostrado 60 (suma); **no** insert |
| S9 | Dos artículos; el 2º excede saldo | Confirmar lote | Artículo 1 OK; 2 rollback; borrador del 2 intacto |

### 12.2 Comportamiento

| Caso | Esperado |
|------|----------|
| B1 | Sin filtro turno en GET |
| B2 | Mismo operario en 2 máquinas → una fila 2da |
| B3 | Solo pendiente oculta artículo saldo 0 |
| B4 | Solo pendiente oculta operario con 2da confirmada; el bloque sigue si hay saldo |
| B5 | Solo Semi nuevo → parte de todos los turnos **editable** |
| B6 | Fixture Semi viejo con operario+turno → ese turno del parte **bloqueado** |
| B7 | Borrador no toca `stock_deposito` |
| B8 | `sumar_clasificado_rendimiento_operario` no suma Semi `NULL`; sí suma 2da |

### 12.3 Auditoría pre/post deploy (SELECT, no UPDATE)

Ejecutar en cada `base_empresa` de prueba **antes** del primer confirm nuevo y **después** de una batería S1–S9 (los conteos de histórico no deben moverse).

```sql
-- A. Histórico intacto (guardar resultado)
SELECT tipo_destino,
       SUM(id_operario IS NOT NULL) AS con_operario,
       SUM(id_operario IS NULL) AS sin_operario,
       COUNT(*) AS filas,
       SUM(cantidad) AS qty
FROM mpr_transicion_lote
WHERE tipo_origen = 'Produccion'
  AND tipo_destino IN ('SemiElaborado','2daSeleccion','Scrap')
GROUP BY tipo_destino;

-- B. Saldos Producción de una muestra de artículos (ids de la batería)
-- comparar con stock_deposito del depósito tipo_mpr = Produccion
```

**Gate de deploy:** A.con_operario y A.qty de filas **anteriores al corte** no bajan. Las filas nuevas Semi aumentan `sin_operario` y `qty` en la medida de las pruebas, no “reparten” las viejas.

---

## 13. Cutover y rollback

### Cutover

1. Aplicar DDL borrador (`apply_mpr_core_tables`) en la empresa.
2. Desplegar código (grilla + POST nuevos juntos; no dejar UI nueva con POST viejo).
3. Aviso: borradores del día se pierden / no precargan.
4. No hay job de datos.

### Rollback de código

- Revertir el deploy de app.
- Ledger nuevo (Semi sin operario) **queda**; la grilla vieja al leer:
  - Semi `NULL` no aparece en celdas por operario → **hueco visual** del Semi ya movido a depósito.
- Por eso el rollback de código **después de confirmar CC nuevo** no es limpio. Mitigación: probar en Staging/empresa de prueba; en producción, ventana corta y no confirmar CC masivo el primer día si hay duda.
- Rollback de **DDL** del borrador: las tablas nuevas pueden convivir; la app vieja ignora cabeceras sin turno. No dropear en caliente.

### Lo que nunca es rollback

- “Pasar Semi nuevo a filas por operario prorrateando el parte.” Prohibido (rompe I3 y no recupera stock).
- Ajustar `stock_deposito` a mano para “cuadrar el plan”. Solo movimiento de stock estándar si producto lo pide **después**, como hoy.

---

## 14. Criterios de aceptación

- [ ] Un artículo con 3 máquinas y 3 turnos se ve como **un** bloque; saldo = Depósito Producción.
- [ ] Semi se guarda **una vez** por artículo, `id_operario` y `id_mpr_turno` nulos.
- [ ] 2da/desperdicio se guardan por operario+turno; dos máquinas del mismo operario no duplican.
- [ ] Artículo solo en Producción, sin parte: solo Semi; 2da/scrap imposibles.
- [ ] `semi + 2da + scrap > saldo` no mueve nada de ese artículo.
- [ ] Fallo a mitad de un artículo no deja stock ni ledger a medias.
- [ ] Conteos de `mpr_transicion_lote` **con operario** previos al corte no disminuyen.
- [ ] Parte: solo-Semi nuevo no bloquea; 2da sí; Semi histórico con operario sí.
- [ ] Borrador no genera MSTOCK.
- [ ] Manual, glosario, `DOCENAS_CLASIFICACION_OPERARIO_MPR.md` y este plan coinciden.

---

## 15. Fuera de alcance

- Planilla A4 de máquinas (`construir_datos_planilla_control_calidad`).
- Corrección post-CC desde la grilla (sigue siendo transferencia interna / movimiento de stock).
- Prorrateo de Semi a operarios.
- Trazabilidad de 2da/scrap sin parte.
- Filtro por turno.
- Migración/compactación de ledger histórico.
- Rediseño visual fuera del chrome actual de CC.

---

## 16. Código y docs a tocar (mapa)

| Área | Paths |
|------|--------|
| Grilla | `mpr/services.py` `construir_grilla_clasificacion_produccion` y helpers de atribuible/extra (dejar de usarlos como tope) |
| POST | `mpr/views.py` `RegistrarClasificacionProduccionView`, `_clasificacion_*_desde_post` |
| Transferencia | `transferir_stock_lote` o wrapper **atómico por artículo** (no reutilizar best-effort para CC) |
| Ledger | `mpr/repositories/transicion_lote.py` (lecturas Semi agregadas; bloqueo dual) |
| Borrador | `mpr/repositories/clasificacion_borrador.py` + `mpr/sql/007_*.sql` + `catalog.py` |
| UI | `clasificacion_produccion.html`, `clasificacion_encabezado.html`, include qty |
| Tests | `test_etapa10_clasificacion_produccion.py`, `test_docenas_clasificacion_operario.py`, nuevos de saldo/huérfano/atomicidad |
| Docs | este plan, `GLOSARIO_MPR.md`, `MANUAL_USUARIO_MPR.md` §5, `DOCENAS_CLASIFICACION_OPERARIO_MPR.md`, `REPORTES_MPR.md`, `README.md` de este índice |

UI: normativa `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`. Diálogos: solo modales Synap.

---

## Next step

Implementar **Fase 0 + Fase 1** (auditoría SELECT + tests en rojo) antes de cualquier HTML. No abrir el POST nuevo hasta que S3, S5 y S7 estén escritos y fallen contra el código actual.
