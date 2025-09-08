"""
File loading service for documents
Supports local file system with future extensibility for cloud storage
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass
import mimetypes
from loguru import logger

@dataclass
class DocumentInfo:
    """Document metadata structure"""
    file_path: str
    filename: str
    file_size: int
    file_type: str
    mime_type: Optional[str]
    created_at: Optional[float]
    modified_at: Optional[float]
    content: Optional[str] = None

class FileLoader:
    """File loading service for different document types"""
    
    SUPPORTED_EXTENSIONS = {
        '.txt': 'text/plain',
        '.md': 'text/markdown', 
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.rtf': 'application/rtf',
        '.html': 'text/html',
        '.htm': 'text/html'
    }
    
    def __init__(self, max_file_size_mb: int = 50):
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        
    def discover_files(
        self, 
        directory_path: Path, 
        recursive: bool = True,
        file_extensions: Optional[List[str]] = None
    ) -> Generator[DocumentInfo, None, None]:
        """
        Discover files in directory matching criteria
        
        Args:
            directory_path: Path to search
            recursive: Search subdirectories
            file_extensions: List of extensions to filter (e.g., ['pdf', 'docx'])
        
        Yields:
            DocumentInfo objects for discovered files
        """
        if not directory_path.exists():
            logger.error(f"Directory does not exist: {directory_path}")
            return
            
        if file_extensions:
            extensions = {f".{ext.lower().lstrip('.')}" for ext in file_extensions}
        else:
            extensions = set(self.SUPPORTED_EXTENSIONS.keys())
        
        search_pattern = "**/*" if recursive else "*"
        
        for file_path in directory_path.glob(search_pattern):
            if not file_path.is_file():
                continue
                
            if file_path.suffix.lower() not in extensions:
                continue
                
            try:
                file_stats = file_path.stat()
                
                if file_stats.st_size > self.max_file_size_bytes:
                    logger.warning(f"File too large, skipping: {file_path}")
                    continue
                    
                doc_info = DocumentInfo(
                    file_path=str(file_path),
                    filename=file_path.name,
                    file_size=file_stats.st_size,
                    file_type=file_path.suffix.lower(),
                    mime_type=self._get_mime_type(file_path),
                    created_at=file_stats.st_ctime,
                    modified_at=file_stats.st_mtime
                )
                
                yield doc_info
                
            except (OSError, PermissionError) as e:
                logger.error(f"Error accessing file {file_path}: {e}")
                continue
    
    def load_document_content(self, doc_info: DocumentInfo) -> DocumentInfo:
        """
        Load content from document
        
        Args:
            doc_info: Document information
            
        Returns:
            DocumentInfo with content loaded
        """
        try:
            if doc_info.file_type == '.txt' or doc_info.file_type == '.md':
                content = self._load_text_file(doc_info.file_path)
            elif doc_info.file_type == '.pdf':
                content = self._load_pdf_file(doc_info.file_path)
            elif doc_info.file_type in ['.docx', '.doc']:
                content = self._load_word_file(doc_info.file_path)
            elif doc_info.file_type in ['.html', '.htm']:
                content = self._load_html_file(doc_info.file_path)
            else:
                logger.warning(f"Unsupported file type: {doc_info.file_type}")
                content = ""
                
            doc_info.content = content
            return doc_info
            
        except Exception as e:
            logger.error(f"Error loading content from {doc_info.file_path}: {e}")
            doc_info.content = ""
            return doc_info
    
    def _get_mime_type(self, file_path: Path) -> Optional[str]:
        """Get MIME type for file"""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or self.SUPPORTED_EXTENSIONS.get(file_path.suffix.lower())
    
    def _load_text_file(self, file_path: str) -> str:
        """Load plain text or markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
    
    def _load_pdf_file(self, file_path: str) -> str:
        """Load PDF file content"""
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except ImportError:
            logger.warning("PyPDF2 not installed, cannot read PDF files")
            return ""
        except Exception as e:
            logger.error(f"Error reading PDF {file_path}: {e}")
            return ""
    
    def _load_word_file(self, file_path: str) -> str:
        """Load Word document content"""
        try:
            import docx
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except ImportError:
            logger.warning("python-docx not installed, cannot read Word files")
            return ""
        except Exception as e:
            logger.error(f"Error reading Word document {file_path}: {e}")
            return ""
    
    def _load_html_file(self, file_path: str) -> str:
        """Load HTML file content"""
        try:
            from bs4 import BeautifulSoup
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                return soup.get_text()
        except ImportError:
            logger.warning("beautifulsoup4 not installed, cannot read HTML files")
            return ""
        except Exception as e:
            logger.error(f"Error reading HTML file {file_path}: {e}")
            return ""

# Future extensibility for cloud storage
class CloudFileLoader:
    """Base class for cloud file loaders (Google Drive, SharePoint, etc.)"""
    
    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path
    
    def authenticate(self):
        """Authenticate with cloud service"""
        raise NotImplementedError
    
    def list_files(self) -> List[Dict]:
        """List files in cloud storage"""
        raise NotImplementedError
    
    def download_file(self, file_id: str) -> bytes:
        """Download file content"""
        raise NotImplementedError