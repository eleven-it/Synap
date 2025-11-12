"""
URLs del módulo Reports AI
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'reports_ai'

# Router para APIs REST
router = DefaultRouter()
# Los ViewSets se registrarán aquí más adelante

urlpatterns = [
    # APIs REST
    path('api/', include(router.urls)),
    
    # Webhooks (endpoints específicos)
    path('webhook/report/', lambda r: __import__('reports_ai.api.webhooks', fromlist=['webhook_report']).webhook_report(r), name='webhook_report'),
    path('webhook/validate/', lambda r: __import__('reports_ai.api.webhooks', fromlist=['webhook_validate']).webhook_validate(r), name='webhook_validate'),
    path('webhook/health/', lambda r: __import__('reports_ai.api.webhooks', fromlist=['webhook_health']).webhook_health(r), name='webhook_health'),
    path('webhook/feedback-nlu/', lambda r: __import__('reports_ai.api.nlu_webhooks', fromlist=['webhook_feedback_nlu']).webhook_feedback_nlu(r), name='webhook_feedback_nlu'),
    
    # APIs de NLU
    path('api/nlu-feedback/', lambda r: __import__('reports_ai.api.nlu_webhooks', fromlist=['nlu_feedback_list']).nlu_feedback_list(r), name='nlu_feedback_list'),
    path('api/nlu-metrics/', lambda r: __import__('reports_ai.api.nlu_webhooks', fromlist=['nlu_metrics_summary']).nlu_metrics_summary(r), name='nlu_metrics_summary'),
    
    # Vistas web principales
    path('dashboard/', lambda r: __import__('reports_ai.views.dashboard', fromlist=['dashboard']).dashboard(r), name='dashboard'),
    path('chat/', lambda r: __import__('reports_ai.views.chat_views', fromlist=['ai_assistant']).ai_assistant(r), name='ai_assistant'),
    path('generate/', lambda r: __import__('reports_ai.views.dashboard', fromlist=['generate_report']).generate_report(r), name='generate_report'),
    path('history/', lambda r: __import__('reports_ai.views.dashboard', fromlist=['report_history']).report_history(r), name='report_history'),
    path('metrics/', lambda r: __import__('reports_ai.views.dashboard', fromlist=['agent_metrics']).agent_metrics(r), name='agent_metrics'),
    path('config/', lambda r: __import__('reports_ai.views.dashboard', fromlist=['config']).config(r), name='config'),
    path('report/<str:request_id>/', lambda r, request_id: __import__('reports_ai.views.dashboard', fromlist=['report_detail']).report_detail(r, request_id), name='report_detail'),
    
    # Functional Catalog
    path('catalog/', lambda r: __import__('reports_ai.views.catalog_views', fromlist=['catalog_list']).catalog_list(r), name='catalog_list'),
    path('catalog/create/', lambda r: __import__('reports_ai.views.catalog_views', fromlist=['catalog_create']).catalog_create(r), name='catalog_create'),
    path('catalog/<int:catalog_id>/', lambda r, catalog_id: __import__('reports_ai.views.catalog_views', fromlist=['catalog_detail']).catalog_detail(r, catalog_id), name='catalog_detail'),
    path('catalog/<int:catalog_id>/edit/', lambda r, catalog_id: __import__('reports_ai.views.catalog_views', fromlist=['catalog_edit']).catalog_edit(r, catalog_id), name='catalog_edit'),
    path('catalog/<int:catalog_id>/delete/', lambda r, catalog_id: __import__('reports_ai.views.catalog_views', fromlist=['catalog_delete']).catalog_delete(r, catalog_id), name='catalog_delete'),
    path('catalog/<int:catalog_id>/toggle/', lambda r, catalog_id: __import__('reports_ai.views.catalog_views', fromlist=['catalog_toggle_active']).catalog_toggle_active(r, catalog_id), name='catalog_toggle_active'),
    
    # Catalog API
    path('api/catalog/vb6-forms/', lambda r: __import__('reports_ai.api.catalog_api', fromlist=['get_vb6_forms']).get_vb6_forms(r), name='api_catalog_vb6_forms'),
    path('api/catalog/vb6-forms-grouped/', lambda r: __import__('reports_ai.api.catalog_api', fromlist=['get_vb6_forms_grouped']).get_vb6_forms_grouped(r), name='api_catalog_vb6_forms_grouped'),
    path('api/catalog/vb6-modules/', lambda r: __import__('reports_ai.api.catalog_api', fromlist=['get_vb6_modules']).get_vb6_modules(r), name='api_catalog_vb6_modules'),
    path('api/catalog/entities/', lambda r: __import__('reports_ai.api.catalog_api', fromlist=['get_entities_suggestions']).get_entities_suggestions(r), name='api_catalog_entities'),
    path('api/catalog/tables/', lambda r: __import__('reports_ai.api.catalog_api', fromlist=['get_tables_from_schema']).get_tables_from_schema(r), name='api_catalog_tables'),
    
    # Business Rules
    path('business-rules/', lambda r: __import__('reports_ai.views.business_rules', fromlist=['business_rules_list']).business_rules_list(r), name='business_rules_list'),
    path('business-rules/create/', lambda r: __import__('reports_ai.views.business_rules', fromlist=['business_rule_create']).business_rule_create(r), name='business_rule_create'),
    path('business-rules/<int:rule_id>/', lambda r, rule_id: __import__('reports_ai.views.business_rules', fromlist=['business_rule_detail']).business_rule_detail(r, rule_id), name='business_rule_detail'),
    path('business-rules/<int:rule_id>/edit/', lambda r, rule_id: __import__('reports_ai.views.business_rules', fromlist=['business_rule_edit']).business_rule_edit(r, rule_id), name='business_rule_edit'),
    path('business-rules/<int:rule_id>/delete/', lambda r, rule_id: __import__('reports_ai.views.business_rules', fromlist=['business_rule_delete']).business_rule_delete(r, rule_id), name='business_rule_delete'),
    path('business-rules/<int:rule_id>/toggle/', lambda r, rule_id: __import__('reports_ai.views.business_rules', fromlist=['business_rule_toggle_active']).business_rule_toggle_active(r, rule_id), name='business_rule_toggle_active'),
    path('business-rules/<int:rule_id>/duplicate/', lambda r, rule_id: __import__('reports_ai.views.business_rules', fromlist=['business_rule_duplicate']).business_rule_duplicate(r, rule_id), name='business_rule_duplicate'),
    path('business-rules/import/', lambda r: __import__('reports_ai.views.business_rules', fromlist=['business_rule_import']).business_rule_import(r), name='business_rule_import'),
    path('business-rules/export/', lambda r: __import__('reports_ai.views.business_rules', fromlist=['business_rule_export']).business_rule_export(r), name='business_rule_export'),
    path('business-rules/bulk-action/', lambda r: __import__('reports_ai.views.business_rules', fromlist=['business_rule_bulk_action']).business_rule_bulk_action(r), name='business_rule_bulk_action'),
    
    # Training (Logic Interpreter)
    path('train/logic-interpreter/', lambda r: __import__('reports_ai.views.training_views', fromlist=['logic_interpreter_training']).logic_interpreter_training(r), name='logic_interpreter_training'),
    path('train/logic-interpreter/session/<str:session_id>/', lambda r, session_id: __import__('reports_ai.views.training_views', fromlist=['training_session_detail']).training_session_detail(r, session_id), name='training_session_detail'),
    
    # Training (Data Analyst)
    path('train/data-analyst/', lambda r: __import__('reports_ai.views.data_analyst_training_views', fromlist=['data_analyst_training']).data_analyst_training(r), name='data_analyst_training'),
    path('train/data-analyst/session/<str:session_id>/', lambda r, session_id: __import__('reports_ai.views.data_analyst_training_views', fromlist=['data_analyst_training_session_detail']).data_analyst_training_session_detail(r, session_id), name='data_analyst_training_session_detail'),
    
    # Training API (Logic Interpreter)
    path('api/train/logic-interpreter/start/', lambda r: __import__('reports_ai.api.training_api', fromlist=['start_training']).start_training(r), name='api_training_start'),
    path('api/train/logic-interpreter/start-guided/', lambda r: __import__('reports_ai.api.training_api', fromlist=['start_guided_training']).start_guided_training(r), name='api_training_start_guided'),
    path('api/train/logic-interpreter/progress/<str:session_id>/', lambda r, session_id: __import__('reports_ai.api.training_api', fromlist=['training_progress_stream']).training_progress_stream(r, session_id), name='api_training_progress'),
    path('api/train/logic-interpreter/status/<str:session_id>/', lambda r, session_id: __import__('reports_ai.api.training_api', fromlist=['training_status']).training_status(r, session_id), name='api_training_status'),
    path('api/train/logic-interpreter/cancel/<str:session_id>/', lambda r, session_id: __import__('reports_ai.api.training_api', fromlist=['cancel_training']).cancel_training(r, session_id), name='api_training_cancel'),
    path('api/train/logic-interpreter/results/<str:session_id>/', lambda r, session_id: __import__('reports_ai.api.training_api', fromlist=['training_results']).training_results(r, session_id), name='api_training_results'),
    path('api/train/logic-interpreter/history/', lambda r: __import__('reports_ai.api.training_api', fromlist=['training_history']).training_history(r), name='api_training_history'),
    
    # Training API (Data Analyst)
    path('api/train/data-analyst/start/', lambda r: __import__('reports_ai.api.data_analyst_training_api', fromlist=['start_data_analyst_training']).start_data_analyst_training(r), name='api_data_analyst_training_start'),
    path('api/train/data-analyst/progress/<str:session_id>/', lambda r, session_id: __import__('reports_ai.api.data_analyst_training_api', fromlist=['data_analyst_training_progress_stream']).data_analyst_training_progress_stream(r, session_id), name='api_data_analyst_training_progress'),
    path('api/train/data-analyst/status/<str:session_id>/', lambda r, session_id: __import__('reports_ai.api.data_analyst_training_api', fromlist=['data_analyst_training_status']).data_analyst_training_status(r, session_id), name='api_data_analyst_training_status'),
    path('api/train/data-analyst/cancel/<str:session_id>/', lambda r, session_id: __import__('reports_ai.api.data_analyst_training_api', fromlist=['cancel_data_analyst_training']).cancel_data_analyst_training(r, session_id), name='api_data_analyst_training_cancel'),
    path('api/train/data-analyst/results/<str:session_id>/', lambda r, session_id: __import__('reports_ai.api.data_analyst_training_api', fromlist=['data_analyst_training_results']).data_analyst_training_results(r, session_id), name='api_data_analyst_training_results'),
    path('api/train/data-analyst/history/', lambda r: __import__('reports_ai.api.data_analyst_training_api', fromlist=['data_analyst_training_history']).data_analyst_training_history(r), name='api_data_analyst_training_history'),
    
    # Glossary
    path('glossary/', lambda r: __import__('reports_ai.views.glossary', fromlist=['glossary_list']).glossary_list(r), name='glossary_list'),
    path('glossary/create/', lambda r: __import__('reports_ai.views.glossary', fromlist=['glossary_term_create']).glossary_term_create(r), name='glossary_term_create'),
    path('glossary/<int:term_id>/', lambda r, term_id: __import__('reports_ai.views.glossary', fromlist=['glossary_term_detail']).glossary_term_detail(r, term_id), name='glossary_term_detail'),
    path('glossary/<int:term_id>/edit/', lambda r, term_id: __import__('reports_ai.views.glossary', fromlist=['glossary_term_edit']).glossary_term_edit(r, term_id), name='glossary_term_edit'),
    path('glossary/<int:term_id>/delete/', lambda r, term_id: __import__('reports_ai.views.glossary', fromlist=['glossary_term_delete']).glossary_term_delete(r, term_id), name='glossary_term_delete'),
    path('glossary/<int:term_id>/toggle/', lambda r, term_id: __import__('reports_ai.views.glossary', fromlist=['glossary_term_toggle_active']).glossary_term_toggle_active(r, term_id), name='glossary_term_toggle_active'),
    path('glossary/search-api/', lambda r: __import__('reports_ai.views.glossary', fromlist=['glossary_search_api']).glossary_search_api(r), name='glossary_search_api'),
    path('glossary/export/', lambda r: __import__('reports_ai.views.glossary', fromlist=['glossary_export']).glossary_export(r), name='glossary_export'),
    path('glossary/import/', lambda r: __import__('reports_ai.views.glossary', fromlist=['glossary_import']).glossary_import(r), name='glossary_import'),
    
    # Quality & Corrections (Active Learning)
    path('quality/dashboard/', lambda r: __import__('reports_ai.views.corrections_views', fromlist=['quality_dashboard']).quality_dashboard(r), name='quality_dashboard'),
    path('quality/relationships/', lambda r: __import__('reports_ai.views.corrections_views', fromlist=['relationships_list']).relationships_list(r), name='relationships_list'),
    path('corrections/', lambda r: __import__('reports_ai.views.query_corrections_views', fromlist=['corrections_list']).corrections_list(r), name='corrections_list'),
    path('corrections/<int:correction_id>/', lambda r, correction_id: __import__('reports_ai.views.query_corrections_views', fromlist=['correction_detail']).correction_detail(r, correction_id), name='correction_detail'),
    path('corrections/create/', lambda r: __import__('reports_ai.views.query_corrections_views', fromlist=['create_correction']).create_correction(r), name='create_correction'),
    path('corrections/<int:correction_id>/edit/', lambda r, correction_id: __import__('reports_ai.views.query_corrections_views', fromlist=['edit_correction']).edit_correction(r, correction_id), name='edit_correction'),
    path('corrections/<int:correction_id>/delete/', lambda r, correction_id: __import__('reports_ai.views.query_corrections_views', fromlist=['delete_correction']).delete_correction(r, correction_id), name='delete_correction'),
    path('corrections/<int:correction_id>/mark-applied/', lambda r, correction_id: __import__('reports_ai.views.query_corrections_views', fromlist=['mark_applied']).mark_applied(r, correction_id), name='mark_applied'),
    path('corrections/<int:correction_id>/apply/', lambda r, correction_id: __import__('reports_ai.views.corrections_views', fromlist=['apply_correction']).apply_correction(r, correction_id), name='apply_correction'),
    path('relationships/<int:relationship_id>/validate/', lambda r, relationship_id: __import__('reports_ai.views.corrections_views', fromlist=['validate_relationship']).validate_relationship(r, relationship_id), name='validate_relationship'),
    
    # Chat APIs
    path('api/chat/send/', lambda r: __import__('reports_ai.api.chat_api', fromlist=['send_message']).send_message(r), name='api_chat_send'),
    path('api/chat/conversation/<str:conversation_id>/', lambda r, conversation_id: __import__('reports_ai.api.chat_api', fromlist=['get_conversation']).get_conversation(r, conversation_id), name='api_chat_conversation'),
    path('api/chat/conversations/', lambda r: __import__('reports_ai.api.chat_api', fromlist=['list_conversations']).list_conversations(r), name='api_chat_conversations'),
    path('api/chat/new/', lambda r: __import__('reports_ai.api.chat_api', fromlist=['new_conversation']).new_conversation(r), name='api_chat_new'),
    path('api/chat/archive/<str:conversation_id>/', lambda r, conversation_id: __import__('reports_ai.api.chat_api', fromlist=['archive_conversation']).archive_conversation(r, conversation_id), name='api_chat_archive'),
    
    # Export APIs
    path('api/export/<str:report_id>/', lambda r, report_id: __import__('reports_ai.api.export_api', fromlist=['export_report']).export_report(r, report_id), name='api_export_report'),
    path('api/export/download/<str:export_id>/', lambda r, export_id: __import__('reports_ai.api.export_api', fromlist=['download_export']).download_export(r, export_id), name='api_export_download'),
    path('api/export/status/<str:export_id>/', lambda r, export_id: __import__('reports_ai.api.export_api', fromlist=['export_status']).export_status(r, export_id), name='api_export_status'),
    path('api/export/list/', lambda r: __import__('reports_ai.api.export_api', fromlist=['list_user_exports']).list_user_exports(r), name='api_export_list'),
]

