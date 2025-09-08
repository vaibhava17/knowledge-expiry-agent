# Knowledge Expiry Agent - Architecture Documentation

## 🏛️ System Architecture Overview

The Knowledge Expiry Agent is designed as a modular, scalable system for intelligent document analysis and knowledge management. The architecture follows modern software engineering principles with clean separation of concerns, async processing, and extensible design patterns.

### 🎯 Core Design Principles

1. **Modularity**: Each component has a single responsibility
2. **Scalability**: Designed to handle large document corpora
3. **Extensibility**: Easy to add new file types, AI providers, and storage backends
4. **Reliability**: Comprehensive error handling and logging
5. **Performance**: Async processing and efficient database operations

## 🧩 System Components

### 1. CLI Interface Layer
```
main.py
├── analyze command - Document analysis orchestration
├── report command - Report generation
└── status command - System health checks
```

**Responsibilities:**
- User interaction and command parsing
- Parameter validation
- Workflow orchestration
- Error reporting

### 2. Core Services Layer
```
src/services/
├── ai_client.py - LLM integration and prompt management
├── vector_db.py - Qdrant vector operations
├── relational_db.py - MySQL structured data operations
├── file_loader.py - Document processing and content extraction
└── report_export.py - Multi-format report generation
```

**AI Client Service:**
- Multi-provider LLM support via LiteLLM
- Structured prompt management
- Response parsing and validation
- Embedding generation

**Vector Database Service:**
- Document embedding storage
- Semantic similarity search
- Vector collection management
- Metadata association

**Relational Database Service:**
- Critical point storage and retrieval
- Ownership and responsibility tracking
- Analysis session management
- Statistical queries and reporting

**File Loader Service:**
- Multi-format document support
- Content extraction pipelines
- Metadata preservation
- Error resilience

**Report Export Service:**
- Excel generation with formatting
- JSON/CSV export capabilities
- Chart and visualization creation
- Template management

### 3. Data Layer
```
src/schemas/
└── database.py - SQLAlchemy models and relationships
```

**Database Schema Design:**
- Documents: File metadata and processing status
- Critical Points: AI-identified knowledge expiry items
- Document Ownership: Responsibility and review tracking
- Recommendations: AI-generated action items
- Analysis Sessions: Batch processing tracking
- Reports: Generated report metadata

### 4. Workflow Orchestration
```
workflows/
├── analyze.py - End-to-end document analysis pipeline
└── report.py - Comprehensive report generation workflow
```

**Analyze Workflow:**
1. File discovery and validation
2. Content extraction and preprocessing
3. AI analysis and embedding generation
4. Dual database storage (vector + relational)
5. Critical point extraction and categorization
6. Recommendation generation

**Report Workflow:**
1. Data aggregation from multiple sources
2. AI-powered report synthesis
3. Statistical analysis and trend identification
4. Multi-format export generation
5. Metadata tracking and audit trails

### 5. Configuration Management
```
src/core/
└── config.py - Centralized configuration with environment variables
```

**Configuration Areas:**
- AI provider settings and API keys
- Database connection parameters
- Processing limits and batch sizes
- Logging and monitoring configuration

## 🔄 Data Flow Architecture

### Document Analysis Flow
```
Document Input → File Loader → AI Analysis → Vector Storage
                                    ↓
Critical Points ← MySQL Storage ← Response Parser
```

### Report Generation Flow
```
Vector DB Query → Data Aggregation → AI Report Generation → Export Processing
       ↓
MySQL Queries → Statistical Analysis → Format Generation → File Output
```

### Inter-Service Communication
- **Synchronous**: Direct method calls for real-time operations
- **Asynchronous**: Async/await for I/O intensive operations
- **Batch Processing**: Queue-based processing for large datasets
- **Error Handling**: Circuit breaker pattern for external service failures

## 💾 Data Storage Strategy

### Vector Database (Qdrant)
**Purpose**: Semantic search and similarity analysis
- Document embeddings (1536-dimensional vectors)
- AI analysis responses and metadata
- Similarity search capabilities
- Scalable vector operations

**Data Structure:**
```json
{
  "id": "uuid",
  "vector": [1536-dim embedding],
  "payload": {
    "document_path": "string",
    "filename": "string",
    "content_summary": "string",
    "analysis_result": {object},
    "metadata": {object},
    "created_at": "timestamp"
  }
}
```

### Relational Database (MySQL)
**Purpose**: Structured data and complex queries
- Normalized schema for efficient storage
- Foreign key relationships for data integrity
- Indexing for fast queries
- Transaction support for consistency

**Key Entities:**
- Documents (metadata, status, processing info)
- Critical Points (expiry items, urgency, categories)
- Ownership (responsibility, review schedules)
- Recommendations (AI-generated actions)
- Sessions (analysis tracking)
- Reports (generation metadata)

## 🔌 Integration Architecture

### AI Provider Integration
- **Abstraction Layer**: LiteLLM for provider independence
- **Fallback Strategy**: Multiple provider support with automatic failover
- **Rate Limiting**: Built-in request throttling
- **Cost Optimization**: Model selection based on task complexity

### Database Integration
- **Connection Pooling**: Efficient resource utilization
- **Migration Support**: Schema version management
- **Backup Strategy**: Automated backup and recovery
- **Monitoring**: Performance metrics and health checks

## 🔐 Security Architecture

### Data Protection
- **Encryption at Rest**: Database and file system encryption
- **Encryption in Transit**: TLS for all network communications
- **API Key Management**: Secure credential storage
- **Access Control**: Role-based permissions (future implementation)

### Privacy Considerations
- **Data Anonymization**: PII scrubbing capabilities
- **Audit Trails**: Complete operation logging
- **Data Retention**: Configurable retention policies
- **Compliance**: GDPR/CCPA ready architecture

## 🎯 Performance Characteristics

### Scalability Metrics
- **Document Processing**: 100-1000 docs/hour (depending on size)
- **Concurrent Operations**: 10-50 parallel analysis tasks
- **Database Performance**: Sub-second queries for <1M records
- **Memory Usage**: ~100MB base + ~10MB per concurrent task

### Optimization Strategies
- **Batch Processing**: Configurable batch sizes
- **Async Operations**: Non-blocking I/O for external services
- **Caching**: Result caching for repeated operations
- **Database Indexing**: Optimized query performance

## 🔍 Monitoring and Observability

### Logging Strategy
- **Structured Logging**: JSON format for log aggregation
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Contextual Information**: Request IDs and session tracking
- **Performance Metrics**: Operation timing and resource usage

### Health Checks
- **Database Connectivity**: Real-time connection status
- **AI Provider Status**: API availability monitoring
- **Resource Usage**: Memory, CPU, and disk monitoring
- **Error Rates**: Failure rate tracking and alerting

## 🧪 Testing Architecture

### Test Strategy
- **Unit Tests**: Individual component testing
- **Integration Tests**: Service interaction validation
- **End-to-End Tests**: Complete workflow validation
- **Performance Tests**: Load and stress testing

### Test Categories
- **Service Tests**: AI client, database operations, file processing
- **Workflow Tests**: Complete pipeline validation
- **Data Tests**: Schema validation and data integrity
- **Error Tests**: Failure scenario validation

## 🚀 Deployment Architecture

### Environment Strategy
- **Development**: Local development with Docker containers
- **Staging**: Production-like environment for testing
- **Production**: Scalable cloud deployment

### Container Strategy
- **Application Container**: Python app with dependencies
- **Database Containers**: MySQL and Qdrant instances
- **Orchestration**: Docker Compose or Kubernetes
- **Configuration**: Environment-specific settings

### Scaling Strategy
- **Horizontal Scaling**: Multiple application instances
- **Database Scaling**: Read replicas and sharding
- **Load Balancing**: Request distribution
- **Resource Management**: Auto-scaling based on load

## 📊 Analytics and Insights

### Operational Analytics
- **Processing Metrics**: Document analysis rates and success rates
- **Usage Patterns**: Most analyzed document types and sources
- **Error Analysis**: Common failure patterns and resolution
- **Performance Trends**: Processing time and resource utilization

### Business Intelligence
- **Knowledge Decay Patterns**: Industry and organizational trends
- **Risk Assessment**: Predictive modeling for knowledge expiry
- **ROI Analysis**: Value delivered through knowledge maintenance
- **Compliance Tracking**: Regulatory requirement adherence

This architecture provides a solid foundation for the current system while enabling future enhancements and scalability requirements.