import json
from django.template.loader import render_to_string
from django.conf import settings
from ..models import Report


class ExportService:
    """Servicio para exportación de reportes"""
    
    @staticmethod
    def generate_preview(report, format_type='html'):
        """Generar vista previa del reporte"""
        try:
            # Preparar datos del reporte
            context = {
                'report': report,
                'components': report.components.all().order_by('z_index'),
                'branding': report.branding or {},
                'data': report.data_sources or [],
            }
            
            if format_type == 'html':
                # Renderizar template HTML
                html_content = render_to_string('reports/export/pdf_template.html', context)
                return {
                    'success': True,
                    'content': html_content,
                    'format': 'html'
                }
            else:
                return {
                    'success': False,
                    'error': f'Formato {format_type} no soportado para preview'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def export_to_pdf(report):
        """Exportar reporte a PDF usando WeasyPrint"""
        try:
            # Importar WeasyPrint solo cuando sea necesario
            from weasyprint import HTML, CSS
            from django.template.loader import render_to_string
            
            # Preparar contexto
            context = {
                'report': report,
                'components': report.components.all().order_by('z_index'),
                'branding': report.branding or {},
                'data': report.data_sources or [],
            }
            
            # Renderizar HTML
            html_content = render_to_string('reports/export/pdf_template.html', context)
            
            # Generar CSS
            css_content = ExportService._get_pdf_styles()
            
            # Crear PDF
            html = HTML(string=html_content)
            css = CSS(string=css_content)
            pdf_bytes = html.write_pdf(stylesheets=[css])
            
            return pdf_bytes
            
        except ImportError:
            raise Exception("WeasyPrint no está instalado. Instale con: pip install weasyprint")
        except Exception as e:
            raise Exception(f"Error generando PDF: {str(e)}")
    
    @staticmethod
    def export_to_pptx(report):
        """Exportar reporte a PPTX usando python-pptx"""
        try:
            # Importar python-pptx solo cuando sea necesario
            from pptx import Presentation
            from pptx.util import Inches
            from io import BytesIO
            
            # Crear presentación
            prs = Presentation()
            
            # Slide de título
            title_slide = prs.slides.add_slide(prs.slide_layouts[0])
            title_slide.shapes.title.text = report.name
            if report.description:
                title_slide.placeholders[1].text = report.description
            
            # Slides de contenido
            for component in report.components.all().order_by('z_index'):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = component.name
                
                # Agregar contenido según el tipo
                if component.component_type == 'text':
                    content = slide.placeholders[1]
                    content.text = component.configuration.get('text', '')
                elif component.component_type == 'kpi':
                    content = slide.placeholders[1]
                    content.text = f"KPI: {component.configuration.get('value', 'N/A')}"
                else:
                    content = slide.placeholders[1]
                    content.text = f"Componente: {component.get_component_type_display()}"
            
            # Guardar en bytes
            output = BytesIO()
            prs.save(output)
            return output.getvalue()
            
        except ImportError:
            raise Exception("python-pptx no está instalado. Instale con: pip install python-pptx")
        except Exception as e:
            raise Exception(f"Error generando PPTX: {str(e)}")
    
    @staticmethod
    def _get_pdf_styles():
        """Obtener estilos CSS para PDF"""
        return """
        @page {
            size: A4;
            margin: 1in;
            @top-center {
                content: "{{ report.name }}";
                font-family: 'Plus Jakarta Sans', sans-serif;
                font-size: 10pt;
                color: #666;
            }
            @bottom-center {
                content: "Página " counter(page) " de " counter(pages);
                font-family: 'Plus Jakarta Sans', sans-serif;
                font-size: 10pt;
                color: #666;
            }
        }
        
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
        }
        
        .header {
            text-align: center;
            margin-bottom: 2em;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 1em;
        }
        
        .report-title {
            font-size: 24pt;
            font-weight: bold;
            color: #1f2937;
            margin-bottom: 0.5em;
        }
        
        .report-description {
            font-size: 12pt;
            color: #6b7280;
        }
        
        .component {
            margin: 1em 0;
            page-break-inside: avoid;
        }
        
        .chart-container {
            margin: 1em 0;
            text-align: center;
        }
        
        .kpi-card {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 1em;
            margin: 1em 0;
            text-align: center;
            background-color: #f9fafb;
        }
        
        .kpi-value {
            font-size: 24pt;
            font-weight: bold;
            color: #1f2937;
        }
        
        .kpi-label {
            font-size: 12pt;
            color: #6b7280;
            margin-top: 0.5em;
        }
        
        .table-container {
            margin: 1em 0;
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
        }
        
        th, td {
            border: 1px solid #e5e7eb;
            padding: 0.5em;
            text-align: left;
        }
        
        th {
            background-color: #f9fafb;
            font-weight: 600;
        }
        
        .text-content {
            margin: 1em 0;
            line-height: 1.8;
        }
        
        .footer {
            margin-top: 2em;
            padding-top: 1em;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            font-size: 10pt;
            color: #6b7280;
        }
        """ 