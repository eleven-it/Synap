from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.contrib import messages
from mercadopago.models import MercadoPagoConfig, MercadoPagoDevice, MercadoPagoTransaction
from mercadopago.services.payment_service import MercadoPagoPaymentService
from mercadopago.services.smartpos_service import MercadoPagoDeviceManager

@login_required
def config_list(request):
    configs = MercadoPagoConfig.objects.select_related('empresa').all()
    return render(request, 'mercadopago/config_list.html', {'configs': configs})

@login_required
def config_edit(request, pk=None):
    if pk:
        config = get_object_or_404(MercadoPagoConfig, pk=pk)
    else:
        config = None
    if request.method == 'POST':
        # TODO: Usar formulario CRisPY
        # Guardar configuración
        pass
    return render(request, 'mercadopago/config_edit.html', {'config': config})

@login_required
def config_test_connection(request, pk):
    config = get_object_or_404(MercadoPagoConfig, pk=pk)
    service = MercadoPagoPaymentService(config.empresa)
    result = service.test_connection()
    messages.info(request, _(result.get('message', result.get('error', ''))))
    return redirect(reverse('mercadopago:config_list'))

@login_required
def device_list(request):
    devices = MercadoPagoDevice.objects.select_related('empresa', 'branch').all()
    return render(request, 'mercadopago/device_list.html', {'devices': devices})

@login_required
def device_edit(request, pk=None):
    if pk:
        device = get_object_or_404(MercadoPagoDevice, pk=pk)
    else:
        device = None
    if request.method == 'POST':
        # TODO: Usar formulario CRisPY
        # Guardar dispositivo
        pass
    return render(request, 'mercadopago/device_edit.html', {'device': device})

@login_required
def device_sync(request, pk):
    device = get_object_or_404(MercadoPagoDevice, pk=pk)
    from mercadopago.services.smartpos_service import MercadoPagoSmartPOSService
    service = MercadoPagoSmartPOSService(device)
    result = service.sync_device_status()
    messages.info(request, _(result.get('message', result.get('error', ''))))
    return redirect(reverse('mercadopago:device_list'))

@login_required
def transaction_list(request):
    transactions = MercadoPagoTransaction.objects.select_related('empresa', 'branch', 'device').all()
    return render(request, 'mercadopago/transaction_list.html', {'transactions': transactions})

@login_required
def transaction_detail(request, pk):
    transaction = get_object_or_404(MercadoPagoTransaction, pk=pk)
    return render(request, 'mercadopago/transaction_detail.html', {'transaction': transaction}) 