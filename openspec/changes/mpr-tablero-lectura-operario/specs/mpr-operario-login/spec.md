# Delta for mpr-operario-login

## ADDED Requirements

### Requirement: Permiso de lectura del tablero (`mpr.tablero_ver`)

El sistema MUST declarar el permiso `mpr.tablero_ver` en `PERMISOS_POR_MODULO["Producción (MPR)"]` (`core/constantes_permisos.py`) y sembrarlo en el catálogo `synap_permiso`. MUST ser asignable de forma opt-in por puesto desde `/core/permisos-puesto/`. MUST NOT incluirse por defecto en el rol Operario ni otorgar `mpr.ver`.

#### Scenario: Permiso sembrado y asignable

- **GIVEN** una instalación con catálogo de permisos sincronizado
- **WHEN** un administrador abre permisos de puesto
- **THEN** puede asignar `mpr.tablero_ver` de forma independiente de `mpr.ver`

#### Scenario: Rol Operario sin tablero por defecto

- **GIVEN** un puesto con rol Operario sin asignación explícita de `mpr.tablero_ver`
- **WHEN** un usuario de ese puesto inicia sesión
- **THEN** NO tiene `mpr.tablero_ver` y NO puede abrir el tablero por URL

#### Scenario: Perfil operario con lectura de tablero

- **GIVEN** un usuario con `mpr.parte_operario` y `mpr.tablero_ver` y sin `mpr.ver`
- **WHEN** consulta sus permisos efectivos
- **THEN** puede acceder en solo lectura al tablero según los requisitos de esta capability
- **AND** MUST NOT tener acceso al resto del escritorio MPR

---

### Requirement: Acceso GET al tablero de producción

Las vistas y endpoints de **consulta** del tablero (página principal, acción Actualizar, modales de solo lectura y AJAX de datos del tablero) MUST permitir acceso a usuarios con `mpr.ver` **OR** `mpr.tablero_ver`. MUST NOT exigir `mpr.ver` para operaciones GET de consulta.

#### Scenario: Operario con tablero abre el tablero

- **GIVEN** un usuario con `mpr.tablero_ver` y sin `mpr.ver`
- **WHEN** hace GET a la URL del tablero de producción
- **THEN** el sistema responde 200 y muestra filtros, Pack|Par, botón Actualizar y modales de consulta

#### Scenario: Supervisor con mpr.ver sin regresión

- **GIVEN** un usuario con `mpr.ver`
- **WHEN** hace GET al tablero
- **THEN** el acceso MUST comportarse como antes del change (200, funcionalidad completa de consulta)

#### Scenario: Usuario sin permiso de tablero

- **GIVEN** un usuario sin `mpr.ver` ni `mpr.tablero_ver`
- **WHEN** intenta GET al tablero por URL directa
- **THEN** el sistema responde acceso denegado (403 o equivalente Synap)

#### Scenario: Actualizar tablero con solo tablero_ver

- **GIVEN** un usuario con `mpr.tablero_ver` y sin `mpr.ver` en el tablero abierto
- **WHEN** ejecuta la acción Actualizar
- **THEN** el sistema recarga los datos del tablero con respuesta exitosa

---

### Requirement: Barrera de escritorio MPR completo

Toda vista de **escritorio MPR** distinta del tablero en modo consulta (centros de costo, parte de carga escritorio, armado, reportes, configuración, clasificación, aprobación, wizard OPT y demás rutas que hoy usan solo `MprLoginRequiredMixin` o equivalente sin permiso explícito) MUST exigir `mpr.ver` en backend. Un usuario con solo `mpr.tablero_ver` MUST NOT acceder aunque conozca la URL.

#### Scenario: CC por URL con solo tablero_ver

- **GIVEN** un usuario con `mpr.tablero_ver` y sin `mpr.ver`
- **WHEN** intenta abrir una URL de centro de costo u otra pantalla de escritorio MPR
- **THEN** el sistema responde acceso denegado (403)

#### Scenario: Reportes MPR bloqueados

- **GIVEN** un usuario con `mpr.tablero_ver` y sin `mpr.ver`
- **WHEN** intenta abrir un reporte MPR por URL
- **THEN** el sistema responde acceso denegado (403)

#### Scenario: Usuario con mpr.ver accede al escritorio

- **GIVEN** un usuario con `mpr.ver`
- **WHEN** abre centros de costo, reportes u otras pantallas de escritorio MPR
- **THEN** el acceso MUST permanecer permitido sin regresión

---

### Requirement: Mega-menú MPR con acceso parcial al tablero

Si el usuario tiene `mpr.tablero_ver` y NO tiene `mpr.ver`, el mega-menú «Producción (MPR)» MUST mostrarse con una sección reducida que incluya únicamente el ítem «Tablero de producción». Los demás ítems del menú MPR MUST permanecer ocultos. El nodo raíz del menú MPR MUST evaluarse con lógica OR: visible si el usuario tiene `mpr.ver` **OR** `mpr.tablero_ver`.

#### Scenario: Menú parcial para operario con tablero

- **GIVEN** un usuario con `mpr.tablero_ver` y sin `mpr.ver`
- **WHEN** navega la aplicación en escritorio
- **THEN** ve la sección «Producción (MPR)» con el ítem «Tablero de producción»
- **AND** NO ve ítems de CC, reportes, armado, configuración ni otras entradas de escritorio

#### Scenario: Operario puro sin menú MPR

- **GIVEN** un usuario con solo `mpr.parte_operario` (sin `mpr.ver` ni `mpr.tablero_ver`)
- **WHEN** navega la aplicación
- **THEN** el mega-menú «Producción (MPR)» NO se muestra

---

### Requirement: Enlaces desde tablero hacia centros de costo

En el tablero de producción, los enlaces o acciones de navegación hacia centros de costo (CC) u otras pantallas de escritorio MPR MUST ocultarse en la UI cuando el usuario tiene solo `mpr.tablero_ver` (sin `mpr.ver`). Si el usuario accede al destino por URL, el backend MUST responder acceso denegado (403).

#### Scenario: Enlace CC oculto en solo lectura

- **GIVEN** un usuario con `mpr.tablero_ver` y sin `mpr.ver` viendo el tablero
- **WHEN** inspecciona la UI del tablero
- **THEN** NO ve enlaces clicables hacia centros de costo u otras rutas de escritorio MPR

#### Scenario: Destino CC denegado por URL

- **GIVEN** un usuario con `mpr.tablero_ver` y sin `mpr.ver`
- **WHEN** accede directamente a la URL de un centro de costo referenciado desde el tablero
- **THEN** el sistema responde 403

---

## MODIFIED Requirements

### Requirement: Permiso dedicado del operario (`mpr.parte_operario`)

El sistema MUST proveer un permiso `mpr.parte_operario` declarado en `PERMISOS_POR_MODULO["Producción (MPR)"]` (`core/constantes_permisos.py`) y sembrado en el catálogo `synap_permiso`, asignable desde `/core/permisos-puesto/`. Este permiso MUST habilitar únicamente la carga de partes desde el móvil y MUST NOT otorgar `mpr.ver`.

Un operario "puro" (tiene `mpr.parte_operario` y NO `mpr.ver` ni `mpr.tablero_ver`) MUST NOT ver el mega-menú MPR ni acceder a pantallas de escritorio MPR. Un operario con `mpr.parte_operario` y `mpr.tablero_ver` (sin `mpr.ver`) MUST poder consultar el tablero según el permiso `mpr.tablero_ver` y MUST NOT acceder al resto del escritorio MPR. Las barreras MUST ser de permiso en backend, no solo ocultación de UI.

(Previously: cualquier operario sin `mpr.ver` quedaba bloqueado también del tablero; el mega-menú MPR quedaba totalmente oculto para quien solo tuviera `mpr.parte_operario`.)

#### Scenario: Operario puro sin acceso al escritorio ni tablero

- **GIVEN** un usuario con `mpr.parte_operario` y sin `mpr.ver` ni `mpr.tablero_ver`
- **WHEN** intenta abrir el tablero u otra pantalla MPR de escritorio
- **THEN** el sistema responde con acceso denegado

#### Scenario: Operario con tablero_ver accede solo al tablero

- **GIVEN** un usuario con `mpr.parte_operario` y `mpr.tablero_ver` y sin `mpr.ver`
- **WHEN** abre el tablero por GET
- **THEN** el acceso es permitido en solo lectura
- **AND** al intentar otra pantalla de escritorio MPR recibe acceso denegado

#### Scenario: Menú MPR oculto para operario puro

- **WHEN** un operario puro (sin `mpr.ver` ni `mpr.tablero_ver`) navega la aplicación
- **THEN** el mega-menú «Producción (MPR)» no se muestra

---

### Requirement: Landing por rol del operario

El sistema MUST redirigir por defecto al operario puro (`mpr.parte_operario` sin `mpr.ver` ni `mpr.tablero_ver`) y al operario con tablero (`mpr.parte_operario` + `mpr.tablero_ver` sin `mpr.ver`) a la pantalla de carga móvil (`/mpr/mi-parte/`, vista `mpr:parte_movil_operario`) tras el login, al acceder a `/` y al `dashboard`. La regla MUST centralizarse en un único resolver reutilizado por esos puntos de entrada. Un usuario con `mpr.ver` MUST NOT ser redirigido por esta regla.

(Previously: la landing aplicaba solo a operario puro; no distinguía operario con `mpr.tablero_ver`, que ahora también aterriza en mi-parte.)

#### Scenario: Landing directa post-login — operario puro

- **GIVEN** un operario puro
- **WHEN** inicia sesión correctamente
- **THEN** es redirigido a `/mpr/mi-parte/`, no al dashboard general

#### Scenario: Landing operario con tablero_ver

- **GIVEN** un usuario con `mpr.parte_operario` y `mpr.tablero_ver` y sin `mpr.ver`
- **WHEN** inicia sesión o accede a `/` o `/core/dashboard/`
- **THEN** es redirigido a `/mpr/mi-parte/`
- **AND** puede abrir el tablero manualmente desde el menú o URL sin cambiar su landing por defecto

#### Scenario: Redirección desde raíz/dashboard — operario puro

- **GIVEN** un operario puro autenticado
- **WHEN** intenta abrir `/` o `/core/dashboard/`
- **THEN** el sistema lo redirige a su pantalla de carga móvil

#### Scenario: Usuario con mpr.ver no se ve afectado

- **GIVEN** un supervisor con `mpr.ver`
- **WHEN** inicia sesión
- **THEN** llega al dashboard general normal (sin redirección de operario)
