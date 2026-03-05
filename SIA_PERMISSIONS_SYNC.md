# Sincronización de Permisos SIA con administraNET MySQL

## Situación Actual

### ❌ Problema Identificado

Los permisos de SIA que creamos están **SOLO en PostgreSQL** (`core.models.Permiso`), pero el sistema carga permisos desde **MySQL de administraNET** en tiempo de ejecución.

### Cómo Funciona el Sistema de Permisos

1. **Autenticación**: Se hace contra MySQL de administraNET (tabla `usuarios`)
2. **Carga de Permisos**: El middleware `base_middleware.py` carga permisos desde:
   - Tabla `permiso_sistema` (MySQL) - Define los permisos disponibles
   - Tabla `permiso_sistema_puesto` (MySQL) - Asigna permisos a puestos
3. **Validación**: Los permisos se validan en **tiempo de ejecución** (cuando se accede a las vistas), NO en el login
4. **Permisos de SIA**: Actualmente están solo en PostgreSQL, NO en MySQL

### Flujo Actual

```
Login → MySQL (validar usuario)
  ↓
Middleware carga permisos desde MySQL (permiso_sistema_puesto)
  ↓
Usuario accede a /sia/ → Verifica permisos en tiempo de ejecución
  ↓
❌ NO encuentra permisos de SIA porque están en PostgreSQL, no en MySQL
```

## Solución Propuesta

### Opción 1: Sincronizar Permisos SIA a MySQL (RECOMENDADA)

Sincronizar los permisos de SIA a las tablas de administraNET MySQL para que funcionen con el sistema existente.

### Opción 2: Modificar Middleware para Consultar PostgreSQL

Modificar el middleware para que también consulte PostgreSQL si no encuentra permisos en MySQL (más complejo, menos eficiente).

## Implementación Recomendada

Agregar los permisos de SIA a `core/constantes_permisos.py` y crear un comando para sincronizarlos a MySQL.













