from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from inventory.models import InitialStockDraft, InitialStockDraftItem, Product, Location, UnitOfMeasure, Category, Subcategory, Brand
from inventory.forms import InitialStockDraftForm, InitialStockDraftItemForm, InitialStockDraftExcelForm
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages
import openpyxl
from django.core.paginator import Paginator
from django.db.models import Q

# Helper para roles

def user_can_edit_draft(user, draft):
    if user.is_superuser:
        return True
    if hasattr(user, 'rol') and user.rol in ['Administrador', 'Supervisor']:
        return True
    return draft.creado_por == user

@login_required
@permission_required('inventory.cargar_stock_inicial', raise_exception=True)
def stock_initial_wizard(request):
    # Paso 1: Solo crear borrador
    if request.method == 'POST':
        draft_form = InitialStockDraftForm(request.POST, request.FILES)
        if draft_form.is_valid():
            draft = draft_form.save(commit=False)
            draft.creado_por = request.user
            draft.save()
            messages.success(request, 'Borrador guardado correctamente.')
            return redirect('inventory:stock_initial_edit', draft_id=draft.id)
    else:
        draft_form = InitialStockDraftForm()
    return render(request, 'inventory/stock_initial_wizard.html', {'draft_form': draft_form})

@login_required
@permission_required('inventory.ver_borradores_stock_inicial', raise_exception=True)
def stock_initial_drafts(request):
    # Listar borradores editables por el usuario
    drafts = InitialStockDraft.objects.filter(
        creado_por=request.user
    )
    # Supervisores y administradores ven todos
    if hasattr(request.user, 'rol') and request.user.rol in ['Administrador', 'Supervisor']:
        drafts = InitialStockDraft.objects.all()
    return render(request, 'inventory/stock_initial_drafts.html', {'drafts': drafts})

@login_required
@permission_required('inventory.editar_borradores_stock_inicial', raise_exception=True)
def stock_initial_edit(request, draft_id):
    draft = get_object_or_404(InitialStockDraft, id=draft_id)
    if not user_can_edit_draft(request.user, draft):
        return render(request, 'core/403.html')
    # Filtros y lógica de productos
    products_qs = Product.objects.filter(type__in=['consumable', 'stockable', 'combo'])
    search = request.GET.get('search', '').strip()
    category = request.GET.get('category', '')
    subcategory = request.GET.get('subcategory', '')
    brand = request.GET.get('brand', '')
    ptype = request.GET.get('ptype', '')
    if search:
        products_qs = products_qs.filter(Q(name__icontains=search) | Q(sku__icontains=search) | Q(description__icontains=search))
    if category:
        products_qs = products_qs.filter(subcategory__category_id=category)
    if subcategory:
        products_qs = products_qs.filter(subcategory_id=subcategory)
    if brand:
        products_qs = products_qs.filter(brand_id=brand)
    if ptype:
        products_qs = products_qs.filter(type=ptype)
    products_qs = products_qs.select_related('brand', 'subcategory', 'subcategory__category')
    page_number = request.GET.get('page', 1)
    paginator = Paginator(products_qs.order_by('sku'), 25)
    page_obj = paginator.get_page(page_number)
    categories = Category.objects.filter(is_active=True)
    subcategories = Subcategory.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    excel_form = InitialStockDraftExcelForm()
    # Guardar productos editados
    if request.method == 'POST' and 'guardar_productos' in request.POST:
        guardados = 0
        for product in products_qs:
            cantidad = request.POST.get(f'cantidad_{product.id}')
            lote = request.POST.get(f'lote_{product.id}', '')
            vencimiento = request.POST.get(f'vencimiento_{product.id}', '')
            try:
                cantidad = float(cantidad)
            except (TypeError, ValueError):
                cantidad = 0
            if cantidad > 0:
                item, created = InitialStockDraftItem.objects.update_or_create(
                    borrador=draft, producto=product,
                    defaults={
                        'sku': product.sku,
                        'cantidad': cantidad,
                        'lote': lote,
                        'fecha_vencimiento': vencimiento or None,
                    }
                )
                guardados += 1
            else:
                InitialStockDraftItem.objects.filter(borrador=draft, producto=product).delete()
        messages.success(request, f'Se guardaron {guardados} productos con stock inicial.')
    # Carga por Excel
    if request.method == 'POST' and 'cargar_excel' in request.POST:
        excel_form = InitialStockDraftExcelForm(request.POST, request.FILES)
        if excel_form.is_valid():
            archivo = request.FILES['archivo_excel']
            try:
                wb = openpyxl.load_workbook(archivo)
                ws = wb.active
                preview = []
                guardados = 0
                for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    sku, nombre, ubicacion, cantidad, lote, obs = row[:6]
                    try:
                        cantidad = float(cantidad)
                    except (TypeError, ValueError):
                        cantidad = 0
                    if not sku or cantidad <= 0:
                        continue
                    try:
                        product = Product.objects.get(sku=sku, type__in=['consumable', 'stockable', 'combo'])
                    except Product.DoesNotExist:
                        continue
                    item, created = InitialStockDraftItem.objects.update_or_create(
                        borrador=draft, producto=product,
                        defaults={
                            'sku': product.sku,
                            'cantidad': cantidad,
                            'lote': lote or '',
                            'fecha_vencimiento': None,
                            'observaciones': obs or '',
                        }
                    )
                    guardados += 1
                    preview.append({'sku': sku, 'nombre': nombre, 'ubicacion': ubicacion, 'cantidad': cantidad, 'lote': lote, 'obs': obs})
                messages.success(request, f'Se guardaron {guardados} productos desde Excel.')
                return render(request, 'inventory/stock_initial_edit.html', {
                    'draft': draft,
                    'excel_form': excel_form,
                    'excel_preview': preview,
                    'products': page_obj,
                    'categories': categories,
                    'subcategories': subcategories,
                    'brands': brands,
                    'search': search,
                    'category': category,
                    'subcategory': subcategory,
                    'brand': brand,
                    'ptype': ptype,
                })
            except Exception as e:
                messages.error(request, f'Error al procesar el Excel: {e}')
    return render(request, 'inventory/stock_initial_edit.html', {
        'draft': draft,
        'excel_form': excel_form,
        'products': page_obj,
        'categories': categories,
        'subcategories': subcategories,
        'brands': brands,
        'search': search,
        'category': category,
        'subcategory': subcategory,
        'brand': brand,
        'ptype': ptype,
    })

@login_required
@permission_required('inventory.finalizar_borradores_stock_inicial', raise_exception=True)
def stock_initial_finish(request, draft_id):
    draft = get_object_or_404(InitialStockDraft, id=draft_id)
    if not user_can_edit_draft(request.user, draft):
        return render(request, 'core/403.html')
    # Lógica para finalizar y aplicar movimientos de stock
    draft.estado = 'finalizado'
    draft.save()
    messages.success(request, 'Stock inicial aplicado correctamente.')
    return redirect(reverse('inventory:stock_initial_drafts')) 