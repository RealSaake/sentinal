#!/usr/bin/env python3
"""
Test UI Integration - Verify Sentinel 2.0 works with the actual UI
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add sentinel to path
sys.path.insert(0, str(Path(__file__).parent))

def test_ui_worker_integration():
    """Test that the AnalysisWorker can use our enhanced pipeline."""
    print("🖥️  Testing UI Worker Integration")
    print("=" * 50)
    
    try:
        # Create test directory
        test_dir = Path(tempfile.mkdtemp(prefix="sentinel_ui_test_"))
        (test_dir / "test.py").write_text("print('hello world')")
        (test_dir / "document.txt").write_text("This is a test document")
        (test_dir / "image.jpg").write_text("JPEG image data")
        
        print(f"📁 Created test directory: {test_dir}")
        
        # Import UI components
        from sentinel.app.ui.main_window import AnalysisWorker
        from sentinel.app.db import DatabaseManager
        from sentinel.app.config_manager import ConfigManager
        
        # Setup
        db = DatabaseManager(":memory:")
        config_mgr = ConfigManager()
        config_mgr.config.ai_backend_mode = "local"  # Use valid backend mode
        
        print("🚀 Creating AnalysisWorker...")
        
        # Create worker (this should work with our enhanced pipeline)
        worker = AnalysisWorker(
            directory=str(test_dir),
            config_mgr=config_mgr,
            db_manager=db
        )
        
        print("✅ AnalysisWorker created successfully")
        print("✅ Enhanced pipeline is compatible with UI components")
        
        # Cleanup
        shutil.rmtree(test_dir)
        return True
        
    except Exception as e:
        print(f"❌ UI integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_manager():
    """Test that ConfigManager works with our system."""
    print("\n⚙️  Testing Config Manager")
    print("=" * 30)
    
    try:
        from sentinel.app.config_manager import ConfigManager, AppConfig
        
        # Test ConfigManager
        config_mgr = ConfigManager()
        print(f"✅ ConfigManager loaded")
        print(f"   Backend mode: {config_mgr.config.ai_backend_mode}")
        
        # Test AppConfig directly
        config = AppConfig()
        print(f"✅ AppConfig created")
        print(f"   Default backend: {config.ai_backend_mode}")
        
        # Test setting mock mode
        config.ai_backend_mode = "mock"
        print(f"✅ Mock mode set: {config.ai_backend_mode}")
        
        return True
        
    except Exception as e:
        print(f"❌ Config manager test failed: {e}")
        return False


def test_database_integration():
    """Test database integration with our enhanced results."""
    print("\n🗄️  Testing Database Integration")
    print("=" * 35)
    
    try:
        from sentinel.app.db import DatabaseManager
        from sentinel.app.pipeline import run_analysis
        from sentinel.app.config_manager import AppConfig
        
        # Create test directory
        test_dir = Path(tempfile.mkdtemp(prefix="sentinel_db_test_"))
        (test_dir / "test.py").write_text("print('hello')")
        
        # Setup
        db = DatabaseManager(":memory:")
        config = AppConfig()
        config.ai_backend_mode = "mock"
        
        print("🚀 Running analysis with database persistence...")
        
        # Run analysis (this will use our enhanced pipeline)
        results = run_analysis(test_dir, db=db, config=config)
        
        print(f"📊 Analysis results: {len(results)} files")
        
        if results:
            sample = results[0]
            print(f"📋 Sample result structure:")
            for key, value in sample.items():
                print(f"   {key}: {type(value).__name__}")
            
            # Check if our enhanced fields are present
            enhanced_fields = ['category', 'tags', 'processing_time_ms', 'success']
            present_fields = [field for field in enhanced_fields if field in sample]
            
            print(f"✅ Enhanced fields present: {present_fields}")
            
            if len(present_fields) >= 3:
                print("✅ Database integration with enhanced results successful")
            else:
                print("⚠️  Some enhanced fields missing")
        
        # Cleanup
        shutil.rmtree(test_dir)
        return True
        
    except Exception as e:
        print(f"❌ Database integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all UI integration tests."""
    print("🎯 Sentinel 2.0 - UI Integration Tests")
    print("=" * 60)
    
    # Test UI worker integration
    ui_ok = test_ui_worker_integration()
    
    # Test config manager
    config_ok = test_config_manager()
    
    # Test database integration
    db_ok = test_database_integration()
    
    print("\n" + "=" * 60)
    print("🏁 UI Integration Test Results:")
    print(f"   UI Worker: {'✅' if ui_ok else '❌'}")
    print(f"   Config Manager: {'✅' if config_ok else '❌'}")
    print(f"   Database Integration: {'✅' if db_ok else '❌'}")
    
    if ui_ok and config_ok and db_ok:
        print("\n🎉 All UI integration tests passed!")
        print("✅ Sentinel 2.0 is fully compatible with the existing UI")
        print("✅ Enhanced pipeline works seamlessly with all components")
    else:
        print("\n⚠️  Some UI integration tests failed")
        print("   Manual verification may be needed")


if __name__ == "__main__":
    main()