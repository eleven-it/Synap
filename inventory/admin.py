# Register your models here.
from django.contrib import admin
from .models import (
    Product, ProductVariant, Location, StockMove,
    StockLot, StockQuant, ReplenishmentRule, ProductComboItem
)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'price', 'tracking', 'is_published')
    list_filter = ('tracking', 'is_published')
    search_fields = ('sku', 'name', 'description', 'handle', 'brand')

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'product', 'price', 'quantity')
    search_fields = ('sku', 'name')

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'location_type', 'parent_location')
    list_filter = ('location_type',)
    search_fields = ('name',)

@admin.register(StockMove)
class StockMoveAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'from_location', 'to_location', 'state', 'timestamp')
    list_filter = ('state', 'from_location', 'to_location')
    search_fields = ('product__name', 'product__sku', 'reference')
    readonly_fields = ('timestamp',)

@admin.register(StockLot)
class StockLotAdmin(admin.ModelAdmin):
    list_display = ('product', 'lot_number', 'expiration_date')
    search_fields = ('product__sku', 'lot_number')

@admin.register(StockQuant)
class StockQuantAdmin(admin.ModelAdmin):
    list_display = ('product', 'location', 'quantity', 'reserved_quantity')
    search_fields = ('product__sku', 'location__name')
    list_filter = ('location',)

@admin.register(ReplenishmentRule)
class ReplenishmentRuleAdmin(admin.ModelAdmin):
    list_display = ('product', 'location', 'min_quantity', 'max_quantity')
    list_filter = ('location',)
    search_fields = ('product__sku',)

admin.site.register(ProductComboItem)
