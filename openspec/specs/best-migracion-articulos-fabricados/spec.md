# best-migracion-articulos-fabricados Specification

## Purpose

Introducir dominio **Artículos fabricados** no bloqueante para cutover ni gate PED: mapeo BOM Admin→BEST vía matcher inverso desde terminados validados, pantalla espejo de terminados, y stock Semi-Embalado↔Semi-elaborado opcional post-cutover. **No** se migran recetas desde BEST (`REP_RECETAS`).

*Archivado desde el cambio OpenSpec `best-articulos-terminados-fabricados-olas` (15/07/2026).*

## Requirements

### Requirement: Dominio fabricados no bloqueante

El sistema MUST registrar un `MigrationDomain` con `codigo="articulos_fabricados"`, `nombre="Artículos fabricados"` y `obligatorio_para_pedidos=False`. MUST NOT incluirse en `refresh_gate` ni en el cálculo de `migracion_habilitada`.

#### Scenario: Tarjeta en hub sin semáforo de gate

- **GIVEN** el usuario abre el hub de migración BEST
- **WHEN** visualiza «Artículos fabricados»
- **THEN** ve contadores propios de pendientes/validados
- **AND** el dominio no figura como requisito del semáforo «Gate PED»

#### Scenario: Cutover posible con fabricados pendientes

- **GIVEN** terminados, clientes y unidades OK
- **AND** fabricados sin resolver
- **WHEN** operaciones de cutover o siembra PED se ejecutan
- **THEN** no se bloquean por el estado de fabricados

---

### Requirement: Pantalla espejo y ruta dedicada

Debe existir pantalla en `/mpr/migracion-best/articulos-fabricados/` con UX equivalente a terminados (listado, Asignar, Validar, métricas). Los mapeos MUST persistirse con `origen_requerimiento=BOM_FABRICADO` (o equivalente distinto de pedidos/stock terminados).

#### Scenario: Navegación desde hub

- **GIVEN** el usuario está en el hub
- **WHEN** hace clic en «Artículos fabricados»
- **THEN** accede a `/mpr/migracion-best/articulos-fabricados/`
- **AND** ve flujo de resolución análogo a terminados

---

### Requirement: BOM AdministraNET como única fuente

La inferencia de fabricados MUST usar exclusivamente tablas Admin `en_abm` / `en_abm_formula`. El sistema MUST NOT leer ni migrar recetas desde BEST (`REP_RECETAS`).

#### Scenario: Explosión BOM desde terminado validado

- **GIVEN** un artículo terminado Admin mapeado y VALIDADO
- **WHEN** el usuario ejecuta «Resolver fabricados» (o acción equivalente)
- **THEN** el sistema explota la BOM Admin del terminado
- **AND** obtiene componentes únicos con `tipo_art_fab=Fabricado`
- **AND** no consulta `REP_RECETAS` en BEST

#### Scenario: Fuera de alcance REP_RECETAS

- **GIVEN** existe stock o receta solo en BEST sin paridad en Admin BOM
- **WHEN** se intenta resolver fabricados
- **THEN** el sistema no importa desde `REP_RECETAS`
- **AND** el operador puede asignar manualmente vía UI

---

### Requirement: Matcher inverso Admin→BEST

Desde fabricados únicos detectados en BOM, el sistema MUST inferir SKU BEST 1:1 con la misma UX de score/lote que terminados. La UI «Asignar» para fabricados MUST NOT limitarse a candidatos Admin Terminado; MUST aceptar candidatos Fabricado.

#### Scenario: Inferencia automática con score

- **GIVEN** un componente Fabricado Admin sin mapeo previo
- **WHEN** el matcher inverso se ejecuta
- **THEN** propone candidato BEST con score/lote visible
- **AND** el operador puede confirmar o corregir manualmente

#### Scenario: Asignación manual fabricado

- **GIVEN** inferencia ambigua o sin match
- **WHEN** el usuario abre «Asignar» en fabricados
- **THEN** puede elegir candidato Admin Fabricado
- **AND** el mapeo queda con `origen_requerimiento=BOM_FABRICADO`

---

### Requirement: Stock Semi-Embalado opcional post-cutover

La carga de stock de fabricados MUST usar depósito BEST Semi-Embalado (típ. Id `4002`) mapeado a Admin Semi-elaborado vía `BestDepositoMap` / `tipo_mpr=SemiElaborado`. MUST aplicar la misma máquina de olas que stock inicial (`LISTO`/`CONCILIADO` procesables; `CARGADO` inmutable). Es opcional y MUST NOT ser checklist bloqueante del hub.

#### Scenario: Sync stock fabricados después del cutover

- **GIVEN** terminados ya cargados en stock inicial (`CARGADO`)
- **AND** fabricados mapeados con depósito Semi mapeado
- **WHEN** el usuario sincroniza/carga stock de fabricados
- **THEN** las cantidades BEST Semi-Embalado se reconcilian contra Admin Semi-elaborado
- **AND** líneas previas `CARGADO` no se reprocesan

#### Scenario: Stock Semi no bloquea PED

- **GIVEN** fabricados mapeados pero stock Semi sin cargar
- **WHEN** el usuario revisa checklist del hub
- **THEN** stock Semi fabricados no aparece como requisito de `migracion_habilitada`
- **AND** cutover de terminados puede considerarse completo independientemente

---

### Requirement: Separación de datos terminados vs fabricados

Los mapeos de fabricados MUST coexistir con terminados sin duplicar SKUs en conflicto: distinto `origen_requerimiento`, contadores separados en hub, y tests que verifiquen que gate PED ignora fabricados.

#### Scenario: Contadores independientes en hub

- **GIVEN** hay 100 terminados resueltos y 20 fabricados pendientes
- **WHEN** el usuario ve el hub
- **THEN** «Artículos terminados» muestra 100/100 OK para gate
- **AND** «Artículos fabricados» muestra 0/20 sin afectar el semáforo PED
