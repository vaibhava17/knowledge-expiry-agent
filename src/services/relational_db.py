"""
MySQL database service using SQLAlchemy
Handles CRUD operations for critical points, metadata, and ownership
"""

from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger
from contextlib import contextmanager

from src.core.config import settings
from src.schemas.database import (
    Base, Document, CriticalPoint, DocumentOwnership, 
    Recommendation, AnalysisSession, KnowledgeExpiryReport,
    UrgencyLevel, DocumentStatus, KnowledgeCategory
)

class DatabaseService:
    """MySQL database service for Knowledge Expiry Agent"""
    
    def __init__(self):
        self.engine = create_engine(
            settings.mysql_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=(settings.log_level.upper() == "DEBUG")
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    # Document operations
    async def create_document(
        self,
        qdrant_id: str,
        file_path: str,
        filename: str,
        file_type: str,
        file_size: int,
        mime_type: Optional[str] = None,
        modified_at: Optional[datetime] = None
    ) -> int:
        """Create a new document record"""
        try:
            with self.get_session() as session:
                document = Document(
                    qdrant_id=qdrant_id,
                    file_path=file_path,
                    filename=filename,
                    file_type=file_type,
                    file_size=file_size,
                    mime_type=mime_type,
                    modified_at=modified_at,
                    status=DocumentStatus.PENDING
                )
                session.add(document)
                session.flush()  # Get the ID without committing
                doc_id = document.id
                logger.info(f"Created document record: {filename} (ID: {doc_id})")
                return doc_id
        except SQLAlchemyError as e:
            logger.error(f"Error creating document: {e}")
            raise
    
    async def update_document_analysis(
        self,
        document_id: int,
        content_summary: str,
        analysis_confidence: float,
        status: DocumentStatus = DocumentStatus.ANALYZED
    ) -> bool:
        """Update document with analysis results"""
        try:
            with self.get_session() as session:
                document = session.query(Document).filter(Document.id == document_id).first()
                if not document:
                    logger.error(f"Document not found: {document_id}")
                    return False
                
                document.content_summary = content_summary
                document.analysis_confidence = analysis_confidence
                document.status = status
                document.processed_at = datetime.utcnow()
                
                logger.info(f"Updated document analysis: {document.filename}")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating document analysis: {e}")
            return False
    
    async def get_document_by_qdrant_id(self, qdrant_id: str) -> Optional[Dict[str, Any]]:
        """Get document by Qdrant ID"""
        try:
            with self.get_session() as session:
                document = session.query(Document).filter(Document.qdrant_id == qdrant_id).first()
                if document:
                    return {
                        "id": document.id,
                        "qdrant_id": document.qdrant_id,
                        "filename": document.filename,
                        "file_path": document.file_path,
                        "status": document.status.value,
                        "analysis_confidence": document.analysis_confidence,
                        "content_summary": document.content_summary
                    }
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting document by Qdrant ID: {e}")
            return None
    
    # Critical Points operations
    async def create_critical_points(
        self,
        document_id: int,
        critical_points: List[Dict[str, Any]],
        extracted_by_model: str
    ) -> List[int]:
        """Create multiple critical points for a document"""
        try:
            with self.get_session() as session:
                point_ids = []
                
                for point_data in critical_points:
                    critical_point = CriticalPoint(
                        document_id=document_id,
                        description=point_data.get('description', ''),
                        category=KnowledgeCategory(point_data.get('category', 'technical').lower()),
                        urgency=UrgencyLevel(point_data.get('urgency', 'medium').lower()),
                        last_updated_date=point_data.get('last_updated_date'),
                        expiry_indicators=point_data.get('expiry_indicators', []),
                        confidence_score=point_data.get('confidence_score'),
                        context_snippet=point_data.get('context_snippet'),
                        page_number=point_data.get('page_number'),
                        section_title=point_data.get('section_title'),
                        extracted_by_model=extracted_by_model
                    )
                    session.add(critical_point)
                    session.flush()
                    point_ids.append(critical_point.id)
                
                logger.info(f"Created {len(point_ids)} critical points for document {document_id}")
                return point_ids
        except SQLAlchemyError as e:
            logger.error(f"Error creating critical points: {e}")
            return []
    
    async def get_critical_points_by_document(self, document_id: int) -> List[Dict[str, Any]]:
        """Get all critical points for a document"""
        try:
            with self.get_session() as session:
                points = session.query(CriticalPoint).filter(
                    CriticalPoint.document_id == document_id
                ).all()
                
                return [
                    {
                        "id": point.id,
                        "description": point.description,
                        "category": point.category.value,
                        "urgency": point.urgency.value,
                        "last_updated_date": point.last_updated_date,
                        "confidence_score": point.confidence_score,
                        "context_snippet": point.context_snippet
                    }
                    for point in points
                ]
        except SQLAlchemyError as e:
            logger.error(f"Error getting critical points: {e}")
            return []
    
    async def get_critical_points_by_urgency(self, urgency: UrgencyLevel) -> List[Dict[str, Any]]:
        """Get critical points filtered by urgency level"""
        try:
            with self.get_session() as session:
                points = session.query(CriticalPoint).filter(
                    CriticalPoint.urgency == urgency
                ).join(Document).all()
                
                return [
                    {
                        "id": point.id,
                        "description": point.description,
                        "category": point.category.value,
                        "urgency": point.urgency.value,
                        "document_filename": point.document.filename,
                        "confidence_score": point.confidence_score
                    }
                    for point in points
                ]
        except SQLAlchemyError as e:
            logger.error(f"Error getting critical points by urgency: {e}")
            return []
    
    # Document Ownership operations
    async def create_document_ownership(
        self,
        document_id: int,
        owner_name: Optional[str] = None,
        owner_email: Optional[str] = None,
        department: Optional[str] = None,
        role: Optional[str] = None
    ) -> int:
        """Create document ownership record"""
        try:
            with self.get_session() as session:
                ownership = DocumentOwnership(
                    document_id=document_id,
                    owner_name=owner_name,
                    owner_email=owner_email,
                    department=department,
                    role=role,
                    is_primary=True
                )
                session.add(ownership)
                session.flush()
                
                logger.info(f"Created ownership record for document {document_id}")
                return ownership.id
        except SQLAlchemyError as e:
            logger.error(f"Error creating document ownership: {e}")
            raise
    
    # Recommendations operations
    async def create_recommendations(
        self,
        critical_point_id: int,
        recommendations: List[Dict[str, Any]],
        generated_by_model: str
    ) -> List[int]:
        """Create recommendations for a critical point"""
        try:
            with self.get_session() as session:
                rec_ids = []
                
                for rec_data in recommendations:
                    recommendation = Recommendation(
                        critical_point_id=critical_point_id,
                        title=rec_data.get('title', ''),
                        description=rec_data.get('description', ''),
                        priority=UrgencyLevel(rec_data.get('priority', 'medium').lower()),
                        estimated_effort_hours=rec_data.get('estimated_effort_hours'),
                        suggested_owner_role=rec_data.get('suggested_owner_role'),
                        suggested_timeline=rec_data.get('suggested_timeline'),
                        dependencies=rec_data.get('dependencies', []),
                        generated_by_model=generated_by_model
                    )
                    session.add(recommendation)
                    session.flush()
                    rec_ids.append(recommendation.id)
                
                logger.info(f"Created {len(rec_ids)} recommendations for critical point {critical_point_id}")
                return rec_ids
        except SQLAlchemyError as e:
            logger.error(f"Error creating recommendations: {e}")
            return []
    
    # Analysis Session operations
    async def create_analysis_session(self, analysis_model: str) -> str:
        """Create new analysis session"""
        try:
            session_id = str(uuid.uuid4())
            with self.get_session() as session:
                analysis_session = AnalysisSession(
                    session_id=session_id,
                    analysis_model=analysis_model,
                    status="running"
                )
                session.add(analysis_session)
                
                logger.info(f"Created analysis session: {session_id}")
                return session_id
        except SQLAlchemyError as e:
            logger.error(f"Error creating analysis session: {e}")
            raise
    
    async def update_analysis_session(
        self,
        session_id: str,
        documents_analyzed: int,
        critical_points_found: int,
        status: str = "completed"
    ) -> bool:
        """Update analysis session with results"""
        try:
            with self.get_session() as session:
                analysis_session = session.query(AnalysisSession).filter(
                    AnalysisSession.session_id == session_id
                ).first()
                
                if not analysis_session:
                    logger.error(f"Analysis session not found: {session_id}")
                    return False
                
                analysis_session.documents_analyzed = documents_analyzed
                analysis_session.critical_points_found = critical_points_found
                analysis_session.status = status
                analysis_session.completed_at = datetime.utcnow()
                
                # Calculate duration
                if analysis_session.started_at:
                    duration = analysis_session.completed_at - analysis_session.started_at
                    analysis_session.duration_seconds = int(duration.total_seconds())
                
                logger.info(f"Updated analysis session: {session_id}")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating analysis session: {e}")
            return False
    
    # Report operations
    async def create_report_record(
        self,
        title: str,
        report_type: str,
        output_format: str,
        documents_included: int,
        generated_by_model: str
    ) -> str:
        """Create knowledge expiry report record"""
        try:
            report_id = str(uuid.uuid4())
            with self.get_session() as session:
                report = KnowledgeExpiryReport(
                    report_id=report_id,
                    title=title,
                    report_type=report_type,
                    output_format=output_format,
                    documents_included=documents_included,
                    generated_by_model=generated_by_model,
                    status="generating"
                )
                session.add(report)
                
                logger.info(f"Created report record: {report_id}")
                return report_id
        except SQLAlchemyError as e:
            logger.error(f"Error creating report record: {e}")
            raise
    
    async def update_report_record(
        self,
        report_id: str,
        expired_knowledge_count: int,
        critical_findings_count: int,
        recommendations_count: int,
        output_path: Optional[str] = None,
        status: str = "completed"
    ) -> bool:
        """Update report record with results"""
        try:
            with self.get_session() as session:
                report = session.query(KnowledgeExpiryReport).filter(
                    KnowledgeExpiryReport.report_id == report_id
                ).first()
                
                if not report:
                    logger.error(f"Report record not found: {report_id}")
                    return False
                
                report.expired_knowledge_count = expired_knowledge_count
                report.critical_findings_count = critical_findings_count
                report.recommendations_count = recommendations_count
                report.output_path = output_path
                report.status = status
                
                logger.info(f"Updated report record: {report_id}")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating report record: {e}")
            return False
    
    # Analytics and reporting queries
    async def get_documents_summary(self) -> Dict[str, Any]:
        """Get summary statistics of all documents"""
        try:
            with self.get_session() as session:
                total_docs = session.query(func.count(Document.id)).scalar()
                analyzed_docs = session.query(func.count(Document.id)).filter(
                    Document.status == DocumentStatus.ANALYZED
                ).scalar()
                
                avg_confidence = session.query(func.avg(Document.analysis_confidence)).filter(
                    Document.analysis_confidence.isnot(None)
                ).scalar()
                
                return {
                    "total_documents": total_docs or 0,
                    "analyzed_documents": analyzed_docs or 0,
                    "average_confidence": float(avg_confidence) if avg_confidence else 0.0,
                    "analysis_completion_rate": (analyzed_docs / total_docs * 100) if total_docs > 0 else 0
                }
        except SQLAlchemyError as e:
            logger.error(f"Error getting documents summary: {e}")
            return {}
    
    async def get_critical_points_summary(self) -> Dict[str, Any]:
        """Get summary statistics of critical points"""
        try:
            with self.get_session() as session:
                total_points = session.query(func.count(CriticalPoint.id)).scalar()
                
                # Count by urgency
                urgency_counts = session.query(
                    CriticalPoint.urgency,
                    func.count(CriticalPoint.id)
                ).group_by(CriticalPoint.urgency).all()
                
                urgency_dict = {urgency.value: count for urgency, count in urgency_counts}
                
                # Count by category
                category_counts = session.query(
                    CriticalPoint.category,
                    func.count(CriticalPoint.id)
                ).group_by(CriticalPoint.category).all()
                
                category_dict = {category.value: count for category, count in category_counts}
                
                return {
                    "total_critical_points": total_points or 0,
                    "by_urgency": urgency_dict,
                    "by_category": category_dict
                }
        except SQLAlchemyError as e:
            logger.error(f"Error getting critical points summary: {e}")
            return {}