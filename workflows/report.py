"""
Report Workflow - Generate comprehensive knowledge expiry reports
Combines data from vector DB and relational DB to create actionable reports
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime, timedelta

from src.services.ai_client import AIClient, ReportResult
from src.services.vector_db import QdrantService
from src.services.relational_db import DatabaseService
from src.services.report_export import ReportExporter
from src.core.config import settings

class ReportWorkflow:
    """Main workflow for generating knowledge expiry reports"""
    
    def __init__(self):
        self.ai_client = AIClient()
        self.vector_db = QdrantService()
        self.relational_db = DatabaseService()
        self.report_exporter = ReportExporter()
        
    async def run(
        self,
        output_file: str,
        output_format: str = "excel",
        report_type: str = "comprehensive",
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run the complete report generation workflow
        
        Args:
            output_file: Path for output file
            output_format: Format for output (excel, json, csv)
            report_type: Type of report (executive, detailed, comprehensive)
            filter_criteria: Optional filters for data selection
            
        Returns:
            Report generation results
        """
        logger.info(f"Starting report workflow - Type: {report_type}, Format: {output_format}")
        start_time = datetime.utcnow()
        
        # Create report record
        report_id = await self.relational_db.create_report_record(
            title=f"Knowledge Expiry Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            report_type=report_type,
            output_format=output_format,
            documents_included=0,  # Will update later
            generated_by_model=settings.default_ai_model
        )
        
        results = {
            "report_id": report_id,
            "output_file": output_file,
            "documents_analyzed": 0,
            "expired_knowledge": 0,
            "critical_findings": 0,
            "recommendations": 0,
            "status": "generating",
            "errors": []
        }
        
        try:
            # Step 1: Gather data from databases
            logger.info("Gathering data from databases...")
            data = await self._gather_report_data(filter_criteria)
            
            if not data["documents"] and not data["critical_points"]:
                logger.warning("No data found for report generation")
                results["status"] = "no_data"
                return results
            
            results["documents_analyzed"] = len(data["documents"])
            
            # Step 2: Generate AI-powered report content
            logger.info("Generating AI report content...")
            ai_report = await self.ai_client.generate_report(
                documents_data=data["documents"],
                critical_points=data["critical_points"]
            )
            
            # Step 3: Prepare comprehensive report data
            report_data = await self._prepare_report_data(data, ai_report, report_type)
            
            # Update results with AI findings
            results["expired_knowledge"] = ai_report.expired_knowledge_count
            results["critical_findings"] = len(ai_report.critical_findings)
            results["recommendations"] = len(ai_report.recommendations)
            
            # Step 4: Export report
            logger.info(f"Exporting report to {output_format} format...")
            export_success = await self._export_report(
                report_data=report_data,
                output_file=output_file,
                output_format=output_format,
                report_type=report_type
            )
            
            if not export_success:
                results["status"] = "export_failed"
                results["errors"].append("Failed to export report")
                return results
            
            # Step 5: Update report record
            await self.relational_db.update_report_record(
                report_id=report_id,
                expired_knowledge_count=results["expired_knowledge"],
                critical_findings_count=results["critical_findings"],
                recommendations_count=results["recommendations"],
                output_path=output_file,
                status="completed"
            )
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            results["status"] = "completed"
            results["duration_seconds"] = duration
            
            logger.info(f"Report workflow completed in {duration:.2f} seconds")
            logger.info(f"Generated report: {output_file}")
            
            return results
            
        except Exception as e:
            logger.error(f"Report workflow failed: {e}")
            results["status"] = "error"
            results["errors"].append(f"Workflow error: {str(e)}")
            
            # Update report record with error status
            await self.relational_db.update_report_record(
                report_id=report_id,
                expired_knowledge_count=0,
                critical_findings_count=0,
                recommendations_count=0,
                status="error"
            )
            
            return results
    
    async def _gather_report_data(self, filter_criteria: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Gather all necessary data for report generation"""
        
        # Get all documents from Qdrant
        documents = await self.vector_db.get_all_documents(limit=1000)
        
        # Get critical points from MySQL
        if filter_criteria and filter_criteria.get("urgency"):
            from src.schemas.database import UrgencyLevel
            urgency = UrgencyLevel(filter_criteria["urgency"])
            critical_points = await self.relational_db.get_critical_points_by_urgency(urgency)
        else:
            # Get all critical points - this would require a new method
            critical_points = await self._get_all_critical_points()
        
        # Get database statistics
        doc_summary = await self.relational_db.get_documents_summary()
        cp_summary = await self.relational_db.get_critical_points_summary()
        
        # Get collection statistics
        qdrant_stats = await self.vector_db.get_collection_stats()
        
        return {
            "documents": documents,
            "critical_points": critical_points,
            "document_summary": doc_summary,
            "critical_points_summary": cp_summary,
            "vector_db_stats": qdrant_stats,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def _get_all_critical_points(self) -> List[Dict[str, Any]]:
        """Get all critical points with document information"""
        try:
            with self.relational_db.get_session() as session:
                from src.schemas.database import CriticalPoint, Document
                
                points = session.query(CriticalPoint).join(Document).all()
                
                return [
                    {
                        "id": point.id,
                        "description": point.description,
                        "category": point.category.value,
                        "urgency": point.urgency.value,
                        "last_updated_date": point.last_updated_date,
                        "confidence_score": point.confidence_score,
                        "document_filename": point.document.filename,
                        "document_path": point.document.file_path,
                        "context_snippet": point.context_snippet,
                        "expiry_indicators": point.expiry_indicators
                    }
                    for point in points
                ]
        except Exception as e:
            logger.error(f"Error getting all critical points: {e}")
            return []
    
    async def _prepare_report_data(
        self,
        raw_data: Dict[str, Any],
        ai_report: ReportResult,
        report_type: str
    ) -> Dict[str, Any]:
        """Prepare structured data for report export"""
        
        # Categorize critical points by urgency and category
        critical_points_by_urgency = {"high": [], "medium": [], "low": [], "critical": []}
        critical_points_by_category = {}
        
        for point in raw_data["critical_points"]:
            urgency = point.get("urgency", "medium")
            category = point.get("category", "technical")
            
            if urgency in critical_points_by_urgency:
                critical_points_by_urgency[urgency].append(point)
            
            if category not in critical_points_by_category:
                critical_points_by_category[category] = []
            critical_points_by_category[category].append(point)
        
        # Analyze expiry indicators
        expiry_analysis = self._analyze_expiry_indicators(raw_data["critical_points"])
        
        # Prepare document analysis
        document_analysis = self._analyze_documents(raw_data["documents"])
        
        # Create timeline analysis
        timeline_analysis = self._create_timeline_analysis(raw_data["critical_points"])
        
        report_data = {
            "metadata": {
                "report_type": report_type,
                "generated_at": raw_data["generated_at"],
                "total_documents": len(raw_data["documents"]),
                "total_critical_points": len(raw_data["critical_points"]),
                "analysis_model": settings.default_ai_model
            },
            "executive_summary": {
                "overview": ai_report.executive_summary,
                "key_metrics": {
                    "documents_analyzed": len(raw_data["documents"]),
                    "critical_points_identified": len(raw_data["critical_points"]),
                    "expired_knowledge_items": ai_report.expired_knowledge_count,
                    "high_priority_items": len(critical_points_by_urgency.get("high", [])) + len(critical_points_by_urgency.get("critical", [])),
                    "average_confidence": sum(doc.get("analysis_result", {}).get("confidence_score", 0) for doc in raw_data["documents"]) / max(len(raw_data["documents"]), 1)
                }
            },
            "critical_findings": ai_report.critical_findings,
            "critical_points": {
                "by_urgency": critical_points_by_urgency,
                "by_category": critical_points_by_category,
                "detailed_list": raw_data["critical_points"]
            },
            "document_analysis": document_analysis,
            "expiry_analysis": expiry_analysis,
            "timeline_analysis": timeline_analysis,
            "recommendations": {
                "strategic": ai_report.recommendations,
                "action_items": ai_report.action_items
            },
            "appendix": {
                "database_statistics": raw_data["document_summary"],
                "vector_db_statistics": raw_data["vector_db_stats"]
            }
        }
        
        return report_data
    
    def _analyze_expiry_indicators(self, critical_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze expiry indicators across all critical points"""
        indicator_counts = {}
        total_with_indicators = 0
        
        for point in critical_points:
            indicators = point.get("expiry_indicators", [])
            if indicators:
                total_with_indicators += 1
                for indicator in indicators:
                    indicator_counts[indicator] = indicator_counts.get(indicator, 0) + 1
        
        return {
            "total_points_with_indicators": total_with_indicators,
            "most_common_indicators": sorted(indicator_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "indicator_distribution": indicator_counts
        }
    
    def _analyze_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze document patterns and statistics"""
        file_type_counts = {}
        confidence_scores = []
        documents_by_age = {"recent": 0, "moderate": 0, "old": 0}
        
        now = datetime.utcnow()
        
        for doc in documents:
            # File type analysis
            filename = doc.get("filename", "")
            if "." in filename:
                ext = filename.split(".")[-1].lower()
                file_type_counts[ext] = file_type_counts.get(ext, 0) + 1
            
            # Confidence score analysis
            analysis_result = doc.get("analysis_result", {})
            if analysis_result.get("confidence_score"):
                confidence_scores.append(analysis_result["confidence_score"])
            
            # Age analysis (based on created_at in metadata or filename patterns)
            created_at = doc.get("created_at")
            if created_at:
                try:
                    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    days_old = (now - created_date).days
                    
                    if days_old < 30:
                        documents_by_age["recent"] += 1
                    elif days_old < 180:
                        documents_by_age["moderate"] += 1
                    else:
                        documents_by_age["old"] += 1
                except:
                    documents_by_age["moderate"] += 1
        
        avg_confidence = sum(confidence_scores) / max(len(confidence_scores), 1)
        
        return {
            "file_type_distribution": file_type_counts,
            "average_confidence_score": avg_confidence,
            "confidence_distribution": {
                "high (>0.8)": len([s for s in confidence_scores if s > 0.8]),
                "medium (0.5-0.8)": len([s for s in confidence_scores if 0.5 <= s <= 0.8]),
                "low (<0.5)": len([s for s in confidence_scores if s < 0.5])
            },
            "document_age_distribution": documents_by_age
        }
    
    def _create_timeline_analysis(self, critical_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create timeline analysis for knowledge expiry"""
        timeline = {
            "immediate_attention": [],
            "next_30_days": [],
            "next_90_days": [],
            "next_6_months": [],
            "annual_review": []
        }
        
        now = datetime.utcnow()
        
        for point in critical_points:
            urgency = point.get("urgency", "medium")
            last_updated = point.get("last_updated_date")
            
            # Categorize based on urgency and age
            if urgency == "critical":
                timeline["immediate_attention"].append(point)
            elif urgency == "high":
                timeline["next_30_days"].append(point)
            elif urgency == "medium":
                timeline["next_90_days"].append(point)
            else:
                # Check if it's been a long time since update
                if last_updated:
                    try:
                        last_update_date = datetime.fromisoformat(last_updated) if isinstance(last_updated, str) else last_updated
                        days_since_update = (now - last_update_date).days
                        
                        if days_since_update > 365:
                            timeline["next_6_months"].append(point)
                        else:
                            timeline["annual_review"].append(point)
                    except:
                        timeline["annual_review"].append(point)
                else:
                    timeline["annual_review"].append(point)
        
        return {
            "timeline_categories": {k: len(v) for k, v in timeline.items()},
            "detailed_timeline": timeline
        }
    
    async def _export_report(
        self,
        report_data: Dict[str, Any],
        output_file: str,
        output_format: str,
        report_type: str
    ) -> bool:
        """Export report in specified format"""
        try:
            if output_format.lower() == "excel":
                return await self.report_exporter.export_to_excel(
                    report_data=report_data,
                    output_file=output_file,
                    report_type=report_type
                )
            elif output_format.lower() == "json":
                return await self.report_exporter.export_to_json(
                    report_data=report_data,
                    output_file=output_file
                )
            elif output_format.lower() == "csv":
                return await self.report_exporter.export_to_csv(
                    report_data=report_data,
                    output_file=output_file
                )
            else:
                logger.error(f"Unsupported output format: {output_format}")
                return False
                
        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            return False

def run_report_workflow(
    output_file: str,
    output_format: str = "excel"
) -> Dict[str, Any]:
    """
    Synchronous wrapper for the report workflow
    
    Args:
        output_file: Path for output file
        output_format: Format for output (excel, json, csv)
        
    Returns:
        Report generation results
    """
    workflow = ReportWorkflow()
    
    # Run the async workflow
    return asyncio.run(workflow.run(output_file, output_format))