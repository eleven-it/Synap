from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .purchase_request import PurchaseRequest
from .approval_workflow import ApprovalLevel
from django.conf import settings

User = get_user_model()


class ApprovalRecord(models.Model):
    """
    Modelo para registrar las acciones de aprobación en los flujos de aprobación
    Mantiene un historial completo de todas las acciones de aprobación
    """
    # Relación con la solicitud y nivel
    request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name='approval_records', verbose_name=_("Request"))
    level = models.ForeignKey(ApprovalLevel, on_delete=models.CASCADE, related_name='approval_records', verbose_name=_("Approval Level"))
    
    # Usuario que realizó la acción
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approval_actions', verbose_name=_("Approver"))
    
    # Acción realizada
    action = models.CharField(_("Action"), max_length=20, choices=[
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('timeout', _('Timeout')),
        ('delegated', _('Delegated')),
        ('returned', _('Returned for Revision')),
    ])
    
    # Comentarios de la acción
    comments = models.TextField(_("Comments"), blank=True)
    
    # Fecha y hora de la acción
    approved_at = models.DateTimeField(_("Action Date"), auto_now_add=True)
    
    # Información adicional
    ip_address = models.GenericIPAddressField(_("IP Address"), null=True, blank=True)
    user_agent = models.TextField(_("User Agent"), blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Approval Record")
        verbose_name_plural = _("Approval Records")
        ordering = ['-approved_at']
        indexes = [
            models.Index(fields=['request', 'level']),
            models.Index(fields=['approver', 'action']),
            models.Index(fields=['approved_at']),
        ]
    
    def __str__(self):
        return f"{self.request.request_number} - {self.level.name} - {self.get_action_display()} by {self.approver or 'System'}"
    
    @property
    def is_positive_action(self):
        """Verifica si la acción es positiva (aprobación)"""
        return self.action == 'approved'
    
    @property
    def is_negative_action(self):
        """Verifica si la acción es negativa (rechazo, timeout)"""
        return self.action in ['rejected', 'timeout']
    
    @property
    def action_color(self):
        """Retorna el color CSS para la acción"""
        colors = {
            'approved': 'text-green-600',
            'rejected': 'text-red-600',
            'timeout': 'text-orange-600',
            'delegated': 'text-blue-600',
            'returned': 'text-yellow-600'
        }
        return colors.get(self.action, 'text-gray-600')
    
    @property
    def action_icon(self):
        """Retorna el ícono para la acción"""
        icons = {
            'approved': '✅',
            'rejected': '❌',
            'timeout': '⏰',
            'delegated': '👥',
            'returned': '↩️'
        }
        return icons.get(self.action, '❓')
    
    def get_duration_from_start(self):
        """Calcula la duración desde el inicio del nivel de aprobación"""
        if not self.request.approval_started_at:
            return None
        
        duration = self.approved_at - self.request.approval_started_at
        return duration
    
    def get_duration_hours(self):
        """Retorna la duración en horas"""
        duration = self.get_duration_from_start()
        if duration:
            return duration.total_seconds() / 3600
        return 0
    
    def is_within_timeout(self):
        """Verifica si la acción fue realizada dentro del timeout del nivel"""
        if not self.level.timeout_hours:
            return True
        
        duration_hours = self.get_duration_hours()
        return duration_hours <= self.level.timeout_hours 