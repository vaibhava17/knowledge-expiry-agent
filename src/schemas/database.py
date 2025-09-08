"""
Database schemas using SQLAlchemy for MySQL
Stores structured critical points, metadata, and ownership information
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Enum, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class UrgencyLevel(enum.Enum):
    """Urgency levels for critical points"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

class DocumentStatus(enum.Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    ERROR = "error"

class KnowledgeCategory(enum.Enum):
    """Categories of knowledge points"""
    TECHNICAL = "technical"
    PROCESS = "process"
    POLICY = "policy"
    REGULATORY = "regulatory"
    PRODUCT = "product"
    ORGANIZATIONAL = "organizational"

class Document(Base):
    """Documents table - tracks analyzed documents"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    qdrant_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID from Qdrant
    file_path = Column(String(500), nullable=False)
    filename = Column(String(255), nullable=False, index=True)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=True)
    
    # Processing metadata
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    analysis_confidence = Column(Float, nullable=True)
    content_summary = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    modified_at = Column(DateTime, nullable=True)  # File modification time
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    critical_points = relationship("CriticalPoint", back_populates="document", cascade="all, delete-orphan")
    ownership_info = relationship("DocumentOwnership", back_populates="document", cascade="all, delete-orphan")

class CriticalPoint(Base):
    """Critical knowledge points extracted from documents"""
    __tablename__ = "critical_points"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    
    # Knowledge point details
    description = Column(Text, nullable=False)
    category = Column(Enum(KnowledgeCategory), nullable=False, index=True)
    urgency = Column(Enum(UrgencyLevel), nullable=False, index=True)
    
    # Expiry analysis
    last_updated_date = Column(DateTime, nullable=True)
    expiry_indicators = Column(JSON, nullable=True)  # List of expiry indicators
    confidence_score = Column(Float, nullable=True)
    
    # Context information
    context_snippet = Column(Text, nullable=True)  # Relevant text from document
    page_number = Column(Integer, nullable=True)
    section_title = Column(String(255), nullable=True)
    
    # Metadata
    extracted_by_model = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="critical_points")
    recommendations = relationship("Recommendation", back_populates="critical_point", cascade="all, delete-orphan")

class DocumentOwnership(Base):
    """Document ownership and responsibility tracking"""
    __tablename__ = "document_ownership"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    
    # Ownership details
    owner_name = Column(String(255), nullable=True)
    owner_email = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True, index=True)
    role = Column(String(255), nullable=True)
    
    # Review information
    last_reviewed_by = Column(String(255), nullable=True)
    last_review_date = Column(DateTime, nullable=True)
    next_review_date = Column(DateTime, nullable=True)
    review_frequency_months = Column(Integer, nullable=True)
    
    # Status
    is_primary = Column(Boolean, default=True, nullable=False)  # Primary vs secondary owner
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="ownership_info")

class Recommendation(Base):
    """Recommendations for addressing knowledge expiry"""
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    critical_point_id = Column(Integer, ForeignKey("critical_points.id"), nullable=False, index=True)
    
    # Recommendation details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(Enum(UrgencyLevel), nullable=False)
    
    # Implementation details
    estimated_effort_hours = Column(Integer, nullable=True)
    suggested_owner_role = Column(String(255), nullable=True)
    suggested_timeline = Column(String(255), nullable=True)
    dependencies = Column(JSON, nullable=True)  # List of dependencies
    
    # Status tracking
    is_implemented = Column(Boolean, default=False, nullable=False)
    implemented_date = Column(DateTime, nullable=True)
    implementation_notes = Column(Text, nullable=True)
    
    # Metadata
    generated_by_model = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    critical_point = relationship("CriticalPoint", back_populates="recommendations")

class AnalysisSession(Base):
    """Track analysis sessions for reporting and auditing"""
    __tablename__ = "analysis_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    
    # Session metadata
    documents_analyzed = Column(Integer, default=0, nullable=False)
    critical_points_found = Column(Integer, default=0, nullable=False)
    analysis_model = Column(String(100), nullable=False)
    
    # Configuration used
    file_types_analyzed = Column(JSON, nullable=True)
    directories_scanned = Column(JSON, nullable=True)
    
    # Results summary
    high_priority_items = Column(Integer, default=0, nullable=False)
    medium_priority_items = Column(Integer, default=0, nullable=False)
    low_priority_items = Column(Integer, default=0, nullable=False)
    
    # Status and timing
    status = Column(String(50), default="running", nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Error tracking
    errors_encountered = Column(Integer, default=0, nullable=False)
    error_details = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class KnowledgeExpiryReport(Base):
    """Generated reports tracking"""
    __tablename__ = "knowledge_expiry_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    
    # Report metadata
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    report_type = Column(String(50), nullable=False)  # 'executive', 'detailed', 'summary'
    output_format = Column(String(20), nullable=False)  # 'excel', 'json', 'csv'
    output_path = Column(String(500), nullable=True)
    
    # Scope of report
    documents_included = Column(Integer, default=0, nullable=False)
    date_range_start = Column(DateTime, nullable=True)
    date_range_end = Column(DateTime, nullable=True)
    departments_included = Column(JSON, nullable=True)
    
    # Report findings
    expired_knowledge_count = Column(Integer, default=0, nullable=False)
    critical_findings_count = Column(Integer, default=0, nullable=False)
    recommendations_count = Column(Integer, default=0, nullable=False)
    
    # Generation details
    generated_by_model = Column(String(100), nullable=False)
    generation_duration_seconds = Column(Integer, nullable=True)
    
    # Status
    status = Column(String(50), default="generating", nullable=False)
    
    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)