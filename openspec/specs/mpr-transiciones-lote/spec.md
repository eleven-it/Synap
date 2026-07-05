# mpr-transiciones-lote

## Purpose

Define el capability de **transiciones entre etapas por lote** en el módulo MPR de Synap: servicio de transferencia de stock entre etapas físicas (`transferir_stock_entre_etapas`), modelo de trazabilidad (`MprTransicionLote`), y acciones contextuales por fila en el tablero de producción para ejecutar transiciones de inspección y movimientos entre depósitos MPR.

Esta capability es la Etapa 5 del refactor MPR multietapa. Implementa las transiciones legales (c) Producción→{Desperdicio|Planchado} y (d) Planchado→{2da Selección|Semi Elaborado} con validación contra `TRANSICIONES_LEGALES` de `mpr/pipeline.py`.

Archivado desde el change SDD `mpr-pipeline-etapa5-transiciones-desmontaje` (2026-07-03), con delta de la Etapa 9 `mpr-pipeline-etapa9-acciones-consolidadas` (2026-07-03): servicio `transferir_stock_lote` best-effort y eliminación de las acciones por fila del tablero (consolidadas en pantallas de lote — ver capability `mpr-acciones-lote-tablero`).

Documento operativo asociado: `docs/mpr/TRANSICIONES_LOTE.md`.

> **Delta Etapa 10 (`mpr-pipeline-etapa10-clasificacion-consolidada`, 2026-07-03):**
> `Planchado` deja de ser etapa con stock. Las transiciones legales desde Producción pasan a
> ser `Produccion → {SemiElaborado | 2daSeleccion | Scrap}`; se retiran `Produccion → Planchado`
> y `Planchado → {2daSeleccion | SemiElaborado}`. Además `transferir_stock_entre_etapas` y
> `transferir_stock_lote` aceptan un parámetro **`fecha`** (opcional) que fecha el asiento MSTOCK
> (carga diferida). Los escenarios "Happy path" que usan `Planchado` como origen o destino quedan
> **obsoletos**; el destino canónico de ejemplo pasa a ser `SemiElaborado`.

---

## Requirements

### Requirement: Servicio de Transferencia Entre Etapas

El sistema MUST proveer `transferir_stock_entre_etapas(base_empresa, id_usuario, id_articulo, tipo_origen, tipo_destino, cantidad, notas="", fecha=None)` que:

- Valida con `validar_transicion(tipo_origen, tipo_destino, cantidad, saldo_origen)` usando `TRANSICIONES_LEGALES` de `pipeline.py`
- Genera comprobante MSTOCK (tipo_mov='OPP', motivo='Parte producción') con salida desde origen y entrada a destino
- Actualiza `stock_deposito` en ambos depósitos (decrementa origen, incrementa destino)
- Crea `MprTransicionLote` para trazabilidad
- MUST NOT ejecutar si cantidad ≤ 0, cantidad > saldo_origen, o transición fuera de TRANSICIONES_LEGALES
- MUST fechar el asiento MSTOCK con `fecha` si se provee; de lo contrario con `date.today()`
- Retorna tupla `(ok, codigo_movimiento, nro_comprobante, mensaje_error)`

**Transiciones legales (Etapa 10):**
- Producción→Semi Elaborado, Producción→2da Selección, Producción→Desperdicio (Scrap)
- {2da Selección | Semi Elaborado}→Terminado (armado)

> Histórico Etapa 5 (obsoleto): Producción→Planchado y Planchado→{2da|Semi}.

El servicio opera a nivel componente directo (no pack); el tablero ya explota BOM pack→componentes.

En Etapa 9 este servicio se conserva sin cambios y se reutiliza en lote mediante `transferir_stock_lote` (ver más abajo).

#### Scenario: Happy path Produccion→Semi Elaborado

- DADO stock_deposito[A, Produccion]=100, stock_deposito[A, SemiElaborado]=20
- CUANDO transferir_stock_entre_etapas(base, usr, A, 'Produccion', 'SemiElaborado', 30)
- ENTONCES stock_deposito[A, Produccion]=70, stock_deposito[A, SemiElaborado]=50
- Y MprTransicionLote creado con tipo_origen='Produccion', tipo_destino='SemiElaborado', cantidad=30

#### Scenario: Happy path Produccion→2da Selección

- DADO stock_deposito[A, Produccion]=50
- CUANDO transferir_stock_entre_etapas(..., 'Produccion', '2daSeleccion', 15)
- ENTONCES Produccion[A]=35, 2daSeleccion[A] sube 15

#### Scenario: Happy path Produccion→Desperdicio

- DADO stock_deposito[A, Produccion]=80
- CUANDO transferir_stock_entre_etapas(..., 'Produccion', 'Desperdicio', 10)
- ENTONCES Produccion[A]=70, Desperdicio[A] sube 10
- Y ok=True, codigo_movimiento provisto

#### Scenario: Fecha del parte fecha el asiento

- DADO transferir_stock_entre_etapas(..., 'Produccion', 'SemiElaborado', 5, fecha=date(2026,7,3))
- CUANDO se ejecuta la transición
- ENTONCES el MSTOCK se registra con fecha 03/07/2026 (no la del sistema)

#### Scenario: Rechaza transición ilegal

- DADO intento tipo_origen='Produccion', tipo_destino='Terminado' (no en TRANSICIONES_LEGALES)
- CUANDO se llama el servicio
- ENTONCES retorna ok=False, mensaje español "Transición no permitida: Produccion → Terminado"
- Y stock_deposito NO MUST modificarse

#### Scenario: Rechaza cantidad mayor a saldo

- DADO stock_deposito[A, Produccion]=20, cantidad solicitada=50
- CUANDO se llama el servicio
- ENTONCES retorna ok=False, mensaje español "Saldo insuficiente en Produccion: disponible 20, solicitado 50"

#### Scenario: Rechaza cantidad ≤ 0

- DADO cantidad=0
- CUANDO se llama el servicio
- ENTONCES retorna ok=False, mensaje español "La cantidad debe ser mayor a cero"

---

### Requirement: Servicio de Transferencia en Lote (Etapa 9)

El sistema MUST proveer `transferir_stock_lote(base_empresa, id_usuario, items: list[dict])` donde cada item es `{id_articulo, tipo_origen, tipo_destino, cantidad}`. MUST ejecutar N llamadas individuales a `transferir_stock_entre_etapas` en modo best-effort (si una falla, las demás continúan). MUST retornar `{exitosas: int, fallidas: int, errores: list[(id_articulo, mensaje)], comprobantes: list[str]}`. MUST NOT envolver las llamadas en una transacción Django `atomic()` (las conexiones MySQL legacy son independientes). MUST NOT modificar `transferir_stock_entre_etapas`.

#### Scenario: Lote de 2 ítems válidos

- DADO `items=[{artA, Produccion, Planchado, 5}, {artB, Produccion, Planchado, 3}]` con saldo suficiente
- CUANDO se llama `transferir_stock_lote`
- ENTONCES `exitosas=2, fallidas=0`; `comprobantes` contiene 2 nros; stocks actualizados en BD

#### Scenario: Ítem con cantidad > saldo origen (parcial)

- DADO `items=[{artA, Produccion, Planchado, 5}, {artB, Produccion, Planchado, 999}]`; saldo artB=3
- CUANDO se llama `transferir_stock_lote`
- ENTONCES `exitosas=1` (artA OK), `fallidas=1` (artB); `errores` incluye mensaje español para artB; stock artB sin cambio

#### Scenario: Lote vacío

- DADO `items=[]`
- CUANDO se llama `transferir_stock_lote`
- ENTONCES retorna `{exitosas: 0, fallidas: 0, errores: [], comprobantes: []}`; sin error

---

### Requirement: Modelo Log MprTransicionLote

El sistema MUST crear `MprTransicionLote` con campos:
- `base_empresa` (CharField 64, db_index): scope por empresa
- `id_articulo` (IntegerField): componente nivel directo
- `tipo_origen` (CharField 64): constante TIPO_MPR_* de origen
- `tipo_destino` (CharField 64): constante TIPO_MPR_* de destino
- `cantidad` (DecimalField 15,2): cantidad transferida
- `codigo_movimiento` (IntegerField, null/blank): CodigoMovimiento MSTOCK en MySQL
- `id_usuario` (IntegerField): usuario que registró la transición
- `creado_en` (DateTimeField, auto_now_add): timestamp de registro

El sistema MUST garantizar:
- **Índices compuestos**: Index (`base_empresa`, `id_articulo`), Index (`base_empresa`, `creado_en`)
- **Ordenamiento**: por `-creado_en` (recientes primero)

La migración MUST ser additive-only (solo CREATE TABLE).

#### Scenario: Log creado por transición exitosa

- DADO transferencia exitosa Produccion→Planchado, qty=30, articulo=A
- CUANDO la función retorna ok=True
- ENTONCES MprTransicionLote(base_empresa, id_articulo=A, tipo_origen='Produccion', tipo_destino='Planchado', cantidad=30, codigo_movimiento>0) MUST existir

---

### Requirement: Acciones del Tablero — Columna Trazabilidad (Etapa 9)

> **Historial:** En Etapa 5 la columna de acciones incluía botones contextuales por fila
> ("Registrar parte", "Inspección ▾", "Transición ▾") con modal Alpine.js por `id_articulo`.
> La Etapa 9 consolidó estas acciones en botones globales de la barra superior y pantallas
> de lote dedicadas (capability `mpr-acciones-lote-tablero`), eliminando los menús por fila.

El tablero MUST mostrar en la columna (renombrada "Trazabilidad") SOLO el enlace "Trazabilidad" condicional a `fila.id_lista_produccion`. Los botones "Registrar parte", "Inspección ▾", "Transición ▾" y el modal Alpine por-fila MUST NOT renderizarse en `tablero_produccion.html`. La vista `TransicionLoteView` y la URL `mpr:transicion_lote` MUST conservarse en el backend sin exposición en la UI (backward-safe).

Las pantallas de lote consumen `transferir_stock_lote` reutilizando las constantes `TIPO_MPR_*` de `pipeline.py`: `'Produccion'`, `'Planchado'`, `'Scrap'` (desperdicio), `'2daSeleccion'`, `'SemiElaborado'` (sin espacios ni tildes).

#### Scenario: Columna sin botones de acción por fila

- DADO fila con `produccion=5, planchado=3, id_lista_produccion=None`
- CUANDO se renderiza tablero post-E9
- ENTONCES columna "Trazabilidad" NO muestra "Inspección ▾" ni "Transición ▾"
- Y no existe ningún modal Alpine ligado a esa fila

#### Scenario: URL transicion_lote backward-safe

- DADO URL `mpr:transicion_lote` existente
- CUANDO se hace GET/POST a esa URL con parámetros válidos
- ENTONCES responde HTTP 200/302 (no 404)

---

### Requirement: No-funcionales Transversales

El sistema MUST cumplir los siguientes requisitos no-funcionales en todas las operaciones de transiciones:

| Requisito | Norma |
|-----------|-------|
| Scoping | Queries MUST filtrar por base_empresa |
| Autenticación | TransicionLoteView MUST usar MprLoginRequiredMixin |
| Tipos AdministraNET | MySQL reads/writes MUST usar to_int_or_none, to_decimal_or_none |
| Fechas UI | Fechas MUST mostrarse en dd/MM/yyyy |
| Idioma | Todos los mensajes MUST estar en español |
| Migración | Additive-only (CREATE TABLE, ADD COLUMN; sin DROP) |
| Rutas | Bajo prefijo /mpr/tablero-produccion/transicion/ |
| Canon UI | Templates MUST extender mpr/base_mpr.html |

#### Scenario: Aislación base_empresa en transiciones

- DADO MprTransicionLote(base_empresa='EMP1') y otro (base_empresa='EMP2')
- CUANDO se consultan transiciones para base_empresa='EMP1'
- ENTONCES MUST retornarse solo los de EMP1, no los de EMP2

---

## Integration with Pipeline

Esta capability se integra con el spec `mpr-pipeline-multietapa` añadiendo acciones operativas al tablero consolidado (antes solo lectura en Etapa 2). Los botones contextuales por fila permiten ejecutar las transiciones legales definidas en `pipeline.py` sin salir del tablero.

El servicio `transferir_stock_entre_etapas` convive con `ejecutar_opp` y `ejecutar_opp_por_componentes` (existentes, bound a OPT) hasta su deprecación planificada en Etapa 6.

---

## Notes

- **Origen del spec:** Derivado de `sdd/mpr-pipeline-etapa5-transiciones-desmontaje/spec` #1006 (Engram) tras verificación y corrección de bugs post-verify.
- **Bugs corregidos post-verify:** CRIT-1 (strings '2da Seleccion'/'Semi Elaborado' en template corregidos a '2daSeleccion'/'SemiElaborado'), WARN-1 (inicialización `opt_map = {}` en `registrar_parte_produccion`).
- **Estado final:** 26/26 tests OK en suite etapa5; 303/303 tests OK en suite completa mpr (skip=1); lints limpios; migración 0012 aplicada y consistente.
- **Fuera de Alcance Etapa 5:** Deprecación/limpieza de `ejecutar_opp`/`RegistrarOppView` (Etapa 6), trazabilidad OPT drill-down completa usando `MprTransicionLote` (Etapa 6).
- **Delta Etapa 9 (`mpr-pipeline-etapa9-acciones-consolidadas`):** Añadido `transferir_stock_lote` (best-effort, sin `atomic()`, sin modificar `transferir_stock_entre_etapas`); acciones por fila del tablero eliminadas y reemplazadas por botones globales + pantallas de lote (capability `mpr-acciones-lote-tablero`); `TransicionLoteView`/`mpr:transicion_lote` conservadas backward-safe. Estado final: 31/31 tests etapa9, 26/26 etapa5 (0 regresiones), 397/397 tests mpr (skip=1); sin migración de esquema.
