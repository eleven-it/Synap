from django.urls import path, include
from . import views
from .views import stock_initial_wizard, stock_initial_drafts, stock_initial_edit, stock_initial_finish
from .views.brands import BrandSearchApiView, BrandQuickCreateApiView
from .views.categories import CategorySearchApiView, SubcategorySearchApiView

app_name = 'inventory'

urlpatterns = [
    path('dashboard/', views.stock_dashboard, name='stock_dashboard'),
    path('dashboard/api/', views.stock_dashboard_api, name='stock_dashboard_api'),
    path('test/', views.test_app_architecture, name='test_app_architecture'),
    path('simple/', views.simple_test, name='simple_test'),
    path('tiendanube/', views.tiendanube_dashboard, name='tiendanube_dashboard'),
    
    # Product URLs
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_update'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),

    # Warehouse URLs
    path('warehouses/', views.WarehouseListView.as_view(), name='warehouse_list'),
    path('warehouses/create/', views.WarehouseCreateView.as_view(), name='warehouse_create'),
    path('warehouses/<int:pk>/edit/', views.WarehouseUpdateView.as_view(), name='warehouse_update'),
    path('warehouses/<int:pk>/delete/', views.WarehouseDeleteView.as_view(), name='warehouse_delete'),

    # Location URLs
    path('locations/', views.LocationListView.as_view(), name='location_list'),
    path('locations/create/', views.LocationCreateView.as_view(), name='location_create'),
    path('locations/<int:pk>/edit/', views.LocationUpdateView.as_view(), name='location_update'),
    path('locations/<int:pk>/delete/', views.LocationDeleteView.as_view(), name='location_delete'),

    # Brand URLs
    path('brands/', views.BrandListView.as_view(), name='brand_list'),
    path('brands/create/', views.BrandCreateView.as_view(), name='brand_create'),
    path('brands/<int:pk>/edit/', views.BrandUpdateView.as_view(), name='brand_update'),
    path('brands/<int:pk>/delete/', views.BrandDeleteView.as_view(), name='brand_delete'),

    # Category URLs
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    # Subcategory URLs
    path('subcategories/', views.SubcategoryListView.as_view(), name='subcategory_list'),
    path('subcategories/create/', views.SubcategoryCreateView.as_view(), name='subcategory_create'),
    path('subcategories/<int:pk>/edit/', views.SubcategoryUpdateView.as_view(), name='subcategory_update'),
    path('subcategories/<int:pk>/delete/', views.SubcategoryDeleteView.as_view(), name='subcategory_delete'),

    path('api/', include('inventory.api.urls')),
    path('stock-initial/', stock_initial_wizard, name='stock_initial_wizard'),
    path('stock-initial/drafts/', stock_initial_drafts, name='stock_initial_drafts'),
    path('stock-initial/edit/<int:draft_id>/', stock_initial_edit, name='stock_initial_edit'),
    path('stock-initial/finish/<int:draft_id>/', stock_initial_finish, name='stock_initial_finish'),
    path('api/brands/search/', BrandSearchApiView.as_view(), name='brand_search_api'),
    path('api/brands/create/', BrandQuickCreateApiView.as_view(), name='brand_quick_create_api'),
    path('api/categories/search/', CategorySearchApiView.as_view(), name='category_search_api'),
    path('api/subcategories/search/', SubcategorySearchApiView.as_view(), name='subcategory_search_api'),
]
