# OPP — Parte de Producción (Etapa 4)

## Concepto

El **Parte de Producción** es el mecanismo de registro que captura la cantidad producida por pack y operario para una fecha y turno. Desde **Etapa 5**, además de crear el ledger Django, genera el asiento físico en el depósito Producción de MySQL legacy (MSTOCK tipo_mov='OPP').

### Relación con el pipeline MPR

| Etapa | Responsabilidad |
|-------|----------------|
| 2 | Tablero consolidado de demanda (Enviado = OPT liberado) |
| 3 | Turnos y roster operarios |
| **4** | **Parte de producción (ledger OPP-parte) — esta etapa** |
| 5 | Movimiento físico y desmontaje de `ejecutar_liberar_opt` |
| 6 | Trazabilidad OPT drill-down |

---

## Captura: Grilla fecha + turno + packs × operarios

### URL

```
GET /mpr/parte-produccion/?fecha=dd/MM/yyyy&turno_id=N
```

### Flujo

1. El usuario selecciona una **fecha** (dd/MM/yyyy, puede ser pasada) y un **turno**.
2. El sistema carga la grilla:
   - **Filas**: packs con `en_proceso_produccion='Si'` en `lista_produccion_agrupada` (MySQL legacy).
   - **Columnas**: operarios del turno/fecha según `MprRosterDia`.
   - **Celdas**: cantidades efectivas ya registradas si existen partes previos para esa combinación.
3. El usuario ingresa las cantidades y presiona **Guardar parte de producción**.
4. Se crea un `MprParte` (cabecera) con N `MprParteLineas` (una por celda con cantidad > 0).

### Registro por lote (POST)

```
POST /mpr/parte-produccion/registrar/
  fecha=dd/MM/yyyy
  turno_id=N
  parte_art_{id_articulo}_op_{id_operario}={cantidad}
  notas=...
```

---

## Modelos Django

### MprParte (cabecera)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID PK | uuid4, no editable |
| `base_empresa` | CharField | scope por empresa, db_index |
| `fecha_produccion` | DateField | puede ser pasada (registro diferido) |
| `turno` | FK → MprTurno | PROTECT (no eliminar turno con partes) |
| `id_usuario` | Integer | usuario Synap que registró |
| `registrado_en` | DateTimeField | auto_now_add |
| `notas` | CharField 500 | opcional |

**Sin UniqueConstraint en (base_empresa, turno, fecha)**: múltiples partes por turno+fecha permitidos.

### MprParteLinea (línea)

| Campo | Tipo | Notas |
|-------|------|-------|
| `parte` | FK → MprParte | CASCADE |
| `id_articulo` | Integer | nivel PACK |
| `id_operario` | Integer | FK lógico a sue_abm_empleado |
| `operario_nombre` | CharField 255 | **snapshot histórico**, no se actualiza |
| `cantidad` | Decimal 15,2 | unidades producidas |

**UniqueConstraint**: `(parte, id_articulo, id_operario)`.

### MprParteAjuste (corrección)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID PK | uuid4 |
| `parte` | FK → MprParte | PROTECT |
| `id_articulo` / `id_operario` | Integer | referencia a la línea |
| `delta` | Decimal 15,2 | positivo o negativo |
| `motivo` | CharField 255 | obligatorio |
| `id_usuario` / `registrado_en` | Integer / DateTime | trazabilidad |

---

## Snapshot de operario

Al crear una `MprParteLinea`, el sistema captura `operario_nombre` como snapshot desde `sue_abm_empleado` usando `obtener_operario()` → `str_or_default`. Este valor es histórico: si el nombre cambia en ABM después, la línea sigue mostrando el nombre al momento del registro.

---

## Corrección append-only (MprParteAjuste)

**No se edita** `MprParteLinea.cantidad`. Las correcciones se registran como `MprParteAjuste` con un `delta` positivo o negativo.

```
Cantidad efectiva (pack, operario) = MprParteLinea.cantidad + Σ(MprParteAjuste.delta)
```

### Endpoint de ajuste

```
POST /mpr/parte-produccion/{parte_id}/ajuste/
  id_articulo=N
  id_operario=N
  delta=±N.NN
  motivo=texto
```

**Regla**: si `cantidad_efectiva + delta < 0` → ValidationError en español, no se crea el ajuste.

---

## Límite de enviado disponible (warning, no bloqueo)

Al guardar un parte, si `OPP_parte_acumulado(pack) > OPT_liberado_acumulado(pack)` para cualquier pack, se muestra un **banner amber** de advertencia. El guardado NO se bloquea (REQ-OPP-007).

---

## Ledger-only — sin movimiento físico

Desde **Etapa 5**, al registrar un parte se escribe el asiento físico en MySQL legacy (ver sección siguiente). El depósito Producción se alimenta exclusivamente de `registrar_parte_produccion` (OPP-parte), ya no de `ejecutar_liberar_opt`.

---

## Asiento Físico Activo — Etapa 5

> **Activado en Etapa 5 (2026-07-03):** `registrar_parte_produccion` ahora escribe en MySQL legacy.

### Función interna: `_registrar_asiento_fisico_opp_parte`

```python
def _registrar_asiento_fisico_opp_parte(
    base_empresa: str,
    id_usuario: int,
    parte: MprParte,
    lineas_pack_qty: List[Tuple[Dict, Decimal]],
    deposito_produccion: int,
) -> None:
    """
    Escribe MSTOCK tipo_mov='OPP' + stock/stock_deposito en depósito Producción.
    Llamar dentro de transaction.atomic() del caller.
    """
```

**Pasos internos:**

1. Explotar BOM: `_explode_packs_to_components(base_empresa, lineas_pack_qty)` → `{id_componente: qty}`
2. `codmov FOR UPDATE` → `codigo_mov`
3. `talonarios MSTOCK FOR UPDATE` → `nro_comprobante`
4. INSERT `movimiento_stock` (tipo_mov='OPP', motivo='Parte producción', deposito_produccion → deposito_produccion)
5. Por cada componente: INSERT `stock` (Entrada=qty) + UPDATE/INSERT `stock_deposito` saldo += qty
6. `conn.commit()` ← MySQL commit ANTES de salir del `transaction.atomic()` de Django

### Flag `movimiento_fisico_ok`

`MprParte.movimiento_fisico_ok` (BooleanField, default=False, migración 0012):
- Se pone en `True` tras el commit MySQL exitoso.
- **Idempotencia:** si `movimiento_fisico_ok=True`, el asiento NO se re-ejecuta en un reintento.
- Permite detectar partes con MySQL fallido (flag=False) para retry.

### Ajuste Físico: `_registrar_delta_stock_ajuste`

Al crear `MprParteAjuste` vía `agregar_ajuste_parte`, se registra el delta físico:

- `delta > 0`: INSERT stock (Entrada) + UPDATE stock_deposito saldo += delta
- `delta < 0`: valida saldo suficiente → INSERT stock (Salida) + UPDATE stock_deposito saldo += delta (negativo)

`MprParteAjuste.ajuste_fisico_ok` (BooleanField, default=False, migración 0012):
- `True` tras commit MySQL exitoso del ajuste físico.
- Si el ajuste físico falla, el ajuste Django se revierte (`.delete()`) para mantener coherencia.

---

## Fecha de producción pasada

`fecha_produccion` puede ser cualquier fecha pasada (registro diferido). No hay regla de cierre formal en Etapa 4.

---

## Ejemplo: flujo POST registro

```
# Seleccionar grilla
GET /mpr/parte-produccion/?fecha=03/07/2026&turno_id=2

# Registrar parte
POST /mpr/parte-produccion/registrar/
  fecha=03/07/2026
  turno_id=2
  parte_art_1001_op_5=12.5
  parte_art_1001_op_6=10.0
  parte_art_1002_op_5=8.0
  notas=Producción normal turno tarde

→ Crea MprParte + 3 MprParteLineas (ledger-only)
→ Redirect a grilla con warnings si superó límite
```

## Ejemplo: ajuste delta

```
POST /mpr/parte-produccion/{parte_uuid}/ajuste/
  id_articulo=1001
  id_operario=5
  delta=-2.5
  motivo=Conteo incorrecto por defecto de calidad

→ Crea MprParteAjuste(delta=-2.5)
→ Cantidad efectiva = 12.5 - 2.5 = 10.0
```

---

## Rollback / migración reversa

```bash
# Revertir migración (drop 3 tablas)
docker exec Synap_app python manage.py migrate mpr 0010

# En services.py: eliminar paso 2b en listar_tablero_por_articulo
# En tablero_produccion.html: restaurar tooltip PROVISIONAL
```

---

## Servicios relevantes (`mpr/services.py`)

| Función | Descripción |
|---------|-------------|
| `registrar_parte_produccion(...)` | Crea MprParte + líneas en atomic(). Ledger-only. |
| `agregar_ajuste_parte(...)` | Crea MprParteAjuste, valida cantidad_efectiva >= 0. |
| `construir_grilla_parte(...)` | Grilla packs×operarios con celdas pre-existentes. |
| `opp_parte_acumulado_por_pack(...)` | {id_pack: Σ(lineas + ajustes)}. Backward-safe. |
| `listar_partes(...)` | QuerySet filtrado por empresa. |
| `obtener_parte(...)` | Parte por UUID y empresa. |

---

---

## Trazabilidad (E6)

### Campo `id_lista_produccion` en `MprParte`

Desde Etapa 6, cada `MprParte` puede tener un campo `id_lista_produccion` que vincula el parte con la OPT activa al momento de su creación.

```python
# mpr/models.py → MprParte
id_lista_produccion = models.IntegerField(null=True, blank=True, db_index=True)
```

**Captura automática** en `registrar_parte_produccion`:
- Se llama a `_capturar_id_lista_opt_activa(base_empresa, id_articulos)` post-creación de líneas.
- Persiste el id de la OPT activa más reciente para los artículos del parte.
- Si hay múltiples OPTs activas → toma la mayor + warning.
- Si no hay OPT o MySQL falla → persiste `None` (best-effort, no interrumpe el asiento físico).

### Escritura a `lista_produccion_historico`

Al completar el asiento físico OPP-parte, `_registrar_asiento_fisico_opp_parte` llama a `_escribir_historico_opp_parte` para dejar un registro en `lista_produccion_historico` con:

- `tipo_evento = 'OPP'`
- `id_lista_produccion = parte.id_lista_produccion`
- `id_articulo`, `codigo_movimiento_mstock`, `id_operario`, `fecha`, `hora_evento`

Si `id_lista_produccion is None` → skip silencioso. Si la tabla no existe o el INSERT falla → warning en log, el asiento físico continúa normalmente (try/except aislado).

Ver también: [TRAZABILIDAD_OPT.md](TRAZABILIDAD_OPT.md)

---

*Documento creado: 2026-07-03 — Etapa 4 MPR Pipeline. Actualizado: 2026-07-03 — Etapa 6 (trazabilidad).*
