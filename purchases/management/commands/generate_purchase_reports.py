from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg
from django.contrib.auth import get_user_model
from datetime import timedelta
import csv
import json
from io import StringIO

from purchases.models import (
    PurchaseRequest, PurchaseOrder, PurchaseQuotation, PurchaseReceipt,
    Supplier, SupplierRating
)
from core.models import Empresa

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate advanced purchase reports with analytics and exports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa',
            type=int,
            help='ID of the company to generate reports for',
        )
        parser.add_argument(
            '--report-type',
            type=str,
            choices=['summary', 'supplier_performance', 'spending_analysis', 'delivery_performance', 'all'],
            default='all',
            help='Type of report to generate',
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for the report period (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for the report period (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--output-format',
            type=str,
            choices=['json', 'csv', 'console'],
            default='console',
            help='Output format for the report',
        )
        parser.add_argument(
            '--output-file',
            type=str,
            help='Output file path (for JSON and CSV formats)',
        )

    def handle(self, *args, **options):
        empresa_id = options['empresa']
        report_type = options['report_type']
        start_date = options['start_date']
        end_date = options['end_date']
        output_format = options['output_format']
        output_file = options['output_file']

        if not empresa_id:
            self.stdout.write(
                self.style.ERROR('Debe especificar el ID de la empresa con --empresa')
            )
            return

        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Empresa con ID {empresa_id} no encontrada')
            )
            return

        # Procesar fechas
        if start_date:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            start_date = timezone.now().date() - timedelta(days=90)

        if end_date:
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()

        self.stdout.write(
            self.style.SUCCESS(f'Generando reportes para empresa: {empresa.name}')
        )
        self.stdout.write(f'Período: {start_date} a {end_date}')

        # Generar reportes
        reports = {}

        if report_type in ['summary', 'all']:
            reports['summary'] = self._generate_summary_report(empresa, start_date, end_date)

        if report_type in ['supplier_performance', 'all']:
            reports['supplier_performance'] = self._generate_supplier_performance_report(empresa, start_date, end_date)

        if report_type in ['spending_analysis', 'all']:
            reports['spending_analysis'] = self._generate_spending_analysis_report(empresa, start_date, end_date)

        if report_type in ['delivery_performance', 'all']:
            reports['delivery_performance'] = self._generate_delivery_performance_report(empresa, start_date, end_date)

        # Generar reporte consolidado
        consolidated_report = {
            'metadata': {
                'empresa': empresa.name,
                'empresa_id': empresa.id,
                'generated_at': timezone.now().isoformat(),
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': (end_date - start_date).days
                }
            },
            'reports': reports
        }

        # Exportar reporte
        self._export_report(consolidated_report, output_format, output_file)

        self.stdout.write(
            self.style.SUCCESS('Reportes generados exitosamente')
        )

    def _generate_summary_report(self, empresa, start_date, end_date):
        """Generar reporte resumen"""
        # Solicitudes
        total_requests = PurchaseRequest.objects.filter(
            empresa=empresa,
            request_date__range=[start_date, end_date]
        ).count()

        approved_requests = PurchaseRequest.objects.filter(
            empresa=empresa,
            status='approved',
            request_date__range=[start_date, end_date]
        ).count()

        rejected_requests = PurchaseRequest.objects.filter(
            empresa=empresa,
            status='rejected',
            request_date__range=[start_date, end_date]
        ).count()

        # Órdenes
        total_orders = PurchaseOrder.objects.filter(
            empresa=empresa,
            order_date__range=[start_date, end_date]
        ).count()

        total_spent = PurchaseOrder.objects.filter(
            empresa=empresa,
            status__in=['confirmed', 'partially_received', 'received'],
            order_date__range=[start_date, end_date]
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        # Cotizaciones
        total_quotations = PurchaseQuotation.objects.filter(
            empresa=empresa,
            quotation_date__range=[start_date, end_date]
        ).count()

        # Recepciones
        total_receipts = PurchaseReceipt.objects.filter(
            empresa=empresa,
            receipt_date__range=[start_date, end_date]
        ).count()

        # Proveedores activos
        active_suppliers = Supplier.objects.filter(
            empresa=empresa,
            is_active=True
        ).count()

        # Métricas de rendimiento
        approval_rate = (approved_requests / total_requests * 100) if total_requests > 0 else 0
        rejection_rate = (rejected_requests / total_requests * 100) if total_requests > 0 else 0
        avg_order_value = total_spent / total_orders if total_orders > 0 else 0

        return {
            'requests': {
                'total': total_requests,
                'approved': approved_requests,
                'rejected': rejected_requests,
                'approval_rate': round(approval_rate, 2),
                'rejection_rate': round(rejection_rate, 2)
            },
            'orders': {
                'total': total_orders,
                'total_spent': float(total_spent),
                'average_order_value': round(avg_order_value, 2)
            },
            'quotations': {
                'total': total_quotations
            },
            'receipts': {
                'total': total_receipts
            },
            'suppliers': {
                'active': active_suppliers
            }
        }

    def _generate_supplier_performance_report(self, empresa, start_date, end_date):
        """Generar reporte de rendimiento de proveedores"""
        # Obtener métricas de proveedores
        supplier_metrics = []
        
        suppliers = Supplier.objects.filter(empresa=empresa, is_active=True)
        
        for supplier in suppliers:
            # Órdenes del proveedor
            orders = PurchaseOrder.objects.filter(
                supplier=supplier,
                order_date__range=[start_date, end_date]
            )
            
            total_orders = orders.count()
            total_spent = orders.aggregate(total=Sum('total_amount'))['total'] or 0
            
            # Recepciones
            receipts = PurchaseReceipt.objects.filter(
                purchase_order_line__purchase_order__supplier=supplier,
                receipt_date__range=[start_date, end_date]
            )
            
            total_receipts = receipts.count()
            avg_quality_score = receipts.aggregate(avg=Avg('quality_score'))['avg'] or 0
            
            # Evaluaciones
            ratings = SupplierRating.objects.filter(
                supplier=supplier,
                rating_date__range=[start_date, end_date]
            )
            
            avg_rating = ratings.aggregate(avg=Avg('overall_score'))['avg'] or 0
            
            # Calcular métricas de entrega
            on_time_deliveries = 0
            total_deliveries = 0
            
            for order in orders.filter(status__in=['partially_received', 'received']):
                if order.last_receipt_date and order.expected_delivery_date:
                    if order.last_receipt_date <= order.expected_delivery_date:
                        on_time_deliveries += 1
                    total_deliveries += 1
            
            on_time_rate = (on_time_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
            
            supplier_metrics.append({
                'supplier_id': supplier.id,
                'supplier_name': supplier.name,
                'supplier_code': supplier.code,
                'total_orders': total_orders,
                'total_spent': float(total_spent),
                'total_receipts': total_receipts,
                'average_quality_score': round(avg_quality_score, 2),
                'average_rating': round(avg_rating, 2),
                'on_time_delivery_rate': round(on_time_rate, 2),
                'rating_class': supplier.rating_class
            })
        
        # Ordenar por rendimiento
        supplier_metrics.sort(key=lambda x: x['average_rating'], reverse=True)
        
        return {
            'suppliers': supplier_metrics,
            'summary': {
                'total_suppliers': len(supplier_metrics),
                'average_rating': round(sum(s['average_rating'] for s in supplier_metrics) / len(supplier_metrics), 2) if supplier_metrics else 0,
                'average_quality_score': round(sum(s['average_quality_score'] for s in supplier_metrics) / len(supplier_metrics), 2) if supplier_metrics else 0,
                'average_on_time_rate': round(sum(s['on_time_delivery_rate'] for s in supplier_metrics) / len(supplier_metrics), 2) if supplier_metrics else 0
            }
        }

    def _generate_spending_analysis_report(self, empresa, start_date, end_date):
        """Generar reporte de análisis de gastos"""
        # Gastos por mes
        monthly_spending = []
        current_date = start_date
        
        while current_date <= end_date:
            month_start = current_date.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            month_total = PurchaseOrder.objects.filter(
                empresa=empresa,
                status__in=['confirmed', 'partially_received', 'received'],
                order_date__range=[month_start, month_end]
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            monthly_spending.append({
                'month': current_date.strftime('%Y-%m'),
                'month_name': current_date.strftime('%B %Y'),
                'total': float(month_total),
                'orders_count': PurchaseOrder.objects.filter(
                    empresa=empresa,
                    order_date__range=[month_start, month_end]
                ).count()
            })
            
            current_date = (current_date + timedelta(days=32)).replace(day=1)

        # Gastos por proveedor
        spending_by_supplier = []
        suppliers = Supplier.objects.filter(empresa=empresa)
        
        for supplier in suppliers:
            total_spent = PurchaseOrder.objects.filter(
                supplier=supplier,
                status__in=['confirmed', 'partially_received', 'received'],
                order_date__range=[start_date, end_date]
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            if total_spent > 0:
                spending_by_supplier.append({
                    'supplier_id': supplier.id,
                    'supplier_name': supplier.name,
                    'total_spent': float(total_spent),
                    'orders_count': PurchaseOrder.objects.filter(
                        supplier=supplier,
                        order_date__range=[start_date, end_date]
                    ).count()
                })
        
        # Ordenar por monto gastado
        spending_by_supplier.sort(key=lambda x: x['total_spent'], reverse=True)

        return {
            'monthly_spending': monthly_spending,
            'spending_by_supplier': spending_by_supplier,
            'summary': {
                'total_spent': sum(s['total_spent'] for s in spending_by_supplier),
                'average_monthly_spending': sum(m['total'] for m in monthly_spending) / len(monthly_spending) if monthly_spending else 0,
                'top_supplier': spending_by_supplier[0] if spending_by_supplier else None
            }
        }

    def _generate_delivery_performance_report(self, empresa, start_date, end_date):
        """Generar reporte de rendimiento de entregas"""
        # Órdenes vencidas
        overdue_orders = PurchaseOrder.objects.filter(
            empresa=empresa,
            status__in=['sent', 'confirmed'],
            expected_delivery_date__lt=timezone.now().date(),
            order_date__range=[start_date, end_date]
        ).count()

        # Órdenes a tiempo
        on_time_orders = PurchaseOrder.objects.filter(
            empresa=empresa,
            status__in=['partially_received', 'received'],
            order_date__range=[start_date, end_date]
        ).filter(
            Q(last_receipt_date__lte=F('expected_delivery_date')) |
            Q(last_receipt_date__isnull=True, expected_delivery_date__gte=timezone.now().date())
        ).count()

        # Total de órdenes para cálculo
        total_orders = PurchaseOrder.objects.filter(
            empresa=empresa,
            order_date__range=[start_date, end_date]
        ).count()

        # Promedio de días de entrega
        delivery_times = []
        orders_with_delivery = PurchaseOrder.objects.filter(
            empresa=empresa,
            status__in=['partially_received', 'received'],
            last_receipt_date__isnull=False,
            order_date__range=[start_date, end_date]
        )

        for order in orders_with_delivery:
            if order.last_receipt_date and order.order_date:
                days = (order.last_receipt_date - order.order_date).days
                delivery_times.append(days)

        avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0

        # Análisis por proveedor
        supplier_delivery_analysis = []
        suppliers = Supplier.objects.filter(empresa=empresa)
        
        for supplier in suppliers:
            supplier_orders = PurchaseOrder.objects.filter(
                supplier=supplier,
                order_date__range=[start_date, end_date]
            )
            
            supplier_on_time = supplier_orders.filter(
                status__in=['partially_received', 'received']
            ).filter(
                Q(last_receipt_date__lte=F('expected_delivery_date')) |
                Q(last_receipt_date__isnull=True, expected_delivery_date__gte=timezone.now().date())
            ).count()
            
            supplier_total = supplier_orders.count()
            supplier_on_time_rate = (supplier_on_time / supplier_total * 100) if supplier_total > 0 else 0
            
            if supplier_total > 0:
                supplier_delivery_analysis.append({
                    'supplier_id': supplier.id,
                    'supplier_name': supplier.name,
                    'total_orders': supplier_total,
                    'on_time_orders': supplier_on_time,
                    'on_time_rate': round(supplier_on_time_rate, 2)
                })

        return {
            'overdue_orders': overdue_orders,
            'on_time_orders': on_time_orders,
            'total_orders': total_orders,
            'on_time_rate': round((on_time_orders / total_orders * 100) if total_orders > 0 else 0, 2),
            'average_delivery_time': round(avg_delivery_time, 1),
            'supplier_analysis': supplier_delivery_analysis
        }

    def _export_report(self, report, output_format, output_file):
        """Exportar reporte en el formato especificado"""
        if output_format == 'json':
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                self.stdout.write(f'Reporte exportado a: {output_file}')
            else:
                self.stdout.write(json.dumps(report, indent=2, ensure_ascii=False))

        elif output_format == 'csv':
            if not output_file:
                output_file = f'purchase_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Escribir metadatos
                writer.writerow(['Reporte de Compras - Synap'])
                writer.writerow(['Empresa', report['metadata']['empresa']])
                writer.writerow(['Período', f"{report['metadata']['period']['start_date']} a {report['metadata']['period']['end_date']}"])
                writer.writerow(['Generado', report['metadata']['generated_at']])
                writer.writerow([])
                
                # Escribir resumen
                if 'summary' in report['reports']:
                    writer.writerow(['RESUMEN'])
                    summary = report['reports']['summary']
                    writer.writerow(['Solicitudes Totales', summary['requests']['total']])
                    writer.writerow(['Solicitudes Aprobadas', summary['requests']['approved']])
                    writer.writerow(['Tasa de Aprobación', f"{summary['requests']['approval_rate']}%"])
                    writer.writerow(['Órdenes Totales', summary['orders']['total']])
                    writer.writerow(['Monto Total Gastado', f"${summary['orders']['total_spent']:,.2f}"])
                    writer.writerow(['Valor Promedio de Orden', f"${summary['orders']['average_order_value']:,.2f}"])
                    writer.writerow([])
                
                # Escribir rendimiento de proveedores
                if 'supplier_performance' in report['reports']:
                    writer.writerow(['RENDIMIENTO DE PROVEEDORES'])
                    writer.writerow(['Proveedor', 'Órdenes', 'Monto Total', 'Calificación Promedio', 'Tasa Entrega a Tiempo'])
                    
                    for supplier in report['reports']['supplier_performance']['suppliers']:
                        writer.writerow([
                            supplier['supplier_name'],
                            supplier['total_orders'],
                            f"${supplier['total_spent']:,.2f}",
                            supplier['average_rating'],
                            f"{supplier['on_time_delivery_rate']}%"
                        ])
                    writer.writerow([])
                
                # Escribir análisis de gastos
                if 'spending_analysis' in report['reports']:
                    writer.writerow(['ANÁLISIS DE GASTOS POR MES'])
                    writer.writerow(['Mes', 'Monto Total', 'Número de Órdenes'])
                    
                    for month in report['reports']['spending_analysis']['monthly_spending']:
                        writer.writerow([
                            month['month_name'],
                            f"${month['total']:,.2f}",
                            month['orders_count']
                        ])
                    writer.writerow([])
            
            self.stdout.write(f'Reporte exportado a: {output_file}')

        else:  # console
            self._print_console_report(report)

    def _print_console_report(self, report):
        """Imprimir reporte en consola"""
        metadata = report['metadata']
        reports = report['reports']
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(f'REPORTE DE COMPRAS - {metadata["empresa"].upper()}')
        self.stdout.write('='*60)
        self.stdout.write(f'Período: {metadata["period"]["start_date"]} a {metadata["period"]["end_date"]}')
        self.stdout.write(f'Generado: {metadata["generated_at"]}')
        self.stdout.write('='*60)
        
        if 'summary' in reports:
            self.stdout.write('\n📊 RESUMEN')
            self.stdout.write('-'*30)
            summary = reports['summary']
            self.stdout.write(f'Solicitudes Totales: {summary["requests"]["total"]}')
            self.stdout.write(f'Solicitudes Aprobadas: {summary["requests"]["approved"]}')
            self.stdout.write(f'Tasa de Aprobación: {summary["requests"]["approval_rate"]}%')
            self.stdout.write(f'Órdenes Totales: {summary["orders"]["total"]}')
            self.stdout.write(f'Monto Total Gastado: ${summary["orders"]["total_spent"]:,.2f}')
            self.stdout.write(f'Valor Promedio de Orden: ${summary["orders"]["average_order_value"]:,.2f}')
        
        if 'supplier_performance' in reports:
            self.stdout.write('\n🏆 RENDIMIENTO DE PROVEEDORES')
            self.stdout.write('-'*40)
            suppliers = reports['supplier_performance']['suppliers'][:10]  # Top 10
            
            for i, supplier in enumerate(suppliers, 1):
                self.stdout.write(f'{i}. {supplier["supplier_name"]}')
                self.stdout.write(f'   Órdenes: {supplier["total_orders"]} | '
                                f'Monto: ${supplier["total_spent"]:,.2f} | '
                                f'Calificación: {supplier["average_rating"]}/10 | '
                                f'Entrega a tiempo: {supplier["on_time_delivery_rate"]}%')
        
        if 'spending_analysis' in reports:
            self.stdout.write('\n💰 ANÁLISIS DE GASTOS')
            self.stdout.write('-'*30)
            spending = reports['spending_analysis']
            
            self.stdout.write('Gastos por Mes:')
            for month in spending['monthly_spending']:
                self.stdout.write(f'  {month["month_name"]}: ${month["total"]:,.2f} ({month["orders_count"]} órdenes)')
            
            if spending['summary']['top_supplier']:
                top_supplier = spending['summary']['top_supplier']
                self.stdout.write(f'\nProveedor con mayor gasto: {top_supplier["supplier_name"]}')
                self.stdout.write(f'Monto: ${top_supplier["total_spent"]:,.2f}')
        
        if 'delivery_performance' in reports:
            self.stdout.write('\n🚚 RENDIMIENTO DE ENTREGAS')
            self.stdout.write('-'*35)
            delivery = reports['delivery_performance']
            self.stdout.write(f'Órdenes a tiempo: {delivery["on_time_orders"]}/{delivery["total_orders"]}')
            self.stdout.write(f'Tasa de entrega a tiempo: {delivery["on_time_rate"]}%')
            self.stdout.write(f'Órdenes vencidas: {delivery["overdue_orders"]}')
            self.stdout.write(f'Tiempo promedio de entrega: {delivery["average_delivery_time"]} días')
        
        self.stdout.write('\n' + '='*60) 