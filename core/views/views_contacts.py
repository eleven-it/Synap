from django.views.generic import CreateView, UpdateView, ListView, DetailView, DeleteView
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from ..forms import get_contact_inline_formset
from ..models import Contact, ContactRelationship


class ContactListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Vista para listar todos los contactos universales"""
    model = Contact
    template_name = 'core/contacts/contact_list.html'
    context_object_name = 'contacts'
    permission_required = 'core.ver_contact'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Contact.objects.all().order_by('name')
        
        # Filtros
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(company_name__icontains=search)
            )
        
        contact_type = self.request.GET.get('type')
        if contact_type:
            queryset = queryset.filter(type=contact_type)
        
        is_active = self.request.GET.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active == 'true')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_contacts'] = Contact.objects.count()
        context['active_contacts'] = Contact.objects.filter(is_active=True).count()
        context['primary_contacts'] = Contact.objects.filter(is_primary=True).count()
        return context


class ContactCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para crear contactos universales"""
    model = Contact
    template_name = 'core/contacts/contact_form.html'
    permission_required = 'core.crear_contact'
    fields = [
        'name', 'type', 'first_name', 'last_name', 'company_name', 
        'position', 'department', 'email', 'phone', 'mobile', 'fax', 
        'website', 'address', 'postal_code', 'city', 'state', 'country',
        'latitude', 'longitude', 'notes', 'tags', 'photo', 'is_active', 'is_primary'
    ]
    success_url = reverse_lazy('core:contact_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Contact created successfully.'))
        return super().form_valid(form)


class ContactUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para editar contactos universales"""
    model = Contact
    template_name = 'core/contacts/contact_form.html'
    permission_required = 'core.editar_contact'
    fields = [
        'name', 'type', 'first_name', 'last_name', 'company_name', 
        'position', 'department', 'email', 'phone', 'mobile', 'fax', 
        'website', 'address', 'postal_code', 'city', 'state', 'country',
        'latitude', 'longitude', 'notes', 'tags', 'photo', 'is_active', 'is_primary'
    ]
    success_url = reverse_lazy('core:contact_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Contact updated successfully.'))
        return super().form_valid(form)


class ContactDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Vista para ver detalles de contactos universales"""
    model = Contact
    template_name = 'core/contacts/contact_detail.html'
    context_object_name = 'contact'
    permission_required = 'core.ver_contact'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['relationships'] = self.object.relationships.all().select_related('related_object')
        return context


class ContactDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Vista para eliminar contactos universales"""
    model = Contact
    template_name = 'core/contacts/contact_confirm_delete.html'
    permission_required = 'core.eliminar_contact'
    success_url = reverse_lazy('core:contact_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Contact deleted successfully.'))
        return super().delete(request, *args, **kwargs)


class ContactRelationshipListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Vista para listar relaciones de contactos"""
    model = ContactRelationship
    template_name = 'core/contacts/contact_relationship_list.html'
    context_object_name = 'relationships'
    permission_required = 'core.ver_contact'
    paginate_by = 20
    
    def get_queryset(self):
        return ContactRelationship.objects.all().select_related(
            'contact', 'content_type'
        ).order_by('contact__name', 'relationship_type')


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