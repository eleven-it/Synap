from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import List, Dict, Any, Optional

from ..models import ApprovalWorkflow, ApprovalLevel, PurchaseRequest, PurchaseOrder

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
        is_active: bool = True,
        min_amount: float = 0,
        max_amount: float = None,
        categories: List[str] = None,
        levels_data: List[Dict] = None
    ) -> ApprovalWorkflow:
        """
        Crea un nuevo flujo de aprobación
        """
        with transaction.atomic():
            workflow = ApprovalWorkflow.objects.create(
                empresa=empresa,
                name=name,
                description=description,
                is_active=is_active,
                min_amount=min_amount,
                max_amount=max_amount,
                created_by=self.user
            )
            
            # Agregar categorías si se proporcionan
            if categories:
                workflow.categories.set(categories)
            
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
        """Crea un nivel de aprobación"""
        level = ApprovalLevel.objects.create(
            workflow=workflow,
            level_number=level_number,
            name=level_data['name'],
            description=level_data.get('description', ''),
            approval_type=level_data['approval_type'],
            approvers=level_data.get('approvers', []),
            min_approvals=level_data.get('min_approvals', 1),
            auto_approve=level_data.get('auto_approve', False),
            timeout_hours=level_data.get('timeout_hours', 24)
        )
        
        return level
    
    def get_applicable_workflow(
        self,
        empresa,
        amount: float,
        category: str = None
    ) -> Optional[ApprovalWorkflow]:
        """
        Obtiene el flujo de aprobación aplicable para una solicitud
        """
        workflows = ApprovalWorkflow.objects.filter(
            empresa=empresa,
            is_active=True,
            min_amount__lte=amount
        )
        
        if max_amount:
            workflows = workflows.filter(
                models.Q(max_amount__isnull=True) | models.Q(max_amount__gte=amount)
            )
        
        if category:
            workflows = workflows.filter(categories__name=category)
        
        # Retornar el flujo con el monto mínimo más alto que aplique
        return workflows.order_by('-min_amount').first()
    
    def initiate_approval_process(
        self,
        request: PurchaseRequest
    ) -> Dict[str, Any]:
        """
        Inicia el proceso de aprobación para una solicitud de compra
        """
        with transaction.atomic():
            # Obtener flujo aplicable
            workflow = self.get_applicable_workflow(
                empresa=request.empresa,
                amount=request.total_amount,
                category=request.category.name if request.category else None
            )
            
            if not workflow:
                # Sin flujo de aprobación, aprobar automáticamente
                request.status = 'approved'
                request.approved_by = self.user
                request.approved_at = timezone.now()
                request.save()
                
                return {
                    'status': 'auto_approved',
                    'message': _('Request automatically approved (no approval workflow)'),
                    'workflow': None
                }
            
            # Asignar flujo a la solicitud
            request.approval_workflow = workflow
            request.status = 'pending_approval'
            request.current_approval_level = 1
            request.save()
            
            # Iniciar primer nivel de aprobación
            first_level = workflow.levels.filter(level_number=1).first()
            if first_level:
                self._start_approval_level(request, first_level)
            
            return {
                'status': 'pending_approval',
                'message': _('Approval process initiated'),
                'workflow': workflow,
                'current_level': first_level
            }
    
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