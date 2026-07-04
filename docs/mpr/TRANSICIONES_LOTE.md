# Transiciones de Lote MPR — Etapa 5

**Capability:** `mpr-transiciones-lote`  
**Implementado en:** Etapa 5 del refactor MPR  
**Fecha:** 2026-07-03

> **Actualización Etapa 10 (03/07/2026):**
> - `Planchado` deja de ser etapa con stock. Transiciones legales desde Producción:
>   `Produccion → SemiElaborado`, `Produccion → 2daSeleccion`, `Produccion → Scrap`.
>   Se retiran `Produccion → Planchado` y `Planchado → {2daSeleccion|SemiElaborado}`.
> - `transferir_stock_entre_etapas(..., fecha=None)` y `transferir_stock_lote(..., fecha=None)`
>   aceptan la **fecha del parte** para fechar el asiento MSTOCK (carga diferida).

---

## Resumen

La capability `mpr-transiciones-lote` permite transferir stock físico entre depósitos MPR
(etapas de producción) de forma trazable. Cada transferencia genera:

1. Un comprobante MSTOCK en MySQL legacy (`movimiento_stock`, `stock`, `stock_deposito`).
2. Un registro de trazabilidad Django (`MprTransicionLote`).

---

## Servicio principal

### `transferir_stock_entre_etapas`

```python
from mpr.services import transferir_stock_entre_etapas

ok, codigo_movimiento, nro_comprobante, mensaje_error = transferir_stock_entre_etapas(
    base_empresa="MiEmpresa",
    id_usuario=42,
    id_articulo=1500,         # ID componente (ya explotado del pack)
    tipo_origen="Produccion",
    tipo_destino="Planchado",
    cantidad=Decimal("30"),
)
```

**Parámetros:**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `base_empresa` | `str` | Nombre de la base MySQL de AdministraNET |
| `id_usuario` | `int` | ID usuario de AdministraNET |
| `id_articulo` | `int` | ID artículo a nivel **componente** (ya explotado) |
| `tipo_origen` | `str` | Constante TIPO_MPR_* de la etapa de origen |
| `tipo_destino` | `str` | Constante TIPO_MPR_* de la etapa de destino |
| `cantidad` | `Decimal` | Unidades a transferir (debe ser > 0) |

**Retorno:** `Tuple[bool, Optional[int], Optional[str], Optional[str]]`

| Posición | Tipo | Descripción |
|----------|------|-------------|
| 0 | `bool` | `True` si la transición fue exitosa |
| 1 | `Optional[int]` | `codigo_movimiento` MSTOCK (o `None` si falló) |
| 2 | `Optional[str]` | Número de comprobante (o `None` si falló) |
| 3 | `Optional[str]` | Mensaje de error en español (o `None` si ok) |

---

## Transiciones legales (Etapa 5)

Definidas en `mpr/pipeline.py` → `TRANSICIONES_LEGALES`:

```
Enviado          → Produccion
Produccion       → Planchado, Desperdicio (Scrap)
Planchado        → 2da Seleccion, Semi Elaborado
2da Seleccion    → Terminado
Semi Elaborado   → Terminado
Scrap            → (terminal)
Terminado        → (terminal)
```

Las transiciones no incluidas en este grafo retornan `ok=False` con mensaje en español.

---

## Mapa tipo → depósito MySQL

| Constante TIPO_MPR_* | Getter de depósito | Nombre visible |
|---------------------|-------------------|----------------|
| `Produccion` | `get_deposito_produccion_mpr` | Producción |
| `Planchado` | `get_deposito_planchado_mpr` | Planchado |
| `Scrap` | `get_deposito_desperdicio_mpr` | Desperdicio |
| `2da Seleccion` | `get_deposito_2da_seleccion_mpr` | 2da Selección |
| `Semi Elaborado` | `get_deposito_semi_elaborado_mpr` | Semi Elaborado |

La resolución del depósito se hace vía `deposito.tipo_mpr` en la tabla MySQL.

---

## Modelo de trazabilidad: `MprTransicionLote`

Definido en `mpr/models.py`, migración `0012_etapa5_transiciones`.

```python
class MprTransicionLote(models.Model):
    base_empresa      = CharField(max_length=64, db_index=True)
    id_articulo       = IntegerField()         # nivel componente
    tipo_origen       = CharField(max_length=64)
    tipo_destino      = CharField(max_length=64)
    cantidad          = DecimalField(15, 2)
    codigo_movimiento = IntegerField(null=True, blank=True)
    id_usuario        = IntegerField()
    creado_en         = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [
            Index(["base_empresa", "id_articulo"], name="mpr_tl_emp_art_idx"),
            Index(["base_empresa", "creado_en"],   name="mpr_tl_emp_fecha_idx"),
        ]
```

**Nota:** `codigo_movimiento` puede ser `null` en casos de error parcial (MySQL commit sin Django ORM).

---

## Vista y URL

| Clase | URL | Nombre URL |
|-------|-----|-----------|
| `TransicionLoteView` | `/mpr/tablero-produccion/transicion/` | `mpr:transicion_lote` |

### Parámetros POST

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id_articulo` | int | ID artículo componente |
| `tipo_origen` | str | Valor hardcodeado en template (`Produccion`, `Planchado`) |
| `tipo_destino` | str | Valor de Alpine.js `:value` (`Planchado`, `Scrap`, `2da Seleccion`, `Semi Elaborado`) |
| `cantidad` | decimal | Cantidad ingresada en modal |

---

## UI — Columna Acciones en tablero

La columna `Acciones` (col 11) en `tablero_produccion.html` muestra botones contextuales
según los saldos de la fila:

| Condición | Botón mostrado |
|-----------|----------------|
| `fila.enviado > 0` | Enlace "Registrar parte" → `mpr:parte_produccion` |
| `fila.produccion > 0` | Menú desplegable "Inspección ▾" → Planchado o Desperdicio |
| `fila.planchado > 0` | Menú desplegable "Transición ▾" → 2da Selección o Semi Elaborado |

Cada opción de transición abre un modal Alpine.js con un campo de cantidad.
El modal envía un formulario POST a `mpr:transicion_lote`.

**Aislamiento Alpine.js:** cada fila tiene su propio `x-data="{ modalOpen: false, ... }"`
en el `<td>` de Acciones para evitar conflictos entre filas.

---

## Flujo de datos (secuencia)

```
Usuario confirma cantidad en modal
  → POST /mpr/tablero-produccion/transicion/
  → TransicionLoteView.post()
  → transferir_stock_entre_etapas()
      → validar_transicion()      [pre-check legalidad + cantidad>0]
      → _get_deposito_por_tipo_mpr() × 2
      → MySQL txn:
          SELECT saldo FOR UPDATE  [re-validación con saldo real]
          codmov FOR UPDATE
          talonarios MSTOCK FOR UPDATE
          INSERT movimiento_stock (tipo_mov='OPP')
          INSERT stock (Salida origen)
          UPDATE stock_deposito[origen] -= cantidad
          INSERT stock (Entrada destino)
          UPDATE/INSERT stock_deposito[destino] += cantidad
          conn.commit()
      → MprTransicionLote.objects.create()
  → messages.success / messages.error
  → redirect(tablero_produccion)
```

---

## Validaciones

| Condición | Retorno |
|-----------|---------|
| `cantidad <= 0` | `(False, None, None, "La cantidad debe ser mayor a cero.")` |
| `tipo_origen → tipo_destino` no en grafo | `(False, None, None, "Transición no permitida: ...")` |
| `cantidad > saldo_origen` | `(False, None, None, "Saldo insuficiente en ...")` |
| `base_empresa` vacía | `(False, None, None, "Base de datos no indicada.")` |
| Depósito no encontrado | `(False, None, None, "No se encontró el depósito de ...")` |

---

## Relación con Etapas anteriores y E9

- **Etapa 4:** `registrar_parte_produccion` (OPP-parte) escribe en stock_deposito[Produccion].  
  Ver `OPP_PARTE_PRODUCCION.md`.
- **Etapa 5** (este doc): `transferir_stock_entre_etapas` — unidad atómica de transferencia.
- **Etapa 6:** drill-down OPT, trazabilidad. Ver `TRAZABILIDAD_OPT.md`.
- **Etapa 9:** UI consolidada (ver abajo).

---

## Etapa 9: Servicio Batch y UI Consolidada

A partir de E9 se añadió el servicio `transferir_stock_lote` (best-effort) que
envuelve N llamadas a `transferir_stock_entre_etapas` sin `atomic()`:

```python
from mpr.services import transferir_stock_lote

resultado = transferir_stock_lote(
    base_empresa="MiEmpresa",
    id_usuario=1,
    items=[
        {"id_articulo": 42, "tipo_origen": "Produccion", "tipo_destino": "Planchado", "cantidad": Decimal("5")},
        {"id_articulo": 42, "tipo_origen": "Produccion", "tipo_destino": "Scrap", "cantidad": Decimal("2")},
    ],
)
# resultado: {exitosas: 2, fallidas: 0, errores: [], comprobantes: ["MSTOCK-..."]}
```

### Deprecación UI por fila

La UI de transición por fila (menú «Inspección ▾» / «Transición ▾» + modal Alpine en `tablero_produccion.html`)
fue **eliminada en E9**. La URL `mpr:transicion_lote` se mantiene backend (backward-safe).

Las transiciones ahora se realizan desde las pantallas globales de lote:
- **Inspección:** `/mpr/tablero-produccion/inspeccion/` (Producción → Planchado/Scrap)
- **Clasificación:** `/mpr/tablero-produccion/clasificacion/` (Planchado → 2daSelección/SemiElaborado)

Ver [ACCIONES_LOTE_TABLERO.md](ACCIONES_LOTE_TABLERO.md) para el detalle completo.
