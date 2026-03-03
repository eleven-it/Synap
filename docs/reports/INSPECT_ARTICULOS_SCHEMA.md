# Comando: inspect_articulos_schema

Este comando inspecciona la estructura de la tabla `articulos` y tablas relacionadas en MySQL para el reporte de Backorder vs Stock vs Facturación.

## Uso

### Ejecutar dentro de Docker:

```bash
docker-compose exec web python manage.py inspect_articulos_schema --base-empresa NOMBRE_BASE_DATOS
```

### Ejemplos:

1. **Inspeccionar solo la tabla `articulos`:**
```bash
docker-compose exec web python manage.py inspect_articulos_schema --base-empresa nombre_base_datos
```

2. **Inspeccionar todas las tablas relacionadas:**
```bash
docker-compose exec web python manage.py inspect_articulos_schema --base-empresa nombre_base_datos --all-tables
```

3. **Inspeccionar una tabla específica:**
```bash
docker-compose exec web python manage.py inspect_articulos_schema --base-empresa nombre_base_datos --table comp_ped_reng
```

## Parámetros

- `--base-empresa` (requerido): Nombre de la base de datos MySQL
- `--table` (opcional): Nombre de la tabla a inspeccionar (default: `articulos`)
- `--all-tables` (opcional): Inspeccionar todas las tablas relacionadas

## Tablas que inspecciona (con --all-tables)

- `articulos` - Maestro de productos
- `comp_ped` - Cabecera de pedidos
- `comp_ped_reng` - Renglones de pedidos
- `stock` - Stock actual
- `inventario` - Alternativa de tabla de stock
- `productos_stock` - Alternativa de tabla de stock
- `categorias` - Categorías de productos
- `rubros` - Alternativa de categorías
- `rubro` - Alternativa de categorías

## Salida

El comando muestra:
- Estructura completa de columnas (nombre, tipo, nullable, keys, default, extra)
- Comentarios de columnas (si existen)
- Total de registros
- Índices de la tabla
- Campos requeridos para el reporte

## Nota

Este comando debe ejecutarse dentro del contenedor Docker donde está disponible `MySQLdb`.
