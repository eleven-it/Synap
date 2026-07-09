# mpr-opp-parte-produccion

## Purpose

Define el capability de **registro de partes de producción** (OPP-parte) en el módulo MPR de Synap: un ledger que registra manualmente la producción real por turno×operario×artículo (PACK), conectando el roster (Etapa 3) con el tablero consolidado (Etapa 2). Implementa la transición Enviado→Producción mediante modelos (`MprParte`, `MprParteLinea`, `MprParteAjuste`) con **asiento físico activo** (desde Etapa 5). Completa la fórmula definitiva de la columna "Enviado a producción" en el tablero: `max(0, OPT_liberado_acumulado − OPP_parte_registrado_acumulado)`.

Esta capability es la Etapa 4 del refactor MPR multietapa, ampliada en Etapa 5 con movimiento físico: al registrar partes se escribe stock en depósito Producción (explosión BOM pack→componentes), y los ajustes aplican deltas físicos. El desmontaje correspondiente de `ejecutar_liberar_opt` se documenta en `mpr-pipeline-multietapa`.

Archivado desde los changes SDD `mpr-pipeline-etapa4-opp-parte` (2026-07-03) y `mpr-pipeline-etapa5-transiciones-desmontaje` (2026-07-03).

Documento operativo asociado: `docs/mpr/OPP_PARTE_PRODUCCION.md`.

---

## Requirements

### Requirement: Modelos de Parte de Producción

El sistema MUST proveer tres modelos Django nuevos en `mpr/models.py` para registrar partes de producción:

#### `MprParte` (cabecera del parte)

- `id` (UUIDField, PK, default=uuid4): identificador único.
- `base_empresa` (CharField 64, db_index): scope por empresa.
- `fecha_produccion` (DateField): fecha de producción, puede ser pasada (registro diferido). Formato UI: dd/MM/yyyy.
- `turno` (ForeignKey a MprTurno, on_delete=PROTECT): turno de producción. PROTECT evita eliminar turno si hay partes asociados.
- `id_usuario` (IntegerField): usuario que registró el parte en Synap.
- `registrado_en` (DateTimeField, auto_now_add): timestamp de registro.
- `notas` (CharField 500, blank): notas opcionales.
- `movimiento_fisico_ok` (BooleanField, default=False): flag de idempotencia del asiento físico en MySQL (Etapa 5). True indica que el stock físico fue escrito exitosamente.

El sistema MUST garantizar:
- **Sin UniqueConstraint en (base_empresa, turno, fecha_produccion)**: múltiples partes por mismo turno/fecha permitidos.
- **Índices compuestos**: Index (`base_empresa`, `fecha_produccion`), Index (`base_empresa`, `turno_id`).

#### `MprParteLinea` (filas artículo×operario)

- `parte` (ForeignKey a MprParte, on_delete=CASCADE): parte al que pertenece la línea.
- `id_articulo` (IntegerField): artículo nivel COMPONENTE (desde grilla Fabricando, E8; anteriormente PACK igual que OPT en E4-E7).
- `id_operario` (IntegerField): FK lógico a `sue_abm_empleado.id_sue_abm_empleado`.
- `operario_nombre` (CharField 255): snapshot de nombre_empleado al momento del registro. No se actualiza.
- `cantidad` (DecimalField 15,2): unidades producidas.

El sistema MUST garantizar:
- **UniqueConstraint**: (`parte`, `id_articulo`, `id_operario`).
- **Ordenamiento**: por `id_articulo`, `id_operario`.

#### `MprParteAjuste` (correcciones append-only)

- `id` (UUIDField, PK, default=uuid4): identificador único.
- `parte` (ForeignKey a MprParte, on_delete=PROTECT): parte al que aplica el ajuste. PROTECT evita eliminar cabecera si hay ajustes.
- `id_articulo` (IntegerField): artículo del ajuste.
- `id_operario` (IntegerField): operario del ajuste.
- `delta` (DecimalField 15,2): ajuste positivo o negativo. Cantidad efectiva = linea.cantidad + Σdeltas.
- `motivo` (CharField 255): razón del ajuste.
- `id_usuario` (IntegerField): usuario que registró el ajuste.
- `registrado_en` (DateTimeField, auto_now_add): timestamp de registro.
- `ajuste_fisico_ok` (BooleanField, default=False): flag de idempotencia del delta físico en MySQL (Etapa 5). True indica que el delta fue aplicado al stock físico exitosamente.

El sistema MUST garantizar:
- **Índice compuesto**: Index (`parte`, `id_articulo`, `id_operario`).
- **Ordenamiento**: por `registrado_en`.

La migración MUST ser additive-only (solo CREATE TABLE), sin ALTER TABLE en tablas existentes.

#### Scenario: Crear parte con línea respeta unique constraint

- DADO base_empresa=X, turno=T1, fecha=2026-07-03
- CUANDO se crea MprParte y MprParteLinea(id_articulo=10, id_operario=5, cantidad=8)
- ENTONCES ambos se persisten sin error
- Y un segundo intento de MprParteLinea(parte=misma, id_articulo=10, id_operario=5) MUST lanzar IntegrityError

#### Scenario: Múltiples partes por mismo turno y fecha

- DADO dos MprParte con base_empresa=X, turno=T1, fecha_produccion=2026-07-03
- CUANDO ambos se guardan
- ENTONCES ambos persisten sin error (no hay UniqueConstraint en cabecera)

---

### Requirement: Grilla de Captura (Componentes × Operarios)

`construir_grilla_parte(base_empresa, fecha, turno_id)` MUST armar filas desde componentes con **Fabricando > 0**. Fabricando(comp) = max(0, Σ MprEnvioProduccion[comp] − stock_produccion[comp]). MUST reutilizar `_query_enviado_tablero_componente`, `_pivot_stock_por_tipo_mpr`, `_fetch_descripciones_articulo`. Retorno MUST usar keys `componentes`/`componentes_vacio` (NO `packs`/`packs_vacio`). Cada fila MUST exponer `fabricando`. Celdas preexistentes (fecha+turno) MUST precargarse. MUST NOT leer `lista_produccion_agrupada WHERE en_proceso='Si'` para armar filas.

**Nota E8 (03/07/2026):** Fuente de filas migrada desde query legacy `lista_produccion_agrupada` (nivel pack) a ledger `MprEnvioProduccion` (nivel componente, E7) + fórmula Fabricando. Keys renombradas `packs`→`componentes`. El registro del parte opera a nivel componente sin explosión BOM intermedia.

El registro MUST enviarse por lote (un solo submit guarda todas las celdas como MprParte + N MprParteLineas con `id_articulo` = ID de componente).

#### Scenario: Componente con envío y sin producción aparece con fabricando correcto

- DADO MprEnvioProduccion[comp=C, total=30], stock_produccion[C]=0
- CUANDO construir_grilla_parte(base, fecha, turno)
- ENTONCES fila C MUST aparecer con fabricando=30

#### Scenario: Componente cuya producción igualó/superó el enviado NO aparece

- DADO MprEnvioProduccion[comp=C, total=30], stock_produccion[C]=30
- CUANDO construir_grilla_parte
- ENTONCES C MUST NOT aparecer (fabricando=0)

#### Scenario: Sin envíos → grilla vacía

- DADO base_empresa=X sin MprEnvioProduccion
- CUANDO construir_grilla_parte
- ENTONCES componentes_vacio=True, lista componentes=[]

#### Scenario: Pack legacy en_proceso='Si' sin envío tablero NO aparece

- DADO pack P en lista_produccion_agrupada(en_proceso='Si') sin MprEnvioProduccion para P
- CUANDO construir_grilla_parte
- ENTONCES P MUST NOT aparecer en la grilla

#### Scenario: Roster vacío emite aviso

- DADO turno T1, fecha F1 sin MprRosterDia
- CUANDO construir_grilla_parte
- ENTONCES roster_vacio=True; MUST mostrarse aviso en español

---

### Requirement: Snapshot de operario_nombre al Registrar

Al crear una MprParteLinea, el sistema MUST capturar `operario_nombre` como snapshot desde `sue_abm_empleado` usando `str_or_default` (core.utils.administranet_types). El snapshot es histórico y NO MUST actualizarse si el nombre cambia en ABM posteriormente.

#### Scenario: Snapshot queda fijo tras cambio de nombre en ABM

- DADO operario id=5 con nombre="Juan Pérez" en sue_abm_empleado al momento del registro
- CUANDO se registra MprParteLinea para id_operario=5
- ENTONCES operario_nombre MUST ser "Juan Pérez"
- Y si sue_abm_empleado cambia el nombre a "Juan P." después, la línea existente MUST seguir mostrando "Juan Pérez"

---

### Requirement: Asiento Físico Componente Directo (ya_componentes=True)

`_registrar_asiento_fisico_opp_parte` MUST aceptar `ya_componentes: bool = False`. Cuando `ya_componentes=True`, MUST escribir `stock_deposito[Producción][comp]` directamente sin llamar `_explode_packs_to_components`. `registrar_parte_produccion` MUST invocar con `ya_componentes=True`. Idempotencia via `movimiento_fisico_ok` MUST preservarse. Callers previos sin parámetro MUST mantener comportamiento (backward-safe).

**Nota E8 (03/07/2026):** Asiento migrado desde explosión BOM pack→componentes a escritura directa por componente. El parámetro `ya_componentes` permite convivencia con callers legacy (E5) que aún operan con packs.

**Nota Histórica (Pre-Etapa 5):** Antes de Etapa 5, el registro de partes era ledger-only (no escribía stock físico). `ejecutar_liberar_opt` era la única función que escribía en depósito Producción. Desde Etapa 5, el asiento físico fue trasladado a `registrar_parte_produccion`, y `ejecutar_liberar_opt` fue desmontado (ver delta en `mpr-pipeline-multietapa`).

#### Scenario: Registro de componente sube stock Producción sin explotar BOM

- DADO linea(id_articulo=C, cantidad=20), stock_deposito[C, Produccion]=100
- CUANDO registrar_parte_produccion (ya_componentes=True)
- ENTONCES stock_deposito[C, Produccion]=120, movimiento_fisico_ok=True
- Y MUST NOT haberse llamado _explode_packs_to_components

#### Scenario: Idempotencia preservada

- DADO MprParte.movimiento_fisico_ok=True
- CUANDO se re-invoca asiento
- ENTONCES stock_deposito MUST NOT cambiar

#### Scenario: Integración con Fabricando (E7 auto-balance)

- DADO Fabricando[C]=15 antes del parte (enviado_tablero=50, stock_prod=35)
- CUANDO registrar_parte_produccion registra cantidad=10 para C
- ENTONCES en el siguiente render del tablero Fabricando[C]=max(0, 50−45)=5
- Y MUST NOT haber doble conteo en la columna Fabricando

---

### Requirement: Fecha de Producción Pasada Permitida

El sistema MUST permitir que `fecha_produccion` en MprParte sea una fecha pasada (registro posterior). No existe regla de cierre formal en Etapa 4.

#### Scenario: Registro posterior a fecha pasada

- DADO fecha actual del servidor = 2026-07-03
- CUANDO se crea MprParte con fecha_produccion = 2026-06-28
- ENTONCES el parte se guarda sin error de validación

---

### Requirement: Vista/Template Parte Producción (Componente)

`RegistrarParteProduccionView` MUST parsear `parte_art_{id_componente}_op_{id_operario}` (sin cambio funcional). Mensajes MUST en español con conteo de líneas registradas + warnings de tope. `parte_produccion.html` MUST mostrar encabezado "Artículo/Componente" (NO "Pack"), usar keys `componentes`/`componentes_vacio`, mostrar columna Fabricando por fila, fechas en dd/MM/yyyy.

**Nota E8 (03/07/2026):** Template refactorizado desde encabezado "Pack" + keys `packs` (E4-E7) a "Artículo/Componente" + keys `componentes`. Columna Fabricando añadida como contexto visual coherente con el tablero.

#### Scenario: Flujo completo grilla→registro→reflejo

- DADO base_empresa con envíos (comp A Fabricando=15, comp B Fabricando=8), turno T1
- CUANDO usuario carga fecha+turno en ParteProduccionView
- ENTONCES MUST mostrarse 2 filas con Fabricando=15 y 8 en columna visible
- CUANDO usuario completa cantidades y guarda
- ENTONCES grilla MUST reflejar Producido actualizado y Fabricando reducido en el siguiente render

---

### Requirement: Trazabilidad E6 — Compatibilidad Partes Componente

Partes E8 MUST tener `MprParte.id_lista_produccion = None` (componentes sin OPT activa en lista_produccion_agrupada). `_escribir_historico_opp_parte` MUST NOT escribir en `lista_produccion_historico` cuando id_lista=None (guard ya existente). `construir_trazabilidad_opt` MUST NOT listar partes E8. MUST NOT lanzarse excepción al procesar partes E8 en ninguna función E6.

**Nota E8 (03/07/2026):** Limitación conocida: partes por componente no tienen traza OPT bidireccional (id_lista=None). El flujo E8 (tablero directo) no requiere OPT activa; el flujo E5-E7 legacy (wizard + OPT) sí mantiene traza completa.

#### Scenario: Parte E8 no rompe trazabilidad OPT

- DADO MprParte(id_lista_produccion=None) registrado desde grilla componente
- CUANDO se ejecuta _escribir_historico_opp_parte y construir_trazabilidad_opt
- ENTONCES MUST NOT crearse fila en lista_produccion_historico
- Y MUST NOT lanzarse excepción; trazabilidad OPT no incluye el parte

---

### Requirement: Corrección Append-only via MprParteAjuste (con Delta Físico desde Etapa 5)

El sistema MUST NOT editar destructivamente `MprParteLinea.cantidad`. Una corrección MUST crear un nuevo `MprParteAjuste` con un `delta` (positivo o negativo). La **cantidad efectiva** de (parte, id_articulo, id_operario) = `MprParteLinea.cantidad + Σ(MprParteAjuste.delta)` para los ajustes de esa combinación.

**Desde Etapa 5:** Al crear un `MprParteAjuste`, el sistema MUST también aplicar el delta al stock físico en depósito Producción:
- Si delta > 0: INSERT en `stock` (Entrada) + UPDATE `stock_deposito` (saldo += delta)
- Si delta < 0: INSERT en `stock` (Salida) + UPDATE `stock_deposito` (saldo += delta)

El sistema MUST validar:
- La cantidad efectiva (ledger) NO MUST quedar negativa
- El saldo físico en `stock_deposito` NO MUST quedar negativo
- Si cualquier validación falla, el sistema MUST rechazar el ajuste SIN crear `MprParteAjuste` ni modificar stock físico

El flag `ajuste_fisico_ok=True` se marca tras commit MySQL exitoso. Si MySQL falla, el ajuste Django MUST revertirse (`.delete()`) para mantener coherencia ledger-stock.

#### Scenario: Ajuste positivo incrementa cantidad efectiva Y stock físico

- DADO MprParteLinea(cantidad=10), stock_deposito[C, Produccion]=50
- CUANDO se registra MprParteAjuste(delta=+5)
- ENTONCES cantidad_efectiva = 15
- Y stock_deposito[C, Produccion]=55
- Y MprParteLinea.cantidad MUST seguir siendo 10

#### Scenario: Ajuste negativo reduce cantidad efectiva Y stock físico

- DADO MprParteLinea(cantidad=10), stock_deposito[C, Produccion]=50
- CUANDO se registra MprParteAjuste(delta=-3)
- ENTONCES cantidad_efectiva = 7
- Y stock_deposito[C, Produccion]=47

#### Scenario: Ajuste rechazado si deja cantidad efectiva negativa

- DADO MprParteLinea(cantidad=5) sin ajustes previos
- CUANDO se intenta registrar MprParteAjuste(delta=-10)
- ENTONCES el sistema MUST rechazar la operación con error en español "La cantidad efectiva no puede ser negativa"
- Y NO MUST crear el MprParteAjuste

#### Scenario: Ajuste rechazado si deja saldo físico negativo

- DADO stock_deposito[C, Produccion]=5
- CUANDO se intenta registrar MprParteAjuste(delta=-10)
- ENTONCES el sistema MUST rechazar con mensaje español "Saldo insuficiente en Producción para aplicar el ajuste"
- Y NO MUST crear el MprParteAjuste

---

### Requirement: Warning al Superar Fabricando Disponible (No Bloqueante)

Al guardar un parte E8, si cantidad_registrada[comp] > Fabricando[comp] (calculado post-transacción via _query_enviado_tablero_componente + _pivot_stock_por_tipo_mpr), el sistema SHOULD mostrar warning visible en UI en español. MUST NOT bloquear el guardado. El warning MUST mencionar nombre del componente, cantidad registrada y Fabricando disponible.

**Nota E8 (03/07/2026):** Warning refactorizado desde comparación OPP_parte_acumulado vs OPT_liberado_acumulado (E4-E7) a comparación directa contra Fabricando disponible (E7, columna del tablero). El warning refleja consistentemente el mismo indicador que el usuario ve en la UI del tablero.

#### Scenario: Fabricando=20, se registran 30 → warning + parte guardado

- DADO Fabricando[C]=20 (enviado=50, stock_prod=30), cantidad_a_registrar=30
- CUANDO se guarda el parte
- ENTONCES parte MUST guardarse sin bloqueo
- Y MUST mostrarse warning en español mencionando C, registrado=30, Fabricando=20

#### Scenario: Sin warning cuando dentro del Fabricando

- DADO Fabricando[C]=20, cantidad_a_registrar=10
- CUANDO se guarda el parte
- ENTONCES MUST NOT mostrarse warning de tope para C

---

### Requirement: No-funcionales Transversales

El sistema MUST cumplir los siguientes requisitos no-funcionales en todas las operaciones relacionadas con partes de producción:

| Requisito | Norma |
|-----------|-------|
| Scoping | Todas las queries a MprParte MUST filtrar por base_empresa |
| Autenticación | Todas las vistas MUST usar MprLoginRequiredMixin |
| Tipos AdministraNET | Lecturas de sue_abm_empleado MUST usar str_or_default, to_int_or_none |
| Fechas UI | Todas las fechas visibles al usuario MUST mostrarse en dd/MM/yyyy |
| Idioma | Todos los mensajes de error, warning y éxito MUST estar en español |
| Rutas | Prefijo `/mpr/parte-produccion/`; sin colisión con `/mpr/opp/` (Etapa 5) |
| Canon UI | Templates MUST extender `mpr/base_mpr.html`; NOT usar ventas/templates como referencia |

#### Scenario: Aislación por base_empresa

- DADO parte P1 (base_empresa='EMP1') y parte P2 (base_empresa='EMP2')
- CUANDO se lista partes para base_empresa='EMP1'
- ENTONCES MUST retornarse solo P1, no P2

---

## Integration with Pipeline

Este capability se integra con el spec `mpr-pipeline-multietapa` mediante la fórmula definitiva de la columna Enviado:

**Columna Enviado a Producción (Fórmula Definitiva desde Etapa 4)**

La columna "Enviado a producción" del tablero consolidado (definida en `mpr-pipeline-multietapa`) MUST calcularse como:

```
Enviado_virtual(pack) = max(0, OPT_liberado_acumulado(pack) − OPP_parte_registrado_acumulado(pack))
```

donde `OPP_parte_registrado_acumulado(pack)` = `SUM(MprParteLinea.cantidad + Σ MprParteAjuste.delta)` para el pack en base_empresa.

La explosión BOM (pack → componentes) MUST seguir aplicándose en `listar_tablero_por_articulo`. La columna Producción (col 4) MUST seguir leyéndose de `stock_deposito` sin cambio. El indicador y tooltip "PROVISIONAL" previo a Etapa 4 MUST eliminarse del encabezado de la columna Enviado.

Nuevo servicio requerido: `opp_parte_acumulado_por_pack(base_empresa, pack_ids) → dict{id_articulo: decimal}`.

#### Scenario: Sin partes registradas — Enviado igual a OPT liberado (backward compatible)

- DADO pack=P con OPT_liberado_acum=50 y sin MprParteLineas asociadas
- CUANDO se calcula Enviado en el tablero
- ENTONCES Enviado MUST ser 50 (OPP_parte_acum = 0, backward safe)

#### Scenario: Con partes registradas — Enviado decrece

- DADO pack=P con OPT_liberado_acum=50 y OPP_parte_acum=20
- CUANDO se calcula Enviado
- ENTONCES Enviado MUST ser max(0, 50−20) = 30

#### Scenario: Enviado nunca negativo

- DADO pack=P con OPT_liberado_acum=30 y OPP_parte_acum=50
- CUANDO se calcula Enviado
- ENTONCES Enviado MUST ser max(0, 30−50) = 0

#### Scenario: Columna Producción inalterada

- DADO pack=P con partes registradas (OPP_parte_acum=15)
- CUANDO se renderiza el tablero
- ENTONCES la columna Producción (col 4) MUST leerse de stock_deposito[tipo_mpr=Produccion]
- Y NO MUST verse afectada por MprParteLinea

---

## Etapa 6: Trazabilidad OPT (2026-07-03)

### Requirement: Campo id_lista_produccion en MprParte

El sistema MUST agregar `id_lista_produccion = IntegerField(null=True, blank=True)` a `MprParte` mediante migración aditiva `0013_mprparte_id_lista_produccion`. La migración MUST ser additive-only (no ALTER con NOT NULL, no modificación de filas existentes). Al registrar un parte, el sistema MUST intentar capturar automáticamente el `id_lista_produccion` de la OPT activa del artículo (registros con `en_proceso_produccion='Si'` en `lista_produccion_agrupada`). Si no se identifica OPT activa → `id_lista_produccion` MUST quedar `null` (best-effort). Si existen múltiples OPTs activas para el mismo artículo → el sistema MUST tomar la primera y registrar warning en log.

#### Scenario: Parte con OPT activa persiste id_lista_produccion

- DADO artículo id_articulo=A con registro en lista_produccion_agrupada(en_proceso_produccion='Si', id_lista_produccion=42)
- CUANDO se registra un MprParte que incluye el artículo A
- ENTONCES MprParte.id_lista_produccion MUST ser 42

#### Scenario: Parte sin OPT identificable queda null

- DADO artículo id_articulo=A sin registros con en_proceso_produccion='Si' en lista_produccion_agrupada
- CUANDO se registra un MprParte con el artículo A
- ENTONCES MprParte.id_lista_produccion MUST ser null sin error

#### Scenario: Múltiples OPTs activas → best-effort primera + warning

- DADO artículo id_articulo=A con dos registros en lista_produccion_agrupada(en_proceso_produccion='Si', id_lista_produccion=42 y 55)
- CUANDO se registra un MprParte con el artículo A
- ENTONCES MprParte.id_lista_produccion MUST ser 42 (primera encontrada)
- Y MUST registrarse un warning en log indicando ambigüedad

---

### Requirement: Escritura a lista_produccion_historico desde asiento OPP-parte

El sistema MUST insertar una fila en `lista_produccion_historico` (tipo_evento='OPP', id_lista_produccion, codigo_movimiento_mstock, id_operario, fecha) desde `_registrar_asiento_fisico_opp_parte` inmediatamente después del asiento en movimiento_stock. Si la tabla `lista_produccion_historico` no existe en la base MySQL → el sistema MUST continuar sin error (fallback graceful), registrando warning en log. Si `MprParte.id_lista_produccion` es null en el momento del asiento → el sistema MUST omitir la escritura al historico sin error.

#### Scenario: Asiento OPP-parte crea evento en historico

- DADO MprParte con id_lista_produccion=42, id_operario=5, y asiento físico con codigo_movimiento='MOV-01'
- CUANDO se ejecuta _registrar_asiento_fisico_opp_parte
- ENTONCES MUST existir nueva fila en lista_produccion_historico con tipo_evento='OPP', id_lista_produccion=42, codigo_movimiento_mstock='MOV-01', id_operario=5

#### Scenario: Tabla historico inexistente no interrumpe el asiento

- DADO que lista_produccion_historico no existe en la base MySQL
- CUANDO se ejecuta _registrar_asiento_fisico_opp_parte
- ENTONCES el asiento en movimiento_stock y stock MUST completarse sin excepción
- Y MUST registrarse warning en log indicando que historico no disponible

#### Scenario: id_lista_produccion null omite escritura historico

- DADO MprParte.id_lista_produccion=null
- CUANDO se ejecuta _registrar_asiento_fisico_opp_parte
- ENTONCES MUST NOT escribirse fila en lista_produccion_historico
- Y el asiento de stock MUST completarse normalmente

---

### Requirement: Deprecación de ejecutar_opp y RegistrarOppView

`ejecutar_opp`, `ejecutar_opp_por_componentes` (services.py) y `RegistrarOppView` (views.py) MUST marcarse como deprecated con comentario `# DEPRECATED (E6): pendiente eliminación hasta migrar wizard paso 3`. Estas funciones y vistas MUST NOT eliminarse en E6. Su comportamiento existente MUST permanecer inalterado.

#### Scenario: ejecutar_opp sigue funcionando tras deprecación

- DADO que ejecutar_opp está marcada deprecated con comentario
- CUANDO wizard paso 3 llama a ejecutar_opp
- ENTONCES la función MUST ejecutarse con el mismo comportamiento previo a E6
- Y el comentario DEPRECATED MUST ser visible en el código fuente

---

### Requirement: Cabecera de parte con estado y origen (flujo dos etapas)

La tabla `mpr_parte` SHALL incluir:
- `estado` (VARCHAR): `borrador` | `pendiente` | `aprobado` (default `aprobado` por backfill).
- `origen` (VARCHAR): `movil_operario` | `directo_supervisor` (default `directo_supervisor`).
- `id_usuario_supervisor` (INT NULL) y `aprobado_en` (DATETIME NULL): auditoría de aprobación.

El asiento físico a depósito "Producción" SHALL ejecutarse **solo** cuando el parte alcanza `estado=aprobado` (aprobación del supervisor, `aprobar_parte_produccion`) o al crear un parte directo del supervisor (`origen=directo_supervisor`, nace aprobado). Los partes `borrador`/`pendiente` MUST NOT mover stock (guardan `cantidad=0`).

#### Scenario: Parte pendiente no mueve stock

- **WHEN** se guarda un parte con `estado=pendiente` (`origen=movil_operario`)
- **THEN** `movimiento_fisico_ok=false` y `stock_deposito` de Producción no cambia

#### Scenario: Compatibilidad de partes históricos

- **GIVEN** partes anteriores al cambio sin `estado`
- **THEN** el sistema los trata como `aprobado`/`directo_supervisor` (backfill por defecto) sin romper reportes

---

### Requirement: Línea de parte con máquina y gap

La tabla `mpr_parte_linea` SHALL incluir:
- `id_mpr_maquina` (BIGINT NULL) + `maquina_nombre` (VARCHAR) snapshot.
- `cantidad_declarada` (DECIMAL): lo cargado por el operario.
- `cantidad_aprobada` (DECIMAL NULL): lo aprobado por el supervisor.
- `gap` (DECIMAL): `cantidad_aprobada − cantidad_declarada`.
- `motivo` (VARCHAR NULL): requerido si `gap != 0`.

La unicidad pasa a `uk_mpr_parte_linea_maq (id_mpr_parte, id_articulo, id_operario, id_mpr_maquina)`. Para partes directos del supervisor, `cantidad_declarada = cantidad_aprobada` y `gap=0`. La columna `cantidad` histórica SHALL mantenerse compatible: en la aprobación se sincroniza `cantidad = cantidad_aprobada`.

#### Scenario: Línea de operario con corrección

- **WHEN** el operario declara 41 y el supervisor aprueba 39
- **THEN** la línea guarda `cantidad_declarada=41`, `cantidad_aprobada=39`, `gap=-2`, `motivo` presente

#### Scenario: Migración idempotente vía catálogo

- **WHEN** se ejecuta dos veces el ALTER de columnas en `core/services/legacy_mysql_schema/catalog.py`
- **THEN** no falla ni duplica columnas

---

## Fuera de Alcance (Etapa 4)

Los siguientes elementos NO están cubiertos por este spec y se abordarán en iteraciones posteriores:

- **Movimiento físico Enviado→Producción y desmontaje de `ejecutar_liberar_opt`**: ✅ Implementado en Etapa 5 del refactor MPR.
- **Transiciones Producción→{Desperdicio|Planchado}/Planchado→{2da|Semi}**: ✅ Implementado en Etapa 5.
- **Trazabilidad OPT drill-down con `id_lista_produccion`**: ✅ Implementado en Etapa 6 (spec permanente: `mpr-trazabilidad-opt`).
- **Eliminación efectiva de ejecutar_opp y reescritura wizard paso 3**: pendiente (espera migración wizard).
- **Plantillas de rotación automáticas**: iteración futura.
- **Cierre formal de parte por turno/fecha**: iteración futura.
- **Eliminación de partes**: NO implementado en Etapa 4; MprParteAjuste con PROTECT evita eliminar cabeceras con ajustes.
