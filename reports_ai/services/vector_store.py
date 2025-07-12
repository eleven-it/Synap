"""
Servicio de base de datos vectorial
Almacena y busca embeddings de reportes y contenido usando Qdrant
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    from sentence_transformers import SentenceTransformer
except ImportError:
    # Fallback para desarrollo sin dependencias
    AsyncQdrantClient = None
    SentenceTransformer = None

from config import settings

logger = logging.getLogger(__name__)

class VectorStore:
    """Servicio de base de datos vectorial"""
    
    def __init__(self):
        self.client = None
        self.embedding_model = None
        self.collection_name = settings.QDRANT_COLLECTION
        self.vector_size = 768  # Tamaño de embeddings por defecto
    
    async def initialize(self):
        """Inicializar cliente y modelo de embeddings"""
        try:
            if AsyncQdrantClient is None:
                logger.warning("Qdrant client no disponible, usando modo simulado")
                return
            
            # Inicializar cliente Qdrant
            self.client = AsyncQdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT
            )
            
            # Inicializar modelo de embeddings
            if SentenceTransformer is not None:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                self.vector_size = self.embedding_model.get_sentence_embedding_dimension()
            
            # Crear colección si no existe
            await self._create_collection()
            
            logger.info("Vector store inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando vector store: {e}")
            raise
    
    async def _create_collection(self):
        """Crear colección en Qdrant"""
        try:
            collections = await self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Colección {self.collection_name} creada")
            else:
                logger.info(f"Colección {self.collection_name} ya existe")
                
        except Exception as e:
            logger.error(f"Error creando colección: {e}")
            raise
    
    async def add_document(
        self,
        document_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Agregar documento al vector store"""
        try:
            if self.client is None or self.embedding_model is None:
                logger.warning("Vector store no disponible, documento no agregado")
                return False
            
            # Generar embedding
            embedding = self.embedding_model.encode(content).tolist()
            
            # Crear punto
            point = PointStruct(
                id=document_id,
                vector=embedding,
                payload={
                    "content": content,
                    "metadata": metadata,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            # Insertar en Qdrant
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Documento {document_id} agregado al vector store")
            return True
            
        except Exception as e:
            logger.error(f"Error agregando documento: {e}")
            return False
    
    async def search_similar(
        self,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Buscar documentos similares"""
        try:
            if self.client is None or self.embedding_model is None:
                logger.warning("Vector store no disponible, retornando resultados simulados")
                return self._get_simulated_results(query, limit)
            
            # Generar embedding de la consulta
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Buscar en Qdrant
            search_result = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Formatear resultados
            results = []
            for point in search_result:
                results.append({
                    "id": point.id,
                    "score": point.score,
                    "content": point.payload.get("content", ""),
                    "metadata": point.payload.get("metadata", {})
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error buscando documentos similares: {e}")
            return []
    
    def _get_simulated_results(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Obtener resultados simulados cuando Qdrant no está disponible"""
        return [
            {
                "id": f"sim_{i}",
                "score": 0.9 - (i * 0.1),
                "content": f"Contenido simulado relacionado con: {query}",
                "metadata": {
                    "type": "simulated",
                    "source": "fallback"
                }
            }
            for i in range(min(limit, 5))
        ]
    
    async def add_report_template(
        self,
        template_id: str,
        template_data: Dict[str, Any]
    ) -> bool:
        """Agregar template de reporte al vector store"""
        try:
            # Extraer información relevante del template
            content = f"""
            Template: {template_data.get('name', '')}
            Descripción: {template_data.get('description', '')}
            Categoría: {template_data.get('category', '')}
            Configuración: {json.dumps(template_data.get('layout_schema', {}), indent=2)}
            """
            
            metadata = {
                "type": "report_template",
                "template_id": template_id,
                "name": template_data.get('name', ''),
                "category": template_data.get('category', ''),
                "company_id": template_data.get('empresa_id', '')
            }
            
            return await self.add_document(template_id, content, metadata)
            
        except Exception as e:
            logger.error(f"Error agregando template: {e}")
            return False
    
    async def add_report_content(
        self,
        report_id: str,
        report_data: Dict[str, Any]
    ) -> bool:
        """Agregar contenido de reporte al vector store"""
        try:
            # Extraer información relevante del reporte
            content = f"""
            Reporte: {report_data.get('name', '')}
            Descripción: {report_data.get('description', '')}
            Contenido: {json.dumps(report_data.get('content', {}), indent=2)}
            Componentes: {json.dumps(report_data.get('components', []), indent=2)}
            """
            
            metadata = {
                "type": "report_content",
                "report_id": report_id,
                "name": report_data.get('name', ''),
                "company_id": report_data.get('empresa_id', ''),
                "created_by": report_data.get('created_by', '')
            }
            
            return await self.add_document(report_id, content, metadata)
            
        except Exception as e:
            logger.error(f"Error agregando contenido de reporte: {e}")
            return False
    
    async def search_templates(
        self,
        query: str,
        category: Optional[str] = None,
        company_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Buscar templates de reportes"""
        try:
            # Construir filtros
            filter_conditions = []
            
            if category:
                filter_conditions.append({
                    "key": "metadata.category",
                    "match": {"value": category}
                })
            
            if company_id:
                filter_conditions.append({
                    "key": "metadata.company_id",
                    "match": {"value": company_id}
                })
            
            # Agregar filtro de tipo
            filter_conditions.append({
                "key": "metadata.type",
                "match": {"value": "report_template"}
            })
            
            if self.client is None or self.embedding_model is None:
                return self._get_simulated_template_results(query, limit)
            
            # Generar embedding de la consulta
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Buscar en Qdrant con filtros
            search_result = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter={"must": filter_conditions} if filter_conditions else None,
                limit=limit
            )
            
            # Formatear resultados
            results = []
            for point in search_result:
                results.append({
                    "template_id": point.id,
                    "score": point.score,
                    "name": point.payload.get("metadata", {}).get("name", ""),
                    "category": point.payload.get("metadata", {}).get("category", ""),
                    "content": point.payload.get("content", "")
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error buscando templates: {e}")
            return []
    
    def _get_simulated_template_results(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Obtener resultados simulados de templates"""
        return [
            {
                "template_id": f"template_{i}",
                "score": 0.9 - (i * 0.1),
                "name": f"Template {i} relacionado con {query}",
                "category": "general",
                "content": f"Contenido del template relacionado con: {query}"
            }
            for i in range(min(limit, 5))
        ]
    
    async def search_similar_reports(
        self,
        query: str,
        company_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Buscar reportes similares"""
        try:
            # Construir filtros
            filter_conditions = []
            
            if company_id:
                filter_conditions.append({
                    "key": "metadata.company_id",
                    "match": {"value": company_id}
                })
            
            # Agregar filtro de tipo
            filter_conditions.append({
                "key": "metadata.type",
                "match": {"value": "report_content"}
            })
            
            if self.client is None or self.embedding_model is None:
                return self._get_simulated_report_results(query, limit)
            
            # Generar embedding de la consulta
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Buscar en Qdrant con filtros
            search_result = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter={"must": filter_conditions} if filter_conditions else None,
                limit=limit
            )
            
            # Formatear resultados
            results = []
            for point in search_result:
                results.append({
                    "report_id": point.id,
                    "score": point.score,
                    "name": point.payload.get("metadata", {}).get("name", ""),
                    "content": point.payload.get("content", ""),
                    "created_by": point.payload.get("metadata", {}).get("created_by", "")
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error buscando reportes similares: {e}")
            return []
    
    def _get_simulated_report_results(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Obtener resultados simulados de reportes"""
        return [
            {
                "report_id": f"report_{i}",
                "score": 0.9 - (i * 0.1),
                "name": f"Reporte {i} relacionado con {query}",
                "content": f"Contenido del reporte relacionado con: {query}",
                "created_by": "user@example.com"
            }
            for i in range(min(limit, 5))
        ]
    
    async def delete_document(self, document_id: str) -> bool:
        """Eliminar documento del vector store"""
        try:
            if self.client is None:
                logger.warning("Vector store no disponible, documento no eliminado")
                return False
            
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=[document_id]
            )
            
            logger.info(f"Documento {document_id} eliminado del vector store")
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando documento: {e}")
            return False
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de la colección"""
        try:
            if self.client is None:
                return {
                    "total_points": 0,
                    "collection_name": self.collection_name,
                    "status": "unavailable"
                }
            
            collection_info = await self.client.get_collection(self.collection_name)
            
            return {
                "total_points": collection_info.points_count,
                "collection_name": self.collection_name,
                "vector_size": self.vector_size,
                "status": "available"
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {
                "total_points": 0,
                "collection_name": self.collection_name,
                "status": "error"
            }
    
    async def close(self):
        """Cerrar conexión con el vector store"""
        try:
            if self.client:
                await self.client.close()
                logger.info("Conexión con vector store cerrada")
        except Exception as e:
            logger.error(f"Error cerrando vector store: {e}") 