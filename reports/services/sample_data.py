"""Datos de muestra para dashboards operacionales y gerenciales."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple


DEFAULT_META = {
    "currency": "ARS",
    "tz": "America/Argentina/Buenos_Aires",
}


SAMPLE_DATA: Dict[str, Dict[str, object]] = {
    "ventas_resumen": {
        "data": [
            {"date": "2025-02-01", "revenue": 152000, "orders": 120, "gross_margin": 54000, "avg_ticket": 1267},
            {"date": "2025-02-02", "revenue": 163800, "orders": 132, "gross_margin": 58640, "avg_ticket": 1241},
            {"date": "2025-02-03", "revenue": 171400, "orders": 138, "gross_margin": 61200, "avg_ticket": 1242},
            {"date": "2025-02-04", "revenue": 158300, "orders": 126, "gross_margin": 57280, "avg_ticket": 1256},
        ],
        "notes": ["Fuente: view_fin_ventas_diaria"],
    },
    "ventas_mix_canal": {
        "data": [
            {"channel": "Retail", "week": "2025-W04", "revenue": 86000, "orders": 82, "conversion_rate": 0.21},
            {"channel": "E-commerce", "week": "2025-W04", "revenue": 94500, "orders": 96, "conversion_rate": 0.27},
            {"channel": "Wholesale", "week": "2025-W04", "revenue": 110400, "orders": 54, "conversion_rate": 0.18},
        ],
        "notes": ["Mix semanal por canal."],
    },
    "ventas_ticket_medio": {
        "data": [
            {"date": "2025-01-29", "channel": "E-commerce", "avg_ticket": 1420, "transactions": 88},
            {"date": "2025-01-30", "channel": "E-commerce", "avg_ticket": 1395, "transactions": 92},
            {"date": "2025-01-31", "channel": "E-commerce", "avg_ticket": 1442, "transactions": 97},
            {"date": "2025-02-01", "channel": "E-commerce", "avg_ticket": 1468, "transactions": 101},
            {"date": "2025-02-02", "channel": "Retail", "avg_ticket": 1184, "transactions": 76},
            {"date": "2025-02-03", "channel": "Retail", "avg_ticket": 1205, "transactions": 79},
        ],
        "notes": ["Ticket medio y transacciones por canal (últimos 6 días)."],
    },
    "clientes_churn_ltv": {
        "data": [
            {"month": "2024-09", "churn_rate": 0.07, "retention_rate": 0.78, "ltv": 11800},
            {"month": "2024-10", "churn_rate": 0.065, "retention_rate": 0.8, "ltv": 12250},
            {"month": "2024-11", "churn_rate": 0.06, "retention_rate": 0.82, "ltv": 13000},
            {"month": "2024-12", "churn_rate": 0.058, "retention_rate": 0.83, "ltv": 13450},
            {"month": "2025-01", "churn_rate": 0.064, "retention_rate": 0.81, "ltv": 12900},
            {"month": "2025-02", "churn_rate": 0.061, "retention_rate": 0.82, "ltv": 13120},
            {"month": "2025-03", "churn_rate": 0.055, "retention_rate": 0.84, "ltv": 13860},
            {"month": "2025-04", "churn_rate": 0.052, "retention_rate": 0.85, "ltv": 14200},
        ],
        "notes": ["Relación churn vs retención con tamaño proporcional al LTV promedio."],
    },
    "inventario_rotacion_cobertura": {
        "data": [
            {"product_family": "Electrónica", "warehouse": "Centro", "stock": 2450, "rotation_days": 38, "coverage_days": 26},
            {"product_family": "Electrónica", "warehouse": "Noroeste", "stock": 1280, "rotation_days": 34, "coverage_days": 22},
            {"product_family": "Hogar", "warehouse": "Centro", "stock": 1800, "rotation_days": 29, "coverage_days": 28},
            {"product_family": "Hogar", "warehouse": "Noroeste", "stock": 760, "rotation_days": 31, "coverage_days": 25},
        ],
        "notes": ["Cobertura objetivo: 30 días."],
    },
    "compras_cumplimiento": {
        "data": [
            {"supplier": "Acme Parts", "month": "2025-01", "orders": 68, "lead_time": 5.2, "compliance_rate": 0.92, "unit_cost_variance": -0.8},
            {"supplier": "Global Foods", "month": "2025-01", "orders": 44, "lead_time": 6.8, "compliance_rate": 0.86, "unit_cost_variance": 1.3},
            {"supplier": "Packaging Co", "month": "2025-01", "orders": 27, "lead_time": 4.7, "compliance_rate": 0.95, "unit_cost_variance": 0.4},
        ],
        "notes": ["Lead time medido en días, desvío de costo unitario en %."],
    },
    "ar_aging_dso": {
        "data": [
            {"aging_bucket": "0-30", "customer_segment": "Retail", "balance": 58400, "dso": 32, "overdue_amount": 0},
            {"aging_bucket": "31-60", "customer_segment": "Retail", "balance": 22600, "dso": 32, "overdue_amount": 6400},
            {"aging_bucket": "61-90", "customer_segment": "Enterprise", "balance": 19400, "dso": 45, "overdue_amount": 19400},
            {"aging_bucket": ">90", "customer_segment": "Enterprise", "balance": 8200, "dso": 45, "overdue_amount": 8200},
        ],
        "notes": ["DSO calculado con ventas promedio de 90 días."],
    },
    "ap_aging_dpo": {
        "data": [
            {"aging_bucket": "0-30", "supplier_group": "Materias primas", "balance": 46600, "dpo": 41, "discounts_lost": 0},
            {"aging_bucket": "31-60", "supplier_group": "Materias primas", "balance": 18800, "dpo": 41, "discounts_lost": 1200},
            {"aging_bucket": "61-90", "supplier_group": "Servicios", "balance": 9800, "dpo": 56, "discounts_lost": 980},
            {"aging_bucket": ">90", "supplier_group": "Servicios", "balance": 4300, "dpo": 56, "discounts_lost": 860},
        ],
        "notes": ["DPO medido contra promedio móvil 90 días."],
    },
    "logistica_otif": {
        "data": [
            {"route": "CABA Norte", "branch": "Centro", "otif": 95.4, "cycle_time": 2.1, "backorders": 4},
            {"route": "CABA Sur", "branch": "Centro", "otif": 93.6, "cycle_time": 2.4, "backorders": 6},
            {"route": "GBA Oeste", "branch": "Centro", "otif": 91.8, "cycle_time": 2.8, "backorders": 9},
            {"route": "GBA Norte", "branch": "Centro", "otif": 96.2, "cycle_time": 2.0, "backorders": 3},
        ],
        "notes": ["OTIF objetivo >= 95%."],
    },
    # Placeholders de catálogo hasta conectar motor legacy / relay en query_runner.
    "mayoristapp-devoluciones": {
        "data": [
            {
                "estado": "Vista previa",
                "detalle": "El informe aparecerá en el catálogo; datos reales al conectar el relay de devoluciones.",
                "lineas": 0,
            },
        ],
        "notes": ["Estado: placeholder de catálogo (mayoristapp)."],
    },
    "mayoristapp-filtros-estadisticas": {
        "data": [
            {
                "estado": "Vista previa",
                "detalle": "Listados de filtros para estadísticas; datos reales al conectar el relay de filtros.",
                "lineas": 0,
            },
        ],
        "notes": ["Estado: placeholder de catálogo (mayoristapp)."],
    },
    "mayoristapp-comprobantes-no-cancelados": {
        "data": [
            {
                "estado": "Vista previa",
                "detalle": "Comprobantes no cancelados; datos reales al conectar el relay de listado.",
                "lineas": 0,
            },
        ],
        "notes": ["Estado: placeholder de catálogo (mayoristapp)."],
    },
}


def get_sample_data(slug: str, payload: Dict) -> Tuple[Dict, List[Dict], Dict, List[str]]:
    """Retorna meta, datos, totales y notas para un slug dado."""
    sample = SAMPLE_DATA.get(slug)
    if not sample:
        return DEFAULT_META, [], {}, []

    data: List[Dict] = sample.get("data", [])
    totals: Dict = sample.get("totals") or _calculate_totals(data)
    notes: List[str] = sample.get("notes", [])

    return DEFAULT_META.copy(), data, totals, notes


def _calculate_totals(data: List[Dict]) -> Dict:
    totals: Dict[str, float] = defaultdict(float)
    for row in data:
        for key, value in row.items():
            if isinstance(value, (int, float)):
                totals[key] += value
    return dict(totals)


