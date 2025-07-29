from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import json
import os
from sales.models import (
    Client, SalesOrder, SalesOrderLine, PriceList, PriceListItem,
    PaymentTerm, PaymentTermLine, Invoice, InvoiceLine, Payment,
    DeliveryOrder, DeliveryOrderLine, ReturnDelivery, CreditNote, ApprovalLog,
    POSSale, POSSaleLine, ClientTag, ClientAttachment, ClientActivity
)
from core.models import Contact, Country, State, FiscalResponsibility
from inventory.models import ProductVariant, Warehouse
from .serializers import (
    ClientSerializer, ClientListSerializer, ClientStatsSerializer,
    ContactSerializer, ContactListSerializer, ContactStatsSerializer,
    UserSerializer, AutocompleteSerializer, SalesOrderSerializer, SalesOrderLineSerializer,
    PriceListSerializer, PriceListItemSerializer, PaymentTermSerializer, PaymentTermLineSerializer,
    InvoiceSerializer, InvoiceLineSerializer, PaymentSerializer, DeliveryOrderSerializer,
    DeliveryOrderLineSerializer, ReturnDeliverySerializer, CreditNoteSerializer,
    ApprovalLogSerializer, SalesOrderCreateSerializer, InvoiceCreateSerializer,
    ClientTagSerializer, ClientAttachmentSerializer, ClientActivitySerializer
)

User = get_user_model()


class ClientViewSet(viewsets.ModelViewSet):
    """ViewSet para clientes"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['client_type', 'status', 'customer_category', 'country', 'state', 'city']
    search_fields = ['first_name', 'last_name', 'company_name', 'email', 'phone', 'tax_id']
    ordering_fields = ['created_at', 'updated_at', 'first_name', 'last_name', 'company_name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Client.objects.select_related('country', 'state', 'city', 'sales_representative').prefetch_related('contacts')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ClientListSerializer
        return ClientSerializer
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Obtener estadísticas de clientes"""
        queryset = self.get_queryset()
        
        # Estadísticas básicas
        total_clients = queryset.count()
        active_clients = queryset.filter(status='active').count()
        individual_clients = queryset.filter(client_type='individual').count()
        company_clients = queryset.filter(client_type='company').count()
        
        # Clientes por categoría
        clients_by_category = queryset.values('customer_category').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Clientes por estado
        clients_by_status = queryset.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Clientes recientes (último mes)
        recent_clients = queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Total de contactos
        total_contacts = Contact.objects.count()
        
        stats = {
            'total_clients': total_clients,
            'active_clients': active_clients,
            'individual_clients': individual_clients,
            'company_clients': company_clients,
            'clients_by_category': {item['customer_category']: item['count'] for item in clients_by_category},
            'clients_by_status': {item['status']: item['count'] for item in clients_by_status},
            'recent_clients': recent_clients,
            'total_contacts': total_contacts,
        }
        
        serializer = ClientStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """Autocompletado de clientes"""
        query = request.query_params.get('q', '')
        if not query:
            return Response([])
        
        queryset = self.get_queryset().filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(company_name__icontains=query) |
            Q(email__icontains=query) |
            Q(tax_id__icontains=query)
        )[:10]
        
        results = []
        for client in queryset:
            name = client.company_name if client.client_type == 'company' else f"{client.first_name} {client.last_name}".strip()
            results.append({
                'id': client.id,
                'name': name,
                'email': client.email,
                'tax_id': client.tax_id,
                'type': client.client_type
            })
        
        return Response({'success': True, 'results': results})
    
    @action(detail=True, methods=['get'])
    def activity_history(self, request, pk=None):
        """Obtener historial de actividad del cliente"""
        client = self.get_object()
        activity_type = request.query_params.get('activity_type', '')
        date_range = request.query_params.get('date_range', '30')
        user = request.query_params.get('user', '')
        
        queryset = ClientActivity.objects.filter(client=client)
        
        # Filtrar por tipo de actividad
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        
        # Filtrar por rango de fechas
        if date_range != 'all':
            days = int(date_range)
            start_date = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(timestamp__gte=start_date)
        
        # Filtrar por usuario
        if user:
            queryset = queryset.filter(user__username__icontains=user)
        
        activities = queryset.order_by('-timestamp')[:50]
        serializer = ClientActivitySerializer(activities, many=True)
        
        return Response({
            'success': True,
            'activities': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def top_products(self, request, pk=None):
        """Obtener productos más comprados por el cliente"""
        client = self.get_object()
        
        # Obtener productos más comprados
        top_products = SalesOrderLine.objects.filter(
            sales_order__client=client,
            sales_order__state='confirmed'
        ).values('product__name').annotate(
            quantity=Sum('quantity')
        ).order_by('-quantity')[:10]
        
        return Response({
            'success': True,
            'products': list(top_products)
        })
    
    @action(detail=True, methods=['get'])
    def sales_chart(self, request, pk=None):
        """Obtener datos de ventas por mes para el cliente"""
        client = self.get_object()
        
        # Obtener ventas de los últimos 12 meses
        sales_data = []
        for i in range(12):
            date = timezone.now() - timedelta(days=30*i)
            month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            
            total = SalesOrder.objects.filter(
                client=client,
                order_date__range=[month_start, month_end],
                state='confirmed'
            ).aggregate(total=Sum('total'))['total'] or 0
            
            sales_data.append({
                'month': month_start.strftime('%B %Y'),
                'amount': float(total)
            })
        
        return Response({
            'success': True,
            'sales_data': sales_data
        })


class ContactViewSet(viewsets.ModelViewSet):
    """ViewSet para contactos"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'department', 'status', 'client']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'mobile', 'position', 'company']
    ordering_fields = ['created_at', 'updated_at', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Contact.objects.select_related('client').prefetch_related('relationships')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ContactListSerializer
        return ContactSerializer
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Obtener estadísticas de contactos"""
        queryset = self.get_queryset()
        
        # Estadísticas básicas
        total_contacts = queryset.count()
        active_contacts = queryset.filter(status='active').count()
        primary_contacts = queryset.filter(is_primary=True).count()
        
        # Contactos por rol
        contacts_by_role = queryset.values('role').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Contactos por departamento
        contacts_by_department = queryset.values('department').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Contactos recientes (último mes)
        recent_contacts = queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        stats = {
            'total_contacts': total_contacts,
            'active_contacts': active_contacts,
            'primary_contacts': primary_contacts,
            'contacts_by_role': {item['role']: item['count'] for item in contacts_by_role},
            'contacts_by_department': {item['department']: item['count'] for item in contacts_by_department},
            'recent_contacts': recent_contacts,
        }
        
        serializer = ContactStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """Autocompletado de contactos"""
        query = request.query_params.get('q', '')
        if not query:
            return Response([])
        
        queryset = self.get_queryset().filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query) |
            Q(company__icontains=query)
        )[:10]
        
        results = []
        for contact in queryset:
            results.append({
                'id': contact.id,
                'name': f"{contact.first_name} {contact.last_name}".strip(),
                'email': contact.email,
                'phone': contact.phone,
                'company': contact.company
            })
        
        return Response({'success': True, 'results': results})
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Búsqueda de contactos"""
        query = request.query_params.get('q', '')
        if not query:
            return Response({'success': True, 'contacts': []})
        
        queryset = self.get_queryset().filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query) |
            Q(company__icontains=query)
        )[:20]
        
        results = []
        for contact in queryset:
            results.append({
                'id': contact.id,
                'name': f"{contact.first_name} {contact.last_name}".strip(),
                'email': contact.email,
                'phone': contact.phone,
                'company': contact.company
            })
        
        return Response({'success': True, 'contacts': results})
    
    @action(detail=False, methods=['post'])
    def create_contact(self, request):
        """Crear nuevo contacto"""
        try:
            data = request.data
            contact = Contact.objects.create(
                first_name=data.get('name', '').split()[0] if data.get('name') else '',
                last_name=' '.join(data.get('name', '').split()[1:]) if data.get('name') and len(data.get('name').split()) > 1 else '',
                email=data.get('email', ''),
                phone=data.get('phone', ''),
                position=data.get('position', ''),
                company=data.get('company', ''),
                is_primary=data.get('is_primary', False)
            )
            
            # Crear relación con cliente si se especifica
            if data.get('client_id'):
                from sales.models import ClientContactRelationship
                ClientContactRelationship.objects.create(
                    client_id=data['client_id'],
                    contact=contact,
                    relationship_type=data.get('relationship_type', 'other'),
                    notes=data.get('notes', ''),
                    is_active=True
                )
            
            return Response({
                'success': True,
                'message': 'Contact created successfully',
                'contact': {
                    'id': contact.id,
                    'name': f"{contact.first_name} {contact.last_name}".strip(),
                    'email': contact.email,
                    'phone': contact.phone
                }
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=400)
    
    @action(detail=True, methods=['post'])
    def update_contact(self, request, pk=None):
        """Actualizar contacto existente"""
        try:
            contact = self.get_object()
            data = request.data
            
            contact.first_name = data.get('name', '').split()[0] if data.get('name') else contact.first_name
            contact.last_name = ' '.join(data.get('name', '').split()[1:]) if data.get('name') and len(data.get('name').split()) > 1 else contact.last_name
            contact.email = data.get('email', contact.email)
            contact.phone = data.get('phone', contact.phone)
            contact.position = data.get('position', contact.position)
            contact.is_primary = data.get('is_primary', contact.is_primary)
            contact.save()
            
            return Response({
                'success': True,
                'message': 'Contact updated successfully'
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=400)
    
    @action(detail=True, methods=['post'])
    def add_to_client(self, request, pk=None):
        """Agregar contacto existente a un cliente"""
        try:
            contact = self.get_object()
            data = request.data
            
            from sales.models import ClientContactRelationship
            relationship, created = ClientContactRelationship.objects.get_or_create(
                client_id=data['client_id'],
                contact=contact,
                defaults={
                    'relationship_type': data.get('relationship_type', 'other'),
                    'notes': data.get('notes', ''),
                    'is_active': True
                }
            )
            
            if not created:
                relationship.relationship_type = data.get('relationship_type', relationship.relationship_type)
                relationship.notes = data.get('notes', relationship.notes)
                relationship.save()
            
            return Response({
                'success': True,
                'message': 'Contact added to client successfully'
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=400)


class ClientTagViewSet(viewsets.ModelViewSet):
    """ViewSet para tags de clientes"""
    permission_classes = [IsAuthenticated]
    serializer_class = ClientTagSerializer
    
    def get_queryset(self):
        return ClientTag.objects.filter(is_active=True).order_by('name')
    
    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """Autocompletado de tags"""
        query = request.query_params.get('q', '')
        if not query:
            return Response({'success': True, 'results': []})
        
        queryset = self.get_queryset().filter(name__icontains=query)[:10]
        results = [{'id': tag.id, 'name': tag.name} for tag in queryset]
        
        return Response({'success': True, 'results': results})


class ClientAttachmentViewSet(viewsets.ModelViewSet):
    """ViewSet para adjuntos de clientes"""
    permission_classes = [IsAuthenticated]
    serializer_class = ClientAttachmentSerializer
    
    def get_queryset(self):
        return ClientAttachment.objects.filter(client__isnull=False).order_by('-uploaded_at')
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Subir archivo adjunto"""
        try:
            file = request.FILES.get('file')
            client_id = request.data.get('client_id')
            description = request.data.get('description', '')
            
            if not file or not client_id:
                return Response({
                    'success': False,
                    'message': 'File and client_id are required'
                }, status=400)
            
            # Validar tipo de archivo
            allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.zip']
            file_extension = os.path.splitext(file.name)[1].lower()
            
            if file_extension not in allowed_extensions:
                return Response({
                    'success': False,
                    'message': 'File type not allowed'
                }, status=400)
            
            # Validar tamaño (10MB máximo)
            if file.size > 10 * 1024 * 1024:
                return Response({
                    'success': False,
                    'message': 'File size too large (max 10MB)'
                }, status=400)
            
            # Guardar archivo
            file_path = default_storage.save(f'client_attachments/{client_id}/{file.name}', ContentFile(file.read()))
            
            # Crear registro en base de datos
            attachment = ClientAttachment.objects.create(
                client_id=client_id,
                file=file_path,
                file_name=file.name,
                file_size=file.size,
                description=description,
                uploaded_by=request.user
            )
            
            return Response({
                'success': True,
                'message': 'File uploaded successfully',
                'attachment': {
                    'id': attachment.id,
                    'file_name': attachment.file_name,
                    'file_size': attachment.file_size,
                    'description': attachment.description
                }
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=400)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Descargar archivo adjunto"""
        attachment = self.get_object()
        
        if default_storage.exists(attachment.file.name):
            response = HttpResponse(default_storage.open(attachment.file.name).read())
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = f'attachment; filename="{attachment.file_name}"'
            return response
        else:
            return Response({
                'success': False,
                'message': 'File not found'
            }, status=404)
    
    @action(detail=True, methods=['post'])
    def update_attachment(self, request, pk=None):
        """Actualizar descripción del archivo"""
        try:
            attachment = self.get_object()
            description = request.data.get('description', '')
            
            attachment.description = description
            attachment.save()
            
            return Response({
                'success': True,
                'message': 'Description updated successfully'
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=400)
    
    @action(detail=True, methods=['post'])
    def delete_attachment(self, request, pk=None):
        """Eliminar archivo adjunto"""
        try:
            attachment = self.get_object()
            
            # Eliminar archivo físico
            if default_storage.exists(attachment.file.name):
                default_storage.delete(attachment.file.name)
            
            # Eliminar registro
            attachment.delete()
            
            return Response({
                'success': True,
                'message': 'File deleted successfully'
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=400)


# Autocomplete endpoints for various entities
class AutocompleteViewSet(viewsets.ViewSet):
    """ViewSet para autocompletado de entidades"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def countries(self, request):
        """Autocompletado de países"""
        query = request.query_params.get('q', '')
        queryset = Country.objects.filter(is_active=True)
        
        if query:
            queryset = queryset.filter(name__icontains=query)
        
        results = [{'id': country.id, 'name': country.name} for country in queryset[:10]]
        return Response({'success': True, 'results': results})
    
    @action(detail=False, methods=['get'])
    def states(self, request):
        """Autocompletado de estados/provincias"""
        query = request.query_params.get('q', '')
        country_id = request.query_params.get('country_id', '')
        
        queryset = State.objects.filter(is_active=True)
        
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        
        if query:
            queryset = queryset.filter(name__icontains=query)
        
        results = [{'id': state.id, 'name': state.name} for state in queryset[:10]]
        return Response({'success': True, 'results': results})
    
    @action(detail=False, methods=['get'])
    def fiscal_responsibilities(self, request):
        """Autocompletado de responsabilidades fiscales"""
        query = request.query_params.get('q', '')
        queryset = FiscalResponsibility.objects.filter(is_active=True)
        
        if query:
            queryset = queryset.filter(name__icontains=query)
        
        results = [{'id': resp.id, 'name': resp.name} for resp in queryset[:10]]
        return Response({'success': True, 'results': results})
    
    @action(detail=False, methods=['get'])
    def payment_terms(self, request):
        """Autocompletado de condiciones de pago"""
        query = request.query_params.get('q', '')
        queryset = PaymentTerm.objects.filter(is_active=True)
        
        if query:
            queryset = queryset.filter(name__icontains=query)
        
        results = [{'id': term.id, 'name': term.name} for term in queryset[:10]]
        return Response({'success': True, 'results': results})


# class CountryViewSet(viewsets.ReadOnlyModelViewSet):
#     """ViewSet para países"""
#     permission_classes = [IsAuthenticated]
#     serializer_class = CountrySerializer
#     filter_backends = [filters.SearchFilter]
#     search_fields = ['name', 'code']
#     
#     def get_queryset(self):
#         return Country.objects.all()
#     
#     @action(detail=False, methods=['get'])
#     def autocomplete(self, request):
#         """Autocompletado de países"""
#         query = request.query_params.get('q', '')
#         if not query:
#             return Response([])
#         
#         countries = Country.objects.filter(
#             Q(name__icontains=query) |
#             Q(name_es__icontains=query) |
#             Q(name_en__icontains=query) |
#             Q(name_pt__icontains=query),
#             is_active=True
#         )[:10]
#         
#         results = []
#         for country in countries:
#             results.append({
#                 'id': country.id,
#                 'name': country.name,
#                 'code': country.code,
#                 'phone_code': country.phone_code,
#                 'currency_code': country.currency_code,
#                 'timezone': country.timezone
#             })
#         
#         return Response(results)


# class StateViewSet(viewsets.ReadOnlyModelViewSet):
#     """ViewSet para estados/provincias"""
#     permission_classes = [IsAuthenticated]
#     serializer_class = StateSerializer
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter]
#     filterset_fields = ['country']
#     search_fields = ['name', 'code']
#     
#     def get_queryset(self):
#         return State.objects.select_related('country')
#     
#     @action(detail=False, methods=['get'])
#     def autocomplete(self, request):
#         """Autocompletado de estados/provincias"""
#         query = request.query_params.get('q', '')
#         country_id = request.query_params.get('country_id')
#         
#         if not query:
#             return Response([])
#         
#         states = State.objects.filter(
#             Q(name__icontains=query) |
#             Q(name_es__icontains=query) |
#             Q(name_en__icontains=query) |
#             Q(name_pt__icontains=query),
#             is_active=True
#         )
#         
#         if country_id:
#             states = states.filter(country_id=country_id)
#         
#         states = states.select_related('country')[:10]
#         
#         results = []
#         for state in states:
#             results.append({
#                 'id': state.id,
#                 'name': state.name,
#                 'code': state.code,
#                 'country_id': state.country.id,
#                 'country_name': state.country.name
#             })
#         
#         return Response(results)


# class CityViewSet(viewsets.ReadOnlyModelViewSet):
#     """ViewSet para ciudades"""
#     permission_classes = [IsAuthenticated]
#     serializer_class = CitySerializer
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter]
#     filterset_fields = ['state']
#     search_fields = ['name']
#     
#     def get_queryset(self):
#         return City.objects.select_related('state')
#     
#     @action(detail=False, methods=['get'])
#     def autocomplete(self, request):
#         """Autocompletado de ciudades"""
#         query = request.query_params.get('q', '')
#         state_id = request.query_params.get('state_id')
#         
#         if not query:
#             return Response([])
#         
#         cities = City.objects.filter(
#             Q(name__icontains=query) |
#             Q(name_es__icontains=query) |
#             Q(name_en__icontains=query) |
#             Q(name_pt__icontains=query),
#             is_active=True
#         )
#         
#         if state_id:
#             cities = cities.filter(state_id=state_id)
#         
#         cities = cities.select_related('state')[:10]
#         
#         results = []
#         for city in cities:
#             results.append({
#                 'id': city.id,
#                 'name': city.name,
#                 'state_id': city.state.id,
#                 'state_name': city.state.name,
#                 'country_id': city.state.country.id,
#                 'country_name': city.state.country.name
#             })
#         
#         return Response(results)


class SalesRepresentativeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para representantes de ventas"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_queryset(self):
        # Filtrar solo usuarios que pueden ser representantes de ventas
        return User.objects.filter(is_active=True)
    
    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """Autocompletado de representantes de ventas"""
        query = request.query_params.get('q', '')
        if not query:
            return Response([])
        
        queryset = self.get_queryset().filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )[:10]
        
        results = []
        for user in queryset:
            results.append({
                'id': user.id,
                'name': user.get_full_name(),
                'additional_info': f"{user.email} ({user.username})"
            })
        
        serializer = AutocompleteSerializer(results, many=True)
        return Response(serializer.data)


class SalesOrderViewSet(viewsets.ModelViewSet):
    """API para gestión de pedidos de venta"""
    queryset = SalesOrder.objects.all().order_by('-order_date')
    serializer_class = SalesOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['state', 'client', 'currency', 'origin']
    search_fields = ['number', 'client__name']
    ordering_fields = ['order_date', 'total', 'number']
    ordering = ['-order_date']

    def get_serializer_class(self):
        """Usar serializer específico para crear"""
        if self.action == 'create':
            return SalesOrderCreateSerializer
        return SalesOrderSerializer

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Aprobar pedido de venta"""
        order = self.get_object()
        
        if order.state != 'draft':
            return Response(
                {'error': 'Solo se pueden aprobar pedidos en borrador'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.state = 'approved'
        order.save()
        
        # Crear log de aprobación
        ApprovalLog.objects.create(
            sales_order=order,
            user=request.user,
            action='approved',
            reason=request.data.get('comments', '')
        )
        
        return Response({
            'id': order.id,
            'state': order.state,
            'message': 'Pedido aprobado correctamente'
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancelar pedido de venta"""
        order = self.get_object()
        
        if order.state in ['cancelled', 'completed']:
            return Response(
                {'error': 'No se puede cancelar un pedido ya cancelado o completado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.state = 'cancelled'
        order.save()
        
        # Crear log de cancelación
        ApprovalLog.objects.create(
            sales_order=order,
            user=request.user,
            action='cancelled',
            reason=request.data.get('comments', '')
        )
        
        return Response({
            'id': order.id,
            'state': order.state,
            'message': 'Pedido cancelado correctamente'
        })

    @action(detail=True, methods=['post'])
    def create_invoice(self, request, pk=None):
        """Crear factura desde pedido"""
        order = self.get_object()
        
        if order.state != 'approved':
            return Response(
                {'error': 'Solo se pueden facturar pedidos aprobados'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar si ya existe una factura para este pedido
        if Invoice.objects.filter(sales_order=order).exists():
            return Response(
                {'error': 'Ya existe una factura para este pedido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear factura con las líneas del pedido
        invoice_data = {
            'client': order.client,
            'sales_order': order,
            'invoice_date': timezone.now().date(),
            'payment_term': order.payment_term,
            'currency': order.currency,
            'total': order.total,
            'state': 'draft',
            'invoice_type': 'sale'
        }
        
        invoice_lines = []
        for line in order.lines.all():
            invoice_lines.append({
                'product_variant': line.product_variant,
                'quantity': line.quantity,
                'unit_price': line.unit_price,
                'discount': line.discount,
                'subtotal': line.subtotal,
                'description': line.description
            })
        
        # Crear factura usando el serializer
        serializer = InvoiceCreateSerializer(data={
            **invoice_data,
            'lines': invoice_lines
        })
        
        if serializer.is_valid():
            invoice = serializer.save()
            return Response({
                'invoice_id': invoice.id,
                'invoice_number': invoice.number,
                'message': 'Factura creada correctamente'
            })
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Estadísticas del dashboard de ventas"""
        # Pedidos por estado
        orders_by_state = SalesOrder.objects.values('state').annotate(
            count=Count('id'),
            total_amount=Sum('total')
        )
        
        # Pedidos del mes actual
        current_month = timezone.now().month
        current_year = timezone.now().year
        monthly_orders = SalesOrder.objects.filter(
            order_date__month=current_month,
            order_date__year=current_year
        ).aggregate(
            count=Count('id'),
            total_amount=Sum('total')
        )
        
        # Top clientes
        top_clients = SalesOrder.objects.values(
            'client__name'
        ).annotate(
            total_orders=Count('id'),
            total_amount=Sum('total')
        ).order_by('-total_amount')[:5]
        
        return Response({
            'orders_by_state': list(orders_by_state),
            'monthly_orders': monthly_orders,
            'top_clients': list(top_clients)
        })


class InvoiceViewSet(viewsets.ModelViewSet):
    """API para gestión de facturas"""
    queryset = Invoice.objects.all().order_by('-invoice_date')
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['state', 'client', 'currency', 'payment_term', 'invoice_type']
    search_fields = ['number', 'client__name']
    ordering_fields = ['invoice_date', 'total', 'number']
    ordering = ['-invoice_date']

    def get_serializer_class(self):
        """Usar serializer específico para crear"""
        if self.action == 'create':
            return InvoiceCreateSerializer
        return InvoiceSerializer

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Marcar factura como pagada"""
        invoice = self.get_object()
        
        if invoice.state == 'paid':
            return Response(
                {'error': 'La factura ya está marcada como pagada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invoice.state = 'paid'
        invoice.save()
        
        return Response({
            'id': invoice.id,
            'state': invoice.state,
            'message': 'Factura marcada como pagada'
        })

    @action(detail=True, methods=['post'])
    def create_payment(self, request, pk=None):
        """Crear pago para la factura"""
        invoice = self.get_object()
        
        payment_data = {
            'invoice': invoice.id,
            'client': invoice.client.id,
            'payment_date': request.data.get('payment_date', timezone.now().date()),
            'amount': request.data.get('amount'),
            'currency': request.data.get('currency', invoice.currency),
            'payment_method': request.data.get('payment_method'),
            'state': 'confirmed'
        }
        
        serializer = PaymentSerializer(data=payment_data)
        if serializer.is_valid():
            payment = serializer.save()
            
            # Verificar si la factura está completamente pagada
            total_paid = Payment.objects.filter(invoice=invoice).aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            if total_paid >= invoice.total:
                invoice.state = 'paid'
                invoice.save()
            
            return Response({
                'payment_id': payment.id,
                'invoice_state': invoice.state,
                'message': 'Pago registrado correctamente'
            })
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentViewSet(viewsets.ModelViewSet):
    """API para gestión de pagos"""
    queryset = Payment.objects.all().order_by('-payment_date')
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['client', 'payment_method', 'currency', 'state']
    search_fields = ['number', 'client__name']
    ordering_fields = ['payment_date', 'amount', 'number']
    ordering = ['-payment_date']


class DeliveryOrderViewSet(viewsets.ModelViewSet):
    """API para gestión de órdenes de entrega"""
    queryset = DeliveryOrder.objects.all().order_by('-delivery_date')
    serializer_class = DeliveryOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['state', 'client', 'warehouse', 'sales_order']
    search_fields = ['number', 'client__name']
    ordering_fields = ['delivery_date', 'number']
    ordering = ['-delivery_date']

    @action(detail=True, methods=['post'])
    def process_delivery(self, request, pk=None):
        """Procesar entrega (confirmar cantidades entregadas)"""
        delivery = self.get_object()
        
        if delivery.state != 'pending':
            return Response(
                {'error': 'Solo se pueden procesar entregas pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Actualizar cantidades entregadas
        lines_data = request.data.get('lines', [])
        
        with transaction.atomic():
            for line_data in lines_data:
                line_id = line_data.get('id')
                delivered_qty = line_data.get('delivered_quantity', 0)
                
                try:
                    line = DeliveryOrderLine.objects.get(id=line_id, delivery_order=delivery)
                    line.quantity = delivered_qty
                    line.state = 'delivered'
                    line.save()
                    
                except DeliveryOrderLine.DoesNotExist:
                    continue
            
            # Marcar entrega como completada
            delivery.state = 'completed'
            delivery.save()
        
        return Response({
            'id': delivery.id,
            'state': delivery.state,
            'message': 'Entrega procesada correctamente'
        })


class ReturnDeliveryViewSet(viewsets.ModelViewSet):
    """API para gestión de devoluciones"""
    queryset = ReturnDelivery.objects.all().order_by('-return_date')
    serializer_class = ReturnDeliverySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['state', 'client', 'sales_order', 'return_type']
    search_fields = ['number', 'client__name', 'reason']
    ordering_fields = ['return_date', 'number']
    ordering = ['-return_date']

    @action(detail=True, methods=['post'])
    def approve_return(self, request, pk=None):
        """Aprobar devolución"""
        return_delivery = self.get_object()
        
        if return_delivery.state != 'pending':
            return Response(
                {'error': 'Solo se pueden aprobar devoluciones pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return_delivery.state = 'approved'
        return_delivery.save()
        
        return Response({
            'id': return_delivery.id,
            'state': return_delivery.state,
            'message': 'Devolución aprobada correctamente'
        })


class CreditNoteViewSet(viewsets.ModelViewSet):
    """API para gestión de notas de crédito"""
    queryset = CreditNote.objects.all().order_by('-credit_date')
    serializer_class = CreditNoteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['state', 'client', 'invoice']
    search_fields = ['number', 'client__name', 'reason']
    ordering_fields = ['credit_date', 'amount', 'number']
    ordering = ['-credit_date']

    @action(detail=True, methods=['post'])
    def apply_credit(self, request, pk=None):
        """Aplicar nota de crédito"""
        credit_note = self.get_object()
        
        if credit_note.state != 'pending':
            return Response(
                {'error': 'Solo se pueden aplicar notas de crédito pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        credit_note.state = 'applied'
        credit_note.save()
        
        return Response({
            'id': credit_note.id,
            'state': credit_note.state,
            'message': 'Nota de crédito aplicada correctamente'
        })


class PriceListViewSet(viewsets.ModelViewSet):
    """API para gestión de listas de precios"""
    queryset = PriceList.objects.all().order_by('name')
    serializer_class = PriceListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'currency']
    search_fields = ['name']
    ordering_fields = ['name', 'valid_from', 'valid_to']
    ordering = ['name']

    @action(detail=True, methods=['post'])
    def add_product(self, request, pk=None):
        """Agregar producto a la lista de precios"""
        price_list = self.get_object()
        
        product_variant_id = request.data.get('product_variant_id')
        price = request.data.get('price')
        
        if not product_variant_id or not price:
            return Response(
                {'error': 'Se requiere product_variant_id y price'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product_variant = ProductVariant.objects.get(id=product_variant_id)
        except ProductVariant.DoesNotExist:
            return Response(
                {'error': 'Variante de producto no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Crear o actualizar item de lista de precios
        item, created = PriceListItem.objects.update_or_create(
            price_list=price_list,
            product_variant=product_variant,
            defaults={
                'price': price,
                'min_qty': request.data.get('min_qty', 1),
                'max_qty': request.data.get('max_qty'),
                'discount': request.data.get('discount', 0)
            }
        )
        
        return Response({
            'id': item.id,
            'created': created,
            'message': f'Producto {"agregado" if created else "actualizado"} correctamente'
        })


class PaymentTermViewSet(viewsets.ModelViewSet):
    """API para gestión de condiciones de pago"""
    queryset = PaymentTerm.objects.all().order_by('name')
    serializer_class = PaymentTermSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name']
    ordering = ['name']


class ApprovalLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API para consulta de logs de aprobación"""
    queryset = ApprovalLog.objects.all().order_by('-action_date')
    serializer_class = ApprovalLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action', 'user', 'sales_order']
    search_fields = ['reason']
    ordering_fields = ['action_date']
    ordering = ['-action_date']


# ============================================================================
# TPV (Point of Sale) API Endpoints
# ============================================================================

class TPVProductViewSet(viewsets.ReadOnlyModelViewSet):
    """API para búsqueda de productos en el TPV"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Obtener productos del inventario si está disponible
        try:
            from inventory.models import ProductVariant
            return ProductVariant.objects.filter(
                is_active=True,
                product__is_active=True
            ).select_related('product', 'product__category')
        except ImportError:
            # Si no hay módulo de inventario, devolver lista vacía
            return ProductVariant.objects.none()
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Búsqueda de productos para el TPV"""
        query = request.query_params.get('q', '')
        if not query or len(query) < 2:
            return Response([])
        
        queryset = self.get_queryset().filter(
            Q(product__name__icontains=query) |
            Q(product__sku__icontains=query) |
            Q(sku__icontains=query)
        )[:20]
        
        results = []
        for variant in queryset:
            # Obtener stock si está disponible
            stock = 0
            try:
                # Intentar obtener stock del inventario si está disponible
                if hasattr(variant, 'stock_quantity'):
                    stock = variant.stock_quantity
                elif hasattr(variant.product, 'stock_quantity'):
                    stock = variant.product.stock_quantity
            except:
                pass
            
            # Obtener precio
            price = 0
            if hasattr(variant, 'sale_price') and variant.sale_price:
                price = float(variant.sale_price)
            elif hasattr(variant.product, 'sale_price') and variant.product.sale_price:
                price = float(variant.product.sale_price)
            
            results.append({
                'id': variant.id,
                'name': variant.product.name,
                'sku': variant.sku or variant.product.sku,
                'price': price,
                'stock': stock,
                'category': variant.product.category.name if variant.product.category else None
            })
        
        return Response(results)
    
    def list(self, request):
        """Lista de productos para el TPV"""
        queryset = self.get_queryset()[:50]  # Limitar a 50 productos
        
        results = []
        for variant in queryset:
            # Obtener stock si está disponible
            stock = 0
            try:
                # Intentar obtener stock del inventario si está disponible
                if hasattr(variant, 'stock_quantity'):
                    stock = variant.stock_quantity
                elif hasattr(variant.product, 'stock_quantity'):
                    stock = variant.product.stock_quantity
            except:
                pass
            
            # Obtener precio
            price = 0
            if hasattr(variant, 'sale_price') and variant.sale_price:
                price = float(variant.sale_price)
            elif hasattr(variant.product, 'sale_price') and variant.product.sale_price:
                price = float(variant.product.sale_price)
            
            results.append({
                'id': variant.id,
                'name': variant.product.name,
                'sku': variant.sku or variant.product.sku,
                'price': price,
                'stock': stock,
                'category': variant.product.category.name if variant.product.category else None
            })
        
        return Response(results)


class TPVPaymentViewSet(viewsets.ViewSet):
    """API para procesamiento de pagos del TPV"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def process_payment(self, request):
        """Procesar pago del TPV"""
        try:
            from sales.services.tpv_service import TPVService
            from sales.services.sale_service import SaleService
            
            data = request.data
            items = data.get('items', [])
            payment_method = data.get('payment_method', 'cash')
            total = data.get('total', 0)
            extra_data = data.get('extra_data', {})
            
            if not items:
                return Response(
                    {'error': 'No items in cart'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Obtener sesión activa del TPV
            tpv_service = TPVService()
            session = tpv_service.get_active_session(request.user)
            
            if not session:
                return Response(
                    {'error': 'No active TPV session'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Crear la venta
            sale_service = SaleService()
            sale_data = {
                'session': session,
                'items': items,
                'payment_method': payment_method,
                'total': total,
                'extra_data': extra_data
            }
            
            sale = sale_service.create_tpv_sale(sale_data)
            
            # Procesar pago
            payment_result = sale_service.process_tpv_payment(sale, payment_method, extra_data)
            
            return Response({
                'success': True,
                'sale_number': sale.number,
                'total': float(sale.total),
                'payment_method': payment_method,
                'change': payment_result.get('change', 0)
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 