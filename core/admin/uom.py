from django.contrib import admin
from core.models import UnitOfMeasure

@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'category', 'ratio', 'is_reference', 'is_active')
    list_filter = ('category', 'is_reference', 'is_active')
    search_fields = ('name', 'code')
