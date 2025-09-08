"""
Qdrant vector database service for storing document embeddings and AI responses
"""

from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from src.core.config import settings

@dataclass
class DocumentVector:
    """Document vector data structure"""
    id: str
    document_path: str
    filename: str
    content_summary: str
    analysis_result: Dict[str, Any]
    embedding: List[float]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class QdrantService:
    """Qdrant vector database service"""
    
    def __init__(self):
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port
        )
        self.collection_name = settings.qdrant_collection_name
        self.vector_size = 1536  # OpenAI embedding size (adjust based on embedding model)
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """Ensure the collection exists, create if not"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection {self.collection_name} created successfully")
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise
    
    async def store_document_analysis(
        self,
        document_path: str,
        filename: str,
        content_summary: str,
        analysis_result: Dict[str, Any],
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store document analysis in Qdrant
        
        Args:
            document_path: Path to the document
            filename: Name of the file
            content_summary: Summary of document content
            analysis_result: AI analysis result
            embedding: Document embedding vector
            metadata: Additional metadata
            
        Returns:
            Document ID
        """
        try:
            doc_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            # Prepare payload
            payload = {
                "document_path": document_path,
                "filename": filename,
                "content_summary": content_summary,
                "analysis_result": analysis_result,
                "metadata": metadata or {},
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            # Create point
            point = PointStruct(
                id=doc_id,
                vector=embedding,
                payload=payload
            )
            
            # Store in Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Stored document analysis for {filename} with ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error storing document analysis: {e}")
            raise
    
    async def search_similar_documents(
        self,
        query_embedding: List[float],
        limit: int = 10,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity
        
        Args:
            query_embedding: Query vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            
        Returns:
            List of similar documents with scores
        """
        try:
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            )
            
            results = []
            for hit in search_result:
                result = {
                    "id": hit.id,
                    "score": hit.score,
                    **hit.payload
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} similar documents")
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar documents: {e}")
            return []
    
    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve document by ID
        
        Args:
            document_id: Document ID
            
        Returns:
            Document data or None if not found
        """
        try:
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[document_id],
                with_payload=True,
                with_vectors=False
            )
            
            if points:
                return {"id": points[0].id, **points[0].payload}
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None
    
    async def get_all_documents(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all documents
        
        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            
        Returns:
            List of all documents
        """
        try:
            # Use scroll to get all documents
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit or 1000,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            results = []
            for point in scroll_result[0]:  # scroll_result is (points, next_page_offset)
                result = {
                    "id": point.id,
                    **point.payload
                }
                results.append(result)
            
            logger.info(f"Retrieved {len(results)} documents")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving all documents: {e}")
            return []
    
    async def update_document_analysis(
        self,
        document_id: str,
        analysis_result: Dict[str, Any],
        embedding: Optional[List[float]] = None
    ) -> bool:
        """
        Update existing document analysis
        
        Args:
            document_id: Document ID
            analysis_result: Updated analysis result
            embedding: Updated embedding (optional)
            
        Returns:
            Success status
        """
        try:
            # Get existing document
            existing_points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[document_id],
                with_payload=True,
                with_vectors=True
            )
            
            if not existing_points:
                logger.error(f"Document {document_id} not found")
                return False
            
            existing_point = existing_points[0]
            
            # Update payload
            updated_payload = existing_point.payload.copy()
            updated_payload["analysis_result"] = analysis_result
            updated_payload["updated_at"] = datetime.utcnow().isoformat()
            
            # Create updated point
            updated_point = PointStruct(
                id=document_id,
                vector=embedding if embedding else existing_point.vector,
                payload=updated_payload
            )
            
            # Update in Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[updated_point]
            )
            
            logger.info(f"Updated document analysis for ID: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating document analysis: {e}")
            return False
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete document from Qdrant
        
        Args:
            document_id: Document ID
            
        Returns:
            Success status
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[document_id]
                )
            )
            
            logger.info(f"Deleted document with ID: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False
    
    async def search_by_metadata(
        self,
        filter_conditions: Dict[str, Any],
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search documents by metadata filters
        
        Args:
            filter_conditions: Metadata filter conditions
            limit: Maximum number of results
            
        Returns:
            List of matching documents
        """
        try:
            # Build Qdrant filter
            must_conditions = []
            for key, value in filter_conditions.items():
                must_conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    )
                )
            
            filter_obj = models.Filter(
                must=must_conditions
            )
            
            # Search with filter
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_obj,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            results = []
            for point in scroll_result[0]:
                result = {
                    "id": point.id,
                    **point.payload
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} documents matching filter")
            return results
            
        except Exception as e:
            logger.error(f"Error searching by metadata: {e}")
            return []
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics
        
        Returns:
            Collection statistics
        """
        try:
            info = self.client.get_collection(self.collection_name)
            
            return {
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status,
                "optimizer_status": info.optimizer_status
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}