"""
Servicio de exportación avanzada para reportes
Genera PDF y PPTX con branding institucional y formato ejecutivo
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from io import BytesIO

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.platypus import PageBreak, KeepTogether, PageTemplate, Frame
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
except ImportError:
    # Fallback para desarrollo sin dependencias
    pass

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
except ImportError:
    # Fallback para desarrollo sin dependencias
    pass

from .ai_service import AIService

logger = logging.getLogger(__name__)

class ExportService:
    """Servicio de exportación avanzada"""
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.default_branding = {
            "primary_color": "#007bff",
            "secondary_color": "#6c757d",
            "accent_color": "#28a745",
            "text_color": "#333333",
            "background_color": "#ffffff",
            "font_family": "Helvetica",
            "logo_path": None,
            "company_name": "Synap",
            "tagline": "Sistema de Gestión Empresarial"
        }
    
    async def export_to_pdf(
        self,
        report_data: Dict[str, Any],
        branding: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> BytesIO:
        """Exportar reporte a PDF con branding institucional"""
        try:
            logger.info("Generando PDF con branding institucional")
            
            # Fusionar branding con valores por defecto
            branding = {**self.default_branding, **branding}
            
            # Crear buffer para el PDF
            buffer = BytesIO()
            
            # Crear documento PDF
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Crear estilos personalizados
            styles = self._create_pdf_styles(branding)
            
            # Crear elementos del documento
            story = []
            
            # Página de portada
            story.extend(self._create_pdf_cover_page(report_data, branding, styles))
            story.append(PageBreak())
            
            # Tabla de contenidos
            story.extend(self._create_pdf_toc(report_data, styles))
            story.append(PageBreak())
            
            # Contenido principal
            story.extend(self._create_pdf_content(report_data, branding, styles))
            
            # Construir PDF
            doc.build(story)
            
            # Agregar encabezados y pies de página
            self._add_pdf_headers_footers(buffer, branding)
            
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            logger.error(f"Error generando PDF: {e}")
            raise
    
    def _create_pdf_styles(self, branding: Dict[str, Any]) -> Dict[str, ParagraphStyle]:
        """Crear estilos personalizados para PDF"""
        styles = getSampleStyleSheet()
        
        # Estilo de título principal
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=HexColor(branding['primary_color']),
            fontName=branding['font_family']
        ))
        
        # Estilo de subtítulo
        styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            textColor=HexColor(branding['primary_color']),
            fontName=branding['font_family']
        ))
        
        # Estilo de encabezado de sección
        styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            textColor=HexColor(branding['secondary_color']),
            fontName=branding['font_family']
        ))
        
        # Estilo de texto normal
        styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            textColor=HexColor(branding['text_color']),
            fontName=branding['font_family']
        ))
        
        # Estilo de texto ejecutivo
        styles.add(ParagraphStyle(
            name='ExecutiveSummary',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=8,
            textColor=HexColor(branding['text_color']),
            fontName=branding['font_family'],
            leftIndent=20,
            rightIndent=20
        ))
        
        return styles
    
    def _create_pdf_cover_page(
        self,
        report_data: Dict[str, Any],
        branding: Dict[str, Any],
        styles: Dict[str, ParagraphStyle]
    ) -> List:
        """Crear página de portada del PDF"""
        elements = []
        
        # Logo de la empresa
        if branding.get('logo_path') and os.path.exists(branding['logo_path']):
            try:
                logo = Image(branding['logo_path'], width=2*inch, height=1*inch)
                logo.hAlign = 'CENTER'
                elements.append(logo)
                elements.append(Spacer(1, 20))
            except Exception as e:
                logger.warning(f"No se pudo cargar el logo: {e}")
        
        # Título del reporte
        title = Paragraph(report_data.get('title', 'Reporte'), styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Descripción
        if report_data.get('description'):
            desc = Paragraph(report_data['description'], styles['CustomNormal'])
            desc.alignment = TA_CENTER
            elements.append(desc)
            elements.append(Spacer(1, 30))
        
        # Información de la empresa
        company_info = f"""
        <b>{branding['company_name']}</b><br/>
        {branding['tagline']}<br/>
        Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
        company_para = Paragraph(company_info, styles['CustomNormal'])
        company_para.alignment = TA_CENTER
        elements.append(company_para)
        
        return elements
    
    def _create_pdf_toc(self, report_data: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> List:
        """Crear tabla de contenidos"""
        elements = []
        
        # Título de TOC
        toc_title = Paragraph("Tabla de Contenidos", styles['CustomHeading1'])
        elements.append(toc_title)
        elements.append(Spacer(1, 20))
        
        # Secciones del reporte
        sections = [
            "Resumen Ejecutivo",
            "Hallazgos Clave",
            "Análisis Detallado",
            "Recomendaciones",
            "Próximos Pasos"
        ]
        
        for i, section in enumerate(sections, 1):
            section_text = f"{i}. {section}"
            section_para = Paragraph(section_text, styles['CustomNormal'])
            elements.append(section_para)
            elements.append(Spacer(1, 8))
        
        return elements
    
    def _create_pdf_content(
        self,
        report_data: Dict[str, Any],
        branding: Dict[str, Any],
        styles: Dict[str, ParagraphStyle]
    ) -> List:
        """Crear contenido principal del PDF"""
        elements = []
        content = report_data.get('content', {})
        
        # Resumen Ejecutivo
        if content.get('executive_summary'):
            elements.append(Paragraph("Resumen Ejecutivo", styles['CustomHeading1']))
            elements.append(Spacer(1, 12))
            
            summary = Paragraph(content['executive_summary'], styles['ExecutiveSummary'])
            elements.append(summary)
            elements.append(PageBreak())
        
        # Hallazgos Clave
        if content.get('key_findings'):
            elements.append(Paragraph("Hallazgos Clave", styles['CustomHeading1']))
            elements.append(Spacer(1, 12))
            
            for finding in content['key_findings']:
                finding_text = f"• {finding}"
                finding_para = Paragraph(finding_text, styles['CustomNormal'])
                elements.append(finding_para)
                elements.append(Spacer(1, 6))
            
            elements.append(PageBreak())
        
        # Análisis Detallado
        if content.get('detailed_analysis'):
            elements.append(Paragraph("Análisis Detallado", styles['CustomHeading1']))
            elements.append(Spacer(1, 12))
            
            for section_name, section_content in content['detailed_analysis'].items():
                elements.append(Paragraph(section_name.title(), styles['CustomHeading2']))
                elements.append(Spacer(1, 8))
                
                section_para = Paragraph(section_content, styles['CustomNormal'])
                elements.append(section_para)
                elements.append(Spacer(1, 12))
        
        # Recomendaciones
        if content.get('recommendations'):
            elements.append(PageBreak())
            elements.append(Paragraph("Recomendaciones", styles['CustomHeading1']))
            elements.append(Spacer(1, 12))
            
            for i, rec in enumerate(content['recommendations'], 1):
                rec_text = f"{i}. {rec}"
                rec_para = Paragraph(rec_text, styles['CustomNormal'])
                elements.append(rec_para)
                elements.append(Spacer(1, 8))
        
        # Próximos Pasos
        if content.get('next_steps'):
            elements.append(PageBreak())
            elements.append(Paragraph("Próximos Pasos", styles['CustomHeading1']))
            elements.append(Spacer(1, 12))
            
            for step in content['next_steps']:
                step_text = f"• {step}"
                step_para = Paragraph(step_text, styles['CustomNormal'])
                elements.append(step_para)
                elements.append(Spacer(1, 6))
        
        return elements
    
    def _add_pdf_headers_footers(self, buffer: BytesIO, branding: Dict[str, Any]) -> None:
        """Agregar encabezados y pies de página al PDF"""
        try:
            # Crear nuevo PDF con encabezados y pies de página
            buffer.seek(0)
            reader = BytesIO(buffer.read())
            
            # Crear nuevo buffer para el PDF final
            final_buffer = BytesIO()
            
            # Aquí se implementaría la lógica para agregar encabezados y pies de página
            # Por simplicidad, se copia el contenido original
            final_buffer.write(reader.getvalue())
            final_buffer.seek(0)
            
            # Reemplazar el buffer original
            buffer.seek(0)
            buffer.write(final_buffer.getvalue())
            
        except Exception as e:
            logger.warning(f"No se pudieron agregar encabezados/pies de página: {e}")
    
    async def export_to_pptx(
        self,
        report_data: Dict[str, Any],
        branding: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> BytesIO:
        """Exportar reporte a PPTX con branding institucional"""
        try:
            logger.info("Generando PPTX con branding institucional")
            
            # Fusionar branding con valores por defecto
            branding = {**self.default_branding, **branding}
            
            # Crear presentación
            prs = Presentation()
            
            # Configurar slide master con branding
            self._setup_pptx_master(prs, branding)
            
            # Página de título
            self._create_pptx_title_slide(prs, report_data, branding)
            
            # Resumen ejecutivo
            self._create_pptx_executive_summary(prs, report_data, branding)
            
            # Hallazgos clave
            self._create_pptx_key_findings(prs, report_data, branding)
            
            # Análisis detallado
            self._create_pptx_detailed_analysis(prs, report_data, branding)
            
            # Recomendaciones
            self._create_pptx_recommendations(prs, report_data, branding)
            
            # Próximos pasos
            self._create_pptx_next_steps(prs, report_data, branding)
            
            # Guardar en buffer
            buffer = BytesIO()
            prs.save(buffer)
            buffer.seek(0)
            
            return buffer
            
        except Exception as e:
            logger.error(f"Error generando PPTX: {e}")
            raise
    
    def _setup_pptx_master(self, prs: Presentation, branding: Dict[str, Any]) -> None:
        """Configurar slide master con branding"""
        try:
            # Obtener slide master
            slide_master = prs.slide_masters[0]
            
            # Configurar colores del tema
            theme_colors = slide_master.theme.themeElements.clrScheme
            primary_color = self._hex_to_rgb(branding['primary_color'])
            secondary_color = self._hex_to_rgb(branding['secondary_color'])
            
            # Configurar colores del tema (simplificado)
            # En una implementación completa, se configurarían todos los colores del tema
            
        except Exception as e:
            logger.warning(f"No se pudo configurar el slide master: {e}")
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convertir color hexadecimal a RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _create_pptx_title_slide(self, prs: Presentation, report_data: Dict[str, Any], branding: Dict[str, Any]) -> None:
        """Crear slide de título"""
        try:
            # Usar layout de título
            slide_layout = prs.slide_layouts[0]  # Layout de título
            slide = prs.slides.add_slide(slide_layout)
            
            # Configurar título
            title = slide.shapes.title
            title.text = report_data.get('title', 'Reporte')
            
            # Configurar subtítulo
            subtitle = slide.placeholders[1]
            subtitle.text = f"{branding['company_name']}\n{datetime.now().strftime('%d/%m/%Y')}"
            
            # Aplicar colores de branding
            title.text_frame.paragraphs[0].font.color.rgb = RGBColor(*self._hex_to_rgb(branding['primary_color']))
            
        except Exception as e:
            logger.warning(f"Error creando slide de título: {e}")
    
    def _create_pptx_executive_summary(self, prs: Presentation, report_data: Dict[str, Any], branding: Dict[str, Any]) -> None:
        """Crear slide de resumen ejecutivo"""
        try:
            content = report_data.get('content', {})
            if not content.get('executive_summary'):
                return
            
            # Usar layout de contenido
            slide_layout = prs.slide_layouts[1]  # Layout de contenido
            slide = prs.slides.add_slide(slide_layout)
            
            # Configurar título
            title = slide.shapes.title
            title.text = "Resumen Ejecutivo"
            
            # Configurar contenido
            content_placeholder = slide.placeholders[1]
            content_placeholder.text = content['executive_summary']
            
            # Aplicar colores de branding
            title.text_frame.paragraphs[0].font.color.rgb = RGBColor(*self._hex_to_rgb(branding['primary_color']))
            
        except Exception as e:
            logger.warning(f"Error creando slide de resumen ejecutivo: {e}")
    
    def _create_pptx_key_findings(self, prs: Presentation, report_data: Dict[str, Any], branding: Dict[str, Any]) -> None:
        """Crear slide de hallazgos clave"""
        try:
            content = report_data.get('content', {})
            if not content.get('key_findings'):
                return
            
            # Usar layout de lista
            slide_layout = prs.slide_layouts[1]  # Layout de contenido
            slide = prs.slides.add_slide(slide_layout)
            
            # Configurar título
            title = slide.shapes.title
            title.text = "Hallazgos Clave"
            
            # Configurar lista de hallazgos
            content_placeholder = slide.placeholders[1]
            findings_text = "\n".join([f"• {finding}" for finding in content['key_findings']])
            content_placeholder.text = findings_text
            
            # Aplicar colores de branding
            title.text_frame.paragraphs[0].font.color.rgb = RGBColor(*self._hex_to_rgb(branding['primary_color']))
            
        except Exception as e:
            logger.warning(f"Error creando slide de hallazgos clave: {e}")
    
    def _create_pptx_detailed_analysis(self, prs: Presentation, report_data: Dict[str, Any], branding: Dict[str, Any]) -> None:
        """Crear slides de análisis detallado"""
        try:
            content = report_data.get('content', {})
            detailed_analysis = content.get('detailed_analysis', {})
            
            for section_name, section_content in detailed_analysis.items():
                # Usar layout de contenido
                slide_layout = prs.slide_layouts[1]
                slide = prs.slides.add_slide(slide_layout)
                
                # Configurar título
                title = slide.shapes.title
                title.text = section_name.title()
                
                # Configurar contenido
                content_placeholder = slide.placeholders[1]
                content_placeholder.text = section_content
                
                # Aplicar colores de branding
                title.text_frame.paragraphs[0].font.color.rgb = RGBColor(*self._hex_to_rgb(branding['primary_color']))
                
        except Exception as e:
            logger.warning(f"Error creando slides de análisis detallado: {e}")
    
    def _create_pptx_recommendations(self, prs: Presentation, report_data: Dict[str, Any], branding: Dict[str, Any]) -> None:
        """Crear slide de recomendaciones"""
        try:
            content = report_data.get('content', {})
            if not content.get('recommendations'):
                return
            
            # Usar layout de lista
            slide_layout = prs.slide_layouts[1]
            slide = prs.slides.add_slide(slide_layout)
            
            # Configurar título
            title = slide.shapes.title
            title.text = "Recomendaciones"
            
            # Configurar lista de recomendaciones
            content_placeholder = slide.placeholders[1]
            recs_text = "\n".join([f"{i}. {rec}" for i, rec in enumerate(content['recommendations'], 1)])
            content_placeholder.text = recs_text
            
            # Aplicar colores de branding
            title.text_frame.paragraphs[0].font.color.rgb = RGBColor(*self._hex_to_rgb(branding['primary_color']))
            
        except Exception as e:
            logger.warning(f"Error creando slide de recomendaciones: {e}")
    
    def _create_pptx_next_steps(self, prs: Presentation, report_data: Dict[str, Any], branding: Dict[str, Any]) -> None:
        """Crear slide de próximos pasos"""
        try:
            content = report_data.get('content', {})
            if not content.get('next_steps'):
                return
            
            # Usar layout de lista
            slide_layout = prs.slide_layouts[1]
            slide = prs.slides.add_slide(slide_layout)
            
            # Configurar título
            title = slide.shapes.title
            title.text = "Próximos Pasos"
            
            # Configurar lista de pasos
            content_placeholder = slide.placeholders[1]
            steps_text = "\n".join([f"• {step}" for step in content['next_steps']])
            content_placeholder.text = steps_text
            
            # Aplicar colores de branding
            title.text_frame.paragraphs[0].font.color.rgb = RGBColor(*self._hex_to_rgb(branding['primary_color']))
            
        except Exception as e:
            logger.warning(f"Error creando slide de próximos pasos: {e}")
    
    async def generate_branding_guidelines(
        self,
        company_data: Dict[str, Any],
        report_type: str
    ) -> Dict[str, Any]:
        """Generar guías de branding usando IA"""
        try:
            prompt = f"""
            Genera guías de branding para una empresa con los siguientes datos:
            
            Empresa: {company_data.get('name', 'N/A')}
            Industria: {company_data.get('industry', 'N/A')}
            Tipo de reporte: {report_type}
            
            Genera un esquema de colores profesional que incluya:
            1. Color primario
            2. Color secundario
            3. Color de acento
            4. Colores neutros
            5. Familia de fuentes recomendada
            6. Justificación de las elecciones
            
            Responde en formato JSON.
            """
            
            response = await self.ai_service.generate_text(prompt, temperature=0.3)
            
            try:
                return json.loads(response)
            except:
                return self.default_branding
                
        except Exception as e:
            logger.error(f"Error generando guías de branding: {e}")
            return self.default_branding
    
    async def optimize_for_executive_audience(
        self,
        content: Dict[str, Any],
        branding: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimizar contenido para audiencia ejecutiva"""
        try:
            # Optimizar resumen ejecutivo
            if content.get('executive_summary'):
                optimized_summary = await self.ai_service.improve_text(
                    content['executive_summary'], 'executive'
                )
                content['executive_summary'] = optimized_summary
            
            # Optimizar recomendaciones
            if content.get('recommendations'):
                optimized_recommendations = []
                for rec in content['recommendations']:
                    optimized_rec = await self.ai_service.improve_text(rec, 'executive')
                    optimized_recommendations.append(optimized_rec)
                content['recommendations'] = optimized_recommendations
            
            return content
            
        except Exception as e:
            logger.error(f"Error optimizando para audiencia ejecutiva: {e}")
            return content 