"""
Agente Multimodal - Procesa imágenes, PDFs y archivos con OCR y análisis de IA
"""
import logging
import os
from typing import Dict, List, Any
from django.utils.translation import gettext_lazy as _
from django.core.files.storage import default_storage
from ..ocr_processor import ocr_processor

logger = logging.getLogger(__name__)


class MultimodalAgent:
    """Agente especializado en procesar contenido multimodal con OCR real"""
    
    def __init__(self):
        self.supported_formats = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff', 'application/pdf']
        self.max_file_size = 10 * 1024 * 1024  # 10MB
    
    def process(self, message: str, ticket, attachments: List = None) -> Dict[str, Any]:
        """Procesa mensaje con archivos adjuntos usando OCR real"""
        try:
            if not attachments:
                return self._process_text_only(message)
            
            # Analizar archivos con OCR
            file_analyses = []
            for attachment in attachments:
                analysis = self.analyze_file(attachment)
                file_analyses.append(analysis)
            
            # Generar respuesta
            return self._generate_response(message, file_analyses, ticket)
            
        except Exception as e:
            logger.error(f"Error in multimodal processing: {str(e)}")
            return {
                'message': _("Error procesando archivos. ¿Podrías describir el problema?"),
                'confidence': 0.3,
                'escalation_reason': f'Error multimodal: {str(e)}'
            }
    
    def analyze_file(self, file) -> Dict[str, Any]:
        """Analiza un archivo individual usando OCR real"""
        try:
            file_type = file.content_type
            
            if file.size > self.max_file_size:
                return {'error': _('Archivo demasiado grande')}
            
            # Guardar archivo temporalmente para OCR
            file_path = self._save_temp_file(file)
            
            try:
                if file_type.startswith('image/'):
                    return self._analyze_image(file_path, file)
                elif file_type == 'application/pdf':
                    return self._analyze_pdf(file_path, file)
                else:
                    return {'error': _('Tipo de archivo no soportado')}
            finally:
                # Limpiar archivo temporal
                if os.path.exists(file_path):
                    os.remove(file_path)
                
        except Exception as e:
            logger.error(f"Error analyzing file {file.name}: {e}")
            return {'error': str(e)}
    
    def _save_temp_file(self, file) -> str:
        """Guarda archivo temporalmente para OCR"""
        import tempfile
        
        # Crear archivo temporal
        temp_fd, temp_path = tempfile.mkstemp()
        os.close(temp_fd)
        
        # Guardar contenido del archivo
        with open(temp_path, 'wb') as f:
            for chunk in file.chunks():
                f.write(chunk)
        
        return temp_path
    
    def _analyze_image(self, file_path: str, file) -> Dict[str, Any]:
        """Analiza una imagen usando OCR real"""
        try:
            # Extraer texto con OCR
            ocr_result = ocr_processor.extract_text_from_image(file_path)
            
            # Extraer datos estructurados
            structured_data = ocr_processor.extract_structured_data(file_path)
            
            # Extraer tablas
            tables = ocr_processor.extract_tables_from_image(file_path)
            
            analysis = {
                'file_type': 'image',
                'file_name': file.name,
                'content_type': 'image',
                'success': True,
                'ocr_text': ocr_result.get('text', ''),
                'ocr_confidence': ocr_result.get('confidence', 0.0),
                'word_count': ocr_result.get('word_count', 0),
                'structured_data': structured_data,
                'tables_detected': len(tables),
                'metadata': {
                    'image_size': ocr_result.get('image_size'),
                    'format': ocr_result.get('format'),
                    'language': ocr_result.get('language')
                }
            }
            
            # Si se detectó texto con buena confianza
            if ocr_result.get('text') and ocr_result.get('confidence', 0) > 0.5:
                analysis['has_readable_text'] = True
                analysis['text_summary'] = ocr_result['text'][:200] + "..." if len(ocr_result['text']) > 200 else ocr_result['text']
            
            # Si se detectaron datos estructurados
            if structured_data.get('invoice_number') or structured_data.get('amount'):
                analysis['has_structured_data'] = True
                analysis['document_type'] = 'invoice' if structured_data.get('invoice_number') else 'document'
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing image {file.name}: {e}")
            return {
                'file_type': 'image',
                'file_name': file.name,
                'error': str(e),
                'success': False
            }
    
    def _analyze_pdf(self, file_path: str, file) -> Dict[str, Any]:
        """Analiza un PDF usando OCR real"""
        try:
            # Extraer texto con OCR
            ocr_result = ocr_processor.extract_text_from_pdf(file_path)
            
            analysis = {
                'file_type': 'pdf',
                'file_name': file.name,
                'content_type': 'document',
                'success': True,
                'ocr_text': ocr_result.get('text', ''),
                'ocr_confidence': ocr_result.get('confidence', 0.0),
                'word_count': ocr_result.get('word_count', 0),
                'metadata': {
                    'method': ocr_result.get('method'),
                    'pages_processed': ocr_result.get('pages_processed'),
                    'total_pages': ocr_result.get('total_pages'),
                    'language': ocr_result.get('language')
                }
            }
            
            # Si se detectó texto con buena confianza
            if ocr_result.get('text') and ocr_result.get('confidence', 0) > 0.5:
                analysis['has_readable_text'] = True
                analysis['text_summary'] = ocr_result['text'][:200] + "..." if len(ocr_result['text']) > 200 else ocr_result['text']
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing PDF {file.name}: {e}")
            return {
                'file_type': 'pdf',
                'file_name': file.name,
                'error': str(e),
                'success': False
            }
    
    def _generate_response(self, message: str, file_analyses: List[Dict], ticket) -> Dict[str, Any]:
        """Genera respuesta basada en análisis OCR"""
        successful_files = [f for f in file_analyses if f.get('success', False)]
        
        if not successful_files:
            return {
                'message': _("No pude procesar los archivos. ¿Podrías describir el problema con palabras?"),
                'confidence': 0.3,
                'escalation_reason': 'Archivos no procesables'
            }
        
        # Analizar contenido extraído
        total_text = ""
        has_invoice_data = False
        total_confidence = 0
        
        for file_analysis in successful_files:
            if file_analysis.get('ocr_text'):
                total_text += file_analysis['ocr_text'] + "\n"
                total_confidence += file_analysis.get('ocr_confidence', 0)
            
            if file_analysis.get('has_structured_data'):
                has_invoice_data = True
        
        avg_confidence = total_confidence / len(successful_files) if successful_files else 0
        
        # Generar respuesta contextual
        if has_invoice_data:
            response = _("He detectado datos de facturación en tus archivos. ¿Podrías especificar cuál es el problema con la facturación?")
            confidence = min(0.8, avg_confidence + 0.2)
        elif total_text and len(total_text) > 100:
            response = _("He extraído texto de tus documentos. ¿Podrías describir específicamente cuál es el problema que necesitas resolver?")
            confidence = min(0.7, avg_confidence + 0.1)
        else:
            response = _("He procesado tus archivos. ¿Podrías describir específicamente cuál es el problema?")
            confidence = 0.6
        
        return {
            'message': response,
            'confidence': confidence,
            'suggestions': [
                _("Describir el problema paso a paso"),
                _("¿Qué esperabas que sucediera?"),
                _("¿Cuándo comenzó el problema?")
            ],
            'metadata': {
                'files_processed': len(successful_files),
                'total_text_extracted': len(total_text),
                'has_invoice_data': has_invoice_data,
                'ocr_confidence': avg_confidence
            }
        }
    
    def _process_text_only(self, message: str) -> Dict[str, Any]:
        """Procesa mensajes solo de texto"""
        return {
            'message': _("¿Podrías adjuntar alguna imagen o documento relacionado con el problema? Esto me ayudará a entender mejor la situación."),
            'confidence': 0.4,
            'metadata': {'response_type': 'text_only'},
            'suggestions': [
                _("Capturas de pantalla del error"),
                _("Documentos PDF relevantes"),
                _("Imágenes de formularios o reportes")
            ]
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene estado del agente"""
        return {
            'status': 'active',
            'supported_formats': self.supported_formats,
            'max_file_size_mb': self.max_file_size / (1024 * 1024),
            'ocr_enabled': True,
            'ocr_languages': ['spa', 'eng']
        }
    
    def train(self, training_data: List[Dict]) -> bool:
        """Entrena el agente"""
        logger.info(f"Training multimodal agent with {len(training_data)} samples")
        return True 