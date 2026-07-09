# Spec — Login de operario y roles MPR

**Capability:** `mpr-operario-login`
**Change:** `mpr-trazabilidad-maquina-linea-operario`
**Estado:** Propuesto

---

## ADDED Requirements

### Requirement: Mapeo operario↔usuario de login

El sistema MUST proveer un mapeo persistente entre un operario (`sue_abm_empleado.id_sue_abm_empleado`) y un usuario de login de AdministraNET (tabla `usuarios`), en una tabla nueva con separador `_` (p. ej. `mpr_operario_usuario`), con scope `base_empresa`. Un usuario de login MUST resolver a lo sumo un operario.

#### Scenario: Resolver operario desde el usuario logueado

- **GIVEN** un usuario de login mapeado al operario `García`
- **WHEN** ese usuario inicia sesión
- **THEN** el sistema resuelve `id_operario = García` para atribuir su carga de producción

#### Scenario: Usuario sin mapeo

- **WHEN** un usuario sin mapeo a operario intenta abrir la carga móvil de producción
- **THEN** el sistema informa que no tiene operario asociado y no permite cargar

---

### Requirement: Autenticación reutilizando el login existente

Los operarios MUST autenticarse mediante el flujo de login vigente contra la tabla `usuarios` de AdministraNET (`login/administranet_auth.py`), sin crear un mecanismo de autenticación paralelo.

#### Scenario: Login de operario

- **WHEN** un operario ingresa sus credenciales válidas
- **THEN** obtiene sesión Synap como cualquier usuario, con su `base_empresa`

---

### Requirement: Rol Supervisor MPR

El sistema MUST reconocer un rol **Supervisor MPR** que habilita la gestión de catálogos, la revisión y la aprobación de partes. La detección MUST integrarse con `_usuario_tiene_permiso_mpr` (además de los actuales `cod_usuario="supervisor"` y rol administrador).

#### Scenario: Supervisor aprueba

- **GIVEN** un usuario con rol Supervisor MPR
- **WHEN** abre la bandeja de partes pendientes
- **THEN** puede revisar y aprobar

#### Scenario: Operario no aprueba

- **GIVEN** un usuario con rol operario (sin Supervisor MPR)
- **WHEN** intenta aprobar un parte
- **THEN** el sistema deniega la acción

---

### Requirement: Permiso dedicado del operario (`mpr.parte_operario`)

El sistema MUST proveer un permiso `mpr.parte_operario` declarado en `PERMISOS_POR_MODULO["Producción (MPR)"]` (`core/constantes_permisos.py`) y sembrado en el catálogo `synap_permiso`, asignable desde `/core/permisos-puesto/`. Este permiso MUST habilitar únicamente la carga de partes desde el móvil y MUST NOT otorgar `mpr.ver`.

Un operario "puro" (tiene `mpr.parte_operario` y NO `mpr.ver`) MUST NOT poder ver el mega-menú MPR ni acceder a ninguna pantalla de escritorio MPR (tablero, reportes, config, clasificación, aprobación). La barrera MUST ser de permiso en backend, no solo ocultación de UI.

#### Scenario: Operario sin acceso al resto del módulo

- **GIVEN** un usuario con `mpr.parte_operario` y sin `mpr.ver`
- **WHEN** intenta abrir el tablero de producción u otra pantalla MPR
- **THEN** el sistema responde con acceso denegado (falta `mpr.ver`)

#### Scenario: Menú MPR oculto para operario

- **WHEN** el operario navega la aplicación
- **THEN** el mega-menú "Producción (MPR)" no se muestra (sus items exigen `mpr.ver` u otros permisos que el operario no tiene)

---

### Requirement: Landing por rol del operario

El sistema MUST redirigir por defecto al operario puro (`mpr.parte_operario` sin `mpr.ver`) a la pantalla de carga móvil (`mpr:parte_movil_operario`) tras el login, al acceder a `/` y al `dashboard`. La regla MUST centralizarse en un único resolver reutilizado por esos puntos de entrada.

#### Scenario: Landing directa post-login

- **GIVEN** un operario puro
- **WHEN** inicia sesión correctamente
- **THEN** es redirigido a la pantalla de carga de parte, no al dashboard general

#### Scenario: Redirección desde raíz/dashboard

- **GIVEN** un operario puro autenticado
- **WHEN** intenta abrir `/` o `/core/dashboard/`
- **THEN** el sistema lo redirige a su pantalla de carga

#### Scenario: Usuario con `mpr.ver` no se ve afectado

- **GIVEN** un supervisor con `mpr.ver`
- **WHEN** inicia sesión
- **THEN** llega al dashboard general normal (sin redirección de operario)

---

### Requirement: Acceso móvil de la pantalla de carga

La pantalla de carga MUST ser accesible en dispositivos móviles (compatible con `MobileLevelAOnlyMiddleware`) y servirse como experiencia enfocada (sin mega-menú). El acceso a la vista MUST exigir `mpr.parte_operario`.

#### Scenario: Operario ve solo su carga

- **WHEN** un operario inicia sesión en el móvil
- **THEN** ve la pantalla de carga de sus máquinas y NO el tablero de producción

---

### Requirement: Persistencia del mapeo vía catálogo central

La tabla de mapeo operario↔usuario MUST crearse mediante `core/services/legacy_mysql_schema/catalog.py` con DDL en `mpr/sql/`, de forma idempotente.

#### Scenario: Idempotencia

- **WHEN** la migración se ejecuta dos veces
- **THEN** no falla ni duplica la tabla
