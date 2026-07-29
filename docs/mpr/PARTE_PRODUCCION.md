# Parte de producción — MPR (Etapa 8)

Documento de referencia para el módulo de Parte de producción en MPR.  
Implementado en **Etapa 8**: parte por componente, conectado a la columna **Fabricando** del tablero.

> **Persistencia MySQL:** el ledger vive en `mpr_parte`, `mpr_parte_linea` y `mpr_parte_ajuste` (MySQL). Ver `docs/mpr/PLAN_MIGRACION_MPR_MYSQL_FUENTE_UNICA.md`.

---

## Índice

1. [Fuente de datos — Fabricando (E7)](#fuente-de-datos)
2. [Registro por componente](#registro-por-componente)
3. [Asiento físico directo (sin explosión BOM)](#asiento-físico)
4. [Validaciones fuertes al guardar](#validaciones)
5. [Flujo de dos etapas (estado/origen/asiento diferido)](#flujo-de-dos-etapas)
6. [Limitaciones — compatibilidad E6 (trazabilidad OPT)](#limitaciones-e6)
7. [Modelo de datos](#modelo-de-datos)
8. [Flujo de pantalla E8 (componente × operario)](#flujo-de-pantalla)
9. [Flujo analista — planilla QC (máquina × artículo)](#flujo-analista-planilla-qc)

---

## Fuente de datos — Fabricando (E7) {#fuente-de-datos}

La grilla de captura muestra los **componentes con Fabricando > 0** según:

```text
Fabricando(comp) = max(0, Σ_MprEnvioProduccion[comp] − acreditado(comp))

acreditado(comp) = max(Semi + 2da + Scrap, clasificado_desde_Producción)
                   + max(0, partes_acumulados − clasificado_desde_Producción)
```

**Misma fórmula** que el tablero consolidado (`_fabricando_por_componentes` / `_calcular_fabricando_componente`). El saldo en **Producción** no acredita (destino del parte). Un **parte nuevo siempre baja Fabricando** aunque haya Semi/2da previos; tras CC, `clasificado` evita doble conteo.
La validación al guardar (`_fabricando_pre_snapshot`) usa la **misma** fórmula que la grilla de parte.

| Término | Fuente |
|---------|--------|
| `Σ_MprEnvioProduccion[comp]` | Ledger MySQL `mpr_envio_produccion` (`anulado = 0`) |
| Stock físico pipeline | `stock_deposito` vía `_pivot_stock_por_tipo_mpr` |
| Clasificado desde Producción | `mpr_transicion_lote` (`sumar_salidas_desde_produccion_por_articulo`) |
| Partes acumulados | `mpr_parte_linea` + ajustes (`opp_acumulado_por_pack`) |

**Componentes excluidos de la grilla:**  
- Componentes cuyo `Fabricando = 0` (envíos ya acreditados por stock, CC o partes previos).  
- Packs en `lista_produccion_agrupada` sin envío tablero: no aparecen en E8 (fuente exclusiva `mpr_envio_produccion`).

**Grilla vacía:** si no hay cupo, la pantalla muestra aviso informativo (recargar si quedan filas obsoletas en el navegador).

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

## Validaciones fuertes al guardar {#validaciones}

Antes de crear el parte o mover stock, `registrar_parte_produccion` ejecuta **siempre** (sin bypass por configuración) dos controles:

| Control | Regla | Función |
|---------|-------|---------|
| **Cupo Fabricando** | Suma por componente (todos los operarios) ≤ Fabricando pre-snapshot | `_validar_parte_contra_cupo_fabricando` |
| **Techo envíos ledger** | Partes acumulados (`opp_acumulado_por_pack`) + cantidad nueva ≤ envíos activos (`MprEnvioProduccion`) | `_validar_parte_contra_techo_envios` |

Si cualquier control falla → `ValidationError` con mensaje en español; **no** se crea `mpr_parte` ni asiento físico.

### Caso típico evitado (artículo 1904 / ID 1275)

1. Envío 12 pares → parte 12 → clasificación CC a Semi 12.
2. Stock Producción = 0, Semi = 0 (consumido en armado del pack).
3. `clasificado_desde_Producción = 12` y `partes_acumulados = 12` → Fabricando = **0**.
4. Un segundo parte de 12 pares se **rechaza** (cupo Fabricando y techo envíos).

### Configuración legacy (`MprEmpresaConfig.bloquear_parte_supera_fabricando`)

El interruptor en **Producción → Config. Depósitos** se conserva por compatibilidad de UI, pero **ya no desactiva** el bloqueo en backend: las validaciones fuertes están siempre activas.

La suma considera **todas las celdas operario** de la misma fila (componente). Ej.: Fabricando=6 → Juan 4 + Luis 2 = OK; Juan 4 + Luis 4 = exceso rechazado.

### Captura por docenas y unidades (paridad OPP)

Cada celda **componente × operario** tiene dos campos:

| Campo POST | Significado |
|------------|-------------|
| `parte_art_{id_art}_op_{id_op}_docenas` | Docenas de pares (entero ≥ 0; 1 docena = 12 pares) |
| `parte_art_{id_art}_op_{id_op}_unidades` | Pares sueltos (entero ≥ 0) |

**Pares registrados** = `docenas × 12 + pares sueltos` (misma regla que OPP por componente BOM).

La columna **Fabricando** muestra el desglose «N docenas · M pares».

### Validación en cliente (JavaScript)

Al enviar el formulario, la UI valida que la suma por fila no supere `data-fabricando` (mismo cupo que la grilla). El backend aplica además el techo de envíos ledger.

---

## Impacto si se intentara superar topes (histórico) {#impacto-stock-exceso}

**Fabricando** = `max(0, Σ envíos tablero − acreditado)` (ver fórmula en [fuente de datos](#fuente-de-datos)).  
**Acreditado** incluye stock físico de componente, clasificación CC (`mpr_transicion_lote`) y partes acumulados — **no** Terminado del componente.

Si se registrara un parte con cantidad **mayor** que los topes (comportamiento anterior con bloqueo OFF):

1. **MySQL legacy:** el asiento físico OPP-parte ingresa **toda** la cantidad registrada al depósito **Producción** (`stock` + `stock_deposito`), sin tope.
2. **Ledger Synap:** `MprParteLinea` guarda las cantidades completas por operario.
3. **Fabricando posterior:** al recargar tablero/grilla, el cupo baja por **partes acumulados** (y luego por Semi/2da/Scrap o CC). El saldo en **Producción** no acredita: stock preexistente ahí no anula Fabricando tras Enviar.
4. **Desvío de control:** quedan unidades en Producción **no respaldadas** por envíos del tablero (`MprEnvioProduccion`). La clasificación posterior puede mover stock “de más” hacia Semi/2da/Scrap.
5. **No hay rollback automático** del exceso; corrige con ajuste de parte o movimiento manual.

Por eso las validaciones fuertes están **siempre activas** desde 07/07/2026; evitan desvío entre ledger de envíos, partes acumulados y saldo físico.

---

## Flujo de dos etapas (estado/origen/asiento diferido) {#flujo-de-dos-etapas}

Con el change `mpr-trazabilidad-maquina-linea-operario`, el parte incorpora un flujo de
**dos etapas** para la carga móvil del operario. El comportamiento se controla con dos columnas
nuevas de `mpr_parte`:

| Columna | Valores | Significado |
|---------|---------|-------------|
| `estado` | `borrador` \| `pendiente` \| `aprobado` (default `aprobado`) | Etapa del parte en el circuito de aprobación |
| `origen` | `movil_operario` \| `directo_supervisor` (default `directo_supervisor`) | Quién originó el parte |

Además se agregan `id_usuario_supervisor` y `aprobado_en` (auditoría de aprobación) y, en
`mpr_parte_linea`, la dimensión máquina (`id_mpr_maquina`, `maquina_nombre`) y el gap
(`cantidad_declarada`, `cantidad_aprobada`, `gap`, `motivo`).

### Parte móvil del operario (asiento diferido)

- El operario carga desde `/mpr/mi-parte/` (`registrar_parte_movil`). El parte queda
  `estado='pendiente'`, `origen='movil_operario'` y **no mueve stock**: `cantidad = 0`,
  `cantidad_declarada = docenas × 12 + pares`, sin asiento físico ni validación de cupo.
- Como las líneas `pendiente` guardan `cantidad = 0`, **no** contaminan los acumulados
  (OPP acumulado, cupo Fabricando).
- La **aprobación del supervisor** (`aprobar_parte_produccion`) es la que ejecuta el asiento:
  fija `cantidad_aprobada` por línea, calcula `gap = aprobada − declarada` (con `motivo`
  obligatorio si `gap != 0`), valida cupo sobre lo aprobado (`validar_cupo_parte`), sincroniza
  `cantidad = cantidad_aprobada`, mueve stock al depósito «Producción» reutilizando
  `_registrar_asiento_fisico_opp_parte` y cierra el parte (`estado='aprobado'`,
  `id_usuario_supervisor`, `aprobado_en`, `movimiento_fisico_ok=1`). Es **idempotente**.

### Parte directo del supervisor (comportamiento actual)

El parte directo (`registrar_parte_produccion`, esta pantalla) **conserva el comportamiento
descrito en el resto de este documento**: nace `estado='aprobado'`, `origen='directo_supervisor'`
(defaults del ALTER) y **mueve stock en el acto** al guardar, con las validaciones fuertes
siempre activas. La única lógica compartida extraída es la validación de cupo
(`validar_cupo_parte`), reutilizada por ambos caminos.

Circuito completo y modelo de datos: ver
[TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md](TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md) y
[CARGA_MOVIL_OPERARIO.md](CARGA_MOVIL_OPERARIO.md).

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
   - Inputs de captura **siempre en 0** al abrir (cada guardado es un parte nuevo; lo ya registrado en el turno se refleja en Fabricando/stock, no se precarga en la grilla)
4. Columna "Fabricando" visible por fila (en pares)
5. **Buscador predictivo** sobre la grilla: filtra filas por código o descripción (client-side, Alpine.js)
6. Por celda operario: **Docenas de pares** + **Pares sueltos** (1 docena = 12 pares); columnas de operario con tono alternado para lectura rápida
7. Usuario completa cantidades y guarda → POST a /mpr/parte-produccion/registrar/
8. registrar_parte_produccion():
   a. Pre-snapshot Fabricando (batch, antes del atomic)
   b. Crea MprParte + MprParteLinea (componentes, no packs)
   c. parte.id_lista_produccion = None
   d. Asiento físico directo (ya_componentes=True) → stock sube
   e. Warnings si cantidad > Fabricando (no bloqueante)
9. Redirect → grilla actualizada; Fabricando reducido en el próximo render
```

> **Nota:** el flujo anterior corresponde al modo **E8 legacy** (componente × operario, un turno por pantalla). Desde el change `mpr-parte-produccion-grilla-planilla-qc`, la pantalla analista usa la **planilla QC** descrita en la sección siguiente. El POST legacy (`parte_art_{id}_op_{id}`) se conserva cuando no hay celdas planilla en el formulario.

---

## Flujo analista — planilla QC (máquina × artículo) {#flujo-analista-planilla-qc}

Pantalla: **`/mpr/parte-produccion/`** (`ParteProduccionView`, `RegistrarParteProduccionView`).  
Builder: `construir_grilla_parte_planilla` en `mpr/services_maquina_linea.py` (no modifica `construir_grilla_parte` de E8).

### Filtros (server-side)

| Filtro | Obligatorio | Comportamiento |
|--------|-------------|----------------|
| **Fecha** | Sí | Formato **dd/MM/yyyy**. Sin fecha → aviso informativo, grilla vacía. |
| **Línea** | No | Restringe máquinas/artículos de la planilla QC. |
| **Máquina** | No | Filtra por `id_mpr_maquina`. |
| **Marcas** | No | Tags de marcas incluidas (mismo patrón que otros informes MPR). |
| **Búsqueda (`q`)** | No | Filtra por descripción o código de artículo. |

**Ya no** se usa un filtro de **turno único** como eje principal: los tres turnos se muestran como columnas fijas.

### Grilla (orden planilla QC)

Filas: **máquina × artículo**, mismo orden que `construir_datos_planilla_control_calidad`.

Columnas sticky (izquierda):

- **Máquina** (`maquina_nombre`, `id_mpr_maquina`)
- **Artículo** (solo descripción visible; código en tooltip / búsqueda)
- **Cupo Fabricando** (pares equivalentes disponibles)

Columnas de turno (fijas):

| Mañana | Tarde | Noche |
|--------|-------|-------|
| docenas + pares por celda | idem | idem |

Columna **Ingresado**: suma en pares de docenas×12 + pares de los tres turnos (precarga incluida).

Celdas con **Fabricando = 0**: inputs deshabilitados (`inputs_habilitados=false`).

Turnos con **control de calidad** (`cel.bloqueado`): mismos casilleros Docenas/Pares (y operario) que en edición, en **solo lectura** (`readonly`, sin `name`/POST). Fondo ámbar suave + ícono candado junto al operario; el banner de día/turno bloqueado se mantiene. Ya no se usa el card de mensaje que reemplazaba la celda.

### Precarga y re-edición

Al abrir con fecha, `precarga_planilla_por_fecha` lee partes existentes por tupla  
`(fecha, id_mpr_maquina, id_articulo, id_mpr_turno)` y rellena docenas/pares en cada columna turno.

El guardado es **idempotente** vía `uk_mpr_parte_linea_maq` (`ON DUPLICATE KEY UPDATE`): un re-envío del formulario actualiza las cantidades del turno correspondiente.

La precarga no persiste un snapshot de **Cupo Fabricando**. Al abrir una fila con
cantidades existentes, el badge de cupo queda oculto. Reaparece y se consulta en vivo
solo cuando se editan sus docenas, pares u operario; si se restaura exactamente el
valor inicial, vuelve a ocultarse. Las filas nuevas sin precarga muestran el cupo desde
el inicio. Cuando el día está bloqueado por CC, no se muestran cupos.

### Registro (POST planilla)

URL: **`/mpr/parte-produccion/registrar/`**

Campos por celda turno:

| Campo POST | Significado |
|------------|-------------|
| `parte_maq_{id_maq}_art_{id_art}_turno_{id_turno}_docenas` | Docenas (entero ≥ 0) |
| `parte_maq_{id_maq}_art_{id_art}_turno_{id_turno}_pares` | Pares sueltos (entero ≥ 0) |
| `parte_maq_{id_maq}_art_{id_art}_turno_{id_turno}_op` | Operario de la celda |
| `parte_maq_{id_maq}_nombre` | Snapshot nombre máquina (opcional) |

Un POST con cantidades en varios turnos genera **un `MprParte` por turno** (hasta 3) dentro de una sola `transaction.atomic()`.

Cada `MprParteLinea` persiste:

- `id_mpr_maquina`, `maquina_nombre`
- `cantidad_declarada` = `cantidad_aprobada` = pares registrados
- `gap = 0` (parte directo supervisor, sin circuito móvil)

### Validación cupo (planilla)

**Aprobar** (`accion=aprobar`): se valida solamente cada fila máquina×artículo que
el usuario modificó frente a la precarga. El backend consulta **Fabricando live** y
controla por artículo la suma de los incrementos positivos de esas filas:
`Σ max(0, nuevo_total_fila − total_precargado_fila) ≤ Fabricando_live`.
Así, la precarga persistida no se vuelve a consumir ni bloquear; si varias máquinas
editan el mismo artículo, sus incrementos comparten el mismo cupo live. Un cambio
solo de operario habilita la consulta visual pero no consume cupo. Si falla → rechazo
(UI + servidor).

**Borrador** (`accion=borrador`): **no** valida cupo Fabricando (se puede guardar
aunque el incremento supere el cupo; cargas diferidas). Sin OPP/stock hasta aprobar.
**No disponible** si el día ya tiene un parte aprobado (origen `directo_supervisor`):
en ese caso las correcciones van por `accion=aprobar` (delta de stock).

### Botones de guardado

Siempre visibles (si el día no está bloqueado por CC):

| Botón | Acción |
|-------|--------|
| **Guardar borrador** | Persistencia sin stock; disponible aunque el cupo permita aprobar. **Deshabilitado** si el día ya está aprobado o bloqueado por CC. |
| **Guardar parte de producción** | Aprueba o re-aprueba con delta; se deshabilita visualmente si hay exceso Fabricando (o día bloqueado por CC). |

Si el día ya está **aprobado**, no se muestran banners de estado: hay un **chip** «Parte aprobado» en el chrome (junto a Cargar grilla). Al hacer clic, `mprShowAviso` explica que las correcciones van por «Guardar parte de producción» y que el borrador queda deshabilitado. Los banners de solo lectura por CC / turnos bloqueados sí se conservan.

Al aprobar, si hay máquinas con al menos un turno editable sin cantidad, se muestra un **modal de aviso** (Continuar / Cancelar) agrupado por máquina: resumen de cantidad, código + artículo, chips de turnos sin carga. **No bloquea**: se puede continuar y aprobar igual.

### Operario por celda (roster)

Heredado de `operadores_por_linea` / roster del builder de planilla:

| Caso roster | UI |
|-------------|-----|
| 1 operario en el turno | `<input type="hidden">` con el ID |
| Varios operarios | `<select>` Synap |
| Sin roster | celda deshabilitada + aviso en español |

### UX (canon MPR)

- Extiende `mpr/base_mpr.html`, contenedor `mpr-contenedor-pagina`.
- Altura de página: `h-[calc(100dvh-5.5rem)]` / `md:h-[calc(100dvh-7.5rem)]` con `-mt-4 md:-mt-8` (cancela el padding superior de `base_app`, mismo patrón que Reports) para pegar el chrome al navbar y maximizar la grilla; deja margen inferior para barra de estado. La grilla scrollea y la barra **Guardar borrador / Guardar parte** queda fija al pie de la tarjeta.
- Tab order por fila: Mañana → Tarde → Noche → siguiente fila (docenas antes que pares).
- Feedback vía `mprShowAviso` / `SynapMessages` y modales Synap; **sin** `alert`/`confirm`/`prompt`.
- Día aprobado: chip «Parte aprobado» en el chrome (detalle con `mprShowAviso`); sin banners de estado.

### Flujo resumido

```
1. Analista abre /mpr/parte-produccion/?fecha=dd/MM/yyyy[&filtros]
2. construir_grilla_parte_planilla → filas máquina×artículo + cupo + precarga M/T/N
3. Completa docenas/pares por turno y operario
4. POST /mpr/parte-produccion/registrar/
5. registrar_parte_produccion(modo_planilla=True):
   a. Valida cupo cross-turno (bloqueante)
   b. Por turno con cantidades: crear_parte_con_lineas(id_mpr_maquina, ...)
   c. Asiento físico OPP (ya_componentes=True) por cada parte creado
6. Redirect con filtros preservados; mensaje éxito/error en español
```

Tests: `mpr/tests/test_parte_planilla_qc.py` (`docker exec Synap_app python manage.py test mpr.tests.test_parte_planilla_qc`).

---

_Implementado en Etapa 8 del pipeline MPR (2026-07-03)._  
_Conectado a: [ENVIO_PRODUCCION_TABLERO.md](ENVIO_PRODUCCION_TABLERO.md) (E7), [TABLERO_CONSOLIDADO.md](TABLERO_CONSOLIDADO.md) (E2)._  
_Trazabilidad OPT: [TRAZABILIDAD_OPT.md](TRAZABILIDAD_OPT.md) (E6)._
