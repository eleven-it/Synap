from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import List, Dict, Any, Optional
from django.contrib.contenttypes.models import ContentType

from ..models import ApprovalWorkflow, ApprovalLevel, PurchaseRequest, PurchaseOrder, ApprovalRequest

User = get_user_model()


class ApprovalService:
    """
    Servicio para gestionar flujos de aprobación de compras
    """
    
    def __init__(self):
        self.user = None
    
    def set_user(self, user: User):
        """Establece el usuario para las operaciones"""
        self.user = user
        return self
    
    def create_approval_workflow(
        self,
        empresa,
        name: str,
        description: str = "",
        min_amount: float = 0,
        max_amount: float = 999999999,
        levels_data: List[Dict] = None
    ) -> ApprovalWorkflow:
        """
        Crea un nuevo flujo de aprobación con niveles
        """
        with transaction.atomic():
            # Crear el workflow
            workflow = ApprovalWorkflow.objects.create(
                empresa=empresa,
                branch=self.user.branch_activa,  # Agregar branch obligatorio
                name=name,
                description=description,
                min_amount=min_amount,
                max_amount=max_amount,
                is_active=True
            )
            
            # Crear niveles de aprobación
            if levels_data:
                for i, level_data in enumerate(levels_data):
                    self._create_approval_level(workflow, level_data, i + 1)
            
            return workflow
    
    def _create_approval_level(
        self,
        workflow: ApprovalWorkflow,
        level_data: Dict,
        level_number: int
    ) -> ApprovalLevel:
        """Crear un nivel de aprobación"""
        # Solo pasar los campos válidos
        level = ApprovalLevel.objects.create(
            workflow=workflow,
            name=level_data['name'],
            approval_type=level_data['approval_type'],
            priority=level_number  # Campo obligatorio
        )
        # Asignar campos opcionales si existen
        if hasattr(level, 'min_approvals') and 'min_approvals' in level_data:
            level.min_approvals = level_data['min_approvals']
        if hasattr(level, 'auto_approve') and 'auto_approve' in level_data:
            level.auto_approve = level_data['auto_approve']
        if hasattr(level, 'level_number'):
            level.level_number = level_number
        level.save()
        # Asignar aprobadores si se especifican
        if 'approvers' in level_data:
            level.approvers.set(level_data['approvers'])
        return level
    
    def get_applicable_workflow(
        self,
        empresa,
        amount: float,
        category: str = None
    ) -> Optional[ApprovalWorkflow]:
        """
        Obtiene el flujo de aprobación aplicable basado en empresa, monto y categoría
        """
        # Construir filtros base
        filters = {
            'empresa': empresa,
            'is_active': True
        }
        
        # Agregar filtros de monto
        if amount is not None:
            filters['min_amount__lte'] = amount
            filters['max_amount__gte'] = amount
        
        # Filtrar workflows aplicables
        workflows = ApprovalWorkflow.objects.filter(**filters)
        
        # Si se especifica categoría, filtrar por ella también
        if category:
            workflows = workflows.filter(categories__contains=[category])
        
        # Retornar el primer workflow encontrado (ordenado por prioridad)
        return workflows.order_by('min_amount').first()
    
    def initiate_approval_process(self, request):
        """Inicia el proceso de aprobación para una solicitud"""
        if not request.approval_workflow:
            raise ValidationError(_("Request has no approval workflow assigned"))
        
        workflow = request.approval_workflow
        first_level = workflow.levels.filter(priority=1).first()
        
        if not first_level:
            raise ValidationError(_("No approval levels found in workflow"))
        
        # Crear solicitud de aprobación
        approval_request = ApprovalRequest.objects.create(
            content_type=ContentType.objects.get_for_model(PurchaseRequest),
            object_id=request.id,
            workflow=workflow,
            current_level=first_level,
            amount=request.total_amount or request.get_total_amount(),
            currency=request.currency,
            requested_by=request.requested_by,
            expires_at=self._calculate_expiry_date(first_level)
        )
        
        # Actualizar estado de la solicitud
        request.status = 'submitted'
        request.current_approval_level = 1
        request.save()
        
        return approval_request
    
    def _start_approval_level(
        self,
        request: PurchaseRequest,
        level: ApprovalLevel
    ):
        """Inicia un nivel de aprobación"""
        # Marcar nivel como iniciado
        request.current_approval_level = level.level_number
        request.approval_started_at = timezone.now()
        request.save()
        
        # Si es auto-aprobación, aprobar inmediatamente
        if level.auto_approve:
            self._approve_level(request, level, self.user)
    
    def approve_request(
        self,
        request: PurchaseRequest,
        approver: User,
        comments: str = ""
    ) -> Dict[str, Any]:
        """
        Aprueba una solicitud en el nivel actual
        """
        with transaction.atomic():
            if request.status != 'pending_approval':
                raise ValidationError(_("Request is not pending approval"))
            
            # Verificar que tiene un workflow asignado
            if not request.approval_workflow:
                raise ValidationError(_("Request has no approval workflow assigned"))
            
            # Obtener nivel actual
            current_level = request.approval_workflow.levels.filter(
                level_number=request.current_approval_level
            ).first()
            
            if not current_level:
                raise ValidationError(_("No approval level found"))
            
            # Verificar que el usuario puede aprobar
            if not self._can_user_approve(approver, current_level):
                raise ValidationError(_("User cannot approve at this level"))
            
            # Registrar aprobación
            self._approve_level(request, current_level, approver, comments)
            
            # Verificar si se completó el flujo
            if self._is_workflow_completed(request):
                self._complete_approval_process(request, approver)
                return {
                    'status': 'approved',
                    'message': _('Request fully approved'),
                    'next_level': None
                }
            else:
                # Mover al siguiente nivel
                next_level = self._get_next_level(request)
                if next_level:
                    self._start_approval_level(request, next_level)
                    return {
                        'status': 'level_approved',
                        'message': _('Level approved, moving to next level'),
                        'next_level': next_level
                    }
                else:
                    # No hay más niveles, completar
                    self._complete_approval_process(request, approver)
                    return {
                        'status': 'approved',
                        'message': _('Request approved (no more levels)'),
                        'next_level': None
                    }
    
    def _approve_level(
        self,
        request: PurchaseRequest,
        level: ApprovalLevel,
        approver: User,
        comments: str = ""
    ):
        """Registra la aprobación de un nivel"""
        # Crear registro de aprobación
        from ..models import ApprovalRecord
        
        ApprovalRecord.objects.create(
            request=request,
            level=level,
            approver=approver,
            action='approved',
            comments=comments,
            approved_at=timezone.now()
        )
        
        # Actualizar contadores de aprobación
        request.approvals_received += 1
        request.save()
    
    def _can_user_approve(self, user: User, level: ApprovalLevel) -> bool:
        """Verifica si un usuario puede aprobar en un nivel específico"""
        if level.approval_type == 'role':
            return user.groups.filter(name__in=level.approvers).exists()
        elif level.approval_type == 'user':
            return user.username in level.approvers
        elif level.approval_type == 'any':
            return True
        else:
            return False
    
    def _is_workflow_completed(self, request: PurchaseRequest) -> bool:
        """Verifica si se completó todo el flujo de aprobación"""
        current_level = request.approval_workflow.levels.filter(
            level_number=request.current_approval_level
        ).first()
        
        if not current_level:
            return True
        
        # Verificar si se alcanzó el mínimo de aprobaciones
        return request.approvals_received >= current_level.min_approvals
    
    def _get_next_level(self, request: PurchaseRequest) -> Optional[ApprovalLevel]:
        """Obtiene el siguiente nivel de aprobación"""
        return request.approval_workflow.levels.filter(
            level_number=request.current_approval_level + 1
        ).first()
    
    def _complete_approval_process(
        self,
        request: PurchaseRequest,
        final_approver: User
    ):
        """Completa el proceso de aprobación"""
        request.status = 'approved'
        request.approved_by = final_approver
        request.approved_at = timezone.now()
        request.save()
    
    def reject_request(
        self,
        request: PurchaseRequest,
        rejector: User,
        reason: str
    ) -> Dict[str, Any]:
        """
        Rechaza una solicitud de compra
        """
        with transaction.atomic():
            if request.status != 'pending_approval':
                raise ValidationError(_("Request is not pending approval"))
            
            # Obtener nivel actual
            current_level = request.approval_workflow.levels.filter(
                level_number=request.current_approval_level
            ).first()
            
            # Registrar rechazo
            from ..models import ApprovalRecord
            
            ApprovalRecord.objects.create(
                request=request,
                level=current_level,
                approver=rejector,
                action='rejected',
                comments=reason,
                approved_at=timezone.now()
            )
            
            # Marcar como rechazada
            request.status = 'rejected'
            request.rejected_by = rejector
            request.rejected_at = timezone.now()
            request.rejection_reason = reason
            request.save()
            
            return {
                'status': 'rejected',
                'message': _('Request rejected'),
                'reason': reason
            }
    
    def get_pending_approvals(self, user: User, empresa) -> List[Dict[str, Any]]:
        """
        Obtiene las solicitudes pendientes de aprobación para un usuario
        """
        # Obtener flujos donde el usuario puede aprobar
        user_workflows = []
        
        for workflow in ApprovalWorkflow.objects.filter(empresa=empresa, is_active=True):
            for level in workflow.levels.all():
                if self._can_user_approve(user, level):
                    user_workflows.append({
                        'workflow': workflow,
                        'level': level
                    })
        
        # Obtener solicitudes pendientes
        pending_requests = []
        
        for workflow_info in user_workflows:
            workflow = workflow_info['workflow']
            level = workflow_info['level']
            
            requests = PurchaseRequest.objects.filter(
                approval_workflow=workflow,
                current_approval_level=level.level_number,
                status='pending_approval'
            )
            
            for request in requests:
                # Verificar si el usuario ya aprobó
                from ..models import ApprovalRecord
                already_approved = ApprovalRecord.objects.filter(
                    request=request,
                    level=level,
                    approver=user,
                    action='approved'
                ).exists()
                
                if not already_approved:
                    pending_requests.append({
                        'request': request,
                        'workflow': workflow,
                        'level': level,
                        'can_approve': True
                    })
        
        return pending_requests
    
    def get_approval_history(self, request: PurchaseRequest) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de aprobaciones de una solicitud
        """
        from ..models import ApprovalRecord
        
        records = ApprovalRecord.objects.filter(request=request).order_by('approved_at')
        
        history = []
        for record in records:
            history.append({
                'level': record.level,
                'approver': record.approver,
                'action': record.action,
                'comments': record.comments,
                'approved_at': record.approved_at
            })
        
        return history
    
    def check_approval_timeouts(self):
        """
        Verifica y maneja timeouts de aprobaciones
        """
        from ..models import ApprovalRecord
        
        # Obtener solicitudes con timeout
        timeout_requests = []
        
        for request in PurchaseRequest.objects.filter(status='pending_approval'):
            current_level = request.approval_workflow.levels.filter(
                level_number=request.current_approval_level
            ).first()
            
            if current_level and current_level.timeout_hours:
                timeout_threshold = request.approval_started_at + timezone.timedelta(
                    hours=current_level.timeout_hours
                )
                
                if timezone.now() > timeout_threshold:
                    timeout_requests.append({
                        'request': request,
                        'level': current_level,
                        'timeout_threshold': timeout_threshold
                    })
        
        # Manejar timeouts
        for timeout_info in timeout_requests:
            request = timeout_info['request']
            level = timeout_info['level']
            
            # Registrar timeout
            ApprovalRecord.objects.create(
                request=request,
                level=level,
                approver=None,
                action='timeout',
                comments=f"Approval timeout after {level.timeout_hours} hours",
                approved_at=timezone.now()
            )
            
            # Mover al siguiente nivel o rechazar
            next_level = self._get_next_level(request)
            if next_level:
                self._start_approval_level(request, next_level)
            else:
                request.status = 'rejected'
                request.rejection_reason = 'Approval timeout'
                request.save()
    
    def _calculate_expiry_date(self, level):
        return timezone.now() + timezone.timedelta(days=7) 