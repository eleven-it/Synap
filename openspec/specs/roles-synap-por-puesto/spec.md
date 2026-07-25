# roles-synap-por-puesto Specification

## Purpose

Modelo de roles Synap (`synap_rol`) desacoplado del catálogo fijo de puestos VB6 (`puestos.idpuesto`), con mapeo flexible puesto→rol vía `synap_puesto_rol`. `idpuesto` permanece como ancla de identidad del usuario sin crear puestos nuevos en legacy.

Referencias: `docs/general/PERMISOS_ASIGNACION_POR_PUESTO_SUPERVISOR.md`, `APPS_CORE_Y_PERMISOS_ADMINISTRANET.md`.

---

## Requirements

### Requirement: Roles Synap independientes de idpuesto

El sistema MUST gestionar roles en `synap_rol` con identificador propio autoincrement. Los roles MUST NOT reutilizar ni reservar valores de `puestos.idpuesto`. Crear un rol Synap MUST NOT implicar INSERT en tabla `puestos`.

#### Scenario: Creación de rol sin puesto legacy

- DADO catálogo `puestos` con `MAX(idpuesto)=50`
- CUANDO supervisor crea rol «Operador TPV extendido» en Synap
- ENTONCES MUST existir fila en `synap_rol` con `id` propio
- Y MUST NOT existir fila nueva en `puestos`
- Y `MAX(idpuesto)` MUST seguir siendo 50

#### Scenario: Rol con es_sistema

- DADO rol marcado `es_sistema=1` (ej. rol backfill «Synap-default»)
- CUANDO supervisor intenta eliminarlo desde UI
- ENTONCES MUST rechazarse la eliminación
- Y MUST mostrarse mensaje en español indicando rol de sistema

---

### Requirement: Mapeo idpuesto → synap_rol por valor sin FK VB6

`synap_puesto_rol` MUST almacenar `idpuesto` como valor entero referenciando el puesto legacy existente. MUST NOT declarar FK física hacia `puestos`. El sistema MUST validar en aplicación que `idpuesto` exista en `puestos` antes de persistir el mapeo.

#### Scenario: Mapeo válido para puesto existente

- DADO `idpuesto=3` existente en `puestos`
- CUANDO se asigna rol Synap al puesto
- ENTONCES MUST insertarse fila en `synap_puesto_rol` con `idpuesto=3`
- Y MUST NOT crearse constraint FK en DDL hacia `puestos`

#### Scenario: Mapeo rechazado para puesto inexistente

- DADO `idpuesto=99999` inexistente en `puestos`
- CUANDO se intenta asignar rol Synap
- ENTONCES MUST rechazarse la operación con error en español
- Y MUST NOT insertarse fila en `synap_puesto_rol`

---

### Requirement: Cardinalidad múltiple rol por puesto

Un mismo `idpuesto` MUST poder mapear a uno o varios roles Synap. Los permisos efectivos del puesto MUST ser la unión (OR) de todos los `key_permiso` activos de los roles asignados, respetando reglas de supervisor y lecturas complementarias legacy.

#### Scenario: Puesto con un solo rol

- DADO puesto 5 mapeado solo a rol «Ventas»
- CUANDO se calculan permisos con `SYNAP_PERMISOS_SOURCE=synap`
- ENTONCES el set MUST coincidir con permisos del rol «Ventas»

#### Scenario: Puesto con múltiples roles

- DADO puesto 5 mapeado a roles «Ventas» y «Reports operativo»
- CUANDO se calculan permisos
- ENTONCES el set MUST incluir permisos de ambos roles (unión sin duplicados)
- Y un permiso activo en cualquiera de los roles MUST otorgar acceso

#### Scenario: Desasignación de un rol mantiene el otro

- DADO puesto con roles A y B asignados
- CUANDO se desasigna rol A
- ENTONCES MUST eliminarse solo la fila `synap_puesto_rol` de A
- Y los permisos de rol B MUST permanecer efectivos

---

### Requirement: Ancla fija idpuesto — Sin creación de puestos desde Synap

`idpuesto` del usuario (`usuarios.idpuesto`) MUST seguir siendo la ancla de identidad. Synap MUST NOT crear puestos nuevos en `puestos` (ni vía `administranet_puestos.py` ni desde UI de permisos). La gestión de nombres de puesto legacy SHOULD permanecer en flujos existentes (`/core/roles/`) sin ampliar catálogo para roles Synap.

#### Scenario: Flujo permisos no crea puesto

- DADO supervisor en `/core/permisos-puesto/` gestionando permisos
- CUANDO crea rol y lo asigna a puesto existente
- ENTONCES MUST NOT ejecutarse `INSERT INTO puestos`
- Y MUST NOT incrementarse `MAX(idpuesto)`

#### Scenario: Usuario conserva idpuesto tras migración

- DADO usuario con `idpuesto=7` antes del cambio
- CUANDO se activa `SYNAP_PERMISOS_SOURCE=synap`
- ENTONCES la resolución de permisos MUST usar `idpuesto=7` como entrada a `synap_puesto_rol`
- Y MUST NOT requerir cambio de `usuarios.idpuesto`

---

### Requirement: Backfill crea mapeo puesto→rol desde legacy

El backfill MUST crear al menos un rol por puesto con asignaciones legacy activas (grupo Synap) y vincularlo en `synap_puesto_rol`. El rol backfill SHOULD marcarse `es_sistema=1` para distinguirlo de roles creados por supervisor.

#### Scenario: Puesto con permisos legacy obtiene rol backfill

- DADO puesto 12 con filas activas en `permiso_sistema_puesto` del grupo Synap
- CUANDO se ejecuta backfill
- ENTONCES MUST existir fila en `synap_puesto_rol` para `idpuesto=12`
- Y los `key_permiso` activos MUST reproducirse en `synap_rol_permiso`

#### Scenario: Puesto sin permisos Synap legacy

- DADO puesto 20 sin filas grupo Synap en legacy
- CUANDO se ejecuta backfill
- ENTONCES MUST NOT crearse mapeo en `synap_puesto_rol` para puesto 20
- Y el cálculo con flag `synap` MUST usar fallback legacy (sin permisos Synap)

---

### Requirement: Gestión de roles y asignaciones desde /core/permisos-puesto/

La pantalla `/core/permisos-puesto/` MUST permitir al supervisor:

- Listar y seleccionar puestos existentes (ancla `idpuesto`).
- Crear, renombrar y desactivar roles Synap.
- Asignar/desasignar uno o más roles a un puesto.
- Activar/desactivar permisos por rol o por atajo de módulo.

Todas las escrituras MUST ir a `synap_rol`, `synap_rol_permiso` y `synap_puesto_rol`. La pestaña «Menú AdministraNET» MUST seguir escribiendo solo en `permisos` (Clavemenu), sin sincronizar a `permiso_sistema_puesto`.

#### Scenario: Asignación múltiple de roles desde UI

- DADO supervisor en editor de puesto «Caja»
- CUANDO asigna roles «TPV básico» y «Self-checkout supervisor»
- ENTONCES MUST existir dos filas en `synap_puesto_rol` para el `idpuesto` de Caja
- Y MUST NOT modificarse `permiso_sistema_puesto`

#### Scenario: Pestaña Menú AdministraNET sin sync legacy Synap

- DADO supervisor que guarda cambios en pestaña «Menú AdministraNET»
- CUANDO activa Clavemenu en tabla `permisos`
- ENTONCES MUST persistirse en `permisos`
- Y MUST NOT insertarse filas en `permiso_sistema_puesto` por `MAPEO_MENU_A_PERMISO`

#### Scenario: Refresco de permisos en sesión

- DADO usuario con sesión activa cuyo puesto fue modificado
- CUANDO el usuario no ha cerrado sesión
- ENTONCES los permisos en sesión MUST permanecer hasta nuevo login (comportamiento actual)
- Y la documentación MUST indicar que se requiere re-login para refrescar

---

### Requirement: Rol Finanzas/Créditos por Puesto

El sistema MUST permitir asignar a puestos legacy (p. ej. Finanzas, Créditos, Administración) uno o más roles Synap que incluyan `finance.credito.aprobar` y/o `finance.credito.configurar`, vía `synap_puesto_rol`, sin crear puestos nuevos en `puestos`. La documentación MUST indicar puestos tipo recomendados: operador de cola (aprobar) vs administrador de políticas (configurar).

#### Scenario: Puesto Finanzas con permiso crédito

- **GIVEN** puesto «Finanzas» existente en `puestos` mapeado a rol «Créditos operador»
- **WHEN** se calculan permisos con `SYNAP_PERMISOS_SOURCE=synap`
- **THEN** el set MUST incluir `finance.credito.aprobar` si el rol lo tiene activo

#### Scenario: Asignación desde UI permisos-puesto

- **GIVEN** supervisor en `/core/permisos-puesto/` editando puesto Créditos
- **WHEN** asigna rol con permiso `finance.credito.aprobar` o `finance.credito.configurar`
- **THEN** MUST persistirse en `synap_puesto_rol` y `synap_rol_permiso`
- **AND** MUST NOT insertarse fila en `puestos`

#### Scenario: Vendedor sin rol Finanzas

- **GIVEN** puesto vendedor sin rol de crédito
- **WHEN** usuario intenta acceder cola Finanzas
- **THEN** MUST denegarse acceso por permisos efectivos

#### Scenario: Admin políticas sin cola

- **GIVEN** puesto solo con `finance.credito.configurar`
- **WHEN** usuario abre ABM políticas
- **THEN** MUST permitirse
- **AND** CTAs de aprobar/rechazar cola MUST permanecer denegados
