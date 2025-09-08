"""
AI Client service using litellm for multiple LLM providers
Handles document analysis and report generation
"""

from typing import Dict, List, Optional, Any
import asyncio
from dataclasses import dataclass
from loguru import logger
import litellm
from src.core.config import settings

@dataclass
class AnalysisResult:
    """Result from document analysis"""
    document_summary: str
    critical_points: List[Dict[str, Any]]
    knowledge_expiry_indicators: List[str]
    recommendations: List[str]
    confidence_score: float
    embedding: Optional[List[float]] = None

@dataclass
class ReportResult:
    """Result from report generation"""
    executive_summary: str
    expired_knowledge_count: int
    critical_findings: List[Dict[str, Any]]
    recommendations: List[str]
    action_items: List[Dict[str, Any]]

class AIClient:
    """AI client wrapper using litellm for multi-provider support"""
    
    def __init__(self):
        self.model = settings.default_ai_model
        self.embedding_model = settings.embedding_model
        
        # Configure API keys
        if settings.openai_api_key:
            litellm.openai_key = settings.openai_api_key
        if settings.anthropic_api_key:
            litellm.anthropic_key = settings.anthropic_api_key
    
    async def analyze_document(self, content: str, document_info: Dict[str, Any]) -> AnalysisResult:
        """
        Analyze document for knowledge expiry patterns
        
        Args:
            content: Document content
            document_info: Document metadata
            
        Returns:
            AnalysisResult with analysis findings
        """
        try:
            analysis_prompt = self._build_analysis_prompt(content, document_info)
            
            # Get analysis from LLM
            response = await litellm.acompletion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert knowledge analyst specializing in identifying outdated or expiring information in documents."
                    },
                    {
                        "role": "user", 
                        "content": analysis_prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            analysis_text = response.choices[0].message.content
            
            # Parse structured analysis
            parsed_result = self._parse_analysis_result(analysis_text)
            
            # Generate embedding
            embedding = await self._generate_embedding(content[:8000])  # Limit for embedding
            parsed_result.embedding = embedding
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"Error in document analysis: {e}")
            return AnalysisResult(
                document_summary="Analysis failed",
                critical_points=[],
                knowledge_expiry_indicators=[],
                recommendations=[],
                confidence_score=0.0
            )
    
    async def generate_report(self, documents_data: List[Dict], critical_points: List[Dict]) -> ReportResult:
        """
        Generate comprehensive knowledge expiry report
        
        Args:
            documents_data: List of analyzed documents
            critical_points: Critical knowledge points from database
            
        Returns:
            ReportResult with report content
        """
        try:
            report_prompt = self._build_report_prompt(documents_data, critical_points)
            
            response = await litellm.acompletion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior knowledge management consultant creating executive reports on knowledge expiry risks."
                    },
                    {
                        "role": "user",
                        "content": report_prompt
                    }
                ],
                temperature=0.1,
                max_tokens=3000
            )
            
            report_text = response.choices[0].message.content
            
            # Parse structured report
            parsed_report = self._parse_report_result(report_text)
            
            return parsed_report
            
        except Exception as e:
            logger.error(f"Error in report generation: {e}")
            return ReportResult(
                executive_summary="Report generation failed",
                expired_knowledge_count=0,
                critical_findings=[],
                recommendations=[],
                action_items=[]
            )
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text content"""
        try:
            response = await litellm.aembedding(
                model=self.embedding_model,
                input=text
            )
            return response['data'][0]['embedding']
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def _build_analysis_prompt(self, content: str, document_info: Dict[str, Any]) -> str:
        """Build prompt for document analysis"""
        return f"""
        Analyze the following document for knowledge expiry patterns and outdated information.
        
        Document Information:
        - Filename: {document_info.get('filename', 'Unknown')}
        - File Type: {document_info.get('file_type', 'Unknown')}
        - Last Modified: {document_info.get('modified_at', 'Unknown')}
        
        Document Content:
        {content[:10000]}  # Limit content length
        
        Please provide a structured analysis in the following format:
        
        **DOCUMENT_SUMMARY:**
        [Provide a concise summary of the document's main topics and purpose]
        
        **CRITICAL_POINTS:**
        [List specific knowledge points that may expire, each with:
        - Point: [Description]
        - Category: [Technical, Process, Policy, etc.]
        - Urgency: [High/Medium/Low]
        - Last_Updated: [When this info was likely last relevant]]
        
        **EXPIRY_INDICATORS:**
        [List specific indicators that suggest knowledge may be outdated:
        - Date references
        - Technology versions
        - Deprecated practices
        - Obsolete regulations]
        
        **RECOMMENDATIONS:**
        [Specific actions to address potential knowledge expiry]
        
        **CONFIDENCE_SCORE:**
        [Provide a confidence score from 0.0 to 1.0 for your analysis]
        """
    
    def _build_report_prompt(self, documents_data: List[Dict], critical_points: List[Dict]) -> str:
        """Build prompt for report generation"""
        docs_summary = "\n".join([
            f"- {doc.get('filename', 'Unknown')}: {doc.get('summary', 'No summary')[:200]}"
            for doc in documents_data[:20]  # Limit number of docs
        ])
        
        points_summary = "\n".join([
            f"- {point.get('description', 'Unknown')}: Urgency {point.get('urgency', 'Unknown')}"
            for point in critical_points[:50]  # Limit number of points
        ])
        
        return f"""
        Generate a comprehensive knowledge expiry report based on the analyzed documents and critical points.
        
        ANALYZED DOCUMENTS ({len(documents_data)}):
        {docs_summary}
        
        CRITICAL KNOWLEDGE POINTS ({len(critical_points)}):
        {points_summary}
        
        Please provide a structured report in the following format:
        
        **EXECUTIVE_SUMMARY:**
        [High-level overview of knowledge expiry risks and key findings]
        
        **EXPIRED_KNOWLEDGE_COUNT:**
        [Number of items identified as likely expired]
        
        **CRITICAL_FINDINGS:**
        [Top 10 most critical findings with:
        - Finding: [Description]
        - Impact: [Business impact]
        - Recommendation: [Specific action]]
        
        **RECOMMENDATIONS:**
        [Strategic recommendations for knowledge management]
        
        **ACTION_ITEMS:**
        [Specific, actionable items with:
        - Task: [Description]
        - Priority: [High/Medium/Low]
        - Owner: [Suggested role/department]
        - Timeline: [Suggested timeframe]]
        """
    
    def _parse_analysis_result(self, analysis_text: str) -> AnalysisResult:
        """Parse structured analysis result from LLM response"""
        try:
            # Simple parsing - in production, use more robust parsing
            sections = {}
            current_section = None
            
            for line in analysis_text.split('\n'):
                line = line.strip()
                if line.startswith('**') and line.endswith(':**'):
                    current_section = line.strip('*:').upper()
                    sections[current_section] = []
                elif current_section and line:
                    sections[current_section].append(line)
            
            # Extract critical points (simplified)
            critical_points = []
            if 'CRITICAL_POINTS' in sections:
                for point_text in sections['CRITICAL_POINTS']:
                    if point_text.startswith('- Point:'):
                        critical_points.append({
                            'description': point_text.replace('- Point:', '').strip(),
                            'category': 'Unknown',
                            'urgency': 'Medium',
                            'source_document': 'current'
                        })
            
            # Extract confidence score
            confidence_score = 0.5
            if 'CONFIDENCE_SCORE' in sections and sections['CONFIDENCE_SCORE']:
                try:
                    confidence_text = sections['CONFIDENCE_SCORE'][0]
                    # Extract number from text
                    import re
                    match = re.search(r'(\d+\.?\d*)', confidence_text)
                    if match:
                        confidence_score = float(match.group(1))
                        if confidence_score > 1.0:
                            confidence_score = confidence_score / 100  # Convert percentage
                except:
                    confidence_score = 0.5
            
            return AnalysisResult(
                document_summary='\n'.join(sections.get('DOCUMENT_SUMMARY', ['No summary available'])),
                critical_points=critical_points,
                knowledge_expiry_indicators=sections.get('EXPIRY_INDICATORS', []),
                recommendations=sections.get('RECOMMENDATIONS', []),
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Error parsing analysis result: {e}")
            return AnalysisResult(
                document_summary="Parsing failed",
                critical_points=[],
                knowledge_expiry_indicators=[],
                recommendations=[],
                confidence_score=0.0
            )
    
    def _parse_report_result(self, report_text: str) -> ReportResult:
        """Parse structured report result from LLM response"""
        try:
            sections = {}
            current_section = None
            
            for line in report_text.split('\n'):
                line = line.strip()
                if line.startswith('**') and line.endswith(':**'):
                    current_section = line.strip('*:').upper()
                    sections[current_section] = []
                elif current_section and line:
                    sections[current_section].append(line)
            
            # Extract expired knowledge count
            expired_count = 0
            if 'EXPIRED_KNOWLEDGE_COUNT' in sections and sections['EXPIRED_KNOWLEDGE_COUNT']:
                try:
                    import re
                    match = re.search(r'(\d+)', sections['EXPIRED_KNOWLEDGE_COUNT'][0])
                    if match:
                        expired_count = int(match.group(1))
                except:
                    expired_count = 0
            
            # Parse critical findings
            critical_findings = []
            if 'CRITICAL_FINDINGS' in sections:
                current_finding = {}
                for line in sections['CRITICAL_FINDINGS']:
                    if line.startswith('- Finding:'):
                        if current_finding:
                            critical_findings.append(current_finding)
                        current_finding = {'finding': line.replace('- Finding:', '').strip()}
                    elif line.startswith('- Impact:') and current_finding:
                        current_finding['impact'] = line.replace('- Impact:', '').strip()
                    elif line.startswith('- Recommendation:') and current_finding:
                        current_finding['recommendation'] = line.replace('- Recommendation:', '').strip()
                
                if current_finding:
                    critical_findings.append(current_finding)
            
            # Parse action items
            action_items = []
            if 'ACTION_ITEMS' in sections:
                current_item = {}
                for line in sections['ACTION_ITEMS']:
                    if line.startswith('- Task:'):
                        if current_item:
                            action_items.append(current_item)
                        current_item = {'task': line.replace('- Task:', '').strip()}
                    elif line.startswith('- Priority:') and current_item:
                        current_item['priority'] = line.replace('- Priority:', '').strip()
                    elif line.startswith('- Owner:') and current_item:
                        current_item['owner'] = line.replace('- Owner:', '').strip()
                    elif line.startswith('- Timeline:') and current_item:
                        current_item['timeline'] = line.replace('- Timeline:', '').strip()
                
                if current_item:
                    action_items.append(current_item)
            
            return ReportResult(
                executive_summary='\n'.join(sections.get('EXECUTIVE_SUMMARY', ['No summary available'])),
                expired_knowledge_count=expired_count,
                critical_findings=critical_findings,
                recommendations=sections.get('RECOMMENDATIONS', []),
                action_items=action_items
            )
            
        except Exception as e:
            logger.error(f"Error parsing report result: {e}")
            return ReportResult(
                executive_summary="Report parsing failed",
                expired_knowledge_count=0,
                critical_findings=[],
                recommendations=[],
                action_items=[]
            )