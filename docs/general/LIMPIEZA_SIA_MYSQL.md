# Limpieza de permisos SIA en MySQL (administraNET)

El módulo **SIA** (Strategic Insights & Alignment) fue eliminado del proyecto. Sus datos de negocio (ciclos de evaluación, encuestas, FODA, etc.) estaban solo en **PostgreSQL**; no creaba tablas propias en MySQL.

En MySQL de administraNET, SIA solo afectaba tablas existentes de permisos:

- **`permiso_sistema`**: el comando `sync_sia_permissions_to_adminet` insertaba aquí los permisos (`sia.manage_cycles`, `sia.view_company_dashboard`, etc.) con `grupo_permiso = 'SIA'`.
- **`permiso_sistema_puesto`**: si se asignaron esos permisos a puestos, hay filas con `id_permiso_sistema` apuntando a esos permisos.

Si en tu entorno se ejecutó ese sync, pueden quedar filas huérfanas. Esta limpieza es **opcional**; el sistema funciona igual con o sin ellas.

## Instrucciones

Ejecutar en **cada base de datos de empresa** de administraNET donde se haya sincronizado SIA (por ejemplo `administranet`, `administranet89`, etc.).

### Opción 1: Por `key_permiso`

```sql
-- 1) Borrar asignaciones por puesto (FK a permiso_sistema)
DELETE FROM permiso_sistema_puesto
WHERE id_permiso_sistema IN (
    SELECT id_permiso_sistema FROM permiso_sistema WHERE key_permiso LIKE 'sia.%'
);

-- 2) Borrar los permisos SIA
DELETE FROM permiso_sistema WHERE key_permiso LIKE 'sia.%';
```

### Opción 2: Por `grupo_permiso`

```sql
DELETE FROM permiso_sistema_puesto
WHERE id_permiso_sistema IN (
    SELECT id_permiso_sistema FROM permiso_sistema WHERE grupo_permiso = 'SIA'
);
DELETE FROM permiso_sistema WHERE grupo_permiso = 'SIA';
```

### Comprobar antes de borrar

Para ver cuántas filas se eliminarían:

```sql
SELECT id_permiso_sistema, key_permiso, nombre_permiso, grupo_permiso
FROM permiso_sistema
WHERE key_permiso LIKE 'sia.%' OR grupo_permiso = 'SIA';

SELECT COUNT(*) FROM permiso_sistema_puesto
WHERE id_permiso_sistema IN (SELECT id_permiso_sistema FROM permiso_sistema WHERE key_permiso LIKE 'sia.%');
```

Recomendación: hacer backup o ejecutar primero en un ambiente de prueba si las bases son críticas.
