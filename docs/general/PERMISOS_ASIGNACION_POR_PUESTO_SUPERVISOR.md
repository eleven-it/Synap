# Asignación de permisos por puesto (usuario supervisor)

Pantalla unificada para que el usuario AdministraNET con **`cod_usuario` = `supervisor`** asigne permisos a cualquier **puesto** sin depender del puesto del usuario logueado.

## Rutas

| URL | Nombre | Descripción |
|-----|--------|-------------|
| `/core/permisos-puesto/` | `core:permisos_puesto_lista` | Listado de puestos |
| `/core/permisos-puesto/<id>/` | `core:permisos_puesto_gestionar` | Editor con pestañas |
| `/core/permisos-puesto/<id>/toggle-synap/` | API POST JSON | Activa/desactiva un `key_permiso` |
| `/core/permisos-puesto/<id>/modulo-synap/` | POST form | Atajo activar/desactivar módulo |

Entrada en menú: **Archivo → Parámetros → Asignar permisos por puesto** (visible con acceso al módulo Archivo; la vista exige `cod_usuario` supervisor).

## Pestañas

### 1. Permisos Synap

- **Tablas: `synap_permiso`, `synap_rol`, `synap_rol_permiso`, `synap_puesto_rol`** (almacén propio Synap, independiente de VB6). Ver **[PERMISOS_SYNAP_STORE.md](PERMISOS_SYNAP_STORE.md)**.
- **Modelo:** rol dedicado por puesto (`synap_rol` `es_sistema=1` mapeado a `idpuesto`). El toggle asigna/quita permisos de ese rol; **no** escribe en `permiso_sistema*`.
- Catálogo `synap_permiso` asegurado desde `core/constantes_permisos.PERMISOS_POR_MODULO` al abrir la pantalla (y tras login) vía `asegurar_synap_schema_si_procede`.
- Toggle por permiso (guardado inmediato; payload JSON `id_permiso`).
- Atajos **+ / −** por módulo (`ventas`, `reports`, `stock`, etc.): activan/desactivan todos los `key_permiso` del prefijo y el comodín `modulo.*`.

### 2. Menú AdministraNET

- Tabla `permisos` (`Clavemenu`, `IDpuesto`).
- Mismo árbol que `/core/roles/<id>/editar/`.
- Al guardar, se sincronizan a `permiso_sistema_puesto` las claves definidas en `MAPEO_MENU_A_PERMISO` (`core/constantes_permisos.py`).

### 3. Reglas por puesto (legacy)

- Enlace al editor existente `/core/permisos-sistema/puesto/<id>/` (tabla ancha `permisos_sistema`).

## Relación con otras pantallas

| Pantalla anterior | Uso recomendado |
|-------------------|-----------------|
| `/core/permisos/` | Catálogo global; el toggle solo afectaba al puesto del usuario logueado |
| `/core/roles/` | Crear/editar nombre del puesto y menú (sigue válido) |
| `/core/permisos-sistema/` | Reglas legacy + navbar global |

## Ejemplo: Objetivos de venta para puesto Ventas

1. Ir a **Asignar permisos por puesto** → **Ventas**.
2. Pestaña **Permisos Synap** → atajo **+ Ventas** o activar manualmente `ventas.ver` y `ventas.editar`.
3. Los usuarios con ese puesto deben **cerrar sesión y volver a entrar** para refrescar permisos en sesión.

## Implementación

- Vistas: `core/views/views_permisos_puesto.py`
- Servicio Synap (toggle/atajo/listado): `core/services/synap_permisos.py::SynapPermisosService`
- Tests: `core/tests/test_permisos_puesto_supervisor.py`, `core/tests/test_synap_permisos.py`
