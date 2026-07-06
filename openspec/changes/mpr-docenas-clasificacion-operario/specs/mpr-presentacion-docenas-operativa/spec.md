# Spec — Presentación docenas operativa MPR

**Capability:** `mpr-presentacion-docenas-operativa`  
**Change:** `mpr-docenas-clasificacion-operario`  
**Estado:** Propuesto

---

## ADDED Requirements

### Requirement: Toggle de presentación en sesión

El sistema SHALL persistir la preferencia de presentación de cantidades MPR operativa en la sesión del usuario con clave `mpr_presentacion_cantidad` y valores permitidos `docenas` o `unidades`.

#### Scenario: Primera visita sin preferencia

- **WHEN** el usuario abre cualquier pantalla operativa MPR del alcance sin valor en sesión
- **THEN** la presentación activa es `docenas`

#### Scenario: Cambio de presentación

- **WHEN** el usuario activa el toggle a Unidades
- **THEN** la sesión se actualiza y las pantallas del alcance recargan mostrando cantidades en unidades hasta nuevo cambio

---

### Requirement: Alcance del toggle operativo

El toggle SHALL aplicarse a: tablero consolidado de producción, envío desde tablero, parte de producción y clasificación de producción.

#### Scenario: Reportes fuera de alcance P0

- **WHEN** el usuario está en el hub de reportes MPR en P0
- **THEN** el toggle de reportes existente (`presentacion` query) MAY mantener su default actual hasta P1

---

### Requirement: Conversión docenas ↔ unidades en UI

Para artículos de **componentes** (tablero, parte, clasificación), el sistema SHALL usar divisor fijo **12 unidades por docena** al convertir entre presentación y persistencia.

#### Scenario: Captura en docenas con resto

- **WHEN** el usuario ingresa 542 docenas y 6 unidades sueltas en un input compuesto
- **THEN** el backend persiste `542 * 12 + 6 = 6510` unidades

#### Scenario: Visualización con resto

- **WHEN** el saldo en unidades es 6510 y la presentación es docenas
- **THEN** la UI muestra `542 doc.` y sublínea `+ 6 u.` cuando el resto es distinto de cero

---

### Requirement: Tablero en docenas por defecto

El tablero consolidado SHALL mostrar columnas numéricas de stock y pendiente en docenas cuando la presentación activa es `docenas`.

#### Scenario: Columna pendiente legible

- **WHEN** el pendiente es 6500 unidades y presentación docenas
- **THEN** la celda muestra 541 docenas y 8 unidades (6500 = 541×12 + 8)

---

### Requirement: Envío desde tablero en docenas

El formulario **Enviar** del tablero SHALL aceptar cantidad principal en docenas y unidades sueltas opcionales; SHALL convertir a unidades antes de invocar el servicio de envío.

#### Scenario: Envío solo docenas enteras

- **WHEN** el usuario envía 50 docenas sin unidades sueltas
- **THEN** `registrar_envio_produccion` recibe `cantidad=600` unidades

#### Scenario: Hint de equivalencia

- **WHEN** el usuario modifica el input de docenas en Enviar
- **THEN** se muestra hint textual con el total en unidades (`= N u.`)

---

### Requirement: Parte alineado al toggle global

La grilla de parte de producción SHALL usar el toggle global de sesión; en modo docenas la captura principal SHALL ser en docenas por celda operario × componente.

#### Scenario: Persistencia parte sin cambio

- **WHEN** el usuario guarda parte en modo docenas
- **THEN** `mpr_parte_linea.cantidad` se almacena en unidades convertidas

---

### Requirement: Reutilización de helpers existentes

La implementación SHALL reutilizar `descomponer_docenas_unidades`, `texto_docenas_unidades` y funciones de enriquecimiento de presentación en `mpr/services.py` sin duplicar lógica de conversión.

#### Scenario: Consistencia con reportes stock

- **WHEN** el mismo artículo aparece en tablero y reporte stock con presentación docenas
- **THEN** el texto formateado usa la misma convención visual (docenas arriba, unidades abajo si aplica)
