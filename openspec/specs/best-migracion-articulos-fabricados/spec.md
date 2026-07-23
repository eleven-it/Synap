# best-migracion-articulos-fabricados Specification

## Purpose

Dominio **Artículos fabricados** no bloqueante para cutover ni gate PED: mapeo **BEST PP → Admin Fabricado** desde stock en depósitos 4000/4002, con olas pedido (REP_RECETAS) y stock, pantalla espejo de terminados, y stock Semi-Embalado↔Semi-elaborado opcional post-cutover.

*Actualizado jul 2026: flujo invertido BEST→Admin (antes Admin→BEST vía BOM Admin).*

## Requirements

### Requirement: Dominio fabricados no bloqueante

El sistema MUST registrar un `MigrationDomain` con `codigo="articulos_fabricados"`, `nombre="Artículos fabricados"` y `obligatorio_para_pedidos=False`. MUST NOT incluirse en `refresh_gate` ni en el cálculo de `migracion_habilitada`.

#### Scenario: Tarjeta en hub sin semáforo de gate

- **GIVEN** el usuario abre el hub de migración BEST
- **WHEN** visualiza «Artículos fabricados»
- **THEN** ve contadores propios de pendientes/validados (olas pedido y stock)
- **AND** el dominio no figura como requisito del semáforo «Gate PED»

#### Scenario: Cutover posible con fabricados pendientes

- **GIVEN** terminados, clientes y unidades OK
- **AND** fabricados sin resolver
- **WHEN** operaciones de cutover o siembra PED se ejecutan
- **THEN** no se bloquean por el estado de fabricados

---

### Requirement: Pantalla espejo y ruta dedicada

Debe existir pantalla en `/mpr/migracion-best/articulos-fabricados/` con UX equivalente a terminados (listado, Asignar, Validar, métricas). Los mapeos MUST persistirse con `origen_requerimiento=BOM_FABRICADO`. Cada fila MUST representar un PP BEST (clave `best_id_articulo`).

#### Scenario: Navegación desde hub

- **GIVEN** el usuario está en el hub
- **WHEN** hace clic en «Artículos fabricados»
- **THEN** accede a `/mpr/migracion-best/articulos-fabricados/`
- **AND** ve PP BEST como fila principal y candidato Admin Fabricado como sugerencia

---

### Requirement: Cola desde stock BEST y recetas de pedido

La inferencia MUST partir de PP BEST con stock en depósitos 4000/4002 (`REP_INVENTARIOS`, `Stock <> 0`). PP sin stock MUST NOT aparecer en el resolver ni generar líneas de stock.

Ola 1 (pedidos): PP cuya receta los vincula a un PT en pedidos abiertos (`REP_ORDENES_COMBINADO` `Finalizada=0`, `Pendiente>0`) vía `REP_RECETAS.[Id PP]` / `[Id PT]` MUST tener `requerido_migracion=True` y `en_snapshot_abierto=True`.

Ola 2 (stock): resto de PP con stock MUST tener `requerido_migracion=False`.

#### Scenario: Resolver desde inventario semi/producción

- **GIVEN** PP con saldo en depósito 4000 o 4002
- **WHEN** el usuario ejecuta «Resolver fabricados»
- **THEN** el sistema consulta `REP_INVENTARIOS` y `REP_RECETAS` (solo para marcar ola pedido)
- **AND** crea o actualiza filas `BOM_FABRICADO` keyed por MMID PP
- **AND** no exige terminados Admin VALIDADO como prerequisito

#### Scenario: Sin stock fuera de alcance

- **GIVEN** un PP BEST sin saldo en 4000/4002
- **WHEN** se ejecuta el resolver
- **THEN** ese PP no aparece en la cola

---

### Requirement: Matcher BEST→Admin Fabricado

Desde cada PP con stock, el sistema MUST inferir `articulo.IDArt` con `tipo_art_fab=Fabricado` usando `match_best_pp_to_admin_fabricados` (scoring simétrico: modelo, Jaccard, marca, talle, pack suave). La UI «Asignar» MUST buscar candidatos Admin Fabricado (no SKU BEST).

#### Scenario: Inferencia automática con score

- **GIVEN** un PP BEST sin mapeo previo
- **WHEN** el matcher se ejecuta
- **THEN** propone candidato Admin Fabricado con score/lote visible
- **AND** el operador puede confirmar o corregir manualmente

#### Scenario: Asignación manual Admin Fabricado

- **GIVEN** inferencia ambigua o sin match
- **WHEN** el usuario abre «Asignar» en fabricados
- **THEN** puede elegir candidato Admin Fabricado
- **AND** el mapeo queda validado con el MMID PP fijo

#### Scenario: No pisar VALIDADO

- **GIVEN** una fila `BOM_FABRICADO` ya VALIDADA
- **WHEN** se re-ejecuta el resolver
- **THEN** no se sobrescribe estado ni `admin_idart`
- **AND** pueden actualizarse solo flags de ola (`requerido_migracion`)

---

### Requirement: Filtros UI por ola

Filtro «necesarios pendientes» MUST usar `requerido_migracion=True`. Filtro «ola stock» MUST usar `requerido_migracion=False`. Contadores MUST distinguir pendientes pedido vs stock.

#### Scenario: Cola de trabajo pedidos

- **GIVEN** filas ola 1 y ola 2 en la base
- **WHEN** el usuario activa «Solo necesarios pendientes (pedido)»
- **THEN** ve solo filas con `requerido_migracion=True` no resueltas

---

### Requirement: Stock Semi-Embalado opcional post-cutover

La carga de stock de fabricados MUST usar depósito BEST Semi-Embalado (típ. Id `4002`) mapeado a Admin Semi-elaborado vía `BestDepositoMap` / `tipo_mpr=SemiElaborado`. MUST aplicar la misma máquina de olas que stock inicial (`LISTO`/`CONCILIADO` procesables; `CARGADO` inmutable). Es opcional y MUST NOT ser checklist bloqueante del hub.

#### Scenario: Sync stock fabricados después del cutover

- **GIVEN** terminados ya cargados en stock inicial (`CARGADO`)
- **AND** fabricados mapeados y VALIDADOS con depósito Semi mapeado
- **WHEN** el usuario sincroniza/carga stock de fabricados
- **THEN** las cantidades BEST Semi-Embalado se reconcilian contra Admin Semi-elaborado
- **AND** líneas previas `CARGADO` no se reprocesan

---

### Requirement: Separación de datos terminados vs fabricados

Los mapeos de fabricados MUST coexistir con terminados sin duplicar SKUs en conflicto: distinto `origen_requerimiento`, contadores separados en hub, y tests que verifiquen que gate PED ignora fabricados.

#### Scenario: Contadores independientes en hub

- **GIVEN** hay 100 terminados resueltos y 20 fabricados pendientes
- **WHEN** el usuario ve el hub
- **THEN** «Artículos terminados» muestra 100/100 OK para gate
- **AND** «Artículos fabricados» muestra pendientes propios sin afectar el semáforo PED
