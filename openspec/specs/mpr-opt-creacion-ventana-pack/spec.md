# Spec — Creación OPT ventana pack (MPR)

**Capability:** `mpr-opt-creacion-ventana-pack`  
**Change origen:** `opt-bloqueo-pack-sin-receta` (archivado 14/07/2026)  
**Ruta:** `/mpr/demanda/ventana-pack/` (Pantalla 1 flujo OPT, pestaña Packs)

---

## Purpose

Flujo de creación de OPT desde la ventana pack: el usuario selecciona artículos pack en Pantalla 1 y avanza a Pantalla 2 (agrupar/Generar OPT). El sistema **MUST** validar que todos los packs seleccionados tengan receta (BOM) definida antes de permitir el avance.

---

## Requirements

### REQ-VPK-001: Validación de receta antes de continuar

El sistema **MUST** validar que todos los artículos pack seleccionados por el usuario en la Pantalla 1 de creación de OPT tengan receta (BOM) definida antes de permitir el avance a la Pantalla 2 (agrupar/Generar OPT).

**Acceptance Scenarios:**

```gherkin
Escenario: Todos los packs seleccionados tienen receta
  DADO que el usuario ha seleccionado 3 artículos pack en la ventana pack
  Y todos los artículos seleccionados tienen receta (BOM) definida
  CUANDO el usuario pulsa el botón "Continuar"
  ENTONCES el sistema guarda la selección en sesión
  Y redirige a la Pantalla 2 (agrupar/Generar OPT) normalmente
```

```gherkin
Escenario: Un pack seleccionado no tiene receta
  DADO que el usuario ha seleccionado 1 artículo pack sin receta definida
  CUANDO el usuario pulsa el botón "Continuar"
  ENTONCES el sistema NO avanza a la Pantalla 2
  Y muestra un modal informativo con los datos del artículo sin receta
```

```gherkin
Escenario: Selección mixta con packs con y sin receta
  DADO que el usuario ha seleccionado 4 artículos pack
  Y 3 de ellos tienen receta definida
  Y 1 de ellos NO tiene receta definida
  CUANDO el usuario pulsa el botón "Continuar"
  ENTONCES el sistema NO avanza a la Pantalla 2
  Y muestra un modal listando únicamente el artículo sin receta
```

---

### REQ-VPK-002: Contenido del modal de bloqueo

Cuando al menos un artículo pack seleccionado no tenga receta, el sistema **MUST** mostrar un modal que presente claramente qué artículo(s) están en esa condición, incluyendo para cada uno: código de sistema, código manual y descripción del artículo.

**Acceptance Scenarios:**

```gherkin
Escenario: Modal muestra datos completos del artículo sin receta
  DADO que el usuario intenta continuar con 1 pack sin receta
  Y ese artículo tiene código de sistema "ART-123", código manual "PKG-001" y descripción "Pack Promocional Verano"
  CUANDO el sistema muestra el modal de bloqueo
  ENTONCES el modal lista el artículo mostrando:
    | Código Sistema | Código Manual | Descripción                |
    | ART-123        | PKG-001       | Pack Promocional Verano    |
```

```gherkin
Escenario: Modal lista múltiples packs sin receta
  DADO que el usuario intenta continuar con 2 packs sin receta
  Y 3 packs con receta en la misma selección
  CUANDO el sistema muestra el modal de bloqueo
  ENTONCES el modal lista únicamente los 2 artículos sin receta
  Y cada uno muestra código de sistema, código manual y descripción
  Y NO lista los 3 artículos que sí tienen receta
```

---

### REQ-VPK-003: Acción correctiva del usuario

El modal **SHOULD** permitir al usuario cerrar el modal y regresar a la Pantalla 1 para modificar la selección o tomar acción correctiva (por ejemplo, cargar la receta faltante en otro módulo del sistema).

**Acceptance Scenarios:**

```gherkin
Escenario: Usuario cierra el modal y corrige selección
  DADO que el sistema ha mostrado el modal de bloqueo por pack sin receta
  CUANDO el usuario cierra el modal
  ENTONCES el usuario permanece en la Pantalla 1 de ventana pack
  Y puede modificar la selección de artículos
  Y puede intentar continuar nuevamente
```

---

## Implementation Constraints

- La validación **MUST** ejecutarse en el servidor (backend) antes de guardar la selección en sesión.
- El modal **MUST** ser accesible y responsive (Tailwind/Alpine según patrón UI Synap).
- Los datos del modal **MUST** provenir de la misma fuente que la vista de la tabla (campo `receta_json` evaluado como lista vacía vs. lista con componentes).
- El flujo NO debe permitir bypass de la validación mediante peticiones directas a la Pantalla 2.

---

## Metadata

- **Archivado desde:** `openspec/changes/archive/2026-07-14-opt-bloqueo-pack-sin-receta/`
- **Estado:** vigente (source of truth)
- **Escenarios:** 6
