# Guía de Migración - Nueva Arquitectura de Menús Synap

## 🎯 Resumen de Cambios

La nueva arquitectura de menús en Synap introduce un sistema más escalable y mantenible que sigue el patrón de **Apps Principales** con **Submenús** para cada app. Esta guía te ayudará a migrar y aprovechar al máximo la nueva funcionalidad.

## 🚀 Nuevas Características

### 1. **Arquitectura Centralizada**
- ✅ Configuración centralizada en `core/utils/utils.py`
- ✅ Sistema de permisos integrado
- ✅ Soporte para traducciones (i18n)
- ✅ Colores y estilos personalizables por app

### 2. **UX Mejorada**
- ✅ Dropdowns tipo Figma con preview de submenús
- ✅ Sidebar dinámico y colapsable
- ✅ Breadcrumbs automáticos
- ✅ Animaciones y microinteracciones
- ✅ Dark mode completo
- ✅ Responsive design

### 3. **Compatibilidad**
- ✅ Mantiene compatibilidad con código existente
- ✅ Migración gradual posible
- ✅ Variables de contexto preservadas

## 📁 Estructura de Archivos

```
core/
├── utils/
│   └── utils.py              # 🆕 Configuración centralizada de apps
├── context_processors.py     # 🔄 Actualizado para nueva arquitectura
├── templates/
│   ├── base_app.html         # 🆕 Nuevo template base
│   ├── dashboard_apps.html   # 🆕 Dashboard moderno
│   └── core/
│       └── menu_example.html # 🆕 Ejemplo de uso
└── views/
    └── views_general.py      # 🔄 Actualizado con nuevas vistas

theme/
└── templates/
    └── partials/
        └── navbar.html       # 🔄 Actualizado para apps_menu
```

## 🔧 Configuración de una Nueva App

### 1. **Definir la App en `core/utils/utils.py`**

```python
{
    "id": "mi_app",
    "nombre": _("Mi Aplicación"),
    "permiso": "mi_app.ver",
    "url": "mi_app:dashboard",
    "icono_svg": """<svg class='h-6 w-6' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
        <path stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M13 10V3L4 14h7v7l9-11h-7z'/>
    </svg>""",
    "orden": 3,
    "color": "blue",
    "submenus": [
        {
            "seccion": "Gestión",
            "items": [
                {
                    "label": "Dashboard",
                    "url": "mi_app:dashboard",
                    "icon": "dashboard"
                },
                {
                    "label": "Lista",
                    "url": "mi_app:lista",
                    "icon": "list"
                }
            ]
        },
        {
            "seccion": "Configuración",
            "items": [
                {
                    "label": "Ajustes",
                    "url": "mi_app:ajustes",
                    "icon": "settings"
                }
            ]
        }
    ]
}
```

### 2. **Crear el Template Base**

```html
<!-- mi_app/templates/mi_app/base.html -->
{% extends "base_app.html" %}
{% load i18n %}

{% block title %}{% trans "Mi Aplicación" %} - Synap{% endblock %}

{% block content %}
    {% block mi_app_content %}{% endblock %}
{% endblock %}
```

### 3. **Usar en las Vistas**

```python
# mi_app/views.py
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class MiAppDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'mi_app/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # El context processor ya proporciona:
        # - current_app_id = "mi_app"
        # - show_sidebar = True
        # - current_sidebar_items = submenús de mi_app
        return context
```

## 🔄 Migración desde Estructura Anterior

### **Opción 1: Migración Gradual (Recomendada)**

1. **Mantener compatibilidad** - Las variables antiguas siguen funcionando:
   ```python
   # En templates existentes
   {% for modulo in modulos_menu %}  # ✅ Sigue funcionando
   {% for app in apps_menu %}        # 🆕 Nueva forma
   ```

2. **Actualizar templates gradualmente**:
   ```html
   <!-- Antes -->
   {% for modulo in modulos_menu %}
       <a href="{{ modulo.url }}">{{ modulo.nombre }}</a>
   {% endfor %}
   
   <!-- Después -->
   {% for app in apps_menu %}
       <a href="{{ app.url }}">{{ app.nombre }}</a>
   {% endfor %}
   ```

### **Opción 2: Migración Completa**

1. **Cambiar template base**:
   ```html
   <!-- Antes -->
   {% extends "base.html" %}
   
   <!-- Después -->
   {% extends "base_app.html" %}
   ```

2. **Actualizar referencias**:
   ```html
   <!-- Antes -->
   {% include 'inventory/partials/sidebar.html' %}
   
   <!-- Después -->
   <!-- El sidebar se genera automáticamente -->
   ```

## 🎨 Personalización de Estilos

### **Colores por App**

```python
# En APPS_MENU
{
    "id": "inventory",
    "color": "purple",  # Usa colores de Tailwind
    # ...
}
```

### **Estilos CSS Personalizados**

```css
/* En tu template o archivo CSS */
.app-card[data-app-id="inventory"] {
    border-color: #a855f7;
}

.app-card[data-app-id="inventory"]:hover {
    background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
}
```

## 📱 Responsive Design

La nueva arquitectura incluye:

- **Desktop**: Dropdowns elegantes con preview de submenús
- **Tablet**: Sidebar colapsable
- **Mobile**: Menú hamburguesa con navegación optimizada

## 🔐 Sistema de Permisos

```python
# En la configuración de la app
{
    "permiso": "inventory.ver",  # Permiso requerido para ver la app
    "submenus": [
        {
            "seccion": "Gestión",
            "items": [
                {
                    "label": "Productos",
                    "url": "inventory:product_list",
                    "icon": "inventory_2",
                    "permiso": "inventory.product.ver"  # Permiso específico
                }
            ]
        }
    ]
}
```

## 🧪 Testing

### **URLs de Prueba**

```bash
# Dashboard con nueva arquitectura
http://localhost:8000/core/dashboard-apps/

# Ejemplo de menús
http://localhost:8000/core/menu-example/

# Dashboard clásico (mantiene compatibilidad)
http://localhost:8000/core/dashboard/
```

### **Verificar Context**

```python
# En una vista de prueba
def test_view(request):
    context = {
        'apps_menu': apps_menu,  # Lista de apps disponibles
        'current_app_id': 'inventory',  # App actual
        'show_sidebar': True,  # Mostrar sidebar
        'current_sidebar_items': [...]  # Submenús de la app actual
    }
    return render(request, 'test.html', context)
```

## 🚨 Consideraciones Importantes

### **Compatibilidad**

- ✅ `modulos_menu` sigue funcionando
- ✅ `admin_sidebar_items` sigue funcionando
- ✅ `inventory_sidebar_items` sigue funcionando

### **Performance**

- ✅ Context processors optimizados
- ✅ Carga lazy de submenús
- ✅ Caché de permisos

### **Seguridad**

- ✅ Validación de permisos en cada nivel
- ✅ Sanitización de URLs
- ✅ Protección CSRF

## 📈 Próximos Pasos

1. **Migrar apps existentes** a la nueva estructura
2. **Personalizar colores y estilos** por app
3. **Agregar nuevas apps** siguiendo el patrón
4. **Optimizar performance** según necesidades
5. **Implementar caché** para menús complejos

## 🆘 Soporte

Si encuentras problemas durante la migración:

1. Revisa los logs de Django
2. Verifica que los permisos estén correctos
3. Confirma que las URLs estén registradas
4. Usa el template de ejemplo como referencia

---

**¡La nueva arquitectura está lista para usar! 🎉** 