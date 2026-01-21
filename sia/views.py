"""
Vistas para el módulo Strategic Insights & Alignment (SIA)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView, View
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Min, Max, Count, StdDev, Q
from django.http import HttpResponse, Http404
from django.utils.text import slugify
import logging
from sia.services import DashboardDataService, generate_cycle_report_pdf, generate_cycle_report_excel
from sia.permissions import (
    SiaPermissionRequiredMixin,
    SiaEmpresaFilterMixin,
    SiaResponseVisibilityMixin,
    get_user_empresa,
    has_sia_permission,
    SIA_PERMISSIONS,
)
from django.utils.translation import gettext_lazy as _
from sia.models import (
    Department,
    EvaluationCycle,
    StrategicSurveyResponse,
    FodaItem,
    Rating,
    OpenAnswer,
    CameAction,
)
from sia.forms import (
    DepartmentForm,
    EvaluationCycleForm,
    StrategicSurveyResponseForm,
    CameActionForm,
    FodaItemFormSet,
    RatingFormSet,
    OpenAnswerFormSet,
)
from core.models import Empresa


class EvaluationCycleListView(SiaPermissionRequiredMixin, SiaEmpresaFilterMixin, ListView):
    """Lista de ciclos de evaluación."""
    model = EvaluationCycle
    template_name = 'sia/evaluation_cycle_list.html'
    context_object_name = 'cycles'
    paginate_by = 20
    permission_required = SIA_PERMISSIONS['can_manage_cycles']
    empresa_field = 'empresa'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related('empresa', 'created_by').order_by('-start_date')


class EvaluationCycleCreateView(SiaPermissionRequiredMixin, CreateView):
    """Crear un nuevo ciclo de evaluación."""
    model = EvaluationCycle
    form_class = EvaluationCycleForm
    template_name = 'sia/evaluation_cycle_form.html'
    permission_required = SIA_PERMISSIONS['can_manage_cycles']
    
    def get_context_data(self, **kwargs):
        """Agregar empresa al contexto para mostrarla como dato de solo lectura"""
        context = super().get_context_data(**kwargs)
        empresa = self.get_empresa()
        context['empresa'] = empresa
        return context
    
    def form_valid(self, form):
        """Asignar empresa automáticamente desde el contexto del usuario"""
        from core.models import UsuarioExtendido
        
        empresa = self.get_empresa()
        if not empresa:
            messages.error(self.request, 'No se pudo determinar la empresa asociada. Por favor, contacta al administrador.')
            return self.form_invalid(form)
        
        # Asignar empresa automáticamente
        form.instance.empresa = empresa
        
        # Asignar creador: solo si request.user es una instancia de UsuarioExtendido
        # Si es AdministraNETUser (mock), dejamos created_by como None
        if isinstance(self.request.user, UsuarioExtendido):
            form.instance.created_by = self.request.user
        else:
            # Intentar obtener UsuarioExtendido desde la sesión si es posible
            session_user = self.request.session.get('user', {})
            cod_usuario = session_user.get('cod_usuario')
            id_usuario = session_user.get('id_usuario')
            
            # Buscar UsuarioExtendido por uid (podría ser cod_usuario o id_usuario como string)
            usuario_extendido = None
            if cod_usuario:
                try:
                    # Intentar buscar por uid si coincide con cod_usuario
                    usuario_extendido = UsuarioExtendido.objects.filter(uid=str(cod_usuario)).first()
                except Exception:
                    pass
            
            # Si no se encontró, dejar como None (el campo permite null)
            form.instance.created_by = usuario_extendido
        
        messages.success(self.request, 'Ciclo de evaluación creado exitosamente.')
        return super().form_valid(form)
    
    def get_success_url(self):
        from django.urls import reverse
        return reverse('sia:evaluation_cycle_list')


class EvaluationCycleUpdateView(SiaPermissionRequiredMixin, UpdateView):
    """Editar un ciclo de evaluación."""
    model = EvaluationCycle
    form_class = EvaluationCycleForm
    template_name = 'sia/evaluation_cycle_form.html'
    permission_required = SIA_PERMISSIONS['can_manage_cycles']
    
    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        queryset = super().get_queryset()
        empresa = self.get_empresa()
        if empresa:
            queryset = queryset.filter(empresa=empresa)
        return queryset
    
    def get_context_data(self, **kwargs):
        """Agregar empresa al contexto para mostrarla como dato de solo lectura"""
        context = super().get_context_data(**kwargs)
        empresa = self.get_empresa()
        context['empresa'] = empresa
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Ciclo de evaluación actualizado exitosamente.')
        return super().form_valid(form)
    
    def get_success_url(self):
        from django.urls import reverse
        return reverse('sia:evaluation_cycle_list')


class EvaluationCycleDetailView(SiaPermissionRequiredMixin, DetailView):
    """Detalle de un ciclo de evaluación con dashboard."""
    model = EvaluationCycle
    template_name = 'sia/evaluation_cycle_detail.html'
    context_object_name = 'cycle'
    permission_required = SIA_PERMISSIONS['can_view_company_dashboard']
    
    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        queryset = super().get_queryset()
        empresa = self.get_empresa()
        if empresa:
            queryset = queryset.filter(empresa=empresa)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cycle = self.get_object()
        empresa = self.get_empresa()
        
        # Verificar que el ciclo pertenezca a la empresa del usuario
        if empresa and cycle.empresa != empresa:
            raise PermissionDenied(_("No tienes acceso a este ciclo de evaluación."))
        
        # Estadísticas de respuestas (solo de la empresa)
        responses = StrategicSurveyResponse.objects.filter(
            evaluation_cycle=cycle,
            evaluation_cycle__empresa=empresa,
            status='submitted'
        )
        context['total_responses'] = responses.count()
        context['total_users'] = responses.values('user').distinct().count()
        
        # FODA consolidado
        foda_consolidated = {}
        for quadrant in ['strength', 'weakness', 'opportunity', 'threat']:
            items = FodaItem.objects.filter(
                survey_response__evaluation_cycle=cycle,
                survey_response__evaluation_cycle__empresa=empresa,
                survey_response__status='submitted',
                quadrant=quadrant
            ).values('description').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            foda_consolidated[quadrant] = list(items)
        context['foda_consolidated'] = foda_consolidated
        
        # Ratings consolidados
        ratings = Rating.objects.filter(
            survey_response__evaluation_cycle=cycle,
            survey_response__evaluation_cycle__empresa=empresa,
            survey_response__status='submitted'
        ).values('dimension').annotate(
            average=Avg('value'),
            min_value=Count('value'),
            max_value=Count('value'),
            count=Count('id')
        )
        context['ratings_consolidated'] = list(ratings)
        
        # Acciones CAME
        came_actions = CameAction.objects.filter(evaluation_cycle=cycle)
        context['came_actions'] = came_actions
        
        return context


class StrategicSurveyResponseCreateView(SiaPermissionRequiredMixin, CreateView):
    """Crear una nueva respuesta de encuesta estratégica."""
    model = StrategicSurveyResponse
    form_class = StrategicSurveyResponseForm
    template_name = 'sia/survey_response_form.html'
    permission_required = SIA_PERMISSIONS['can_create_response']
    
    def get_form_kwargs(self):
        """Pasar usuario, empresa y ciclo de evaluación al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user if hasattr(self.request.user, 'id') else None
        kwargs['empresa'] = self.get_empresa()
        
        # Obtener ciclo de evaluación desde GET param o ciclo activo
        empresa = kwargs['empresa']
        cycle_id = self.request.GET.get('cycle', None)
        evaluation_cycle = None
        
        if cycle_id and empresa:
            try:
                evaluation_cycle = EvaluationCycle.objects.get(id=cycle_id, empresa=empresa, is_active=True)
            except EvaluationCycle.DoesNotExist:
                pass
        
        # Si no hay ciclo desde GET, usar el ciclo activo más reciente
        if not evaluation_cycle and empresa:
            evaluation_cycle = EvaluationCycle.objects.filter(
                empresa=empresa,
                is_active=True
            ).order_by('-start_date').first()
        
        kwargs['evaluation_cycle'] = evaluation_cycle
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Agregar evaluation_cycle al contexto para mostrarlo como solo lectura
        form_kwargs = self.get_form_kwargs()
        evaluation_cycle = form_kwargs.get('evaluation_cycle')
        context['evaluation_cycle'] = evaluation_cycle
        
        # Obtener instance si existe (para edición) o None (para creación)
        instance = self.object if hasattr(self, 'object') and self.object else None
        
        if self.request.method == 'POST':
            context['foda_formset'] = FodaItemFormSet(self.request.POST, instance=instance)
            context['rating_formset'] = RatingFormSet(self.request.POST, instance=instance)
            context['open_answer_formset'] = OpenAnswerFormSet(self.request.POST, instance=instance)
        else:
            context['foda_formset'] = FodaItemFormSet(instance=instance)
            context['rating_formset'] = RatingFormSet(instance=instance)
            context['open_answer_formset'] = OpenAnswerFormSet(instance=instance)
        
        return context
    
    def form_valid(self, form):
        # Asignar ciclo de evaluación automáticamente
        form_kwargs = self.get_form_kwargs()
        evaluation_cycle = form_kwargs.get('evaluation_cycle')
        if not evaluation_cycle:
            messages.error(self.request, 'No se pudo determinar el ciclo de evaluación. Por favor, contacta al administrador.')
            return self.form_invalid(form)
        
        form.instance.evaluation_cycle = evaluation_cycle
        
        # Asignar usuario actual
        if hasattr(self.request.user, 'id'):
            form.instance.user = self.request.user
        form.instance.status = 'draft'
        
        # Guardar la respuesta primero para tener el ID
        response = form.save()
        
        # Validar y guardar formsets
        foda_formset = FodaItemFormSet(self.request.POST, instance=response)
        rating_formset = RatingFormSet(self.request.POST, instance=response)
        open_answer_formset = OpenAnswerFormSet(self.request.POST, instance=response)
        
        # Validar todos los formsets
        if foda_formset.is_valid() and rating_formset.is_valid() and open_answer_formset.is_valid():
            foda_formset.save()
            rating_formset.save()
            open_answer_formset.save()
            
            messages.success(self.request, 'Respuesta de encuesta estratégica creada exitosamente.')
            return redirect('sia:survey_response_detail', pk=response.id)
        else:
            # Si hay errores en los formsets, volver a mostrar el formulario con errores
            # Necesitamos reconstruir el contexto con los formsets con errores
            context = self.get_context_data(form=form)
            context['foda_formset'] = foda_formset
            context['rating_formset'] = rating_formset
            context['open_answer_formset'] = open_answer_formset
            return self.render_to_response(context)
    
    def get_success_url(self):
        from django.urls import reverse
        return reverse('sia:survey_response_detail', kwargs={'pk': self.object.id})


class StrategicSurveyResponseDetailView(SiaPermissionRequiredMixin, SiaResponseVisibilityMixin, DetailView):
    """Detalle de una respuesta de encuesta."""
    model = StrategicSurveyResponse
    template_name = 'sia/survey_response_detail.html'
    context_object_name = 'response'
    permission_required = SIA_PERMISSIONS['can_view_own_responses']
    
    def get_object(self, queryset=None):
        """Obtener objeto y verificar permisos de visibilidad"""
        obj = super().get_object(queryset)
        empresa = self.get_empresa()
        
        # Verificar que la respuesta pertenezca a la empresa del usuario
        if empresa and obj.evaluation_cycle.empresa != empresa:
            raise PermissionDenied(_("No tienes acceso a esta respuesta."))
        
        # Verificar que el usuario pueda ver esta respuesta
        # (SiaResponseVisibilityMixin ya filtra por empresa y usuario en get_queryset)
        # Pero aquí verificamos explícitamente si no tiene permiso para ver todas
        if not has_sia_permission(self.request.user, SIA_PERMISSIONS['can_view_all_responses']):
            if obj.user != self.request.user:
                raise PermissionDenied(_("Solo puedes ver tus propias respuestas."))
        
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        response = self.get_object()
        
        # Obtener FODA items agrupados por cuadrante
        foda_items = {}
        for quadrant in ['strength', 'weakness', 'opportunity', 'threat']:
            foda_items[quadrant] = response.foda_items.filter(quadrant=quadrant).order_by('priority')
        context['foda_items'] = foda_items
        
        # Obtener ratings
        context['ratings'] = response.ratings.all()
        
        # Obtener open answers
        context['open_answers'] = response.open_answers.all()
        
        return context


# ============================================================================
# VISTAS PARA DEPARTAMENTOS
# ============================================================================

class DepartmentListView(SiaPermissionRequiredMixin, SiaEmpresaFilterMixin, ListView):
    """Lista de departamentos."""
    model = Department
    template_name = 'sia/department_list.html'
    context_object_name = 'departments'
    paginate_by = 20
    permission_required = SIA_PERMISSIONS['can_manage_cycles']  # Usar mismo permiso que ciclos por ahora
    empresa_field = 'empresa'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related('empresa').order_by('name')


class DepartmentCreateView(SiaPermissionRequiredMixin, CreateView):
    """Crear un nuevo departamento."""
    model = Department
    form_class = DepartmentForm
    template_name = 'sia/department_form.html'
    permission_required = SIA_PERMISSIONS['can_manage_cycles']
    
    def get_context_data(self, **kwargs):
        """Agregar empresa al contexto para mostrarla como dato de solo lectura"""
        context = super().get_context_data(**kwargs)
        empresa = self.get_empresa()
        context['empresa'] = empresa
        return context
    
    def form_valid(self, form):
        """Asignar empresa automáticamente desde el contexto del usuario"""
        empresa = self.get_empresa()
        if not empresa:
            messages.error(self.request, 'No se pudo determinar la empresa asociada. Por favor, contacta al administrador.')
            return self.form_invalid(form)
        
        # Asignar empresa automáticamente
        form.instance.empresa = empresa
        
        messages.success(self.request, 'Departamento creado exitosamente.')
        return super().form_valid(form)
    
    def get_success_url(self):
        from django.urls import reverse
        return reverse('sia:department_list')


class DepartmentUpdateView(SiaPermissionRequiredMixin, UpdateView):
    """Editar un departamento."""
    model = Department
    form_class = DepartmentForm
    template_name = 'sia/department_form.html'
    permission_required = SIA_PERMISSIONS['can_manage_cycles']
    
    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        queryset = super().get_queryset()
        empresa = self.get_empresa()
        if empresa:
            queryset = queryset.filter(empresa=empresa)
        return queryset
    
    def get_context_data(self, **kwargs):
        """Agregar empresa al contexto para mostrarla como dato de solo lectura"""
        context = super().get_context_data(**kwargs)
        empresa = self.get_empresa()
        context['empresa'] = empresa
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Departamento actualizado exitosamente.')
        return super().form_valid(form)
    
    def get_success_url(self):
        from django.urls import reverse
        return reverse('sia:department_list')


class DepartmentDeleteView(SiaPermissionRequiredMixin, DeleteView):
    """Eliminar un departamento."""
    model = Department
    template_name = 'sia/department_confirm_delete.html'
    permission_required = SIA_PERMISSIONS['can_manage_cycles']
    
    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        queryset = super().get_queryset()
        empresa = self.get_empresa()
        if empresa:
            queryset = queryset.filter(empresa=empresa)
        return queryset
    
    def get_success_url(self):
        from django.urls import reverse
        return reverse('sia:department_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Departamento eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)


class DashboardView(SiaPermissionRequiredMixin, TemplateView):
    """Dashboard ejecutivo principal con consolidación de datos."""
    template_name = 'sia/dashboard.html'
    permission_required = SIA_PERMISSIONS['can_view_company_dashboard']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener empresa usando el helper centralizado
        empresa = self.get_empresa()
        
        # Obtener ciclo de evaluación (de parámetro GET o el más reciente)
        cycle_id = self.request.GET.get('cycle', None)
        evaluation_cycle = None
        
        if cycle_id and empresa:
            try:
                evaluation_cycle = EvaluationCycle.objects.get(id=cycle_id, empresa=empresa)
            except EvaluationCycle.DoesNotExist:
                pass
        
        if empresa:
            # Ciclos activos
            active_cycles = EvaluationCycle.objects.filter(
                empresa=empresa,
                is_active=True
            ).order_by('-start_date')[:5]
            context['active_cycles'] = active_cycles
            
            # Si no se especificó ciclo, usar el más reciente activo
            if not evaluation_cycle and active_cycles:
                evaluation_cycle = active_cycles.first()
            
            # Resumen de respuestas
            total_responses = StrategicSurveyResponse.objects.filter(
                evaluation_cycle__empresa=empresa,
                status='submitted'
            ).count()
            context['total_responses'] = total_responses
            
            # Acciones CAME pendientes
            pending_actions = CameAction.objects.filter(
                evaluation_cycle__empresa=empresa,
                status__in=['planned', 'in_progress']
            ).count()
            context['pending_actions'] = pending_actions
            
            # Consolidación de datos si hay un ciclo seleccionado
            if evaluation_cycle:
                context['selected_cycle'] = evaluation_cycle
                
                # Usar el servicio para obtener datos consolidados
                consolidated_data = DashboardDataService.get_consolidated_data(
                    empresa_id=empresa.id if empresa else None,
                    cycle_id=evaluation_cycle.id
                )
                
                context['ratings_stats'] = consolidated_data['ratings']
                context['foda_stats'] = consolidated_data['foda']
                context['cycle_responses'] = consolidated_data['total_responses']
        
        return context


class CyclePdfReportView(SiaPermissionRequiredMixin, View):
    """
    Vista para exportar el PDF ejecutivo de un ciclo de evaluación SIA.
    
    Requiere el permiso 'sia.view_company_dashboard' y valida que el ciclo
    pertenezca a la empresa del usuario autenticado.
    """
    permission_required = SIA_PERMISSIONS['can_view_company_dashboard']
    
    def get(self, request, pk):
        """Genera y devuelve el PDF del ciclo especificado."""
        # Obtener empresa del usuario
        empresa = self.get_empresa()
        if not empresa:
            raise PermissionDenied("No se pudo determinar la empresa asociada.")
        
        # Obtener ciclo de evaluación
        try:
            evaluation_cycle = EvaluationCycle.objects.select_related('empresa').get(
                id=pk,
                empresa=empresa,
                is_active=True
            )
        except EvaluationCycle.DoesNotExist:
            raise Http404("El ciclo de evaluación no existe o no pertenece a tu empresa.")
        
        # Generar PDF
        try:
            pdf_bytes = generate_cycle_report_pdf(empresa, evaluation_cycle)
        except ValueError as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error al validar ciclo para PDF: {e}")
            raise PermissionDenied(str(e))
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception(f"Error al generar PDF del ciclo {pk}: {e}")
            raise
        
        # Crear nombre de archivo sanitizado
        cycle_name_sanitized = slugify(evaluation_cycle.name)
        empresa_slug = slugify(empresa.nombre)
        filename = f"SIA_{empresa_slug}_{cycle_name_sanitized}.pdf"
        
        # Crear respuesta HTTP con el PDF
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response


class CycleExcelReportView(SiaPermissionRequiredMixin, View):
    """
    Vista para exportar el archivo Excel analítico de un ciclo de evaluación SIA.
    
    Requiere el permiso 'sia.view_company_dashboard' y valida que el ciclo
    pertenezca a la empresa del usuario autenticado.
    
    El Excel generado contiene 5 hojas:
    - Resumen: Métricas consolidadas por dimensión
    - Ratings: Datos detallados de cada rating
    - FODA: Elementos FODA individuales
    - Preguntas Abiertas: Respuestas a preguntas abiertas
    - CAME: Acciones CAME del ciclo
    """
    permission_required = SIA_PERMISSIONS['can_view_company_dashboard']
    
    def get(self, request, pk):
        """Genera y devuelve el Excel del ciclo especificado."""
        # Obtener empresa del usuario
        empresa = self.get_empresa()
        if not empresa:
            raise PermissionDenied("No se pudo determinar la empresa asociada.")
        
        # Obtener ciclo de evaluación
        try:
            evaluation_cycle = EvaluationCycle.objects.select_related('empresa').get(
                id=pk,
                empresa=empresa,
                is_active=True
            )
        except EvaluationCycle.DoesNotExist:
            raise Http404("El ciclo de evaluación no existe o no pertenece a tu empresa.")
        
        # Generar Excel
        try:
            excel_bytes = generate_cycle_report_excel(empresa, evaluation_cycle)
        except ValueError as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error al validar ciclo para Excel: {e}")
            raise PermissionDenied(str(e))
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception(f"Error al generar Excel del ciclo {pk}: {e}")
            raise
        
        # Crear nombre de archivo sanitizado
        cycle_name_sanitized = slugify(evaluation_cycle.name)
        empresa_slug = slugify(empresa.nombre)
        filename = f"SIA_{empresa_slug}_{cycle_name_sanitized}.xlsx"
        
        # Crear respuesta HTTP con el Excel
        response = HttpResponse(
            excel_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response

