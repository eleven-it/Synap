from django.views.generic import CreateView, UpdateView
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .forms import get_contact_inline_formset
from .models import Contact, ContactRelationship


class ContactableCreateView(CreateView):
    """
    Vista base para crear entidades que pueden tener contactos
    """
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['contact_formset'] = get_contact_inline_formset(
                self.model,
                data=self.request.POST,
                files=self.request.FILES,
                prefix='contacts'
            )
        else:
            context['contact_formset'] = get_contact_inline_formset(
                self.model,
                prefix='contacts'
            )
        
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        contact_formset = context['contact_formset']
        
        if contact_formset.is_valid():
            # Guardar la entidad principal
            self.object = form.save()
            
            # Guardar los contactos
            contact_formset.instance = self.object
            contact_formset.save()
            
            messages.success(self.request, _('Entity created successfully with contacts.'))
            return super().form_valid(form)
        else:
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        context = self.get_context_data()
        contact_formset = context['contact_formset']
        
        if not contact_formset.is_valid():
            for error in contact_formset.errors:
                messages.error(self.request, f"Contact error: {error}")
        
        return super().form_invalid(form)


class ContactableUpdateView(UpdateView):
    """
    Vista base para editar entidades que pueden tener contactos
    """
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['contact_formset'] = get_contact_inline_formset(
                self.model,
                instance=self.object,
                data=self.request.POST,
                files=self.request.FILES,
                prefix='contacts'
            )
        else:
            context['contact_formset'] = get_contact_inline_formset(
                self.model,
                instance=self.object,
                prefix='contacts'
            )
        
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        contact_formset = context['contact_formset']
        
        if contact_formset.is_valid():
            # Guardar la entidad principal
            self.object = form.save()
            
            # Guardar los contactos
            contact_formset.instance = self.object
            contact_formset.save()
            
            messages.success(self.request, _('Entity updated successfully with contacts.'))
            return super().form_valid(form)
        else:
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        context = self.get_context_data()
        contact_formset = context['contact_formset']
        
        if not contact_formset.is_valid():
            for error in contact_formset.errors:
                messages.error(self.request, f"Contact error: {error}")
        
        return super().form_invalid(form) 