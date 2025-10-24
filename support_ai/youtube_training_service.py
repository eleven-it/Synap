"""
Servicio para entrenar agentes con videos de YouTube
"""
import re
import requests
import json
import logging
from typing import List, Dict, Optional, Tuple, Any
from urllib.parse import urlparse, parse_qs
from django.conf import settings
import os
import tempfile
import subprocess
from pathlib import Path
from django.utils import timezone

logger = logging.getLogger(__name__)

# Configuración de yt-dlp
YT_DLP_CONFIG = {
    'executable_path': 'yt-dlp',  # Usar yt-dlp del PATH del sistema
    'format': 'best[ext=mp4]/best',
    'outtmpl': '%(title)s.%(ext)s',
    'writeinfojson': True,
    'writesubtitles': True,
    'writeautomaticsub': True,
    'subtitleslangs': ['es', 'en'],
    'ignoreerrors': True,
    'no_warnings': False,
    'quiet': False,
    'verbose': True
}

class YouTubeTrainingService:
    """
    Servicio para extraer y procesar contenido de videos de YouTube
    para entrenar agentes de IA
    """
    
    def __init__(self):
        self.base_url = "https://www.youtube.com"
        self.api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
        self.yt_dlp_path = self._get_yt_dlp_path()
        
        if self.yt_dlp_path:
            logger.info(f"✅ YouTube Training Service inicializado con yt-dlp en: {self.yt_dlp_path}")
        else:
            logger.warning("⚠️ yt-dlp no encontrado, algunas funcionalidades estarán limitadas")
        
    def _get_yt_dlp_path(self) -> Optional[str]:
        """Obtiene la ruta de yt-dlp"""
        # Rutas específicas donde buscar yt-dlp
        possible_paths = [
            '/usr/local/bin/yt-dlp',  # Ruta instalada en Dockerfile
            '/usr/bin/yt-dlp',        # Ruta estándar
            'yt-dlp',                 # PATH del sistema
        ]
        
        # Verificar rutas específicas primero
        for path in possible_paths:
            try:
                result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    logger.info(f"yt-dlp encontrado en: {path}")
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                continue
        
        # Fallback: buscar en PATH
        try:
            result = subprocess.run(['which', 'yt-dlp'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                path = result.stdout.strip()
                logger.info(f"yt-dlp encontrado en PATH: {path}")
                return path
        except:
            pass
        
        logger.error("yt-dlp no encontrado en el sistema")
        return None
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extrae el ID del video de una URL de YouTube"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_video_info(self, video_id: str) -> Optional[Dict]:
        """Obtiene información del video usando la API de YouTube"""
        if not self.api_key:
            logger.warning("YouTube API key no configurada")
            return None
            
        try:
            url = f"https://www.googleapis.com/youtube/v3/videos"
            params = {
                'id': video_id,
                'key': self.api_key,
                'part': 'snippet,contentDetails,statistics'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    return data['items'][0]
            
            logger.error(f"Error obteniendo info del video: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Error en API de YouTube: {str(e)}")
            return None
    
    def download_video_transcript(self, url: str) -> Optional[str]:
        """Descarga la transcripción del video usando yt-dlp"""
        if not self.yt_dlp_path:
            logger.error("yt-dlp no está instalado")
            return None
            
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                logger.error("No se pudo extraer el ID del video")
                return None
            
            # Crear directorio temporal
            temp_dir = tempfile.mkdtemp()
            transcript_file = os.path.join(temp_dir, f"{video_id}_transcript.txt")
            
            # Comando para descargar transcripción
            cmd = [
                self.yt_dlp_path,
                '--write-sub',
                '--write-auto-sub',
                '--sub-format', 'txt',
                '--skip-download',
                '--output', f"{temp_dir}/{video_id}",
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                # Buscar archivo de transcripción
                transcript_files = list(Path(temp_dir).glob(f"{video_id}*.txt"))
                if transcript_files:
                    with open(transcript_files[0], 'r', encoding='utf-8') as f:
                        transcript = f.read()
                    
                    # Limpiar archivos temporales
                    for file in transcript_files:
                        file.unlink()
                    os.rmdir(temp_dir)
                    
                    return transcript
                else:
                    logger.warning("No se encontró transcripción para el video")
            else:
                logger.error(f"Error descargando transcripción: {result.stderr}")
            
            # Limpiar
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
                
            return None
            
        except Exception as e:
            logger.error(f"Error descargando transcripción: {str(e)}")
            return None
    
    def extract_video_content(self, url: str) -> Dict:
        """Extrae todo el contenido relevante de un video de YouTube"""
        video_id = self.extract_video_id(url)
        if not video_id:
            return {'error': 'URL de YouTube inválida'}
        
        result = {
            'video_id': video_id,
            'url': url,
            'title': None,
            'description': None,
            'transcript': None,
            'duration': None,
            'views': None,
            'upload_date': None,
            'channel': None
        }
        
        # Obtener información del video
        video_info = self.get_video_info(video_id)
        if video_info:
            snippet = video_info.get('snippet', {})
            result.update({
                'title': snippet.get('title'),
                'description': snippet.get('description'),
                'upload_date': snippet.get('publishedAt'),
                'channel': snippet.get('channelTitle')
            })
            
            # Duración y estadísticas
            if 'contentDetails' in video_info:
                duration = video_info['contentDetails'].get('duration')
                if duration:
                    result['duration'] = self._parse_duration(duration)
            
            if 'statistics' in video_info:
                result['views'] = video_info['statistics'].get('viewCount')
        
        # Descargar transcripción
        transcript = self.download_video_transcript(url)
        if transcript:
            result['transcript'] = transcript
        
        return result
    
    def _parse_duration(self, duration: str) -> str:
        """Convierte duración ISO 8601 a formato legible"""
        import re
        match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration)
        if match:
            hours = match.group(1)[:-1] if match.group(1) else '0'
            minutes = match.group(2)[:-1] if match.group(2) else '0'
            seconds = match.group(3)[:-1] if match.group(3) else '0'
            return f"{hours}:{minutes.zfill(2)}:{seconds.zfill(2)}"
        return duration
    
    def process_video_for_training(self, url: str, category: str = "General") -> Dict:
        """Procesa un video para entrenamiento de agentes"""
        try:
            logger.info(f"Procesando video: {url}")
            
            # Extraer contenido
            content = self.extract_video_content(url)
            if 'error' in content:
                return content
            
            # Preparar para entrenamiento
            training_data = {
                'source_type': 'youtube_video',
                'source_url': url,
                'video_id': content['video_id'],
                'title': content['title'],
                'category': category,
                'content': self._prepare_content_for_training(content),
                'metadata': {
                    'channel': content['channel'],
                    'duration': content['duration'],
                    'views': content['views'],
                    'upload_date': content['upload_date']
                }
            }
            
            logger.info(f"Video procesado exitosamente: {content['title']}")
            return training_data
            
        except Exception as e:
            logger.error(f"Error procesando video: {str(e)}")
            return {'error': str(e)}
    
    def _prepare_content_for_training(self, content: Dict) -> str:
        """Prepara el contenido para entrenamiento de agentes"""
        parts = []
        
        # Título
        if content['title']:
            parts.append(f"Título: {content['title']}")
        
        # Descripción
        if content['description']:
            # Limpiar descripción (remover URLs, caracteres especiales)
            description = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content['description'])
            description = re.sub(r'[^\w\s.,!?-]', '', description)
            parts.append(f"Descripción: {description}")
        
        # Transcripción
        if content['transcript']:
            # Limpiar transcripción
            transcript = content['transcript']
            # Remover timestamps y formato de subtítulos
            transcript = re.sub(r'^\d+:\d+', '', transcript, flags=re.MULTILINE)
            transcript = re.sub(r'^\d+$', '', transcript, flags=re.MULTILINE)
            transcript = re.sub(r'^\s*$', '', transcript, flags=re.MULTILINE)
            transcript = transcript.strip()
            
            if transcript:
                parts.append(f"Contenido del video:\n{transcript}")
        
        return '\n\n'.join(parts)
    
    def process_youtube_video(self, video_url: str, agent_id: str = None) -> Dict[str, Any]:
        """
        Procesa un video de YouTube y genera contenido de entrenamiento
        
        Args:
            video_url: URL del video de YouTube
            agent_id: ID del agente para entrenar (opcional)
            
        Returns:
            Resultado del procesamiento
        """
        try:
            if not self.yt_dlp_path:
                return {
                    'success': False,
                    'error': 'yt-dlp no está disponible'
                }
            
            # Extraer ID del video
            video_id = self.extract_video_id(video_url)
            if not video_id:
                return {
                    'success': False,
                    'error': 'No se pudo extraer el ID del video'
                }
            
            logger.info(f"Procesando video: {video_id}")
            
            # Descargar información del video
            video_info = self._download_video_info(video_url)
            if not video_info:
                return {
                    'success': False,
                    'error': 'No se pudo obtener información del video'
                }
            
            # Extraer subtítulos
            subtitles = self._extract_subtitles(video_url)
            
            # Generar contenido de entrenamiento
            training_content = self._generate_training_content(video_info, subtitles, agent_id)
            
            return {
                'success': True,
                'video_id': video_id,
                'video_info': video_info,
                'subtitles': subtitles,
                'training_content': training_content,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error procesando video {video_url}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _download_video_info(self, video_url: str) -> Optional[Dict]:
        """Descarga información del video usando yt-dlp"""
        try:
            cmd = [
                self.yt_dlp_path,
                '--dump-json',
                '--no-playlist',
                video_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                video_data = json.loads(result.stdout)
                return {
                    'title': video_data.get('title', ''),
                    'description': video_data.get('description', ''),
                    'duration': video_data.get('duration', 0),
                    'uploader': video_data.get('uploader', ''),
                    'view_count': video_data.get('view_count', 0),
                    'like_count': video_data.get('like_count', 0),
                    'tags': video_data.get('tags', []),
                    'categories': video_data.get('categories', [])
                }
            else:
                logger.error(f"Error descargando info del video: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error en _download_video_info: {e}")
            return None
    
    def _extract_subtitles(self, video_url: str) -> List[Dict]:
        """Extrae subtítulos del video"""
        try:
            # Descargar subtítulos automáticos en español e inglés
            subtitle_langs = ['es', 'en']
            subtitles = []
            
            for lang in subtitle_langs:
                try:
                    cmd = [
                        self.yt_dlp_path,
                        '--write-sub',
                        '--write-auto-sub',
                        '--sub-lang', lang,
                        '--skip-download',
                        '--convert-subs', 'txt',
                        video_url
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        # Buscar archivo de subtítulos generado
                        subtitle_file = self._find_subtitle_file(lang)
                        if subtitle_file:
                            with open(subtitle_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                subtitles.append({
                                    'language': lang,
                                    'content': content,
                                    'type': 'auto' if 'auto' in subtitle_file else 'manual'
                                })
                            
                            # Limpiar archivo temporal
                            os.remove(subtitle_file)
                            
                except Exception as e:
                    logger.warning(f"No se pudieron extraer subtítulos en {lang}: {e}")
                    continue
            
            return subtitles
            
        except Exception as e:
            logger.error(f"Error extrayendo subtítulos: {e}")
            return []
    
    def _find_subtitle_file(self, lang: str) -> Optional[str]:
        """Busca archivo de subtítulos generado"""
        try:
            # Buscar archivos .txt que contengan el idioma
            current_dir = os.getcwd()
            for file in os.listdir(current_dir):
                if file.endswith('.txt') and lang in file:
                    return os.path.join(current_dir, file)
            return None
        except Exception as e:
            logger.error(f"Error buscando archivo de subtítulos: {e}")
            return None
    
    def _generate_training_content(self, video_info: Dict, subtitles: List[Dict], agent_id: str = None) -> Dict[str, Any]:
        """Genera contenido de entrenamiento basado en el video"""
        try:
            # Procesar descripción del video
            description = video_info.get('description', '')
            title = video_info.get('title', '')
            
            # Procesar subtítulos
            subtitle_text = ""
            for sub in subtitles:
                if sub['language'] == 'es':  # Priorizar español
                    subtitle_text = sub['content']
                    break
                elif sub['language'] == 'en' and not subtitle_text:
                    subtitle_text = sub['content']
            
            # Generar preguntas y respuestas basadas en el contenido
            qa_pairs = self._generate_qa_pairs(title, description, subtitle_text)
            
            # Crear contenido de entrenamiento
            training_content = {
                'source': 'youtube',
                'video_title': title,
                'video_description': description,
                'qa_pairs': qa_pairs,
                'subtitle_languages': [sub['language'] for sub in subtitles],
                'total_qa_pairs': len(qa_pairs),
                'agent_id': agent_id
            }
            
            return training_content
            
        except Exception as e:
            logger.error(f"Error generando contenido de entrenamiento: {e}")
            return {
                'source': 'youtube',
                'error': str(e),
                'qa_pairs': []
            }
    
    def _generate_qa_pairs(self, title: str, description: str, subtitle_text: str) -> List[Dict[str, str]]:
        """Genera pares de pregunta-respuesta basados en el contenido"""
        qa_pairs = []
        
        # Preguntas básicas basadas en el título
        if title:
            qa_pairs.append({
                'question': f'¿De qué trata el video "{title}"?',
                'answer': f'El video trata sobre: {title}. {description[:200]}...' if description else f'El video trata sobre: {title}'
            })
        
        # Preguntas basadas en la descripción
        if description:
            # Dividir descripción en párrafos
            paragraphs = [p.strip() for p in description.split('\n') if p.strip()]
            
            for i, paragraph in enumerate(paragraphs[:3]):  # Limitar a 3 párrafos
                if len(paragraph) > 50:  # Solo párrafos sustanciales
                    qa_pairs.append({
                        'question': f'¿Qué información adicional proporciona el video sobre el tema?',
                        'answer': paragraph
                    })
        
        # Preguntas basadas en subtítulos (si están disponibles)
        if subtitle_text:
            # Dividir subtítulos en segmentos
            segments = subtitle_text.split('\n\n')[:5]  # Limitar a 5 segmentos
            
            for segment in segments:
                if len(segment.strip()) > 30:  # Solo segmentos sustanciales
                    qa_pairs.append({
                        'question': '¿Qué se menciona en el video sobre este tema?',
                        'answer': segment.strip()
                    })
        
        return qa_pairs
    
    def batch_process_videos(self, video_urls: List[str], agent_id: str = None) -> Dict[str, Any]:
        """Procesa múltiples videos en lote"""
        results = []
        success_count = 0
        
        for url in video_urls:
            try:
                result = self.process_youtube_video(url, agent_id)
                results.append({
                    'url': url,
                    'result': result
                })
                
                if result['success']:
                    success_count += 1
                    
            except Exception as e:
                results.append({
                    'url': url,
                    'result': {
                        'success': False,
                        'error': str(e)
                    }
                })
        
        return {
            'success': success_count == len(video_urls),
            'total_videos': len(video_urls),
            'successful_processings': success_count,
            'failed_processings': len(video_urls) - success_count,
            'results': results,
            'timestamp': timezone.now().isoformat()
        }
    
    def get_processing_status(self) -> Dict[str, Any]:
        """Obtiene el estado del servicio de procesamiento"""
        return {
            'yt_dlp_available': self.yt_dlp_path is not None,
            'yt_dlp_path': self.yt_dlp_path,
            'youtube_api_available': self.api_key is not None,
            'service_status': 'ready' if self.yt_dlp_path else 'limited'
        }


# Instancia global
_youtube_training_service = None


def get_youtube_training_service() -> YouTubeTrainingService:
    """Obtiene la instancia global del servicio de YouTube"""
    global _youtube_training_service
    
    if _youtube_training_service is None:
        _youtube_training_service = YouTubeTrainingService()
    
    return _youtube_training_service


def test_youtube_processing() -> Dict[str, Any]:
    """Prueba el procesamiento de videos de YouTube"""
    try:
        youtube_service = get_youtube_training_service()
        
        # Verificar disponibilidad
        status = youtube_service.get_processing_status()
        
        if not status['yt_dlp_available']:
            return {
                'success': False,
                'error': 'yt-dlp no está disponible',
                'status': status
            }
        
        # URL de prueba (video corto de YouTube)
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll (video corto)
        
        # Procesar video de prueba
        result = youtube_service.process_youtube_video(test_url)
        
        return {
            'success': result['success'],
            'status': status,
            'test_result': result,
            'yt_dlp_working': result['success']
        }
        
    except Exception as e:
        logger.error(f"Error en prueba de YouTube: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def create_youtube_training_data(urls: List[str], category: str = "General") -> List[Dict]:
    """
    Función de conveniencia para crear datos de entrenamiento desde videos de YouTube
    """
    service = YouTubeTrainingService()
    return service.batch_process_videos(urls, category)


if __name__ == "__main__":
    # Ejemplo de uso
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=9bZkp7q19f0"
    ]
    
    results = create_youtube_training_data(urls, "Música")
    
    for result in results:
        if 'error' not in result:
            print(f"✅ {result['title']}")
            print(f"   Categoría: {result['category']}")
            print(f"   Contenido: {len(result['content'])} caracteres")
        else:
            print(f"❌ Error: {result['error']}")
        print()
