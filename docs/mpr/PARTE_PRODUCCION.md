# Parte de producción — MPR (Etapa 8)

Documento de referencia para el módulo de Parte de producción en MPR.  
Implementado en **Etapa 8**: parte por componente, conectado a la columna **Fabricando** del tablero.

---

## Índice

1. [Fuente de datos — Fabricando (E7)](#fuente-de-datos)
2. [Registro por componente](#registro-por-componente)
3. [Asiento físico directo (sin explosión BOM)](#asiento-físico)
4. [Validaciones y warning de tope](#validaciones)
5. [Limitaciones — compatibilidad E6 (trazabilidad OPT)](#limitaciones-e6)
6. [Modelo de datos](#modelo-de-datos)
7. [Flujo de pantalla](#flujo-de-pantalla)

---

## Fuente de datos — Fabricando (E7) {#fuente-de-datos}

La grilla de captura muestra los **componentes con Fabricando > 0** según la fórmula E7:

```
Fabricando(comp) = max(0, Σ_MprEnvioProduccion[comp] − stock_deposito[comp, Produccion])
```

| Término | Fuente |
|---------|--------|
| `Σ_MprEnvioProduccion[comp]` | Ledger ORM Synap (`MprEnvioProduccion.filter(anulado=False).annotate(Sum('cantidad'))`) |
| `stock_deposito[comp, Produccion]` | MySQL legacy, tabla `stock_deposito` vía `_pivot_stock_por_tipo_mpr` |

**Componentes excluidos de la grilla:**  
- Componentes cuyo `Fabricando = 0` (producción ya igualó o superó lo enviado).  
- Packs en `lista_produccion_agrupada` con `en_proceso='Si'` sin envío tablero: no aparecen en E8 (la fuente es exclusivamente `MprEnvioProduccion`).

Función responsable: `construir_grilla_parte(base_empresa, fecha, turno_id)` → `mpr/services.py`.

---

## Registro por componente {#registro-por-componente}

Al guardar el parte, `registrar_parte_produccion` crea:

- **`MprParte`**: encabezado (empresa, fecha, turno, usuario, notas).
- **`MprParteLinea`** (una por cada (componente, operario) con cantidad > 0):
  - `id_articulo` = ID del **componente** (nivel COMPONENTE, no PACK).
  - `id_operario` = ID del operario desde la grilla.
  - `cantidad` = cantidad registrada.

La URL de cada celda sigue el patrón `parte_art_{id_componente}_op_{id_operario}` (sin cambio de regex respecto a E4/E5).

### Partes E8 y `id_lista_produccion`

A diferencia de partes E5 (packs con OPT), los partes E8 tienen:

```python
parte.id_lista_produccion = None
```

No se vincula a ninguna `lista_produccion_agrupada` porque los componentes enviados directamente al tablero no tienen OPT individual.

---

## Asiento físico directo (sin explosión BOM) {#asiento-físico}

Al registrar un parte E8, `_registrar_asiento_fisico_opp_parte` se invoca con `ya_componentes=True`:

```python
_registrar_asiento_fisico_opp_parte(
    base_empresa=...,
    id_usuario=...,
    parte=...,
    lineas_pack_qty=lineas_creadas,
    deposito_produccion=...,
    ya_componentes=True,         # E8: bypass BOM
)
```

### Diferencia con E4/E5

| Parámetro | E4/E5 (packs) | E8 (componentes) |
|-----------|---------------|-----------------|
| `ya_componentes` | `False` (default) | `True` |
| Fuente de `componentes_total` | `_explode_packs_to_components(BOM)` | Directo: `{id_articulo: qty}` de cada línea |
| `stock_deposito[Produccion]` sube | Para cada componente del BOM | Para el componente directamente |

El bloque MySQL (INSERT `movimiento_stock`, UPDATE `stock_deposito`) es **idéntico** para ambos caminos.

### Idempotencia

Si `MprParte.movimiento_fisico_ok = True`, el asiento **no se re-ejecuta**. Esta guardia protege reintentos accidentales.

---

## Validaciones y warning de tope {#validaciones}

### Warning no bloqueante al superar Fabricando

Si la cantidad registrada para un componente supera el Fabricando disponible (calculado con pre-snapshot antes del `atomic()`), el sistema emite un **warning en español visible en UI**:

```
Atención: se registraron {qty:.1f} u. de {descripcion} ({codigo_manual})
pero solo {fabricando:.1f} u. estaban en Fabricando. El parte fue guardado.
```

- El parte **sí se guarda** (no bloqueante).
- El warning aparece en la siguiente carga de la grilla como mensaje de aviso.
- Pre-snapshot batch: una sola round-trip SQL antes del `atomic()` (sin N+1).

---

## Limitaciones — compatibilidad E6 (trazabilidad OPT) {#limitaciones-e6}

Los partes E8 tienen `id_lista_produccion = None`, por lo que:

- **`_escribir_historico_opp_parte`**: retorna temprano (`guard: if id_lista is None: return`). No crea fila en `lista_produccion_historico`.
- **`construir_trazabilidad_opt`**: no incluye partes E8 (filtro por `id_lista_produccion`).
- **Traza OPT inversa**: los partes E8 no aparecen en el historial de ninguna OPT.

Esto es **intencional**: los componentes enviados por tablero no provienen de una OPT específica, sino del flujo de envío directo (E7).

---

## Modelo de datos {#modelo-de-datos}

### `MprParte` (sin cambio)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `base_empresa` | CharField | Scope empresa |
| `fecha_produccion` | DateField | Fecha del parte (dd/MM/yyyy en UI) |
| `turno` | FK MprTurno | Turno del parte |
| `id_lista_produccion` | IntegerField (nullable) | `None` en partes E8 |
| `movimiento_fisico_ok` | BooleanField | Idempotencia del asiento físico |

### `MprParteLinea` (E8)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id_articulo` | IntegerField | **ID artículo nivel COMPONENTE** (migración 0015) |
| `id_operario` | IntegerField | FK lógico a `sue_abm_empleado` |
| `cantidad` | DecimalField | Cantidad producida en la celda |

Migración: `0015_mprpartelinea_id_articulo_componente.py` — `AlterField` help_text (sin DDL SQL, compatible `SYNAP_MIGRATIONS_POSTGRES_ONLY=1`).

---

## Flujo de pantalla {#flujo-de-pantalla}

```
1. Usuario abre /mpr/parte-produccion/
2. Selecciona fecha (dd/MM/yyyy) + turno → GET
3. Vista construir_grilla_parte() carga:
   - Componentes con Fabricando > 0 (fuente: MprEnvioProduccion, no lista_produccion_agrupada)
   - Operarios del roster (fecha + turno)
   - Cantidades previas (celdas precargadas)
4. Columna "Fabricando" visible por fila (en unidades)
5. Usuario completa cantidades y guarda → POST a /mpr/parte-produccion/registrar/
6. registrar_parte_produccion():
   a. Pre-snapshot Fabricando (batch, antes del atomic)
   b. Crea MprParte + MprParteLinea (componentes, no packs)
   c. parte.id_lista_produccion = None
   d. Asiento físico directo (ya_componentes=True) → stock sube
   e. Warnings si cantidad > Fabricando (no bloqueante)
7. Redirect → grilla actualizada; Fabricando reducido en el próximo render
```

---

_Implementado en Etapa 8 del pipeline MPR (2026-07-03)._  
_Conectado a: [ENVIO_PRODUCCION_TABLERO.md](ENVIO_PRODUCCION_TABLERO.md) (E7), [TABLERO_CONSOLIDADO.md](TABLERO_CONSOLIDADO.md) (E2)._  
_Trazabilidad OPT: [TRAZABILIDAD_OPT.md](TRAZABILIDAD_OPT.md) (E6)._
