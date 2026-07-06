# Spec — Clasificación por operario fabricante

**Capability:** `mpr-clasificacion-operario-fabricante`  
**Change:** `mpr-docenas-clasificacion-operario`  
**Estado:** Propuesto

---

## ADDED Requirements

### Requirement: Dimensión operario fabricante en ledger

La tabla `mpr_transicion_lote` SHALL incluir columnas `id_operario` (INT NULL) y `operario_nombre` (VARCHAR) que identifican al **operario que fabricó** la producción clasificada, no al usuario que registra la transición.

#### Scenario: Guardado con operario

- **WHEN** el clasificador guarda 10 docenas a Semi elaborado para artículo A y operario García
- **THEN** el INSERT en `mpr_transicion_lote` incluye `id_operario` de García y `operario_nombre` snapshot

#### Scenario: Histórico sin operario

- **WHEN** existen filas anteriores al cambio con `id_operario IS NULL`
- **THEN** el sistema las lista sin error y las reportes etiquetan como «Sin atribución»

---

### Requirement: Migración de esquema vía catálogo central

El ALTER TABLE SHALL implementarse en `core/services/legacy_mysql_schema/catalog.py` y script SQL en `mpr/sql/`, ejecutable por la herramienta global de migración legacy.

#### Scenario: Idempotencia

- **WHEN** la migración se ejecuta dos veces
- **THEN** no falla ni duplica columnas

---

### Requirement: Grilla por artículo y operario

La pantalla de clasificación de producción SHALL mostrar una fila por cada par **(id_articulo, id_operario)** con pendiente de clasificación mayor que cero para la fecha y turno seleccionados del clasificador.

#### Scenario: Dos operarios mismo artículo

- **WHEN** el parte del turno registra 45 docenas para operario A y 38 para operario B en el mismo artículo
- **THEN** la grilla muestra dos filas independientes con inputs Semi / 2da / Scrap

#### Scenario: Sin filas vacías por defecto

- **WHEN** un operario ya clasificó todo su pendiente del turno
- **THEN** esa fila no aparece en la sección «Turno actual»

---

### Requirement: Cálculo de pendiente por operario

Para cada fila (artículo, operario), el pendiente SHALL ser:

`cantidad_parte(artículo, operario, fecha, turno) − Σ clasificado(artículo, operario, fecha, turno)`

donde clasificado suma semi, 2da y scrap en `mpr_transicion_lote` con el mismo `id_operario`.

#### Scenario: Clasificación parcial

- **WHEN** el operario tiene 45 docenas en parte y se clasifican 20 docenas a semi
- **THEN** el pendiente mostrado es 25 docenas hasta nuevo guardado

---

### Requirement: Validación por fila

El sistema SHALL rechazar un guardado donde la suma de semi + 2da + scrap en la fila supere el **en producción atribuible** al operario (parte menos ya clasificado en el turno).

#### Scenario: Exceso por operario

- **WHEN** el usuario intenta clasificar 50 docenas teniendo 45 docenas atribuibles
- **THEN** se muestra error en español y no se persiste

---

### Requirement: Validación global por artículo

El sistema SHALL rechazar guardados donde la suma de clasificación de **todos los operarios** del artículo en el turno supere el saldo agregado en depósito Producción para ese artículo.

#### Scenario: Desfase con stock físico

- **WHEN** Σ clasificado del turno > stock Producción del artículo
- **THEN** se bloquea el guardado con mensaje que indica el tope disponible

---

### Requirement: Bloqueo sin desglose por operario en parte

Si el parte del artículo en fecha/turno no tiene líneas con `id_operario` válido o la suma por operarios es menor que la producción declarada, el sistema SHALL bloquear la clasificación por rendimiento para ese artículo y SHALL indicar corregir en Parte de producción.

#### Scenario: Parte agregado sin operarios

- **WHEN** existe cantidad en parte para el artículo pero ninguna línea con operario
- **THEN** la grilla no permite guardar clasificación por operario para ese artículo

---

### Requirement: Arrastre de turnos anteriores

El sistema SHALL mostrar en sección separada («Pendiente de turnos anteriores») los pares (artículo, operario) con parte en fechas/turnos anteriores no totalmente clasificados, sin mezclarlos con el turno actual.

#### Scenario: Arrastre visible

- **WHEN** quedó pendiente de clasificar del turno Noche del día anterior
- **THEN** aparece en la sección de arrastre con fecha y turno de origen legibles (dd/MM/yyyy)

---

### Requirement: Presentación docenas en clasificación

Los inputs y columnas de lectura de la grilla de clasificación SHALL respetar el toggle global `mpr_presentacion_cantidad`; en modo docenas los inputs principales son docenas.

#### Scenario: POST en docenas

- **WHEN** presentación docenas y el usuario ingresa 5 docenas a scrap
- **THEN** `mpr_transicion_lote.cantidad` = 60 unidades

---

### Requirement: Auditoría del clasificador

El campo `id_usuario` existente en `mpr_transicion_lote` SHALL seguir registrando al usuario logueado que ejecutó el guardado; MUST NOT usarse como dimensión de rendimiento del operario.

#### Scenario: Distinción fabricante vs usuario

- **WHEN** el supervisor S guarda clasificación del operario O
- **THEN** `id_operario`=O y `id_usuario`=S

---

## MODIFIED Requirements

### Requirement: Grilla clasificación agregada por artículo (comportamiento anterior)

La grilla que mostraba **una sola fila por artículo** sin dimensión operario queda **reemplazada** por la grilla (artículo × operario) descrita arriba para el flujo de rendimiento.

#### Scenario: Ya no hay fila única por artículo en turno actual

- **WHEN** el usuario abre clasificación con parte desglosado por operarios
- **THEN** no ve una fila agregada sin operario en la sección turno actual
