from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
import random

@login_required
def dashboard_view(request):
    # Verificar si el usuario está autenticado a través de Firebase
    if "user" not in request.session:
        return redirect("login:login")

    user_info = request.session.get("user", {})
    
    # Enriquecer la información del usuario con valores por defecto
    user_data = {
        "uid": user_info.get("uid", ""),
        "name": user_info.get("name", ""),
        "email": user_info.get("email", ""),
        "idioma": user_info.get("idioma", "es"),
        "last_login": user_info.get("last_login", timezone.now().strftime("%B %d, %Y"))
    }
    
    # Datos simulados para el dashboard
    # En un entorno real, estos datos vendrían de la base de datos
    dashboard_data = {
        "user": user_data,
        "metrics": {
            "sales": {
                "current": 24580,
                "change": 12.5,
                "trend": "up"
            },
            "orders": {
                "current": 1247,
                "change": 8.2,
                "trend": "up"
            },
            "customers": {
                "current": 892,
                "change": 15.3,
                "trend": "up"
            },
            "products": {
                "current": 156,
                "change": 5.7,
                "trend": "up"
            }
        },
        "recent_activity": [
            {
                "type": "order",
                "title": "New order received",
                "description": "Order #1234 from John Doe",
                "time": "2 minutes ago",
                "icon": "currency-dollar",
                "color": "green"
            },
            {
                "type": "customer",
                "title": "New customer registered",
                "description": "Jane Smith joined",
                "time": "15 minutes ago",
                "icon": "user",
                "color": "blue"
            },
            {
                "type": "product",
                "title": "Product updated",
                "description": "iPhone 15 Pro stock updated",
                "time": "1 hour ago",
                "icon": "cube",
                "color": "purple"
            },
            {
                "type": "system",
                "title": "System notification",
                "description": "Backup completed successfully",
                "time": "2 hours ago",
                "icon": "information-circle",
                "color": "orange"
            }
        ],
        "quick_actions": [
            {
                "title": "Sales",
                "description": "Manage orders and invoices",
                "url": "/sales/",
                "icon": "document-text",
                "color": "blue"
            },
            {
                "title": "Inventory",
                "description": "Track products and stock",
                "url": "/inventory/",
                "icon": "cube",
                "color": "green"
            },
            {
                "title": "Customers",
                "description": "Manage customer database",
                "url": "/sales/clients/",
                "icon": "users",
                "color": "purple"
            },
            {
                "title": "Reports",
                "description": "Analytics and insights",
                "url": "/reports/",
                "icon": "chart-bar",
                "color": "orange"
            }
        ],
        "last_login": user_data["last_login"],
        "chart_data": {
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "sales": [12000, 19000, 15000, 25000, 22000, 30000, 28000],
            "orders": [45, 52, 38, 65, 58, 72, 68]
        }
    }
    
    return render(request, "dashboard/dashboard.html", dashboard_data)
