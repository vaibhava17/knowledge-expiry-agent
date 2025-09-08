#!/usr/bin/env python3
"""
Knowledge Expiry Agent - CLI Entry Point
Analyzes documents for knowledge expiry and generates reports.
"""

import typer
from pathlib import Path
from loguru import logger
from src.core.config import settings
from workflows.analyze import run_analyze_workflow
from workflows.report import run_report_workflow

app = typer.Typer(help="Knowledge Expiry Agent - Document Analysis and Reporting")

@app.command()
def analyze(
    path: str = typer.Argument(..., help="Path to documents directory"),
    recursive: bool = typer.Option(True, "--recursive", "-r", help="Recursively analyze subdirectories"),
    file_types: str = typer.Option("pdf,docx,txt,md", "--types", "-t", help="Comma-separated file types to analyze")
):
    """Analyze documents for knowledge expiry patterns."""
    logger.info(f"Starting analysis of documents in: {path}")
    
    document_path = Path(path)
    if not document_path.exists():
        typer.echo(f"Error: Path {path} does not exist", err=True)
        raise typer.Exit(1)
    
    file_extensions = [ext.strip() for ext in file_types.split(",")]
    
    try:
        results = run_analyze_workflow(document_path, recursive, file_extensions)
        typer.echo(f"✅ Analysis completed successfully!")
        typer.echo(f"📊 Processed {results['files_processed']} files")
        typer.echo(f"🔍 Found {results['critical_points']} critical knowledge points")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        typer.echo(f"❌ Analysis failed: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def report(
    output: str = typer.Option("knowledge_expiry_report.xlsx", "--output", "-o", help="Output file path"),
    format: str = typer.Option("excel", "--format", "-f", help="Output format (excel, json, csv)")
):
    """Generate knowledge expiry report from analyzed data."""
    logger.info("Starting report generation")
    
    try:
        results = run_report_workflow(output, format)
        typer.echo(f"✅ Report generated successfully!")
        typer.echo(f"📄 Report saved to: {output}")
        typer.echo(f"📈 Included {results['documents_analyzed']} documents")
        typer.echo(f"⚠️ Found {results['expired_knowledge']} potentially expired knowledge items")
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        typer.echo(f"❌ Report generation failed: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def status():
    """Show system status and configuration."""
    typer.echo("🔧 Knowledge Expiry Agent Status")
    typer.echo(f"AI Model: {settings.default_ai_model}")
    typer.echo(f"Qdrant: {settings.qdrant_host}:{settings.qdrant_port}")
    typer.echo(f"MySQL: {settings.mysql_host}:{settings.mysql_port}")
    typer.echo(f"Log Level: {settings.log_level}")

if __name__ == "__main__":
    logger.configure(handlers=[{"sink": "logs/app.log", "level": settings.log_level}])
    app()