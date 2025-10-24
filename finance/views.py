from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

import json
from decimal import Decimal
from datetime import datetime

from .models import AccountReceivable, CreditLimitLog, FinancialReport, FinancialEntry
from .forms import AccountReceivableForm, CreditLimitLogForm, FinancialReportForm, SqlChatForm
from .services.financial_services import get_monthly_financial_summary
from .services.sql_chat import run_sql_chat

# AccountReceivable
class AccountReceivableListView(ListView):
    model = AccountReceivable
    template_name = 'finance/account_receivable_list.html'
    context_object_name = 'accounts_receivable'

class AccountReceivableDetailView(DetailView):
    model = AccountReceivable
    template_name = 'finance/account_receivable_detail.html'
    context_object_name = 'accountreceivable'

class AccountReceivableCreateView(CreateView):
    model = AccountReceivable
    form_class = AccountReceivableForm
    template_name = 'finance/account_receivable_form.html'
    success_url = reverse_lazy('finance:account_receivable_list')

class AccountReceivableUpdateView(UpdateView):
    model = AccountReceivable
    form_class = AccountReceivableForm
    template_name = 'finance/account_receivable_form.html'
    success_url = reverse_lazy('finance:account_receivable_list')

class AccountReceivableDeleteView(DeleteView):
    model = AccountReceivable
    template_name = 'finance/account_receivable_confirm_delete.html'
    success_url = reverse_lazy('finance:account_receivable_list')

# CreditLimitLog
class CreditLimitLogListView(ListView):
    model = CreditLimitLog
    template_name = 'finance/creditlimitlog_list.html'
    context_object_name = 'creditlimitlogs'

class CreditLimitLogDetailView(DetailView):
    model = CreditLimitLog
    template_name = 'finance/creditlimitlog_detail.html'
    context_object_name = 'creditlimitlog'

class CreditLimitLogCreateView(CreateView):
    model = CreditLimitLog
    form_class = CreditLimitLogForm
    template_name = 'finance/creditlimitlog_form.html'
    success_url = reverse_lazy('finance:creditlimitlog_list')

class CreditLimitLogUpdateView(UpdateView):
    model = CreditLimitLog
    form_class = CreditLimitLogForm
    template_name = 'finance/creditlimitlog_form.html'
    success_url = reverse_lazy('finance:creditlimitlog_list')

class CreditLimitLogDeleteView(DeleteView):
    model = CreditLimitLog
    template_name = 'finance/creditlimitlog_confirm_delete.html'
    success_url = reverse_lazy('finance:creditlimitlog_list')

# FinancialReport
class FinancialReportListView(ListView):
    model = FinancialReport
    template_name = 'finance/financialreport_list.html'
    context_object_name = 'financialreports'

class FinancialReportDetailView(DetailView):
    model = FinancialReport
    template_name = 'finance/financialreport_detail.html'
    context_object_name = 'financialreport'

class FinancialReportCreateView(CreateView):
    model = FinancialReport
    form_class = FinancialReportForm
    template_name = 'finance/financialreport_form.html'
    success_url = reverse_lazy('finance:financialreport_list')

class FinancialReportUpdateView(UpdateView):
    model = FinancialReport
    form_class = FinancialReportForm
    template_name = 'finance/financialreport_form.html'
    success_url = reverse_lazy('finance:financialreport_list')

class FinancialReportDeleteView(DeleteView):
    model = FinancialReport
    template_name = 'finance/financialreport_confirm_delete.html'
    success_url = reverse_lazy('finance:financialreport_list')


# =============================================================================
# SQL CHAT VIEW
# =============================================================================

class SqlChatView(LoginRequiredMixin, FormView):
    """
    Vista para el chat SQL de IA.
    Permite a los usuarios hacer consultas en lenguaje natural sobre datos financieros.
    """
    template_name = 'finance/sql_chat.html'
    form_class = SqlChatForm
    
    def get_context_data(self, **kwargs):
        """Agregar contexto adicional al template."""
        context = super().get_context_data(**kwargs)
        
        # Verificar si el webhook está configurado
        webhook_url = getattr(settings, 'N8N_SQL_CHAT_WEBHOOK', '')
        context['webhook_configured'] = bool(webhook_url)
        
        return context
    
    def form_valid(self, form):
        """Procesar consulta válida."""
        # Extraer datos del formulario
        message = form.cleaned_data['message']
        year = form.cleaned_data.get('year')
        currency = form.cleaned_data.get('currency')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        
        # Convertir fechas a string si existen
        if date_from:
            date_from = date_from.strftime('%Y-%m-%d')
        if date_to:
            date_to = date_to.strftime('%Y-%m-%d')
        
        # Llamar al servicio de SQL chat
        response = run_sql_chat(
            message=message,
            user_id=str(self.request.user.pk),
            year=year,
            currency=currency or None,
            date_from=date_from,
            date_to=date_to
        )
        
        # Preparar contexto para renderizar respuesta
        context = self.get_context_data(form=form)
        context['response'] = response
        
        if response.get('ok'):
            # Respuesta exitosa
            context['has_error'] = False
            context['sql'] = response.get('sql', '')
            context['columns'] = response.get('columns', [])
            context['rows'] = response.get('rows', [])
            context['rowcount'] = response.get('rowcount', 0)
            context['meta'] = response.get('meta', {})
        else:
            # Error en la respuesta
            context['has_error'] = True
            context['error_reason'] = response.get('reason', 'Error desconocido')
            context['error_details'] = response.get('details', {})
        
        return self.render_to_response(context)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def ingest(request):
    """
    API endpoint para ingesta de datos financieros desde fuentes externas.
    
    Requiere autenticación mediante API key en header X-API-KEY.
    
    Formato esperado:
    [
        {
            "idempotency_key": "unique_key_123",
            "source_table": "ventas",
            "entry_type": "sale",
            "date": "2024-01-15",
            "currency": "ARS",
            "net_amount": "1000.00",
            "tax_amount": "210.00",
            "total_amount": "1210.00",
            "cost_center": "VENTAS",
            "counterparty_id": "CLI001",
            "source_id": "VTA001",
            "source_updated_at": "2024-01-15T10:30:00Z"
        }
    ]
    
    Respuesta:
    {
        "accepted": 10,
        "duplicates": 2,
        "errors": []
    }
    """
    # Verificar API key
    api_key = request.headers.get('X-API-KEY', '')
    expected_key = getattr(settings, 'INGEST_API_KEY', '')
    
    if not expected_key or api_key != expected_key:
        return JsonResponse(
            {'detail': 'unauthorized', 'message': 'Invalid or missing API key'},
            status=401
        )
    
    # Verificar método
    if request.method != 'POST':
        return JsonResponse(
            {'detail': 'Method not allowed', 'message': 'Only POST is allowed'},
            status=405
        )
    
    # Parsear JSON
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {'detail': 'Invalid JSON', 'message': 'Request body must be valid JSON'},
            status=400
        )
    
    # Verificar que sea un array
    if not isinstance(data, list):
        return JsonResponse(
            {'detail': 'Expected array of objects', 'message': 'Request body must be an array'},
            status=400
        )
    
    # Procesar entradas
    accepted = 0
    duplicates = 0
    errors = []
    
    for idx, entry in enumerate(data):
        try:
            # Validar campos requeridos
            required_fields = [
                'idempotency_key', 'source_table', 'entry_type', 'date',
                'net_amount', 'tax_amount', 'total_amount', 'source_id', 'source_updated_at'
            ]
            
            missing_fields = [field for field in required_fields if field not in entry]
            if missing_fields:
                errors.append({
                    'index': idx,
                    'idempotency_key': entry.get('idempotency_key', 'unknown'),
                    'error': f"Missing required fields: {', '.join(missing_fields)}"
                })
                continue
            
            # Verificar si ya existe (idempotencia)
            if FinancialEntry.objects.filter(idempotency_key=entry['idempotency_key']).exists():
                duplicates += 1
                continue
            
            # Parsear fecha
            try:
                date_obj = datetime.strptime(entry['date'], '%Y-%m-%d').date()
            except ValueError:
                errors.append({
                    'index': idx,
                    'idempotency_key': entry['idempotency_key'],
                    'error': f"Invalid date format: {entry['date']}"
                })
                continue
            
            # Parsear timestamp
            try:
                source_updated_at = datetime.fromisoformat(entry['source_updated_at'].replace('Z', '+00:00'))
            except ValueError:
                errors.append({
                    'index': idx,
                    'idempotency_key': entry['idempotency_key'],
                    'error': f"Invalid timestamp format: {entry['source_updated_at']}"
                })
                continue
            
            # Crear entrada
            FinancialEntry.objects.create(
                idempotency_key=entry['idempotency_key'],
                source_table=entry['source_table'],
                entry_type=entry['entry_type'],
                date=date_obj,
                currency=entry.get('currency', 'ARS'),
                net_amount=Decimal(str(entry['net_amount'])),
                tax_amount=Decimal(str(entry['tax_amount'])),
                total_amount=Decimal(str(entry['total_amount'])),
                cost_center=entry.get('cost_center'),
                counterparty_id=entry.get('counterparty_id'),
                source_id=entry['source_id'],
                source_updated_at=source_updated_at
            )
            
            accepted += 1
            
        except Exception as e:
            errors.append({
                'index': idx,
                'idempotency_key': entry.get('idempotency_key', 'unknown'),
                'error': str(e)
            })
    
    return JsonResponse({
        'accepted': accepted,
        'duplicates': duplicates,
        'errors': errors
    }, status=200)


@require_http_methods(["GET"])
def monthly_report(request):
    """
    API endpoint para obtener reporte financiero mensual.
    
    Parámetros de query:
        - year: Año (requerido, ej: 2024)
        - currency: Moneda (opcional, default: ARS)
    
    Respuesta:
    [
        {
            "month": "2024-01",
            "income": "10000.00",
            "cost": "5000.00",
            "margin": "5000.00"
        },
        ...
    ]
    """
    # Obtener parámetros
    try:
        year = int(request.GET.get('year', ''))
    except (ValueError, TypeError):
        return JsonResponse(
            {'detail': 'Invalid year', 'message': 'Year parameter is required and must be a valid integer'},
            status=400
        )
    
    currency = request.GET.get('currency', 'ARS')
    
    # Obtener datos
    try:
        data = get_monthly_financial_summary(year=year, currency=currency)
        
        # Convertir Decimal a string para JSON
        result = []
        for item in data:
            result.append({
                'month': item['month'],
                'income': str(item['income']),
                'cost': str(item['cost']),
                'margin': str(item['margin'])
            })
        
        return JsonResponse(result, safe=False, status=200)
        
    except ValueError as e:
        return JsonResponse(
            {'detail': 'Invalid parameters', 'message': str(e)},
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'detail': 'Internal error', 'message': str(e)},
            status=500
        )


@csrf_exempt
@require_http_methods(["POST"])
def sql_chat(request):
    """
    API endpoint para chat SQL de IA (versión JSON).
    
    Formato esperado:
    {
        "message": "Muéstrame las ventas del último mes",
        "user_id": "user_123",
        "year": 2024,
        "currency": "ARS",
        "date_from": "2024-01-01",
        "date_to": "2024-12-31"
    }
    
    Respuesta:
    {
        "ok": true,
        "sql": "SELECT ...",
        "columns": ["col1", "col2"],
        "rows": [[val1, val2], ...],
        "rowcount": 10,
        "meta": {...}
    }
    """
    # Parsear JSON
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {'ok': False, 'reason': 'Invalid JSON', 'details': {}},
            status=400
        )
    
    # Validar campos requeridos
    message = data.get('message')
    user_id = data.get('user_id')
    
    if not message:
        return JsonResponse(
            {'ok': False, 'reason': 'Missing required field: message', 'details': {}},
            status=400
        )
    
    if not user_id:
        return JsonResponse(
            {'ok': False, 'reason': 'Missing required field: user_id', 'details': {}},
            status=400
        )
    
    # Extraer parámetros opcionales
    year = data.get('year')
    currency = data.get('currency')
    date_from = data.get('date_from')
    date_to = data.get('date_to')
    
    # Llamar al servicio
    try:
        response = run_sql_chat(
            message=message,
            user_id=user_id,
            year=year,
            currency=currency,
            date_from=date_from,
            date_to=date_to
        )
        
        return JsonResponse(response, status=200)
        
    except Exception as e:
        return JsonResponse(
            {'ok': False, 'reason': f'Internal error: {str(e)}', 'details': {}},
            status=500
        ) 