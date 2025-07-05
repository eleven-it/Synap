from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from core.models import Empresa, Branch

User = get_user_model()


class ApprovalWorkflow(models.Model):
    """
    Modelo para definir workflows de aprobación configurables
    Permite crear flujos de aprobación personalizados por empresa
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='approval_workflows', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='approval_workflows', verbose_name=_('Branch'))
    
    name = models.CharField(_("Name"), max_length=100, help_text=_("e.g., Standard Purchase Approval, High Value Approval"))
    description = models.TextField(_("Description"), blank=True)
    
    # Configuración del workflow
    is_active = models.BooleanField(_("Active"), default=True)
    requires_all_approvals = models.BooleanField(_("Requires All Approvals"), default=True, 
                                               help_text=_("If True, all levels must approve. If False, any level can approve."))
    
    # Configuración de montos
    min_amount = models.DecimalField(_("Minimum Amount"), max_digits=15, decimal_places=2, default=0,
                                   help_text=_("Minimum amount to trigger this workflow"))
    max_amount = models.DecimalField(_("Maximum Amount"), max_digits=15, decimal_places=2, null=True, blank=True,
                                   help_text=_("Maximum amount for this workflow (null = no limit)"))
    
    # Auditoría
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_workflows', verbose_name=_("Created By"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Approval Workflow")
        verbose_name_plural = _("Approval Workflows")
        ordering = ['min_amount']
        unique_together = [['empresa', 'name']]
    
    def __str__(self):
        return f"{self.name} ({self.empresa})"
    
    def get_levels(self):
        """Retorna los niveles de aprobación ordenados por prioridad"""
        return self.levels.filter(is_active=True).order_by('priority')
    
    def can_approve_amount(self, amount):
        """Verifica si el workflow aplica para el monto especificado"""
        if amount < self.min_amount:
            return False
        if self.max_amount and amount > self.max_amount:
            return False
        return True
    
    def get_next_approval_level(self, current_level=None):
        """Retorna el siguiente nivel de aprobación"""
        levels = self.get_levels()
        if current_level is None:
            return levels.first()
        
        current_priority = current_level.priority
        return levels.filter(priority__gt=current_priority).first()


class ApprovalLevel(models.Model):
    """
    Modelo para definir niveles específicos dentro de un workflow de aprobación
    """
    workflow = models.ForeignKey(ApprovalWorkflow, on_delete=models.CASCADE, related_name='levels', verbose_name=_("Workflow"))
    
    name = models.CharField(_("Level Name"), max_length=100, help_text=_("e.g., Supervisor, Manager, Director"))
    priority = models.PositiveIntegerField(_("Priority"), help_text=_("Lower number = higher priority"))
    
    # Configuración de aprobadores
    approval_type = models.CharField(_("Approval Type"), max_length=20, choices=[
        ('role', _('Role Based')),
        ('user', _('Specific User')),
        ('group', _('User Group')),
        ('any_role', _('Any Role')),
    ], default='role')
    
    # Aprobadores específicos (se usa según approval_type)
    approvers = models.ManyToManyField(User, blank=True, related_name='approval_levels', verbose_name=_("Approvers"))
    roles = models.JSONField(_("Roles"), default=list, blank=True, help_text=_("List of role IDs that can approve"))
    groups = models.JSONField(_("Groups"), default=list, blank=True, help_text=_("List of group IDs that can approve"))
    
    # Configuración del nivel
    is_active = models.BooleanField(_("Active"), default=True)
    requires_all_approvers = models.BooleanField(_("Requires All Approvers"), default=False,
                                               help_text=_("If True, all approvers must approve. If False, any approver can approve."))
    
    # Configuración de tiempo
    max_approval_time = models.PositiveIntegerField(_("Max Approval Time (hours)"), null=True, blank=True,
                                                  help_text=_("Maximum time allowed for approval (null = no limit)"))
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Approval Level")
        verbose_name_plural = _("Approval Levels")
        ordering = ['workflow', 'priority']
        unique_together = [['workflow', 'priority']]
    
    def __str__(self):
        return f"{self.workflow.name} - {self.name} (Priority: {self.priority})"
    
    def can_user_approve(self, user):
        """Verifica si un usuario puede aprobar en este nivel"""
        if not self.is_active:
            return False
        
        if self.approval_type == 'user':
            return user in self.approvers.all()
        
        elif self.approval_type == 'role':
            # Verificar si el usuario tiene alguno de los roles especificados
            user_roles = user.roles.filter(id__in=self.roles).exists()
            return user_roles
        
        elif self.approval_type == 'group':
            # Verificar si el usuario pertenece a alguno de los grupos especificados
            user_groups = user.groups.filter(id__in=self.groups).exists()
            return user_groups
        
        elif self.approval_type == 'any_role':
            # Cualquier usuario con roles puede aprobar
            return user.roles.exists()
        
        return False
    
    def get_available_approvers(self):
        """Retorna la lista de usuarios que pueden aprobar en este nivel"""
        if self.approval_type == 'user':
            return self.approvers.all()
        
        elif self.approval_type == 'role':
            from core.models import UsuarioExtendido
            return UsuarioExtendido.objects.filter(roles__id__in=self.roles).distinct()
        
        elif self.approval_type == 'group':
            return User.objects.filter(groups__id__in=self.groups).distinct()
        
        elif self.approval_type == 'any_role':
            from core.models import UsuarioExtendido
            return UsuarioExtendido.objects.filter(roles__isnull=False).distinct()
        
        return User.objects.none()


class ApprovalRequest(models.Model):
    """
    Modelo para registrar solicitudes de aprobación específicas
    """
    # Referencia genérica al objeto que requiere aprobación
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    workflow = models.ForeignKey(ApprovalWorkflow, on_delete=models.CASCADE, related_name='approval_requests', verbose_name=_("Workflow"))
    current_level = models.ForeignKey(ApprovalLevel, on_delete=models.CASCADE, related_name='current_approval_requests', verbose_name=_("Current Level"))
    
    # Estado de la aprobación
    status = models.CharField(_("Status"), max_length=20, choices=[
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('cancelled', _('Cancelled')),
        ('expired', _('Expired')),
    ], default='pending')
    
    # Información de la solicitud
    amount = models.DecimalField(_("Amount"), max_digits=15, decimal_places=2, help_text=_("Amount requiring approval"))
    currency = models.ForeignKey('core.Currency', on_delete=models.CASCADE, verbose_name=_("Currency"))
    
    # Usuarios involucrados
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requested_approvals', verbose_name=_("Requested By"))
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_requests', verbose_name=_("Approved By"))
    
    # Comentarios y notas
    request_notes = models.TextField(_("Request Notes"), blank=True)
    approval_notes = models.TextField(_("Approval Notes"), blank=True)
    rejection_reason = models.TextField(_("Rejection Reason"), blank=True)
    
    # Fechas
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _("Approval Request")
        verbose_name_plural = _("Approval Requests")
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['status', 'requested_at']),
        ]
    
    def __str__(self):
        return f"Approval Request {self.id} - {self.content_object} ({self.status})"
    
    def approve(self, user, notes=""):
        """Aprueba la solicitud"""
        from django.utils import timezone
        
        self.status = 'approved'
        self.approved_by = user
        self.approval_notes = notes
        self.approved_at = timezone.now()
        self.save()
        
        # Crear siguiente nivel de aprobación si existe
        next_level = self.workflow.get_next_approval_level(self.current_level)
        if next_level:
            ApprovalRequest.objects.create(
                content_type=self.content_type,
                object_id=self.object_id,
                workflow=self.workflow,
                current_level=next_level,
                amount=self.amount,
                currency=self.currency,
                requested_by=self.requested_by,
                request_notes=self.request_notes,
                expires_at=self._calculate_expiry_date(next_level)
            )
    
    def reject(self, user, reason=""):
        """Rechaza la solicitud"""
        from django.utils import timezone
        
        self.status = 'rejected'
        self.approved_by = user
        self.rejection_reason = reason
        self.approved_at = timezone.now()
        self.save()
    
    def cancel(self, user):
        """Cancela la solicitud"""
        from django.utils import timezone
        
        self.status = 'cancelled'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()
    
    def _calculate_expiry_date(self, level):
        """Calcula la fecha de expiración basada en la configuración del nivel"""
        if not level.max_approval_time:
            return None
        
        from django.utils import timezone
        from datetime import timedelta
        
        return timezone.now() + timedelta(hours=level.max_approval_time)
    
    def is_expired(self):
        """Verifica si la solicitud ha expirado"""
        if not self.expires_at:
            return False
        
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def get_available_approvers(self):
        """Retorna los usuarios que pueden aprobar esta solicitud"""
        return self.current_level.get_available_approvers() 