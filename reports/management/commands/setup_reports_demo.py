from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Empresa, UsuarioExtendido
from reports.models import Report, ReportTemplate, ReportComponent, ReportSchedule
import json

User = get_user_model()

class Command(BaseCommand):
    help = 'Setup demo data for the reports module'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up reports demo data...'))
        
        # Get the first empresa and user
        try:
            empresa = Empresa.objects.first()
            if not empresa:
                self.stdout.write(self.style.ERROR('No empresa found. Please create an empresa first.'))
                return
            
            # Get user from branches of the empresa
            user = UsuarioExtendido.objects.filter(branches__empresa=empresa).first()
            if not user:
                self.stdout.write(self.style.ERROR('No user found for this empresa.'))
                return
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error getting empresa/user: {e}'))
            return

        # Create templates
        templates = self.create_templates(empresa, user)
        
        # Create reports
        reports = self.create_reports(empresa, user, templates)
        
        # Create schedules
        self.create_schedules(empresa, user, reports)
        
        self.stdout.write(self.style.SUCCESS('Reports demo data setup completed successfully!'))

    def create_templates(self, empresa, user):
        """Create demo templates"""
        templates_data = [
            {
                'name': 'Sales Report Template',
                'description': 'Template for monthly sales reports with charts and metrics',
                'category': 'sales'
            },
            {
                'name': 'Financial Summary Template',
                'description': 'Template for financial reports with balance sheets and income statements',
                'category': 'financial'
            },
            {
                'name': 'Inventory Report Template',
                'description': 'Template for inventory reports with stock levels and movements',
                'category': 'inventory'
            },
            {
                'name': 'Executive Dashboard Template',
                'description': 'High-level dashboard template for executive summaries',
                'category': 'executive'
            }
        ]
        
        templates = []
        for template_data in templates_data:
            template, created = ReportTemplate.objects.get_or_create(
                name=template_data['name'],
                empresa=empresa,
                defaults={
                    'description': template_data['description'],
                    'category': template_data['category'],
                    'layout_schema': {},
                    'default_data': {},
                    'styling': {}
                }
            )
            templates.append(template)
            
            if created:
                self.stdout.write(f'Created template: {template.name}')
            else:
                self.stdout.write(f'Template already exists: {template.name}')
        
        return templates

    def create_reports(self, empresa, user, templates):
        """Create demo reports"""
        reports_data = [
            {
                'name': 'Monthly Sales Report',
                'description': 'Comprehensive monthly sales analysis with trends and forecasts',
                'template': templates[0] if templates else None
            },
            {
                'name': 'Q4 Financial Summary',
                'description': 'Quarterly financial performance summary for stakeholders',
                'template': templates[1] if len(templates) > 1 else None
            },
            {
                'name': 'Inventory Status Report',
                'description': 'Current inventory levels and stock movement analysis',
                'template': templates[2] if len(templates) > 2 else None
            },
            {
                'name': 'Executive Dashboard',
                'description': 'High-level business metrics and KPIs for executives',
                'template': templates[3] if len(templates) > 3 else None
            }
        ]
        
        reports = []
        for report_data in reports_data:
            # Get a branch for this empresa
            branch = empresa.branches.first()
            if not branch:
                self.stdout.write(self.style.ERROR(f'No branch found for empresa {empresa.nombre}'))
                continue
                
            report, created = Report.objects.get_or_create(
                name=report_data['name'],
                empresa=empresa,
                defaults={
                    'description': report_data['description'],
                    'template': report_data['template'],
                    'branch': branch,
                    'created_by': user,
                    'layout_config': {},
                    'data_sources': [],
                    'filters': {},
                    'branding': {}
                }
            )
            reports.append(report)
            
            if created:
                self.stdout.write(f'Created report: {report.name}')
                # Add some demo components
                self.add_demo_components(report, user)
            else:
                self.stdout.write(f'Report already exists: {report.name}')
        
        return reports

    def add_demo_components(self, report, user):
        """Add demo components to a report"""
        components_data = [
            {
                'name': 'Report Title',
                'component_type': 'title',
                'config': json.dumps({
                    'text': report.name,
                    'size': 'h1'
                })
            },
            {
                'name': 'Executive Summary',
                'component_type': 'text',
                'config': json.dumps({
                    'content': f'This {report.name.lower()} provides a comprehensive overview of our business performance. The data shows positive trends across key metrics and indicates strong growth potential for the upcoming period.'
                })
            },
            {
                'name': 'Sales Trend Chart',
                'component_type': 'line-chart',
                'config': json.dumps({
                    'title': 'Monthly Sales Trend',
                    'dataSource': 'sales'
                })
            },
            {
                'name': 'Key Metrics',
                'component_type': 'metric',
                'config': json.dumps({
                    'title': 'Total Revenue',
                    'value': '$125,000',
                    'format': 'currency'
                })
            }
        ]
        
        for i, component_data in enumerate(components_data):
            ReportComponent.objects.get_or_create(
                report=report,
                name=component_data['name'],
                defaults={
                    'component_type': component_data['component_type'],
                    'configuration': component_data['config'],
                    'data_source': '',
                    'styling': {},
                    'position': {'x': 0, 'y': i * 100, 'width': 400, 'height': 80},
                    'z_index': i
                }
            )

    def create_schedules(self, empresa, user, reports):
        """Create demo schedules"""
        schedules_data = [
            {
                'name': 'Monthly Sales Report Schedule',
                'report': reports[0] if reports else None,
                'frequency': 'monthly'
            },
            {
                'name': 'Quarterly Financial Report Schedule',
                'report': reports[1] if len(reports) > 1 else None,
                'frequency': 'quarterly'
            },
            {
                'name': 'Weekly Inventory Report Schedule',
                'report': reports[2] if len(reports) > 2 else None,
                'frequency': 'weekly'
            }
        ]
        
        for schedule_data in schedules_data:
            if schedule_data['report']:
                schedule, created = ReportSchedule.objects.get_or_create(
                    name=schedule_data['name'],
                    report=schedule_data['report'],
                    defaults={
                        'frequency': schedule_data['frequency'],
                        'cron_expression': '',
                        'recipients': ['admin@example.com'],
                        'export_format': 'pdf',
                        'subject_template': f'{schedule_data["name"]} - {{date}}',
                        'message_template': f'Please find attached the {schedule_data["name"]} for {{date}}.'
                    }
                )
                
                if created:
                    self.stdout.write(f'Created schedule: {schedule.name}')
                else:
                    self.stdout.write(f'Schedule already exists: {schedule.name}') 