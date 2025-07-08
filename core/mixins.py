from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy as _


class ContactableMixin(models.Model):
    """
    Mixin para agregar funcionalidad de contactos a cualquier modelo
    Similar al comportamiento de Odoo v18
    """
    
    # Relación genérica con contactos
    contact_relationships = GenericRelation(
        'core.ContactRelationship',
        content_type_field='content_type',
        object_id_field='object_id',
        verbose_name=_('Contact Relationships')
    )
    
    class Meta:
        abstract = True
    
    def get_contacts(self, relationship_type=None, active_only=True):
        """
        Obtiene los contactos relacionados con esta entidad
        """
        queryset = self.contact_relationships.all()
        
        if relationship_type:
            queryset = queryset.filter(relationship_type=relationship_type)
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        return queryset.select_related('contact').order_by('relationship_type', 'contact__name')
    
    def get_primary_contact(self):
        """
        Obtiene el contacto principal
        """
        try:
            return self.contact_relationships.filter(
                relationship_type='primary',
                is_active=True
            ).select_related('contact').first()
        except:
            return None
    
    def get_primary_contact_object(self):
        """
        Obtiene el objeto Contact del contacto principal
        """
        relationship = self.get_primary_contact()
        return relationship.contact if relationship else None
    
    def add_contact(self, contact, relationship_type='secondary', **kwargs):
        """
        Agrega un contacto a esta entidad
        """
        from .models import ContactRelationship
        
        content_type = ContentType.objects.get_for_model(self)
        
        relationship, created = ContactRelationship.objects.get_or_create(
            contact=contact,
            content_type=content_type,
            object_id=self.pk,
            relationship_type=relationship_type,
            defaults=kwargs
        )
        
        return relationship
    
    def remove_contact(self, contact, relationship_type=None):
        """
        Remueve un contacto de esta entidad
        """
        from .models import ContactRelationship
        
        content_type = ContentType.objects.get_for_model(self)
        queryset = ContactRelationship.objects.filter(
            contact=contact,
            content_type=content_type,
            object_id=self.pk
        )
        
        if relationship_type:
            queryset = queryset.filter(relationship_type=relationship_type)
        
        return queryset.delete()
    
    def has_contact(self, contact, relationship_type=None):
        """
        Verifica si un contacto está relacionado con esta entidad
        """
        from .models import ContactRelationship
        
        content_type = ContentType.objects.get_for_model(self)
        queryset = ContactRelationship.objects.filter(
            contact=contact,
            content_type=content_type,
            object_id=self.pk,
            is_active=True
        )
        
        if relationship_type:
            queryset = queryset.filter(relationship_type=relationship_type)
        
        return queryset.exists()
    
    @property
    def contacts_count(self):
        """
        Retorna el número de contactos activos
        """
        return self.contact_relationships.filter(is_active=True).count()
    
    @property
    def has_contacts(self):
        """
        Verifica si tiene contactos
        """
        return self.contacts_count > 0 