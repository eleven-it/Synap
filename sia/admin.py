from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Department,
    EvaluationCycle,
    StrategicSurveyResponse,
    FodaItem,
    Rating,
    OpenAnswer,
    CameAction,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'empresa', 'code', 'is_active', 'created_at')
    list_filter = ('empresa', 'is_active', 'created_at')
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('empresa', 'name')


@admin.register(EvaluationCycle)
class EvaluationCycleAdmin(admin.ModelAdmin):
    list_display = ('name', 'empresa', 'start_date', 'end_date', 'is_active', 'created_at')
    list_filter = ('empresa', 'is_active', 'start_date', 'end_date')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    date_hierarchy = 'start_date'
    ordering = ('-start_date', 'empresa', 'name')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Solo al crear
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(StrategicSurveyResponse)
class StrategicSurveyResponseAdmin(admin.ModelAdmin):
    list_display = ('user', 'evaluation_cycle', 'department', 'status', 'submitted_at', 'created_at')
    list_filter = ('evaluation_cycle', 'status', 'department', 'created_at')
    search_fields = ('user__email', 'user__nombre', 'evaluation_cycle__name')
    readonly_fields = ('created_at', 'updated_at', 'submitted_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('evaluation_cycle', 'user', 'department', 'status')
        }),
        (_('Timestamps'), {
            'fields': ('submitted_at', 'created_at', 'updated_at')
        }),
    )


@admin.register(FodaItem)
class FodaItemAdmin(admin.ModelAdmin):
    list_display = ('survey_response', 'quadrant', 'priority', 'description_short', 'created_at')
    list_filter = ('quadrant', 'priority', 'created_at')
    search_fields = ('description', 'survey_response__user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('survey_response', 'quadrant', 'priority')
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = _('Description')


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('survey_response', 'dimension', 'value', 'created_at')
    list_filter = ('dimension', 'value', 'created_at')
    search_fields = ('survey_response__user__email', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('survey_response', 'dimension')


@admin.register(OpenAnswer)
class OpenAnswerAdmin(admin.ModelAdmin):
    list_display = ('survey_response', 'question_type', 'question_text_short', 'created_at')
    list_filter = ('question_type', 'created_at')
    search_fields = ('question_text', 'answer', 'survey_response__user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('survey_response', 'question_type')
    
    def question_text_short(self, obj):
        return obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = _('Question')


@admin.register(CameAction)
class CameActionAdmin(admin.ModelAdmin):
    list_display = ('title', 'evaluation_cycle', 'action_type', 'priority', 'status', 'assigned_to', 'due_date')
    list_filter = ('evaluation_cycle', 'action_type', 'status', 'priority', 'created_at')
    search_fields = ('title', 'description', 'assigned_to__email')
    readonly_fields = ('created_at', 'updated_at', 'completed_at', 'created_by')
    date_hierarchy = 'created_at'
    ordering = ('evaluation_cycle', 'action_type', 'priority')
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('evaluation_cycle', 'action_type', 'title', 'description', 'related_foda_item')
        }),
        (_('Status & Priority'), {
            'fields': ('priority', 'status')
        }),
        (_('Assignment'), {
            'fields': ('assigned_to', 'due_date')
        }),
        (_('Timestamps'), {
            'fields': ('completed_at', 'created_by', 'created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Solo al crear
            obj.created_by = request.user
        super().save_model(request, obj, form, change)













