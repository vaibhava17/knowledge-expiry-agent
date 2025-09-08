"""
Analyze Workflow - Complete pipeline for document analysis
Orchestrates file loading, AI analysis, vector storage, and database operations
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger
from datetime import datetime

from src.services.file_loader import FileLoader, DocumentInfo
from src.services.ai_client import AIClient, AnalysisResult
from src.services.vector_db import QdrantService
from src.services.relational_db import DatabaseService
from src.core.config import settings

class AnalyzeWorkflow:
    """Main workflow for analyzing documents for knowledge expiry"""
    
    def __init__(self):
        self.file_loader = FileLoader(max_file_size_mb=settings.max_file_size_mb)
        self.ai_client = AIClient()
        self.vector_db = QdrantService()
        self.relational_db = DatabaseService()
        
    async def run(
        self,
        directory_path: Path,
        recursive: bool = True,
        file_extensions: List[str] = None
    ) -> Dict[str, Any]:
        """
        Run the complete analyze workflow
        
        Args:
            directory_path: Path to directory containing documents
            recursive: Whether to search recursively
            file_extensions: File extensions to process
            
        Returns:
            Analysis results summary
        """
        logger.info(f"Starting analyze workflow for: {directory_path}")
        start_time = datetime.utcnow()
        
        # Create analysis session
        session_id = await self.relational_db.create_analysis_session(
            analysis_model=settings.default_ai_model
        )
        
        results = {
            "session_id": session_id,
            "files_processed": 0,
            "files_failed": 0,
            "critical_points": 0,
            "documents_stored": 0,
            "errors": []
        }
        
        try:
            # Step 1: Discover files
            logger.info("Discovering files...")
            documents = list(self.file_loader.discover_files(
                directory_path=directory_path,
                recursive=recursive,
                file_extensions=file_extensions
            ))
            
            if not documents:
                logger.warning("No documents found to analyze")
                return results
            
            logger.info(f"Found {len(documents)} documents to analyze")
            
            # Step 2: Process documents in batches
            batch_size = settings.batch_size
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                batch_results = await self._process_batch(batch, session_id)
                
                # Update results
                results["files_processed"] += batch_results["processed"]
                results["files_failed"] += batch_results["failed"]
                results["critical_points"] += batch_results["critical_points"]
                results["documents_stored"] += batch_results["stored"]
                results["errors"].extend(batch_results["errors"])
                
                logger.info(f"Processed batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}")
            
            # Step 3: Update analysis session
            await self.relational_db.update_analysis_session(
                session_id=session_id,
                documents_analyzed=results["files_processed"],
                critical_points_found=results["critical_points"],
                status="completed"
            )
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Analyze workflow completed in {duration:.2f} seconds")
            logger.info(f"Processed: {results['files_processed']} files")
            logger.info(f"Found: {results['critical_points']} critical points")
            
            return results
            
        except Exception as e:
            logger.error(f"Analyze workflow failed: {e}")
            results["errors"].append(f"Workflow error: {str(e)}")
            
            # Update session with error status
            await self.relational_db.update_analysis_session(
                session_id=session_id,
                documents_analyzed=results["files_processed"],
                critical_points_found=results["critical_points"],
                status="error"
            )
            
            return results
    
    async def _process_batch(self, documents: List[DocumentInfo], session_id: str) -> Dict[str, Any]:
        """Process a batch of documents"""
        batch_results = {
            "processed": 0,
            "failed": 0,
            "critical_points": 0,
            "stored": 0,
            "errors": []
        }
        
        # Create tasks for concurrent processing
        tasks = []
        for doc_info in documents:
            task = asyncio.create_task(self._process_single_document(doc_info, session_id))
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                batch_results["failed"] += 1
                batch_results["errors"].append(f"Document {documents[i].filename}: {str(result)}")
            elif result:
                batch_results["processed"] += 1
                batch_results["critical_points"] += result.get("critical_points", 0)
                batch_results["stored"] += 1
            else:
                batch_results["failed"] += 1
        
        return batch_results
    
    async def _process_single_document(self, doc_info: DocumentInfo, session_id: str) -> Dict[str, Any]:
        """Process a single document through the complete pipeline"""
        try:
            logger.info(f"Processing document: {doc_info.filename}")
            
            # Step 1: Load document content
            doc_with_content = self.file_loader.load_document_content(doc_info)
            
            if not doc_with_content.content:
                logger.warning(f"No content loaded for {doc_info.filename}")
                return None
            
            # Step 2: Create document record in MySQL
            document_metadata = {
                "filename": doc_info.filename,
                "file_type": doc_info.file_type,
                "file_size": doc_info.file_size,
                "modified_at": datetime.fromtimestamp(doc_info.modified_at) if doc_info.modified_at else None
            }
            
            # Step 3: Analyze document with AI
            analysis_result = await self.ai_client.analyze_document(
                content=doc_with_content.content,
                document_info=document_metadata
            )
            
            if not analysis_result.embedding:
                logger.warning(f"No embedding generated for {doc_info.filename}")
                return None
            
            # Step 4: Store in Qdrant vector database
            qdrant_id = await self.vector_db.store_document_analysis(
                document_path=doc_info.file_path,
                filename=doc_info.filename,
                content_summary=analysis_result.document_summary,
                analysis_result={
                    "critical_points": [asdict(point) for point in analysis_result.critical_points] if hasattr(analysis_result.critical_points[0] if analysis_result.critical_points else {}, '__dict__') else analysis_result.critical_points,
                    "expiry_indicators": analysis_result.knowledge_expiry_indicators,
                    "recommendations": analysis_result.recommendations,
                    "confidence_score": analysis_result.confidence_score
                },
                embedding=analysis_result.embedding,
                metadata={
                    "file_size": doc_info.file_size,
                    "mime_type": doc_info.mime_type,
                    "session_id": session_id
                }
            )
            
            # Step 5: Create document record in MySQL with Qdrant ID
            document_id = await self.relational_db.create_document(
                qdrant_id=qdrant_id,
                file_path=doc_info.file_path,
                filename=doc_info.filename,
                file_type=doc_info.file_type,
                file_size=doc_info.file_size,
                mime_type=doc_info.mime_type,
                modified_at=datetime.fromtimestamp(doc_info.modified_at) if doc_info.modified_at else None
            )
            
            # Step 6: Update document with analysis results
            await self.relational_db.update_document_analysis(
                document_id=document_id,
                content_summary=analysis_result.document_summary,
                analysis_confidence=analysis_result.confidence_score
            )
            
            # Step 7: Store critical points
            critical_point_ids = []
            if analysis_result.critical_points:
                critical_point_ids = await self.relational_db.create_critical_points(
                    document_id=document_id,
                    critical_points=analysis_result.critical_points,
                    extracted_by_model=settings.default_ai_model
                )
            
            # Step 8: Create recommendations for high-priority critical points
            recommendations_created = 0
            for i, point in enumerate(analysis_result.critical_points):
                if point.get('urgency') in ['high', 'critical'] and i < len(critical_point_ids):
                    # Generate specific recommendations for this critical point
                    recommendations = [
                        {
                            "title": f"Review {point.get('category', 'knowledge')} information",
                            "description": f"Review and update: {point.get('description', 'Unknown')}",
                            "priority": point.get('urgency', 'medium'),
                            "suggested_owner_role": "Knowledge Manager",
                            "suggested_timeline": "30 days"
                        }
                    ]
                    
                    rec_ids = await self.relational_db.create_recommendations(
                        critical_point_id=critical_point_ids[i],
                        recommendations=recommendations,
                        generated_by_model=settings.default_ai_model
                    )
                    recommendations_created += len(rec_ids)
            
            result = {
                "document_id": document_id,
                "qdrant_id": qdrant_id,
                "critical_points": len(analysis_result.critical_points),
                "recommendations_created": recommendations_created,
                "confidence_score": analysis_result.confidence_score
            }
            
            logger.info(f"Successfully processed {doc_info.filename} - {result['critical_points']} critical points found")
            return result
            
        except Exception as e:
            logger.error(f"Error processing document {doc_info.filename}: {e}")
            raise

def run_analyze_workflow(
    directory_path: Path,
    recursive: bool = True,
    file_extensions: List[str] = None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for the analyze workflow
    
    Args:
        directory_path: Path to directory containing documents
        recursive: Whether to search recursively
        file_extensions: File extensions to process
        
    Returns:
        Analysis results summary
    """
    workflow = AnalyzeWorkflow()
    
    # Create database tables if they don't exist
    workflow.relational_db.create_tables()
    
    # Run the async workflow
    return asyncio.run(workflow.run(directory_path, recursive, file_extensions))

# Helper function to convert dataclass to dict
def asdict(obj):
    """Convert dataclass to dictionary"""
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    return obj