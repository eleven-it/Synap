import os
import logging
import tempfile
from typing import Dict, List, Optional, Tuple
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import fitz  # PyMuPDF
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

class OCRProcessor:
    """Procesador OCR para imágenes y PDFs"""
    
    def __init__(self):
        # Configurar Tesseract path si es necesario
        if hasattr(settings, 'TESSERACT_CMD_PATH'):
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD_PATH
    
    def extract_text_from_image(self, image_path: str, language: str = 'spa+eng') -> Dict[str, any]:
        """
        Extrae texto de una imagen usando OCR
        
        Args:
            image_path: Ruta al archivo de imagen
            language: Idiomas para OCR (spa+eng por defecto)
            
        Returns:
            Dict con texto extraído y metadatos
        """
        try:
            # Abrir imagen
            image = Image.open(image_path)
            
            # Configurar OCR
            custom_config = r'--oem 3 --psm 6'
            
            # Extraer texto
            text = pytesseract.image_to_string(image, lang=language, config=custom_config)
            
            # Extraer datos estructurados
            data = pytesseract.image_to_data(image, lang=language, config=custom_config, output_type=pytesseract.Output.DICT)
            
            # Calcular confianza promedio
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "text": text.strip(),
                "confidence": avg_confidence / 100.0,  # Normalizar a 0-1
                "word_count": len(text.split()),
                "language": language,
                "image_size": image.size,
                "format": image.format
            }
            
        except Exception as e:
            logger.error(f"Error en OCR de imagen {image_path}: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "error": str(e)
            }
    
    def extract_text_from_pdf(self, pdf_path: str, language: str = 'spa+eng') -> Dict[str, any]:
        """
        Extrae texto de un PDF usando OCR en las páginas
        
        Args:
            pdf_path: Ruta al archivo PDF
            language: Idiomas para OCR
            
        Returns:
            Dict con texto extraído y metadatos
        """
        try:
            # Intentar extraer texto nativo primero
            doc = fitz.open(pdf_path)
            native_text = ""
            pages_with_native_text = 0
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                if text.strip():
                    native_text += text + "\n"
                    pages_with_native_text += 1
            
            doc.close()
            
            # Si hay texto nativo, usarlo
            if native_text.strip():
                return {
                    "text": native_text.strip(),
                    "confidence": 0.95,  # Texto nativo tiene alta confianza
                    "word_count": len(native_text.split()),
                    "language": language,
                    "method": "native_text",
                    "pages_with_text": pages_with_native_text
                }
            
            # Si no hay texto nativo, usar OCR
            images = convert_from_path(pdf_path)
            ocr_text = ""
            total_confidence = 0
            pages_processed = 0
            
            for i, image in enumerate(images):
                # Guardar imagen temporalmente
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    image.save(tmp_file.name, 'PNG')
                    result = self.extract_text_from_image(tmp_file.name, language)
                    os.unlink(tmp_file.name)
                    
                    if result["text"]:
                        ocr_text += f"--- Página {i+1} ---\n{result['text']}\n\n"
                        total_confidence += result["confidence"]
                        pages_processed += 1
            
            avg_confidence = total_confidence / pages_processed if pages_processed > 0 else 0
            
            return {
                "text": ocr_text.strip(),
                "confidence": avg_confidence,
                "word_count": len(ocr_text.split()),
                "language": language,
                "method": "ocr",
                "pages_processed": pages_processed,
                "total_pages": len(images)
            }
            
        except Exception as e:
            logger.error(f"Error en OCR de PDF {pdf_path}: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "error": str(e)
            }
    
    def extract_tables_from_image(self, image_path: str) -> List[Dict[str, any]]:
        """
        Extrae tablas de una imagen
        
        Args:
            image_path: Ruta al archivo de imagen
            
        Returns:
            Lista de tablas extraídas
        """
        try:
            image = Image.open(image_path)
            
            # Extraer tablas usando Tesseract
            tables = pytesseract.image_to_data(
                image, 
                lang='spa+eng', 
                config='--oem 3 --psm 6',
                output_type=pytesseract.Output.DICT
            )
            
            # Procesar datos de tabla (simplificado)
            # En una implementación completa, usaríamos OpenCV para detectar líneas de tabla
            
            return [{
                "table_data": tables,
                "confidence": 0.7
            }]
            
        except Exception as e:
            logger.error(f"Error extrayendo tablas de {image_path}: {e}")
            return []
    
    def extract_structured_data(self, image_path: str) -> Dict[str, any]:
        """
        Extrae datos estructurados (formularios, facturas, etc.)
        
        Args:
            image_path: Ruta al archivo de imagen
            
        Returns:
            Dict con datos estructurados
        """
        try:
            image = Image.open(image_path)
            
            # Extraer texto con posiciones
            data = pytesseract.image_to_data(
                image, 
                lang='spa+eng', 
                config='--oem 3 --psm 6',
                output_type=pytesseract.Output.DICT
            )
            
            # Procesar datos para encontrar campos estructurados
            structured_data = {
                "invoice_number": None,
                "date": None,
                "amount": None,
                "company_name": None,
                "items": []
            }
            
            # Buscar patrones en el texto extraído
            text_blocks = []
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 50:  # Solo texto con confianza > 50%
                    text_blocks.append({
                        'text': data['text'][i],
                        'conf': int(data['conf'][i]),
                        'x': data['left'][i],
                        'y': data['top'][i]
                    })
            
            # Análisis simple de patrones
            for block in text_blocks:
                text = block['text'].lower()
                
                # Buscar número de factura
                if any(word in text for word in ['factura', 'invoice', 'nº', 'no.']):
                    structured_data['invoice_number'] = block['text']
                
                # Buscar fechas
                if any(word in text for word in ['fecha', 'date', '/', '-']):
                    structured_data['date'] = block['text']
                
                # Buscar montos
                if any(word in text for word in ['total', 'monto', 'amount', '$', '€']):
                    structured_data['amount'] = block['text']
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Error extrayendo datos estructurados de {image_path}: {e}")
            return {}
    
    def get_supported_formats(self) -> List[str]:
        """Retorna los formatos de archivo soportados"""
        return [
            'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff',  # Imágenes
            'pdf'  # Documentos
        ]
    
    def is_supported_format(self, file_path: str) -> bool:
        """Verifica si el formato de archivo es soportado"""
        ext = file_path.lower().split('.')[-1]
        return ext in self.get_supported_formats()

# Instancia global
ocr_processor = OCRProcessor() 