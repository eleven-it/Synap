"""
Comando para crear plantillas de reportes del sistema.

Ejecutar: python manage.py create_report_templates
"""
from django.core.management.base import BaseCommand
from reports.models import ReportTemplate


class Command(BaseCommand):
    help = 'Crea plantillas de reportes del sistema'

    def handle(self, *args, **options):
        self.stdout.write('Creando plantillas de reportes del sistema...')
        
        templates_data = [
            {
                'name': 'Ventas por Mes',
                'description': 'Reporte de ventas agrupadas por mes con totales y promedios',
                'category': 'operational',
                'config': {
                    'version': 'declarative-v1',
                    'datasource': 'cuentacliente',
                    'metrics': {
                        'ventas_totales': {
                            'expression': 'SUM(importeventa)',
                            'depends_on': []
                        },
                        'cantidad_comprobantes': {
                            'expression': 'COUNT(DISTINCT nrocomprobante)',
                            'depends_on': []
                        },
                        'ticket_promedio': {
                            'expression': 'SUM(importeventa) / NULLIF(COUNT(DISTINCT nrocomprobante), 0)',
                            'depends_on': ['ventas_totales', 'cantidad_comprobantes']
                        }
                    },
                    'dimensions': {
                        'fecha_mes': {
                            'expression': "DATE_FORMAT(fecha, '%Y-%m')"
                        }
                    },
                    'filters': [
                        {
                            'name': 'filtro_fecha',
                            'field': 'fecha',
                            'operator': 'BETWEEN',
                            'param': 'fecha_inicio,fecha_fin'
                        }
                    ],
                    'group_by': ['fecha_mes'],
                    'order_by': ['fecha_mes ASC'],
                    'joins': None,
                    'notes': None,
                    'options': {}
                },
                'widgets': [
                    {
                        'name': 'Gráfico de Ventas',
                        'widget_type': 'd3-line',
                        'order': 0,
                        'layout': {'cols': 12, 'rows': 4},
                        'configuration': {
                            'x_dimension': 'fecha_mes',
                            'y_metrics': ['ventas_totales'],
                            'series_dimension': '',
                            'options': {}
                        }
                    },
                    {
                        'name': 'Tabla de Resumen',
                        'widget_type': 'table',
                        'order': 1,
                        'layout': {'cols': 12, 'rows': 4},
                        'configuration': {
                            'x_dimension': 'fecha_mes',
                            'y_metrics': ['ventas_totales', 'cantidad_comprobantes', 'ticket_promedio'],
                            'series_dimension': '',
                            'options': {}
                        }
                    }
                ]
            },
            {
                'name': 'Ventas por Sucursal',
                'description': 'Reporte de ventas agrupadas por sucursal',
                'category': 'operational',
                'config': {
                    'version': 'declarative-v1',
                    'datasource': 'cuentacliente',
                    'metrics': {
                        'ventas_totales': {
                            'expression': 'SUM(importeventa)',
                            'depends_on': []
                        },
                        'cantidad_comprobantes': {
                            'expression': 'COUNT(DISTINCT nrocomprobante)',
                            'depends_on': []
                        }
                    },
                    'dimensions': {
                        'sucursal': {
                            'expression': 'CodSucursal'
                        }
                    },
                    'filters': [
                        {
                            'name': 'filtro_fecha',
                            'field': 'fecha',
                            'operator': 'BETWEEN',
                            'param': 'fecha_inicio,fecha_fin'
                        }
                    ],
                    'group_by': ['sucursal'],
                    'order_by': ['ventas_totales DESC'],
                    'joins': None,
                    'notes': None,
                    'options': {}
                },
                'widgets': [
                    {
                        'name': 'Tabla de Sucursales',
                        'widget_type': 'table',
                        'order': 0,
                        'layout': {'cols': 12, 'rows': 6},
                        'configuration': {
                            'x_dimension': 'sucursal',
                            'y_metrics': ['ventas_totales', 'cantidad_comprobantes'],
                            'series_dimension': '',
                            'options': {}
                        }
                    }
                ]
            },
            {
                'name': 'Ticket Promedio',
                'description': 'Calcula el ticket promedio (ventas totales / cantidad de comprobantes)',
                'category': 'operational',
                'config': {
                    'version': 'declarative-v1',
                    'datasource': 'cuentacliente',
                    'metrics': {
                        'ticket_promedio': {
                            'expression': 'SUM(importeventa) / NULLIF(COUNT(DISTINCT nrocomprobante), 0)',
                            'depends_on': []
                        },
                        'ventas_totales': {
                            'expression': 'SUM(importeventa)',
                            'depends_on': []
                        },
                        'cantidad_comprobantes': {
                            'expression': 'COUNT(DISTINCT nrocomprobante)',
                            'depends_on': []
                        }
                    },
                    'dimensions': {
                        'fecha_mes': {
                            'expression': "DATE_FORMAT(fecha, '%Y-%m')"
                        }
                    },
                    'filters': [
                        {
                            'name': 'filtro_fecha',
                            'field': 'fecha',
                            'operator': 'BETWEEN',
                            'param': 'fecha_inicio,fecha_fin'
                        }
                    ],
                    'group_by': ['fecha_mes'],
                    'order_by': ['fecha_mes ASC'],
                    'joins': None,
                    'notes': None,
                    'options': {}
                },
                'widgets': [
                    {
                        'name': 'Evolución Ticket Promedio',
                        'widget_type': 'd3-line',
                        'order': 0,
                        'layout': {'cols': 12, 'rows': 4},
                        'configuration': {
                            'x_dimension': 'fecha_mes',
                            'y_metrics': ['ticket_promedio'],
                            'series_dimension': '',
                            'options': {}
                        }
                    }
                ]
            },
            {
                'name': 'Top Clientes',
                'description': 'Reporte de los clientes con mayores ventas',
                'category': 'managerial',
                'config': {
                    'version': 'declarative-v1',
                    'datasource': 'cuentacliente',
                    'metrics': {
                        'ventas_totales': {
                            'expression': 'SUM(importeventa)',
                            'depends_on': []
                        },
                        'cantidad_comprobantes': {
                            'expression': 'COUNT(DISTINCT nrocomprobante)',
                            'depends_on': []
                        }
                    },
                    'dimensions': {
                        'cliente': {
                            'expression': 'CodCliente'
                        }
                    },
                    'filters': [
                        {
                            'name': 'filtro_fecha',
                            'field': 'fecha',
                            'operator': 'BETWEEN',
                            'param': 'fecha_inicio,fecha_fin'
                        }
                    ],
                    'group_by': ['cliente'],
                    'order_by': ['ventas_totales DESC'],
                    'joins': None,
                    'notes': None,
                    'options': {}
                },
                'widgets': [
                    {
                        'name': 'Top 10 Clientes',
                        'widget_type': 'table',
                        'order': 0,
                        'layout': {'cols': 12, 'rows': 6},
                        'configuration': {
                            'x_dimension': 'cliente',
                            'y_metrics': ['ventas_totales', 'cantidad_comprobantes'],
                            'series_dimension': '',
                            'options': {'limit': 10}
                        }
                    }
                ]
            }
        ]
        
        created_count = 0
        for template_data in templates_data:
            # Verificar si ya existe
            if ReportTemplate.objects.filter(name=template_data['name'], is_system=True).exists():
                self.stdout.write(self.style.WARNING(f'  Plantilla "{template_data["name"]}" ya existe, omitiendo...'))
                continue
            
            template = ReportTemplate(
                name=template_data['name'],
                description=template_data['description'],
                category=template_data['category'],
                config=template_data['config'],
                widgets=template_data['widgets'],
                is_system=True,
                created_by=None  # Plantillas del sistema sin creador
            )
            template.save()
            created_count += 1
            self.stdout.write(self.style.SUCCESS(f'  ✓ Creada: {template_data["name"]}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ {created_count} plantilla(s) creada(s) exitosamente.'))





