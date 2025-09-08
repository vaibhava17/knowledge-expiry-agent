# Knowledge Expiry Agent

An AI-powered system for analyzing documents to identify knowledge that may be expired, outdated, or requiring attention. The system uses advanced language models, vector databases, and structured analysis to help organizations maintain up-to-date knowledge bases.

## 🏗 Architecture

The Knowledge Expiry Agent follows a modular architecture with clear separation of concerns:

### Core Components

- **AI Integration**: Uses `litellm` for multi-provider LLM support (OpenAI, Anthropic, etc.)
- **Vector Storage**: Qdrant for storing document embeddings and similarity search
- **Relational Database**: MySQL for structured metadata, critical points, and ownership tracking
- **File Processing**: Local file system support (extensible to cloud storage)
- **Report Generation**: Multi-format export (Excel, JSON, CSV)

### Workflow Modes

1. **Analyze Mode**: Processes documents and identifies knowledge expiry patterns
2. **Report Mode**: Generates comprehensive reports from analyzed data

## 📂 Project Structure

```
knowledge-expiry-agent/
├── src/
│   ├── api/                 # Future API endpoints
│   ├── core/
│   │   └── config.py        # Configuration management
│   ├── schemas/
│   │   └── database.py      # SQLAlchemy database models
│   ├── services/
│   │   ├── file_loader.py   # Document loading and processing
│   │   ├── ai_client.py     # LLM integration via litellm
│   │   ├── vector_db.py     # Qdrant vector operations
│   │   ├── relational_db.py # MySQL database operations
│   │   └── report_export.py # Report export functionality
│   └── utils/               # Utility functions
├── workflows/
│   ├── analyze.py           # Document analysis pipeline
│   └── report.py            # Report generation pipeline
├── prompts/
│   ├── analyze.txt          # Analysis prompt template
│   └── report.txt           # Report generation prompt
├── tests/                   # Test cases
├── logs/                    # Application logs
├── main.py                  # CLI entry point
├── requirements.txt         # Python dependencies
├── .env                     # Environment configuration
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- MySQL database
- Qdrant vector database
- API keys for LLM providers (OpenAI, Anthropic)

### Installation

1. **Clone and setup:**
```bash
git clone <repository-url>
cd knowledge-expiry-agent
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Setup databases:**
```bash
# Start Qdrant (using Docker)
docker run -p 6333:6333 qdrant/qdrant

# Create MySQL database
mysql -u root -p -e "CREATE DATABASE knowledge_expiry;"
```

4. **Initialize database tables:**
```python
from src.services.relational_db import DatabaseService
db = DatabaseService()
db.create_tables()
```

### Basic Usage

**Analyze documents in a directory:**
```bash
python main.py analyze /path/to/documents --recursive --types pdf,docx,md
```

**Generate a report:**
```bash
python main.py report --output report.xlsx --format excel
```

**Check system status:**
```bash
python main.py status
```

## 📋 Configuration

### Environment Variables

```env
# AI Configuration
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
DEFAULT_AI_MODEL=gpt-4-turbo-preview

# Database Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=knowledge_agent
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=knowledge_expiry

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=knowledge_documents

# Application Configuration
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=50
BATCH_SIZE=10
```

## 🔧 Features

### Document Analysis
- **Multi-format support**: PDF, DOCX, TXT, MD, HTML
- **Content extraction**: Text extraction with metadata preservation
- **AI-powered analysis**: Uses LLMs to identify expiry patterns
- **Confidence scoring**: Each analysis includes confidence metrics

### Knowledge Expiry Detection
- **Date pattern recognition**: Identifies timestamps and version references
- **Technology deprecation**: Detects outdated technology references
- **Process obsolescence**: Identifies potentially outdated procedures
- **Regulatory changes**: Flags compliance information that may be stale

### Vector Search
- **Semantic similarity**: Find related documents using embeddings
- **Duplicate detection**: Identify similar or redundant content
- **Knowledge gaps**: Discover missing information areas

### Comprehensive Reporting
- **Executive summaries**: High-level insights for leadership
- **Detailed analysis**: In-depth findings for knowledge managers
- **Action items**: Specific recommendations with priorities and timelines
- **Multiple formats**: Excel, JSON, CSV export options

### Database Schema
- **Documents**: File metadata and processing status
- **Critical Points**: Identified knowledge expiry items
- **Ownership**: Document responsibility tracking
- **Recommendations**: AI-generated action items
- **Sessions**: Analysis run tracking
- **Reports**: Generated report metadata

## 🔄 Workflows

### Analyze Workflow
1. **File Discovery**: Scan directories for supported documents
2. **Content Extraction**: Extract text and metadata
3. **AI Analysis**: Process content through LLM for expiry detection
4. **Vector Storage**: Store embeddings in Qdrant
5. **Structured Storage**: Save critical points and metadata to MySQL
6. **Batch Processing**: Handle large document sets efficiently

### Report Workflow
1. **Data Gathering**: Retrieve analyzed data from databases
2. **AI Report Generation**: Create comprehensive analysis using LLM
3. **Data Synthesis**: Combine structured data with AI insights
4. **Export Processing**: Generate reports in requested format
5. **Metadata Tracking**: Record report generation details

## 🎯 Use Cases

### Enterprise Knowledge Management
- **Document lifecycle management**: Track document freshness
- **Compliance audits**: Ensure regulatory information is current
- **Knowledge base maintenance**: Identify outdated wiki content
- **Onboarding materials**: Keep training documents current

### Technical Documentation
- **API documentation**: Flag deprecated endpoints
- **System procedures**: Identify outdated operational guides
- **Architecture decisions**: Track technology evolution
- **Deployment guides**: Ensure current environment information

### Regulatory Compliance
- **Policy documents**: Monitor regulation changes
- **Compliance procedures**: Update based on new requirements
- **Audit preparations**: Ensure documentation currency
- **Training materials**: Keep compliance training current

## 🔮 Future Enhancements

### Cloud Storage Integration
- Google Drive API integration
- SharePoint Online support
- Confluence knowledge base sync
- Slack workspace analysis

### Advanced Analytics
- Knowledge decay prediction models
- Organizational knowledge mapping
- Expertise identification
- Knowledge flow analysis

### API and Integrations
- REST API for programmatic access
- Webhook notifications for expiry alerts
- Integration with knowledge management systems
- Automated report scheduling

### Enhanced AI Features
- Multi-modal analysis (images, charts)
- Domain-specific knowledge models
- Collaborative filtering for recommendations
- Natural language query interface

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

[Your chosen license]

## 🆘 Support

For issues and questions:
- Check the [Issues](link-to-issues) page
- Review the documentation
- Contact the development team

---

**Knowledge Expiry Agent** - Keeping your organization's knowledge fresh and actionable.