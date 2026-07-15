# Spec — Artículos terminados (migración BEST)

**Capability:** `best-migracion-articulos-terminados`  
**Change:** `best-articulos-terminados-fabricados-olas`  
**Estado:** Propuesto

---

## Purpose

Renombrar el dominio de paridad «Artículos» a **Artículos terminados** para eliminar ambigüedad con fabricados, manteniendo el identificador técnico `codigo="articulos"` y la semántica del gate PED sin cambios.

---

## ADDED Requirements

### Requirement: Etiqueta visible «Artículos terminados»

En hub, navegación, títulos de pantalla y documentación de migración BEST, el dominio `codigo="articulos"` MUST mostrarse al usuario como **«Artículos terminados»**. El código interno `articulos` MUST permanecer estable salvo refactor explícito posterior.

#### Scenario: Hub de migración BEST

- **GIVEN** el usuario abre el hub de migración BEST
- **WHEN** visualiza la tarjeta del dominio de artículos
- **THEN** el título visible es «Artículos terminados»
- **AND** no aparece la etiqueta genérica «Artículos» como nombre principal

#### Scenario: Ruta y código sin ruptura

- **GIVEN** integraciones o bookmarks usan `/mpr/migracion-best/articulos/` o `codigo="articulos"`
- **WHEN** el usuario navega tras el rename
- **THEN** las rutas y APIs existentes siguen resolviendo
- **AND** solo cambia el texto visible y descriptivo del dominio

---

### Requirement: Matcher terminados sin cambio semántico

El matcher de artículos terminados MUST seguir usando AdministraNET con `tipo_art_fab=Terminado` como destino. La acción «Asignar» en terminados MUST limitarse a candidatos Admin de tipo Terminado (comportamiento actual preservado).

#### Scenario: Asignación manual terminado

- **GIVEN** un SKU BEST pendiente en el dominio terminados
- **WHEN** el usuario abre «Asignar»
- **THEN** solo ve candidatos Admin con `tipo_art_fab=Terminado`
- **AND** no ve artículos Fabricado en la lista de terminados

---

### Requirement: Gate PED solo exige terminados (sin fabricados)

`migracion_habilitada` MUST calcularse únicamente con dominios obligatorios existentes: artículos terminados (`articulos`), clientes y unidades. Los artículos fabricados MUST NOT influir en `refresh_gate` ni en `migracion_habilitada`.

#### Scenario: Gate habilitado sin fabricados mapeados

- **GIVEN** terminados, clientes y unidades están OK según paridad
- **AND** no existe ningún mapeo en dominio fabricados
- **WHEN** se ejecuta `refresh_gate`
- **THEN** `migracion_habilitada` es verdadero
- **AND** la siembra PED puede proceder

#### Scenario: Fabricados incompletos no bloquean hub PED

- **GIVEN** el dominio fabricados tiene pendientes
- **WHEN** el usuario consulta el semáforo «Gate PED» en el hub
- **THEN** el estado refleja solo terminados + clientes + unidades
- **AND** fabricados no aparece como requisito del gate

---

### Requirement: Descripción de dominio actualizada

La descripción del dominio en `MigrationDomain` MUST aclarar que corresponde a productos terminados (BEST MM/MYL → Admin Terminado) y que el gate exige SKUs en pedidos abiertos BEST, distinguiéndolo explícitamente de artículos fabricados.

#### Scenario: Texto de ayuda en pantalla terminados

- **GIVEN** el usuario abre la pantalla de artículos terminados
- **WHEN** lee la descripción del dominio
- **THEN** entiende que aplica a productos Terminado en Admin
- **AND** se menciona que fabricados se gestionan en dominio aparte
