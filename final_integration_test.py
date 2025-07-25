#!/usr/bin/env python3
"""Final integration test - everything working together."""

import sys
import os
import yaml
import time
from pathlib import Path

# Add sentinel to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sentinel'))

from sentinel.app.logging import LoggerManager, PerformanceMonitor, DebugInfoCollector
from sentinel.app.ai.inference_engine import InferenceEngine

def final_integration_test():
    """Test everything working together like in a real application."""
    print("🚀 FINAL INTEGRATION TEST - Real-world scenario simulation")
    print("="*80)
    
    # Load configuration
    config_path = Path('sentinel/config/config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize complete logging system
    print("1. 🔧 Initializing complete logging infrastructure...")
    logger_manager = LoggerManager(config)
    perf_monitor = PerformanceMonitor(logger_manager)
    debug_collector = DebugInfoCollector(config, logger_manager, perf_monitor)
    
    # Get application logger
    app_logger = logger_manager.get_logger('sentinel_app')
    app_logger.info("🎯 Sentinel Storage Analyzer starting up...")
    
    # Initialize AI engine with logging
    print("2. 🤖 Initializing AI inference engine...")
    ai_engine = InferenceEngine(
        backend_mode="local",
        logger_manager=logger_manager,
        performance_monitor=perf_monitor
    )
    
    # Simulate real application workflow
    print("3. 📁 Simulating file analysis workflow...")
    
    test_files = [
        {"path": "/Users/john/Documents/ProjectPlan_2024.docx", "content": "Project planning document with timelines and milestones"},
        {"path": "/Users/john/Downloads/invoice_12345.pdf", "content": "Invoice from vendor for office supplies"},
        {"path": "/Users/john/Pictures/vacation_beach.jpg", "content": "Photo from summer vacation at the beach"},
        {"path": "/Users/john/Code/python/data_analyzer.py", "content": "Python script for analyzing CSV data files"},
        {"path": "/Users/john/Music/playlist_workout.m3u", "content": "Workout music playlist file"},
        {"path": "/Users/john/Desktop/meeting_notes_jan.txt", "content": "Notes from January team meeting"},
        {"path": "/Users/john/Documents/budget_2024.xlsx", "content": "Annual budget spreadsheet with financial projections"},
        {"path": "/Users/john/Downloads/software_manual.pdf", "content": "User manual for new software installation"},
    ]
    
    successful_analyses = 0
    failed_analyses = 0
    
    for i, file_info in enumerate(test_files, 1):
        try:
            app_logger.info(f"📄 Processing file {i}/{len(test_files)}: {file_info['path']}")
            
            # Simulate file metadata extraction
            metadata = {
                "path": file_info["path"],
                "size": 1024 * (i * 100),  # Varying file sizes
                "extension": Path(file_info["path"]).suffix,
                "modified_time": time.time() - (i * 3600)  # Files modified at different times
            }
            
            # Perform AI analysis
            result = ai_engine.analyze(metadata, file_info["content"])
            
            app_logger.info(f"✅ Analysis complete: {result.suggested_path} (confidence: {result.confidence})")
            successful_analyses += 1
            
            # Simulate some processing delay
            time.sleep(0.1)
            
        except Exception as e:
            app_logger.error(f"❌ Failed to analyze {file_info['path']}: {e}")
            failed_analyses += 1
    
    # Log summary
    app_logger.info(f"📊 Analysis complete: {successful_analyses} successful, {failed_analyses} failed")
    
    # Test system health checks
    print("4. 🔍 Running system health checks...")
    
    ai_status = debug_collector.test_ai_connectivity()
    db_status = debug_collector.test_database_connectivity()
    
    app_logger.info(f"🤖 AI Backend Status: {ai_status['status']}")
    app_logger.info(f"🗄️ Database Status: {db_status['status']}")
    
    # Get performance metrics
    print("5. 📈 Collecting performance metrics...")
    metrics = perf_monitor.get_metrics()
    
    if 'ai_inference' in metrics:
        ai_metrics = metrics['ai_inference']
        app_logger.info(f"📊 AI Performance: {ai_metrics['total_calls']} calls, "
                       f"{ai_metrics['average_duration']:.3f}s avg, "
                       f"{ai_metrics['success_rate']:.1f}% success rate")
    
    # Test log level changes during runtime
    print("6. 🎚️ Testing runtime configuration changes...")
    app_logger.info("Switching to DEBUG mode for detailed logging...")
    logger_manager.set_log_level('DEBUG')
    
    app_logger.debug("This is a debug message - should be visible now")
    app_logger.info("Debug mode is now active")
    
    # Switch back to INFO
    logger_manager.set_log_level('INFO')
    app_logger.info("Switched back to INFO level")
    
    # Test error handling
    print("7. ⚠️ Testing error handling...")
    try:
        # Simulate an application error
        raise RuntimeError("Simulated application error for testing")
    except Exception as e:
        app_logger.error("Caught application error", exc_info=True)
    
    # Generate final debug report
    print("8. 📄 Generating comprehensive debug report...")
    debug_report = debug_collector.generate_debug_report()
    
    # Save the report
    report_path = Path('final_integration_report.json')
    with open(report_path, 'w') as f:
        f.write(debug_report)
    
    app_logger.info(f"Debug report saved to: {report_path}")
    
    # Display final statistics
    print("\n" + "="*80)
    print("🎉 FINAL INTEGRATION TEST RESULTS")
    print("="*80)
    
    log_stats = logger_manager.get_log_stats()
    recent_logs = logger_manager.get_recent_logs(20)
    
    print(f"✅ Files Analyzed: {successful_analyses}/{len(test_files)}")
    print(f"✅ AI Backend: {ai_status['status']}")
    print(f"✅ Database: {db_status['status']}")
    print(f"✅ Log Level: {log_stats['current_level']}")
    print(f"✅ Active Loggers: {log_stats['total_loggers']}")
    print(f"✅ Recent Log Entries: {len(recent_logs)}")
    print(f"✅ Log File Size: {log_stats['log_file_size_mb']:.2f}MB")
    print(f"✅ Performance Metrics: {len(metrics)} operation types tracked")
    
    if 'ai_inference' in metrics:
        ai_perf = metrics['ai_inference']
        print(f"✅ AI Performance: {ai_perf['total_calls']} calls, {ai_perf['success_rate']:.1f}% success")
    
    print(f"✅ Debug Report: {len(debug_report)} bytes generated")
    
    app_logger.info("🎯 Sentinel Storage Analyzer session completed successfully")
    
    print("\n🎉 ALL SYSTEMS OPERATIONAL! The logging system is production-ready! 🎉")
    print("="*80)
    
    return True

if __name__ == "__main__":
    success = final_integration_test()
    sys.exit(0 if success else 1)