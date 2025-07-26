"""Analysis pipeline orchestrator.

This layer glues core scanning/content extraction, AI inference, and database
persistence together.  It intentionally handles *only* control-flow and error
management – heavyweight tasks remain delegated to their respective modules.

ENHANCED: Now uses the FastAgentOrchestrator for maximum performance!
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from sentinel.app.core import FileMetadata, scan_directory, extract_content
from sentinel.app.ai import InferenceEngine, InferenceResult, build_prompt
from sentinel.app.db import DatabaseManager
from sentinel.app.config_manager import AppConfig

# Import the enhanced agentic pipeline
from sentinel.app.agentic_pipeline import run_agentic_analysis


def run_analysis(directory: str | Path, *, db: DatabaseManager, config: AppConfig, logger_manager=None, performance_monitor=None) -> List[dict]:
    """Run full analysis over *directory* using the enhanced agentic system.

    Returns a list of dictionaries suitable for consumption by ReviewDialog.
    Each dict has keys: ``original_path``, ``suggested_path``, ``confidence``,
    and ``justification``.

    ENHANCED: Now uses FastAgentOrchestrator for massive performance improvements!
    - Processes thousands of files per second
    - Parallel agent execution
    - Smart caching and optimizations
    - RTX 3060 Ti optimized batch processing
    """
    
    # Get logger if available
    logger = None
    if logger_manager:
        logger = logger_manager.get_logger('pipeline')
        logger.info(f"🚀 Starting ENHANCED agentic analysis pipeline for directory: {directory}")

    try:
        # Use the enhanced agentic pipeline
        results = run_agentic_analysis(
            directory, 
            db=db, 
            config=config,
            logger_manager=logger_manager,
            performance_monitor=performance_monitor
        )
        
        if logger:
            successful = len([r for r in results if r.get('success', True)])
            logger.info(f"🎉 Enhanced pipeline completed: {successful}/{len(results)} files processed successfully")
        
        return results
        
    except Exception as e:
        if logger:
            logger.error(f"Enhanced pipeline failed, falling back to legacy mode: {e}")
        
        # Fallback to original implementation if agentic pipeline fails
        return _run_legacy_analysis(directory, db=db, config=config, logger_manager=logger_manager, performance_monitor=performance_monitor)


def _run_legacy_analysis(directory: str | Path, *, db: DatabaseManager, config: AppConfig, logger_manager=None, performance_monitor=None) -> List[dict]:
    """Legacy analysis pipeline - fallback implementation."""
    results: list[dict] = []
    
    # Get logger if available
    logger = None
    if logger_manager:
        logger = logger_manager.get_logger('legacy_pipeline')
        logger.warning("Using legacy pipeline as fallback")

    try:
        db.init_schema()

        # Prepare engine according to backend mode
        engine = InferenceEngine(
            backend_mode=config.ai_backend_mode,
            logger_manager=logger_manager,
            performance_monitor=performance_monitor
        )

        file_count = 0
        for meta in scan_directory(directory):  # type: ignore[arg-type]
            file_count += 1
                
            # Persist metadata first
            file_id = db.save_scan_result(meta.as_dict())

            try:
                content = extract_content(meta.path)
                prompt = build_prompt(meta.as_dict(), content)
                inference: InferenceResult = engine.analyze(meta.as_dict(), content)  # type: ignore[arg-type]
                    
            except NotImplementedError:
                # Placeholder inference – suggest same path
                inference = InferenceResult(
                    suggested_path=str(meta.path),
                    confidence=0.5,
                    justification="Backend not implemented",
                )
                    
            except Exception as e:
                # Handle other errors gracefully
                inference = InferenceResult(
                    suggested_path=str(meta.path),
                    confidence=0.0,
                    justification=f"Analysis failed: {str(e)}",
                )
                    
            db.save_inference(file_id, inference.as_dict())

            results.append(
                {
                    "file_id": file_id,
                    "original_path": str(meta.path),
                    "suggested_path": inference.suggested_path,
                    "confidence": inference.confidence,
                    "justification": inference.justification,
                }
            )
            
    except NotImplementedError:
        # If the very first call fails, fallback to stub scan
        from pathlib import Path as _P

        for path in list(_P(directory).rglob("*"))[:100]:
            results.append(
                {
                    "file_id": -1,
                    "original_path": str(path),
                    "suggested_path": str(path),
                    "confidence": 0.1,
                    "justification": "Stub – full pipeline not ready",
                }
            )
            
    return results 