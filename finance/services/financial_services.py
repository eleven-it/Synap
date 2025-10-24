# coding: utf-8
"""
Servicios financieros para cálculo de métricas y reportes.

Este módulo contiene funciones para calcular ingresos, costos y márgenes
a partir de los datos de FinancialEntry, agrupados por períodos temporales.
"""
from decimal import Decimal
from typing import List, Dict, Any
from django.db.models import Sum, F, Case, When, Value, CharField, DecimalField
from django.db.models.functions import TruncMonth
from ..models import FinancialEntry


def get_monthly_financial_summary(year: int, currency: str = 'ARS') -> List[Dict[str, Any]]:
    """
    Calcula el resumen financiero mensual para un año específico.
    
    Args:
        year (int): Año para el cual calcular las métricas (formato YYYY)
        currency (str): Moneda para filtrar los datos (default: 'ARS')
    
    Returns:
        List[Dict[str, Any]]: Lista de diccionarios con métricas mensuales:
            - month: Mes en formato 'YYYY-MM'
            - income: Suma de ingresos (entry_type='sale')
            - cost: Suma de costos (entry_type='purchase')
            - margin: Margen calculado (income - cost)
    
    Raises:
        ValueError: Si el año no es un entero de 4 dígitos válido
    """
    # Validar año
    if not isinstance(year, int) or year < 1000 or year > 9999:
        raise ValueError("Year must be a 4-digit integer")
    
    # Filtrar registros por año y moneda
    queryset = FinancialEntry.objects.filter(
        date__year=year,
        currency=currency
    )
    
    # Agregar por mes usando TruncMonth
    monthly_data = queryset.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        income=Sum(
            Case(
                When(entry_type='sale', then='net_amount'),
                default=Value(0),
                output_field=DecimalField()
            )
        ),
        cost=Sum(
            Case(
                When(entry_type='purchase', then='net_amount'),
                default=Value(0),
                output_field=DecimalField()
            )
        )
    ).order_by('month')
    
    # Procesar resultados y calcular margen
    result = []
    for item in monthly_data:
        month_str = item['month'].strftime('%Y-%m')
        income = item['income'] or Decimal('0')
        cost = item['cost'] or Decimal('0')
        margin = income - cost
        
        result.append({
            'month': month_str,
            'income': income,
            'cost': cost,
            'margin': margin
        })
    
    return result


def get_annual_financial_summary(year: int, currency: str = 'ARS') -> Dict[str, Any]:
    """
    Calcula el resumen financiero anual para un año específico.
    
    Args:
        year (int): Año para el cual calcular las métricas (formato YYYY)
        currency (str): Moneda para filtrar los datos (default: 'ARS')
    
    Returns:
        Dict[str, Any]: Diccionario con métricas anuales:
            - year: Año calculado
            - currency: Moneda utilizada
            - income: Suma total de ingresos
            - cost: Suma total de costos
            - margin: Margen total calculado
            - transaction_count: Número total de transacciones
    
    Raises:
        ValueError: Si el año no es un entero de 4 dígitos válido
    """
    # Validar año
    if not isinstance(year, int) or year < 1000 or year > 9999:
        raise ValueError("Year must be a 4-digit integer")
    
    # Filtrar registros por año y moneda
    queryset = FinancialEntry.objects.filter(
        date__year=year,
        currency=currency
    )
    
    # Calcular agregaciones anuales
    annual_data = queryset.aggregate(
        income=Sum(
            Case(
                When(entry_type='sale', then='net_amount'),
                default=Value(0),
                output_field=DecimalField()
            )
        ),
        cost=Sum(
            Case(
                When(entry_type='purchase', then='net_amount'),
                default=Value(0),
                output_field=DecimalField()
            )
        ),
        transaction_count=Sum(
            Case(
                When(entry_type__in=['sale', 'purchase'], then=Value(1)),
                default=Value(0),
                output_field=DecimalField()
            )
        )
    )
    
    income = annual_data['income'] or Decimal('0')
    cost = annual_data['cost'] or Decimal('0')
    margin = income - cost
    transaction_count = int(annual_data['transaction_count'] or 0)
    
    return {
        'year': year,
        'currency': currency,
        'income': income,
        'cost': cost,
        'margin': margin,
        'transaction_count': transaction_count
    }


def get_financial_summary_by_period(start_year: int, end_year: int, currency: str = 'ARS') -> Dict[str, Any]:
    """
    Calcula el resumen financiero para un rango de años.
    
    Args:
        start_year (int): Año de inicio (formato YYYY)
        end_year (int): Año de fin (formato YYYY)
        currency (str): Moneda para filtrar los datos (default: 'ARS')
    
    Returns:
        Dict[str, Any]: Diccionario con métricas del período:
            - period: Rango de años como string
            - currency: Moneda utilizada
            - income: Suma total de ingresos
            - cost: Suma total de costos
            - margin: Margen total calculado
            - transaction_count: Número total de transacciones
            - years: Lista de años incluidos
    
    Raises:
        ValueError: Si los años no son válidos o el rango es inválido
    """
    # Validar años
    if not isinstance(start_year, int) or start_year < 1000 or start_year > 9999:
        raise ValueError("Start year must be a 4-digit integer")
    if not isinstance(end_year, int) or end_year < 1000 or end_year > 9999:
        raise ValueError("End year must be a 4-digit integer")
    if start_year > end_year:
        raise ValueError("Start year cannot be greater than end year")
    
    # Filtrar registros por rango de años y moneda
    queryset = FinancialEntry.objects.filter(
        date__year__gte=start_year,
        date__year__lte=end_year,
        currency=currency
    )
    
    # Calcular agregaciones del período
    period_data = queryset.aggregate(
        income=Sum(
            Case(
                When(entry_type='sale', then='net_amount'),
                default=Value(0),
                output_field=DecimalField()
            )
        ),
        cost=Sum(
            Case(
                When(entry_type='purchase', then='net_amount'),
                default=Value(0),
                output_field=DecimalField()
            )
        ),
        transaction_count=Sum(
            Case(
                When(entry_type__in=['sale', 'purchase'], then=Value(1)),
                default=Value(0),
                output_field=DecimalField()
            )
        )
    )
    
    income = period_data['income'] or Decimal('0')
    cost = period_data['cost'] or Decimal('0')
    margin = income - cost
    transaction_count = int(period_data['transaction_count'] or 0)
    
    return {
        'period': f"{start_year}-{end_year}",
        'currency': currency,
        'income': income,
        'cost': cost,
        'margin': margin,
        'transaction_count': transaction_count,
        'years': list(range(start_year, end_year + 1))
    }
