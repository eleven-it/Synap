# Delta — mpr-opp-parte-produccion

**Change:** `mpr-parte-produccion-grilla-planilla-qc`

---

## MODIFIED Requirements

### Requirement: Grilla de Captura (Componentes × Operarios)

`construir_grilla_parte` (o servicio analista dedicado) MUST armar la grilla analista en `/mpr/parte-produccion/` reutilizando la misma fuente y orden que `construir_datos_planilla_control_calidad` (`mpr/services_maquina_linea.py`) para la fecha y filtros aplicados. Filas MUST ser **máquina × artículo** (orden planilla QC). Columnas fijas MUST ser **Mañana | Tarde | Noche**, cada una con docenas + pares. MUST exponer por fila `id_mpr_maquina`, `id_articulo`, `fabricando` (cupo), `ingresado` (suma docenas×12 + pares de los tres turnos) y `turnos[{docenas, pares, operarios[]}]`. Precarga MUST leer partes existentes por (fecha, máquina, artículo, turno). MUST NOT usar filtro de turno único como eje principal ni columnas por operario. MUST NOT incluir columnas Color ni Talle. MUST NOT leer `lista_produccion_agrupada WHERE en_proceso='Si'` para armar filas.

(Previously: filas componente×operario filtradas por un turno; operarios como columnas; sin máquina ni turnos en columnas.)

#### Scenario: Filas coinciden con planilla QC

- **GIVEN** fecha F, línea L y filtros aplicados
- **WHEN** el analista abre `/mpr/parte-produccion/`
- **THEN** las filas MUST coincidir en orden y contenido con la planilla QC de F/L
- **AND** cada fila MUST incluir máquina y artículo

#### Scenario: Tres columnas turno con docenas y pares

- **GIVEN** una fila con cupo Fabricando > 0
- **WHEN** se renderiza la grilla
- **THEN** MUST mostrarse columnas Mañana, Tarde y Noche
- **AND** cada columna MUST tener inputs docenas y pares
- **AND** MUST NOT mostrarse columnas Color ni Talle

#### Scenario: Ingresado suma los tres turnos

- **GIVEN** docenas/pares cargados en Mañana, Tarde y Noche para un artículo
- **WHEN** se calcula la columna Ingresado
- **THEN** MUST ser la suma en pares equivalentes de los tres turnos

#### Scenario: Sin envíos ni cupo → grilla vacía o filas inactivas

- **GIVEN** base_empresa sin artículos con Fabricando > 0 para la fecha
- **WHEN** se construye la grilla
- **THEN** MUST indicarse vacío en español o filas con inputs deshabilitados

---

### Requirement: Vista/Template Parte Producción (Componente)

`ParteProduccionView` y `RegistrarParteProduccionView` MUST servir la grilla planilla QC. Filtros MUST incluir Fecha (obligatoria), Línea, Máquina, Marcas y búsqueda de artículo; MUST aplicarse server-side. El nombre del artículo MUST mostrarse sin código visible; el código MUST estar en tooltip y/o búsqueda. `RegistrarParteProduccionView` MUST parsear celdas `parte_maq_{id_mpr_maquina}_art_{id_articulo}_turno_{id_turno}` con docenas/pares; MUST crear un `MprParte` por turno con líneas que incluyan `id_mpr_maquina`; unicidad MUST respetar `(parte, id_articulo, id_operario, id_mpr_maquina)`. Mensajes MUST estar en español. `parte_produccion.html` MUST extender `mpr/base_mpr.html`, usar modales Synap y MUST NOT usar `alert`/`confirm`/`prompt` nativos. Fechas visibles MUST usar dd/MM/yyyy.

(Previously: filtro fecha+turno; grilla componente×operario; parseo `parte_art_{id}_op_{id_operario}`; sin máquina en registro analista.)

#### Scenario: Filtros obligatorios y opcionales

- **GIVEN** un analista en `/mpr/parte-produccion/`
- **WHEN** envía filtros sin Fecha
- **THEN** MUST rechazarse o solicitarse Fecha en español
- **WHEN** selecciona Fecha, Línea, Máquina, Marcas o búsqueda
- **THEN** la grilla MUST recargarse acorde a esos filtros

#### Scenario: Artículo sin código visible

- **GIVEN** un artículo con código y descripción
- **WHEN** se muestra la fila en grilla
- **THEN** MUST mostrarse solo la descripción
- **AND** el código MUST estar disponible en tooltip o búsqueda

#### Scenario: Registro por turno con máquina

- **GIVEN** cantidades válidas en celdas de Mañana para máquina M y artículo A
- **WHEN** el analista guarda
- **THEN** MUST persistirse `MprParteLinea.id_mpr_maquina=M`
- **AND** MUST crearse/actualizarse el parte del turno correspondiente

#### Scenario: Feedback sin diálogos nativos

- **GIVEN** error o éxito al guardar
- **WHEN** la vista responde
- **THEN** MUST usarse toast/modal Synap o mensajes Django
- **AND** MUST NOT invocarse diálogos nativos del navegador

---

### Requirement: Warning al Superar Fabricando Disponible (No Bloqueante)

Al guardar desde la grilla analista planilla QC, la suma de pares equivalentes (docenas×12 + pares) de **Mañana + Tarde + Noche** para cada fila artículo×máquina MUST NOT superar el cupo **Fabricando** de esa fila. Si la suma excede el cupo, el sistema MUST rechazar el guardado con mensaje en español que indique artículo, ingresado y Fabricando. MUST NOT guardar parcialmente la fila inválida. El warning no bloqueante por componente global (E8) MUST NOT aplicarse en sustitución de esta validación por fila planilla.

(Previously: warning no bloqueante al superar Fabricando por componente al registrar una celda.)

#### Scenario: Suma dentro del cupo permite guardar

- **GIVEN** Fabricando=24 pares equivalentes en una fila
- **WHEN** la suma de los tres turnos es 20
- **THEN** el guardado MUST completarse sin error de cupo

#### Scenario: Suma sobre cupo bloquea guardado

- **GIVEN** Fabricando=24 pares equivalentes en una fila
- **WHEN** la suma de los tres turnos es 30
- **THEN** MUST rechazarse el guardado con mensaje en español
- **AND** MUST NOT persistirse cantidades de esa fila

---

### Requirement: Línea de parte con máquina y gap

La tabla `mpr_parte_linea` SHALL incluir `id_mpr_maquina` (BIGINT NULL) + `maquina_nombre` snapshot, `cantidad_declarada`, `cantidad_aprobada`, `gap`, `motivo` y unicidad `uk_mpr_parte_linea_maq (id_mpr_parte, id_articulo, id_operario, id_mpr_maquina)`. El flujo analista en `/mpr/parte-produccion/` MUST persistir `id_mpr_maquina` en cada línea registrada (no NULL en registros nuevos del analista). Partes históricos sin máquina MUST seguir siendo legibles. Para partes directos del supervisor, `cantidad_declarada = cantidad_aprobada` y `gap=0`.

(Previously: campos definidos; flujo analista no exigía persistir máquina en cada línea.)

#### Scenario: Línea analista con máquina

- **WHEN** el analista registra producción desde la grilla planilla
- **THEN** cada `MprParteLinea` MUST incluir `id_mpr_maquina` y snapshot `maquina_nombre`

#### Scenario: Parte histórico sin máquina sigue visible

- **GIVEN** líneas antiguas con `id_mpr_maquina` NULL
- **WHEN** se listan o precargan partes
- **THEN** MUST mostrarse sin error de integridad

---

### Requirement: No-funcionales Transversales

El sistema MUST cumplir scoping por `base_empresa`, `MprLoginRequiredMixin`, tipos AdministraNET, fechas dd/MM/yyyy, mensajes en español y ruta `/mpr/parte-produccion/`. Templates MUST extender `mpr/base_mpr.html` y MUST NOT usar `ventas/templates` como referencia. En la grilla analista MUST NOT usarse diálogos nativos del navegador; confirmaciones y avisos MUST usar modales Synap o `mprShowAviso`/`SynapMessages`.

(Previously: canon UI sin prohibición explícita de diálogos nativos en parte-produccion.)

#### Scenario: Aislación por base_empresa

- **GIVEN** partes de EMP1 y EMP2
- **WHEN** se opera con base_empresa=EMP1
- **THEN** MUST verse solo datos de EMP1

---

## ADDED Requirements

### Requirement: Cupo Fabricando e inputs condicionados

Por cada fila máquina×artículo MUST mostrarse columna **Fabricando** (cupo). Inputs de docenas/pares MUST estar activos solo si Fabricando > 0; si Fabricando = 0, MUST deshabilitarse sin permitir edición.

#### Scenario: Fila sin cupo deshabilitada

- **GIVEN** una fila con Fabricando=0
- **WHEN** se renderiza la grilla
- **THEN** los inputs de los tres turnos MUST estar deshabilitados

#### Scenario: Fila con cupo habilitada

- **GIVEN** una fila con Fabricando>0
- **WHEN** se renderiza la grilla
- **THEN** los inputs MUST estar habilitados para edición

---

### Requirement: Operario por celda turno (roster)

Cada celda turno MUST mostrar el operario del roster de la línea y turno correspondiente. MUST heredar `id_operario` cuando hay un único operario. Si hay varios operarios en roster, MUST ofrecer selector. Si no hay roster para la línea/turno, la celda MUST deshabilitarse y MUST mostrarse aviso en español en la celda o fila.

#### Scenario: Un operario en roster

- **GIVEN** roster con un operario para línea L turno Mañana
- **WHEN** se renderiza la celda Mañana de una fila de L
- **THEN** MUST mostrarse ese operario como seleccionado

#### Scenario: Varios operarios en roster

- **GIVEN** roster con dos operarios para un turno
- **WHEN** se renderiza la celda
- **THEN** MUST permitirse elegir operario antes de guardar

#### Scenario: Sin roster celda inactiva

- **GIVEN** turno sin operarios en roster para la línea filtrada
- **WHEN** se renderiza la celda
- **THEN** MUST deshabilitarse la celda
- **AND** MUST mostrarse indicación en español

---

### Requirement: Alcance excluido del cambio de grilla

El cambio MUST NOT alterar el comportamiento de la PWA operario `/mpr/mi-parte/`. MUST NOT implementar pantalla digital de clasificación CC (semi/2da/scrap) salvo mantener enlaces existentes sin rotura. MUST NOT añadir columnas Color ni Talle a la grilla analista.

#### Scenario: PWA sin regresión

- **GIVEN** flujo operario en `/mpr/mi-parte/`
- **WHEN** se despliega este cambio
- **THEN** MUST conservarse el comportamiento previo de la PWA

#### Scenario: Enlaces a clasificación CC siguen operativos

- **GIVEN** pantallas que enlazan a `/mpr/parte-produccion/` o clasificación
- **WHEN** el usuario navega
- **THEN** MUST NOT producirse error 404 por este cambio
