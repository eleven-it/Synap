from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import JsonResponse
from django.db import transaction, models
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib import messages
from decimal import Decimal
import json

from core.models import Empresa, Branch, UsuarioExtendido
from sales.models import (
    POSTerminal, POSSession, POSSale, POSSaleLine, POSPayment, POSPromotion,
    PriceList, Client
)

# Verificar módulos disponibles
try:
    from inventory.models import Product, ProductVariant, StockQuant
    INVENTORY_AVAILABLE = True
except ImportError:
    INVENTORY_AVAILABLE = False

try:
    from accounting.models import ChartOfAccounts
    ACCOUNTING_AVAILABLE = True
except ImportError:
    ACCOUNTING_AVAILABLE = False


@login_required
def tpv_main(request):
    """Vista principal del TPV - Interfaz moderna con todas las mejoras UX/UI"""
    try:
        # Obtener empresa y sucursal del usuario - versión simplificada
        # Por ahora usamos la primera empresa y sucursal disponibles
        from core.models import Empresa, Branch
        
        empresa = Empresa.objects.filter(is_active=True).first()
        branch = Branch.objects.filter(is_active=True).first()
        
        if not empresa or not branch:
            messages.error(request, "No se pudo determinar la empresa o sucursal activa")
            return redirect('core:dashboard')
        
        # Obtener terminales disponibles
        terminals = POSTerminal.objects.filter(branch=branch, is_active=True)
        
        if not terminals.exists():
            messages.error(request, "No hay terminales TPV disponibles para esta sucursal")
            return redirect('core:dashboard')
        
        # Obtener o crear sesión activa para el usuario
        session = POSSession.objects.filter(
            operator=request.user,
            pos_terminal__branch=branch,
            state='open'
        ).first()
        
        # Si no hay sesión activa, crear una automáticamente con el primer terminal
        if not session:
            terminal = terminals.first()
            session = POSSession.objects.create(
                number=f"TPV-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                operator=request.user,
                branch=branch,
                pos_terminal=terminal,
                opening_amount=Decimal('0.00')
            )
        
        context = {
            'empresa': empresa,
            'branch': branch,
            'session': session,
            'terminals': terminals,
            'inventory_available': INVENTORY_AVAILABLE,
            'accounting_available': ACCOUNTING_AVAILABLE,
        }
        
        return render(request, 'sales/pos/tpv_main.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al cargar el TPV: {str(e)}")
        return redirect('core:dashboard')


@login_required
def tpv_dashboard(request):
    """Dashboard principal del TPV"""
    try:
        # Obtener empresa y sucursal del usuario - versión simplificada
        from core.models import Empresa, Branch
        
        empresa = Empresa.objects.filter(is_active=True).first()
        branch = Branch.objects.filter(is_active=True).first()
        
        if not empresa or not branch:
            messages.error(request, "No se pudo determinar la empresa o sucursal activa")
            return redirect('core:dashboard')
        
        # Obtener terminales disponibles
        terminals = POSTerminal.objects.filter(branch=branch, is_active=True)
        
        # Obtener sesiones activas
        active_sessions = POSSession.objects.filter(
            pos_terminal__branch=branch,
            state='open'
        ).select_related('operator', 'pos_terminal')
        
        # Estadísticas del día
        today = timezone.now().date()
        today_sales = POSSale.objects.filter(
            session__pos_terminal__branch=branch,
            created_at__date=today,
            state='completed'
        )
        
        daily_stats = {
            'total_sales': today_sales.count(),
            'total_amount': today_sales.aggregate(total=models.Sum('total'))['total'] or Decimal('0.00'),
            'active_sessions': active_sessions.count(),
        }
        
        context = {
            'empresa': empresa,
            'branch': branch,
            'terminals': terminals,
            'active_sessions': active_sessions,
            'daily_stats': daily_stats,
            'inventory_available': INVENTORY_AVAILABLE,
            'accounting_available': ACCOUNTING_AVAILABLE,
        }
        
        return render(request, 'sales/tpv/dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al cargar el dashboard: {str(e)}")
        return redirect('core:dashboard')


@login_required
def tpv_session_list(request):
    """Lista de sesiones del TPV"""
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        branch = user_extended.branch_activa
        
        if not empresa or not branch:
            messages.error(request, "No se pudo determinar la empresa o sucursal activa")
            return redirect('tpv_dashboard')
        
        # Obtener sesiones con paginación
        sessions = POSSession.objects.filter(
            pos_terminal__branch=branch
        ).select_related('operator', 'pos_terminal').order_by('-opened_at')
        
        paginator = Paginator(sessions, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'empresa': empresa,
            'branch': branch,
            'page_obj': page_obj,
        }
        
        return render(request, 'sales/tpv/session_list.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al cargar las sesiones: {str(e)}")
        return redirect('tpv_dashboard')


@login_required
def tpv_session_detail(request, session_id):
    """Detalle de una sesión del TPV"""
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        branch = user_extended.branch_activa
        
        if not empresa or not branch:
            messages.error(request, "No se pudo determinar la empresa o sucursal activa")
            return redirect('tpv_dashboard')
        
        # Obtener sesión
        session = get_object_or_404(
            POSSession.objects.select_related('operator', 'pos_terminal'),
            id=session_id,
            pos_terminal__branch=branch
        )
        
        # Obtener ventas de la sesión
        sales = POSSale.objects.filter(session=session).select_related('client').order_by('-created_at')
        
        # Obtener pagos de la sesión
        payments = POSPayment.objects.filter(
            sale__session=session
        ).select_related('sale').order_by('-created_at')
        
        context = {
            'empresa': empresa,
            'branch': branch,
            'session': session,
            'sales': sales,
            'payments': payments,
        }
        
        return render(request, 'sales/tpv/session_detail.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al cargar la sesión: {str(e)}")
        return redirect('tpv_session_list')


@login_required
def tpv_open_session(request):
    """Abrir nueva sesión del TPV"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user_extended = UsuarioExtendido.objects.get(user=request.user)
                empresa = user_extended.empresa_activa
                branch = user_extended.branch_activa
                
                if not empresa or not branch:
                    return JsonResponse({'success': False, 'error': 'Empresa o sucursal no válida'})
                
                # Obtener datos del formulario
                terminal_id = request.POST.get('terminal_id')
                opening_amount = Decimal(request.POST.get('opening_amount', '0'))
                
                # Validar terminal
                terminal = get_object_or_404(POSTerminal, id=terminal_id, branch=branch, is_active=True)
                
                # Verificar si ya hay una sesión abierta para este terminal
                existing_session = POSSession.objects.filter(
                    pos_terminal=terminal,
                    state='open'
                ).first()
                
                if existing_session:
                    return JsonResponse({
                        'success': False, 
                        'error': f'Ya existe una sesión abierta para el terminal {terminal.name}'
                    })
                
                # Crear nueva sesión
                session = POSSession.objects.create(
                    number=f"TPV-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    operator=request.user,
                    branch=branch,
                    pos_terminal=terminal,
                    opening_amount=opening_amount
                )
                
                return JsonResponse({
                    'success': True,
                    'session_id': session.id,
                    'session_number': session.number,
                    'redirect_url': f'/sales/tpv/session/{session.id}/'
                })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET request - mostrar formulario
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        branch = user_extended.branch_activa
        
        if not empresa or not branch:
            messages.error(request, "No se pudo determinar la empresa o sucursal activa")
            return redirect('tpv_dashboard')
        
        # Obtener terminales disponibles
        terminals = POSTerminal.objects.filter(branch=branch, is_active=True)
        
        context = {
            'empresa': empresa,
            'branch': branch,
            'terminals': terminals,
        }
        
        return render(request, 'sales/tpv/open_session.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al abrir sesión: {str(e)}")
        return redirect('tpv_dashboard')


@login_required
def tpv_close_session(request, session_id):
    """Cerrar sesión del TPV"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user_extended = UsuarioExtendido.objects.get(user=request.user)
                empresa = user_extended.empresa_activa
                branch = user_extended.branch_activa
                
                if not empresa or not branch:
                    return JsonResponse({'success': False, 'error': 'Empresa o sucursal no válida'})
                
                # Obtener sesión
                session = get_object_or_404(
                    POSSession,
                    id=session_id,
                    pos_terminal__branch=branch,
                    state='open'
                )
                
                # Obtener monto de cierre
                closing_amount = Decimal(request.POST.get('closing_amount', '0'))
                
                # Cerrar sesión
                session.close_session(closing_amount, request.user)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Sesión cerrada exitosamente',
                    'redirect_url': '/sales/tpv/sessions/'
                })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET request - mostrar formulario de cierre
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        branch = user_extended.branch_activa
        
        if not empresa or not branch:
            messages.error(request, "No se pudo determinar la empresa o sucursal activa")
            return redirect('tpv_dashboard')
        
        # Obtener sesión
        session = get_object_or_404(
            POSSession.objects.select_related('operator', 'pos_terminal'),
            id=session_id,
            pos_terminal__branch=branch,
            state='open'
        )
        
        # Calcular totales
        total_sales = POSSale.objects.filter(session=session).count()
        total_amount = POSSale.objects.filter(session=session).aggregate(
            total=models.Sum('total')
        )['total'] or Decimal('0.00')
        
        context = {
            'empresa': empresa,
            'branch': branch,
            'session': session,
            'total_sales': total_sales,
            'total_amount': total_amount,
        }
        
        return render(request, 'sales/tpv/close_session.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al cerrar sesión: {str(e)}")
        return redirect('tpv_session_list')


@login_required
def tpv_sale_create(request, session_id):
    """Crear nueva venta en el TPV"""
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        branch = user_extended.branch_activa
        
        if not empresa or not branch:
            messages.error(request, "No se pudo determinar la empresa o sucursal activa")
            return redirect('tpv_dashboard')
        
        # Obtener sesión
        session = get_object_or_404(
            POSSession,
            id=session_id,
            pos_terminal__branch=branch,
            state='open'
        )
        
        # Obtener lista de precios
        price_list = PriceList.objects.filter(is_active=True).first()
        
        # Obtener productos si el inventario está disponible
        products = []
        if INVENTORY_AVAILABLE:
            products = ProductVariant.objects.filter(
                product__empresa=empresa,
                product__is_active=True
            ).select_related('product')[:50]  # Limitar a 50 productos para rendimiento
        
        # Obtener clientes
        clients = Client.objects.filter(is_active=True)[:20]  # Limitar a 20 clientes
        
        context = {
            'empresa': empresa,
            'branch': branch,
            'session': session,
            'price_list': price_list,
            'products': products,
            'clients': clients,
            'inventory_available': INVENTORY_AVAILABLE,
        }
        
        return render(request, 'sales/tpv/sale_create.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al crear venta: {str(e)}")
        return redirect('tpv_session_detail', session_id=session_id)


@login_required
def tpv_product_search(request):
    """API para búsqueda de productos en el TPV"""
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        
        if not empresa or not INVENTORY_AVAILABLE:
            return JsonResponse({'success': False, 'error': 'Inventario no disponible'})
        
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'success': False, 'error': 'Query requerida'})
        
        # Buscar productos por SKU, nombre o código de barras
        products = ProductVariant.objects.filter(
            product__empresa=empresa,
            product__is_active=True
        ).select_related('product')
        
        # Búsqueda por SKU
        sku_results = products.filter(sku__icontains=query)
        
        # Búsqueda por nombre del producto
        name_results = products.filter(product__name__icontains=query)
        
        # Búsqueda por código de barras (si existe el campo)
        barcode_results = products.filter(barcode__icontains=query) if hasattr(products.model, 'barcode') else products.none()
        
        # Combinar resultados únicos
        all_results = list(sku_results) + list(name_results) + list(barcode_results)
        unique_results = []
        seen_ids = set()
        
        for product in all_results:
            if product.id not in seen_ids:
                seen_ids.add(product.id)
                unique_results.append(product)
        
        # Limitar resultados
        results = unique_results[:10]
        
        # Formatear resultados
        formatted_results = []
        for product in results:
            # Obtener stock si está disponible
            stock_info = ""
            if INVENTORY_AVAILABLE:
                stock_quant = StockQuant.objects.filter(
                    product=product.product
                ).aggregate(total=models.Sum('quantity'))['total'] or 0
                stock_info = f"Stock: {stock_quant}"
            
            formatted_results.append({
                'id': product.id,
                'sku': product.sku,
                'name': f"{product.product.name} - {product.name}",
                'price': float(product.product.list_price) if hasattr(product.product, 'list_price') else 0.0,
                'stock_info': stock_info,
                'barcode': getattr(product, 'barcode', ''),
            })
        
        return JsonResponse({
            'success': True,
            'results': formatted_results
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def tpv_sale_save(request, session_id):
    """API para guardar venta del TPV"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user_extended = UsuarioExtendido.objects.get(user=request.user)
                empresa = user_extended.empresa_activa
                branch = user_extended.branch_activa
                
                if not empresa or not branch:
                    return JsonResponse({'success': False, 'error': 'Empresa o sucursal no válida'})
                
                # Obtener sesión
                session = get_object_or_404(
                    POSSession,
                    id=session_id,
                    pos_terminal__branch=branch,
                    state='open'
                )
                
                # Obtener datos de la venta
                data = json.loads(request.body)
                
                # Crear venta
                sale = POSSale.objects.create(
                    session=session,
                    operator=request.user,
                    empresa=empresa,
                    branch=branch,
                    client_id=data.get('client_id'),
                    price_list_id=data.get('price_list_id'),
                    currency='ARS',
                    state='completed'
                )
                
                # Crear líneas de venta
                total_subtotal = Decimal('0.00')
                total_tax = Decimal('0.00')
                
                for line_data in data.get('lines', []):
                    if INVENTORY_AVAILABLE:
                        product_variant = get_object_or_404(ProductVariant, id=line_data['product_id'])
                        
                        quantity = Decimal(line_data['quantity'])
                        unit_price = Decimal(line_data['unit_price'])
                        line_total = quantity * unit_price
                        tax_amount = line_total * Decimal('0.21')  # 21% IVA
                        
                        line = POSSaleLine.objects.create(
                            sale=sale,
                            product_variant=product_variant,
                            empresa=empresa,
                            branch=branch,
                            quantity=quantity,
                            unit_price=unit_price,
                            subtotal=line_total,
                            tax_percentage=Decimal('21.00'),
                            tax_amount=tax_amount,
                            discount_percentage=Decimal('0.00'),
                            discount_amount=Decimal('0.00')
                        )
                        
                        total_subtotal += line_total
                        total_tax += tax_amount
                
                # Actualizar totales de la venta
                sale.subtotal = total_subtotal
                sale.total_tax = total_tax
                sale.total = total_subtotal + total_tax
                sale.save()
                
                # Crear asiento contable si está disponible
                if ACCOUNTING_AVAILABLE:
                    try:
                        from accounting.models import Journal, JournalEntry, JournalEntryLine
                        
                        journal = Journal.objects.filter(empresa=empresa, journal_type='sale').first()
                        if journal:
                            # Obtener cuentas contables
                            sales_account = ChartOfAccounts.objects.filter(
                                empresa=empresa,
                                code__icontains='4001-TPV'
                            ).first()
                            
                            cash_account = ChartOfAccounts.objects.filter(
                                empresa=empresa,
                                code__icontains='1101-TPV'
                            ).first()
                            
                            if sales_account and cash_account:
                                # Crear asiento contable
                                journal_entry = JournalEntry.objects.create(
                                    empresa=empresa,
                                    journal=journal,
                                    number=f"TPV-{sale.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                                    date=sale.created_at.date(),
                                    reference=f"Venta TPV {sale.id}",
                                    narration=f"Venta TPV - {sale.total}",
                                    state='posted',
                                    created_by=request.user,
                                    posted_by=request.user,
                                    posted_at=timezone.now(),
                                    origin_model='sales.POSSale',
                                    origin_id=sale.id
                                )
                                
                                # Crear líneas del asiento
                                JournalEntryLine.objects.create(
                                    entry=journal_entry,
                                    account=sales_account,
                                    debit=sale.total,
                                    credit=Decimal('0.00'),
                                    name="Venta TPV"
                                )
                                
                                JournalEntryLine.objects.create(
                                    entry=journal_entry,
                                    account=cash_account,
                                    debit=Decimal('0.00'),
                                    credit=sale.total,
                                    name="Caja TPV"
                                )
                    except Exception as e:
                        # Log error pero no fallar la venta
                        print(f"Error al crear asiento contable: {e}")
                
                return JsonResponse({
                    'success': True,
                    'sale_id': sale.id,
                    'sale_number': sale.number,
                    'total': float(sale.total),
                    'redirect_url': f'/sales/tpv/session/{session_id}/'
                })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required
def tpv_reports(request):
    """Reportes del TPV"""
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        branch = user_extended.branch_activa
        
        if not empresa or not branch:
            messages.error(request, "No se pudo determinar la empresa o sucursal activa")
            return redirect('tpv_dashboard')
        
        # Filtros de fecha
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        # Obtener ventas filtradas
        sales = POSSale.objects.filter(
            session__pos_terminal__branch=branch,
            state='completed'
        ).select_related('session', 'client')
        
        if date_from:
            sales = sales.filter(created_at__date__gte=date_from)
        if date_to:
            sales = sales.filter(created_at__date__lte=date_to)
        
        # Estadísticas
        total_sales = sales.count()
        total_amount = sales.aggregate(total=models.Sum('total'))['total'] or Decimal('0.00')
        avg_sale = total_amount / total_sales if total_sales > 0 else Decimal('0.00')
        
        # Paginación
        paginator = Paginator(sales.order_by('-created_at'), 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'empresa': empresa,
            'branch': branch,
            'page_obj': page_obj,
            'total_sales': total_sales,
            'total_amount': total_amount,
            'avg_sale': avg_sale,
            'date_from': date_from,
            'date_to': date_to,
        }
        
        return render(request, 'sales/tpv/reports.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al generar reportes: {str(e)}")
        return redirect('tpv_dashboard')


class TPVSaleSummaryView(LoginRequiredMixin, View):
    """Vista para mostrar el resumen de una venta del TPV"""
    
    def get(self, request, sale_id):
        try:
            sale = POSSale.objects.get(
                id=sale_id,
                session__operator=request.user,
                session__state='open'
            )
            return render(request, 'sales/pos/sale_summary.html', {
                'sale': sale
            })
        except POSSale.DoesNotExist:
            messages.error(request, _('Sale not found'))
            return redirect('tpv_dashboard') 