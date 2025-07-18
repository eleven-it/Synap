from django.http import JsonResponse
from django.db.models import Q
from core.models import Contact, Country, FiscalResponsibility, State, Currency


def contact_search_api(request):
    """API para buscar contactos existentes"""
    query = request.GET.get('q', '')
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    contacts = Contact.objects.filter(
        Q(name__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query) |
        Q(company_name__icontains=query)
    ).filter(is_active=True)[:10]
    
    results = []
    for contact in contacts:
        results.append({
            'id': contact.id,
            'text': contact.display_name,
            'name': contact.display_name,
            'email': contact.email,
            'phone': contact.phone,
            'position': contact.position,
            'company_name': contact.company_name,
        })
    
    return JsonResponse({'results': results}) 

def country_search_api(request):
    """API para buscar países por nombre o código"""
    query = request.GET.get('q', '').strip()
    if not query:
        countries = Country.objects.filter(is_active=True)[:10]
    else:
        countries = Country.objects.filter(
            Q(name__icontains=query) |
            Q(name_es__icontains=query) |
            Q(name_en__icontains=query) |
            Q(name_pt__icontains=query) |
            Q(code__icontains=query) |
            Q(code_2__icontains=query)
        ).filter(is_active=True)[:10]
    results = [
        {
            'id': c.id,
            'text': c.name,
            'name': c.name,
            'code': c.code,
            'code_2': c.code_2,
            'name_es': c.name_es,
            'name_en': c.name_en,
            'name_pt': c.name_pt,
        } for c in countries
    ]
    return JsonResponse({'results': results})

def fiscal_responsibility_search_api(request):
    """API para buscar responsabilidades fiscales por nombre o código y país"""
    query = request.GET.get('q', '').strip()
    country_name = request.GET.get('country_name', '').strip()
    country_code = request.GET.get('country_code', '').strip()
    respons = FiscalResponsibility.objects.all()
    if country_name:
        respons = respons.filter(
            Q(country__name__icontains=country_name) |
            Q(country__name_es__icontains=country_name) |
            Q(country__name_en__icontains=country_name) |
            Q(country__name_pt__icontains=country_name)
        )
    if country_code:
        respons = respons.filter(country__code__iexact=country_code)
    if query:
        respons = respons.filter(
            Q(name__icontains=query) |
            Q(code__icontains=query)
        )
    respons = respons[:10]
    results = [
        {
            'id': r.id,
            'text': f"{r.name} ({r.code})",
            'name': r.name,
            'code': r.code,
        } for r in respons
    ]
    return JsonResponse({'results': results}) 

def state_search_api(request):
    """API para buscar estados/provincias por nombre/código y país"""
    query = request.GET.get('q', '').strip()
    country_id = request.GET.get('country_id')
    country_name = request.GET.get('country_name', '').strip()
    country_code = request.GET.get('country_code', '').strip()
    qs = State.objects.all()
    if country_id:
        qs = qs.filter(country_id=country_id)
    elif country_code:
        qs = qs.filter(country__code__iexact=country_code)
    elif country_name:
        qs = qs.filter(
            Q(country__name__icontains=country_name) |
            Q(country__name_es__icontains=country_name) |
            Q(country__name_en__icontains=country_name) |
            Q(country__name_pt__icontains=country_name)
        )
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(name_es__icontains=query) | Q(name_en__icontains=query) | Q(name_pt__icontains=query) | Q(code__icontains=query))
    qs = qs[:10]
    results = [
        {
            'id': s.id,
            'text': f"{s.name} ({s.code})" if s.code else s.name,
            'name': s.name,
            'code': s.code,
            'country_id': s.country_id,
        } for s in qs
    ]
    return JsonResponse({'results': results}) 

def currency_search_api(request):
    """API para buscar monedas por nombre o código"""
    query = request.GET.get('q', '').strip()
    if not query:
        currencies = Currency.objects.filter(is_active=True)[:10]
    else:
        currencies = Currency.objects.filter(
            Q(name__icontains=query) |
            Q(code__icontains=query) |
            Q(symbol__icontains=query)
        ).filter(is_active=True)[:10]
    results = [
        {
            'id': c.id,
            'text': f"{c.name} ({c.code})",
            'name': c.name,
            'code': c.code,
            'symbol': c.symbol,
        } for c in currencies
    ]
    return JsonResponse({'results': results}) 