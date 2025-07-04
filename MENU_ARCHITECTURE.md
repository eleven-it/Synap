# Arquitectura de Menús en Synap

## Visión General

La nueva arquitectura de menús en Synap implementa un sistema centralizado y escalable que sigue el patrón de **Apps Principales** con **Submenús** para cada app. Esta estructura mejora la mantenibilidad, escalabilidad y experiencia de usuario.

## Estructura de Datos

### Configuración Principal (`APPS_MENU`)

Cada app se define con la siguiente estructura:

```python
{
    "id": "inventory",                    # Identificador único de la app
    "nombre": _("Inventory"),            # Nombre traducible
    "permiso": "inventory.ver",          # Permiso requerido para acceder
    "url": "inventory:stock_dashboard",  # URL principal de la app
    "icono_svg": "...",                  # Ícono SVG para el menú principal
    "orden": 2,                          # Orden de aparición
    "color": "green",                    # Color temático de la app
    "submenus": [...]                    # Lista de submenús
}
```

### Estructura de Submenús

Cada app puede tener múltiples secciones de submenús:

```python
{
    "seccion": _("Main"),                # Nombre de la sección
    "items": [
        {
            "label": _("Dashboard"),     # Etiqueta del item
            "url_name": "inventory:stock_dashboard",
            "icon": "dashboard",         # Ícono Material Design
            "permission": "inventory.ver" # Permiso específico
        }
    ]
}
```

## Apps Configuradas

### 1. Dashboard
- **ID**: `dashboard`
- **Color**: Blue
- **Submenús**: Ninguno (app simple)
- **Permiso**: `usuarios.dashboard`

### 2. Inventory
- **ID**: `inventory`
- **Color**: Green
- **Submenús**: Main, Stock Management, Catalog, TiendaNube
- **Permiso**: `inventory.ver`

### 3. TiendaNube
- **ID**: `tiendanube`
- **Color**: Purple
- **Submenús**: Integration, Sync Management
- **Permiso**: `tiendanube.access`

### 4. Settings
- **ID**: `settings`
- **Color**: Gray
- **Submenús**: Quick Access, Access Management, General Configuration, Financial Configuration, System Configuration
- **Permiso**: `usuarios.dashboard`

## Funciones de Utilidad

### `apps_visibles_para_usuario(user)`
Obtiene todas las apps visibles para un usuario según sus permisos.

### `obtener_app_por_id(app_id)`
Obtiene una app específica por su ID.

### `obtener_submenus_por_app(app_id, permisos_usuario)`
Obtiene los submenús visibles para una app específica.

## Context Processors

### `usuario_y_permisos(request)`
Proporciona:
- `apps_menu`: Lista de apps visibles
- `modulos_menu`: Compatibilidad con código existente

### `menu_context(request)`
Proporciona:
- `apps_menu`: Apps visibles
- `current_app_id`: ID de la app actual
- `current_sidebar_items`: Submenús de la app actual
- `show_sidebar`: Si debe mostrar sidebar

### `inventory_menu_context(request)`
Compatibilidad para plantillas de inventory.

### `tiendanube_menu_context(request)`
Compatibilidad para plantillas de TiendaNube.

## Uso en Plantillas

### Menú Principal de Apps
```html
{% for app in apps_menu %}
<div class="app-card" data-app-id="{{ app.id }}">
    <div class="app-icon">{{ app.icono_svg|safe }}</div>
    <div class="app-name">{{ app.nombre }}</div>
    {% if app.submenus %}
        <div class="app-submenus">
            {% for submenu in app.submenus %}
                <div class="submenu-section">
                    <h4>{{ submenu.seccion }}</h4>
                    {% for item in submenu.items %}
                        <a href="{{ item.url }}">{{ item.label }}</a>
                    {% endfor %}
                </div>
            {% endfor %}
        </div>
    {% endif %}
</div>
{% endfor %}
```

### Sidebar Dinámico
```html
{% if show_sidebar %}
<aside class="sidebar">
    {% for submenu in current_sidebar_items %}
        <div class="submenu-section">
            <h3>{{ submenu.seccion }}</h3>
            {% for item in submenu.items %}
                <a href="{{ item.url }}" class="sidebar-item">
                    <span class="material-icons">{{ item.icon }}</span>
                    {{ item.label }}
                </a>
            {% endfor %}
        </div>
    {% endfor %}
</aside>
{% endif %}
```

## Agregar una Nueva App

1. **Definir la app en `APPS_MENU`**:
```python
{
    "id": "nueva_app",
    "nombre": _("Nueva App"),
    "permiso": "nueva_app.ver",
    "url": "nueva_app:dashboard",
    "icono_svg": "...",
    "orden": 5,
    "color": "orange",
    "submenus": [
        {
            "seccion": _("Principal"),
            "items": [
                {
                    "label": _("Dashboard"),
                    "url_name": "nueva_app:dashboard",
                    "icon": "dashboard",
                    "permission": "nueva_app.ver"
                }
            ]
        }
    ]
}
```

2. **Agregar permisos en `constantes_permisos.py`**:
```python
"Nueva App": [
    ("nueva_app.ver", "Ver nueva app"),
    ("nueva_app.crear", "Crear en nueva app"),
    # ...
]
```

3. **Crear context processor si es necesario**:
```python
def nueva_app_menu_context(request):
    # Lógica específica si es necesaria
    return {"nueva_app_sidebar_items": [...]}
```

## Ventajas de la Nueva Arquitectura

1. **Centralización**: Toda la configuración de menús está en un solo lugar
2. **Escalabilidad**: Fácil agregar nuevas apps y submenús
3. **Mantenibilidad**: Cambios en un lugar se reflejan en toda la aplicación
4. **Consistencia**: Estructura uniforme para todas las apps
5. **Permisos**: Control granular de acceso por app y por item
6. **Internacionalización**: Soporte completo para traducciones
7. **Compatibilidad**: Mantiene compatibilidad con código existente

## Migración

La nueva arquitectura es **compatible hacia atrás**:
- Las funciones antiguas siguen funcionando
- Las plantillas existentes no necesitan cambios inmediatos
- Se puede migrar gradualmente

## Próximos Pasos

1. Actualizar plantillas para usar la nueva estructura
2. Implementar el nuevo diseño de menú principal
3. Agregar apps comentadas (CRM, Ventas, etc.) según se desarrollen
4. Optimizar el rendimiento con cache si es necesario 