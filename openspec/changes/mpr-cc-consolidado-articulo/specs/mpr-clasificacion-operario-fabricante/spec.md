# Delta — Clasificación por operario fabricante (consolidado por artículo)

**Capability:** `mpr-clasificacion-operario-fabricante`  
**Change:** `mpr-cc-consolidado-articulo`  
**Base:** `openspec/changes/mpr-docenas-clasificacion-operario/specs/mpr-clasificacion-operario-fabricante/spec.md`  
**Fuente de producto:** `docs/mpr/PLAN_CC_CONSOLIDADO_POR_ARTICULO.md`

---

## ADDED Requirements

### Requirement: Grilla por bloque artículo

La pantalla `/mpr/tablero-produccion/clasificacion-produccion/` SHALL agrupar la clasificación en **un bloque por artículo y fecha**, sin columna máquina y sin filtro Turno en encabezado. Cada bloque MUST mostrar subfilas por **(operario, turno)** del parte del día con máquinas colapsadas (mismo operario+turno = una fila).

#### Scenario: Varias máquinas y turnos en un bloque

- DADO un artículo con parte en 3 máquinas y 3 turnos el mismo día
- CUANDO el clasificador abre la pantalla
- ENTONCES ve un solo bloque del artículo con filas operario+turno, no filas por máquina

#### Scenario: Sin filtro turno en GET

- DADO la pantalla de clasificación abierta
- CUANDO se carga la grilla
- ENTONCES el encabezado no incluye combo Turno y el universo abarca el día completo

---

### Requirement: Columna cantidad = saldo Depósito Producción

La columna de cantidad disponible SHALL mostrar el **saldo vivo** en depósito `tipo_mpr = Produccion` del artículo. MUST NOT usar el parte ni `cantidad_extra` como tope de pantalla ni de validación.

#### Scenario: Parte menor que saldo físico

- DADO parte del día 100 pares y saldo Producción 150 pares
- CUANDO se renderiza el bloque
- ENTONCES la cantidad mostrada y el tope de confirmación es 150, no 100

#### Scenario: Saldo como única autoridad

- DADO saldo Producción 0 y parte con cantidad > 0 histórica
- CUANDO se evalúa el tope
- ENTONCES el sistema MUST NOT reconstruir Producción desde el parte

---

### Requirement: Semi consolidado por artículo

El clasificador SHALL registrar **un solo ingreso Semi** por artículo y fecha. Las altas nuevas en `mpr_transicion_lote` con `tipo_destino = SemiElaborado` MUST persistir `id_operario = NULL` e `id_mpr_turno = NULL`. MUST NOT prorratear Semi entre operarios.

#### Scenario: Guardado Semi único

- DADO un bloque con dos operarios en el parte
- CUANDO el usuario confirma 80 pares a Semi
- ENTONCES existe una fila Semi del artículo con `id_operario NULL` y cantidad 80

#### Scenario: Lectura Semi agregada del día

- DADO filas históricas Semi con `id_operario` distinto de NULL y filas nuevas con NULL
- CUANDO la UI muestra Semi del bloque en solo lectura
- ENTONCES el valor mostrado es `SUM(cantidad)` de SemiElaborado del artículo y fecha, sin desglose por operario en grilla

---

### Requirement: Segunda y desperdicio por operario y turno

Las cantidades de **2da selección** y **scrap** SHALL registrarse por **(id_articulo, id_operario, id_mpr_turno)** del parte del día. MUST NOT duplicar filas por máquina. `id_operario` e `id_mpr_turno` MUST NOT ser NULL en altas nuevas de 2da/scrap.

#### Scenario: Mismo operario en dos máquinas

- DADO el operario Luis en máquina A y máquina B del mismo turno
- CUANDO se construye la grilla
- ENTONCES hay una sola fila Luis+turno con inputs 2da/scrap

#### Scenario: POST 2da con operario del parte

- DADO celda válida (artículo, operario, turno) en el parte del día
- CUANDO se confirman 20 pares a 2da
- ENTONCES el INSERT incluye `id_operario` e `id_mpr_turno` del fabricante

---

### Requirement: Artículo huérfano solo Semi

Un artículo con saldo Producción > 0 **sin filas de parte** ese día SHALL aparecer como bloque de **una fila** con Semi editable y 2da/scrap **no editables**. El servidor MUST rechazar cualquier 2da/scrap de artículos huérfanos.

#### Scenario: Huérfano con Semi

- DADO saldo Producción 50 pares y sin parte del artículo
- CUANDO el usuario confirma Semi 50
- ENTONCES Prod pasa a 0 y no se exige operario en ledger Semi

#### Scenario: POST 2da en huérfano rechazado

- DADO artículo huérfano con saldo 50
- CUANDO el POST incluye scrap o 2da para ese artículo
- ENTONCES la confirmación de ese artículo falla, el saldo Producción no cambia y no hay filas nuevas

---

### Requirement: Tope único por artículo con bloqueo de saldo

Antes de transferir, el sistema MUST releer saldo Producción del artículo en la misma transacción con `SELECT … FOR UPDATE` sobre `stock_deposito`. MUST rechazar si `qty_semi + Σ qty_2da + Σ qty_scrap > saldo_lock`. Si la validación falla, MUST NOT mover stock ni insertar ledger de ese artículo.

#### Scenario: Exceso sobre saldo

- DADO saldo Producción 120 pares
- CUANDO el POST intenta Semi 100 + 2da 30 del mismo artículo
- ENTONCES se rechaza el artículo, Prod sigue 120 y no hay filas nuevas

#### Scenario: Cantidad cero no escribe ledger

- DADO destinos con cantidad 0 en el POST
- CUANDO se confirma
- ENTONCES MUST NOT insertar filas vacías en `mpr_transicion_lote`

---

### Requirement: Parser POST consolidado

El POST de confirmación SHALL aceptar `semi_{id_articulo}`, `seg2da_{id_articulo}_op_{id_operario}_t_{id_turno}` y `scrap_{id_articulo}_op_{id_operario}_t_{id_turno}`. MUST ignorar claves legadas `semi_{art}_op_{op}_t_{t}_m_{m}` y variantes `semi_*_op_*` para Semi. MUST NOT usar `turno_id` como alcance de Semi.

#### Scenario: Clave Semi legada ignorada

- DADO un POST con `semi_10_op_5_t_1_m_2` y `semi_10` con cantidades distintas
- CUANDO se procesa confirmación
- ENTONCES solo `semi_10` define el Semi del artículo 10

---

### Requirement: Borrador por fecha

Las tablas `mpr_clasificacion_borrador` y `mpr_clasificacion_borrador_linea` SHALL usar cabecera **una por fecha** (`UNIQUE (fecha_produccion)`) y líneas de tipo Semi (`id_operario NULL`, `cant_semi > 0`) o 2da/scrap (`id_operario`+`id_mpr_turno`, `cant_semi = 0`). DDL MUST implementarse vía catálogo central. Guardar borrador MUST NOT mover `stock_deposito`, MSTOCK ni `mpr_transicion_lote`.

#### Scenario: Borrador viejo incompatible

- DADO cabecera borrador legada `(fecha, turno)` sin cabecera nueva del día
- CUANDO se abre la pantalla
- ENTONCES se muestra aviso en español de recarga y MUST NOT precargar cantidades del shape viejo

#### Scenario: Borrador no mueve stock

- DADO cantidades en borrador sin confirmar
- CUANDO el usuario guarda borrador
- ENTONCES saldo Producción y ledger permanecen iguales

---

### Requirement: Filtro Solo pendiente

La pantalla SHALL ofrecer filtro **Solo pendiente** (default off). Con Solo pendiente activo MUST ocultar artículos con saldo Producción 0 y, dentro del bloque, operarios con 2da/scrap ya confirmados ese día. **Ver roster** MUST incluir bloques en saldo 0 (solo lectura) y operarios ya confirmados.

#### Scenario: Ocultar artículo sin saldo

- DADO artículo con saldo Producción 0 y CC confirmada
- CUANDO Solo pendiente está activo
- ENTONCES el bloque no aparece

#### Scenario: Ocultar operario confirmado en 2da

- DADO bloque con saldo > 0 y operario con 2da confirmada
- CUANDO Solo pendiente está activo
- ENTONCES la fila del operario no aparece pero el bloque sí si queda saldo o Semi pendiente

---

### Requirement: Bloqueo dual del parte

Un turno del parte queda bloqueado para edición SI existe fila CC de esa fecha+turno con `tipo_destino IN ('2daSeleccion','Scrap')` **O** existe fila CC SemiElaborado con `id_operario IS NOT NULL` (shape histórico). Semi nuevo con `id_operario NULL` MUST NOT bloquear turnos. MUST NOT requerir fecha de corte ni backfill de datos.

#### Scenario: Solo Semi nuevo no bloquea

- DADO confirmación de solo Semi con `id_operario NULL` en un día
- CUANDO se abre el parte de mañana/tarde/noche
- ENTONCES todos los turnos siguen editables

#### Scenario: Semi histórico con operario bloquea

- DADO fila SemiElaborado histórica con `id_operario` y `id_mpr_turno` del turno Mañana
- CUANDO se evalúa bloqueo del parte
- ENTONCES el turno Mañana MUST quedar bloqueado

#### Scenario: 2da bloquea turno

- DADO fila 2daSeleccion confirmada para fecha y turno Tarde
- CUANDO se evalúa bloqueo
- ENTONCES el turno Tarde MUST quedar bloqueado

---

### Requirement: Histórico de ledger de solo lectura

El sistema MUST NOT ejecutar UPDATE/DELETE masivo de `mpr_transicion_lote` para consolidar Semi, MUST NOT backfill de `id_operario` en filas viejas y MUST NOT rehacer MSTOCK de días cerrados. Conteos de filas Semi con operario anteriores al deploy MUST NOT disminuir.

#### Scenario: Histórico intacto tras confirmación nueva

- DADO conteo de filas Semi con `id_operario NOT NULL` antes del deploy
- CUANDO se confirman Semi nuevos con `id_operario NULL`
- ENTONCES el conteo histórico con operario se mantiene; solo aumentan filas con NULL

---

## MODIFIED Requirements

### Requirement: Dimensión operario fabricante en ledger

La tabla `mpr_transicion_lote` SHALL conservar `id_operario` e `id_mpr_turno` para **2da selección y scrap** (fabricante del parte). Para **SemiElaborado en altas nuevas** MUST persistir `id_operario = NULL` e `id_mpr_turno = NULL`. Filas históricas con operario MUST seguir legibles sin migración.

(Previously: todo Semi llevaba operario del fabricante.)

#### Scenario: Guardado 2da con operario

- CUANDO el clasificador guarda 10 docenas a 2da para artículo A y operario García
- ENTONCES el INSERT incluye `id_operario` de García y snapshot de nombre

#### Scenario: Semi nuevo sin operario

- CUANDO se confirma Semi de un artículo
- ENTONCES el INSERT SemiElaborado tiene `id_operario NULL` e `id_mpr_turno NULL`

#### Scenario: Histórico sin operario

- CUANDO existen filas con `id_operario IS NULL` de cualquier origen
- ENTONCES el sistema las lista sin error

---

### Requirement: Grilla por artículo y operario

La pantalla SHALL mostrar bloques por **id_articulo** del día. Dentro de cada bloque, subfilas por **(id_operario, id_mpr_turno)** con pendiente de 2da/scrap o parte activo. Semi es **un control por bloque** (rowspan). El universo MUST ser: parte del día ∪ artículos con saldo Producción > 0 ∪ (modo roster) CC confirmada hoy.

(Previously: una fila por par artículo×operario con Semi/2da/scrap en cada celda y filtro turno.)

#### Scenario: Dos operarios mismo artículo

- CUANDO el parte registra operario A y operario B en el mismo artículo
- ENTONCES el bloque muestra dos filas 2da/scrap y un solo input Semi

#### Scenario: Sin filas vacías por defecto en Solo pendiente

- CUANDO un operario ya clasificó toda su 2da/scrap y Solo pendiente está activo
- ENTONCES esa subfila no aparece

---

### Requirement: Cálculo de pendiente por operario

Para cada subfila (artículo, operario, turno), el pendiente de **2da y scrap** SHALL ser la porción del parte colapsada menos lo ya clasificado con el mismo `id_operario` e `id_mpr_turno`. El pendiente de **Semi** SHALL ser el saldo Producción del artículo menos Semi ya clasificado agregado del día (sin filtrar operario en lectura).

(Previously: pendiente por operario incluía Semi en la misma fila respecto al parte del turno.)

#### Scenario: Clasificación parcial 2da

- CUANDO el operario tiene 45 docenas en parte y se clasificaron 20 a 2da
- ENTONCES el pendiente 2da mostrado es 25 docenas hasta nuevo guardado

---

### Requirement: Validación por fila

El sistema SHALL rechazar 2da/scrap donde la cantidad supere lo atribuible al operario+turno en el parte (menos ya clasificado). MUST NOT aplicar esta regla a Semi (validado a nivel artículo). MUST NOT permitir 2da/scrap sin celda de parte ese día.

(Previously: validación semi+2da+scrap por fila contra atribuible del operario.)

#### Scenario: Exceso 2da por operario

- CUANDO el usuario intenta clasificar 50 docenas a 2da teniendo 45 atribuibles
- ENTONCES se muestra error en español y no se persiste ese destino

---

### Requirement: Validación global por artículo

El sistema SHALL rechazar confirmación del artículo cuando `semi + Σ 2da + Σ scrap` supere el **saldo vivo** Producción lockeado. MUST NOT validar tope por suma de celdas del parte ni por `_max_clasificable_celda` / extra pool.

(Previously: tope agregado por turno contra stock con split parte/extra por celda.)

#### Scenario: Desfase con stock físico

- CUANDO la suma del POST del artículo excede saldo Producción
- ENTONCES se bloquea ese artículo con mensaje que indica el tope disponible

---

### Requirement: Presentación docenas en clasificación

Los inputs y columnas SHALL respetar el toggle global `mpr_presentacion_cantidad`; en modo docenas los inputs principales son docenas. MUST NOT usar `alert`/`confirm`/`prompt` nativos.

(Previously: sin cambio funcional; se mantiene obligatoriedad modales Synap.)

#### Scenario: POST en docenas

- CUANDO presentación docenas y el usuario ingresa 5 docenas a scrap
- ENTONCES `mpr_transicion_lote.cantidad` = 60 unidades

---

### Requirement: Auditoría del clasificador

`id_usuario` en `mpr_transicion_lote` SHALL registrar al usuario logueado que ejecutó el guardado. `id_operario` MUST usarse solo en 2da/scrap como fabricante; MUST NOT copiarse a Semi nuevo. Altas nuevas MUST usar `cantidad_extra = 0`.

(Previously: `id_operario` también en Semi.)

#### Scenario: Distinción fabricante vs usuario en 2da

- CUANDO el supervisor S guarda 2da del operario O
- ENTONCES `id_operario`=O, `id_usuario`=S y Semi del mismo POST no lleva operario

---

## REMOVED Requirements

### Requirement: Bloqueo sin desglose por operario en parte

(Reason: el modelo huérfano permite clasificar Semi con saldo Producción sin parte; 2da/scrap siguen exigiendo operario en parte.)  
(Migration: artículos sin operarios en parte entran como huérfanos Semi-only; 2da/scrap rechazadas server-side.)

### Requirement: Grilla clasificación agregada por artículo (comportamiento anterior)

(Reason: reemplazada por bloque artículo con Semi consolidado y subfilas operario para 2da/scrap, distinto del agregado sin operario del change docenas.)  
(Migration: ninguna en datos; solo lectura/UI.)
