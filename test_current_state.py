#!/usr/bin/env python3
"""
Quick test to check current state of Sentinel 2.0
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add sentinel to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test if all imports work correctly."""
    print("🧪 Testing imports...")
    
    try:
        from sentinel.app.pipeline import run_analysis
        print("   ✅ pipeline.run_analysis imported successfully")
    except Exception as e:
        print(f"   ❌ pipeline.run_analysis import failed: {e}")
        return False
    
    try:
        from sentinel.app.agentic_pipeline import run_agentic_analysis, AgenticPipeline
        print("   ✅ agentic_pipeline imports successful")
    except Exception as e:
        print(f"   ❌ agentic_pipeline import failed: {e}")
        return False
    
    try:
        from sentinel.agents.fast_orchestrator import FastAgentOrchestrator
        print("   ✅ FastAgentOrchestrator imported successfully")
    except Exception as e:
        print(f"   ❌ FastAgentOrchestrator import failed: {e}")
        return False
    
    try:
        from sentinel.app.db import DatabaseManager
        from sentinel.app.config_manager import AppConfig
        print("   ✅ Database and Config imports successful")
    except Exception as e:
        print(f"   ❌ Database/Config import failed: {e}")
        return False
    
    return True


def test_basic_functionality():
    """Test basic functionality with minimal setup."""
    print("\n🔧 Testing basic functionality...")
    
    try:
        # Create test directory
        test_dir = Path(tempfile.mkdtemp(prefix="sentinel_test_"))
        (test_dir / "test.txt").write_text("Test file content")
        (test_dir / "script.py").write_text("print('hello')")
        
        print(f"   📁 Created test directory: {test_dir}")
        
        # Import required modules
        from sentinel.app.pipeline import run_analysis
        from sentinel.app.db import DatabaseManager
        from sentinel.app.config_manager import AppConfig
        
        # Setup
        db = DatabaseManager(":memory:")
        config = AppConfig()
        config.ai_backend_mode = "mock"
        
        print("   🚀 Running analysis...")
        
        # Run analysis
        results = run_analysis(test_dir, db=db, config=config)
        
        print(f"   📊 Results: {len(results)} files processed")
        
        if results:
            sample = results[0]
            print(f"   📋 Sample result keys: {list(sample.keys())}")
            print("   ✅ Basic functionality test passed")
        else:
            print("   ⚠️  No results returned")
        
        # Cleanup
        shutil.rmtree(test_dir)
        return True
        
    except Exception as e:
        print(f"   ❌ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agentic_pipeline_direct():
    """Test the agentic pipeline directly."""
    print("\n🤖 Testing agentic pipeline directly...")
    
    try:
        # Create test directory
        test_dir = Path(tempfile.mkdtemp(prefix="sentinel_agentic_test_"))
        (test_dir / "test.txt").write_text("Test file content")
        (test_dir / "script.py").write_text("print('hello')")
        
        # Import and setup
        from sentinel.app.agentic_pipeline import run_agentic_analysis
        from sentinel.app.db import DatabaseManager
        from sentinel.app.config_manager import AppConfig
        
        db = DatabaseManager(":memory:")
        config = AppConfig()
        config.ai_backend_mode = "mock"
        
        print("   🚀 Running agentic analysis...")
        
        # Run agentic analysis
        results = run_agentic_analysis(test_dir, db=db, config=config)
        
        print(f"   📊 Agentic results: {len(results)} files processed")
        
        if results:
            sample = results[0]
            print(f"   📋 Sample result keys: {list(sample.keys())}")
            print("   ✅ Agentic pipeline test passed")
        else:
            print("   ⚠️  No results from agentic pipeline")
        
        # Cleanup
        shutil.rmtree(test_dir)
        return True
        
    except Exception as e:
        print(f"   ❌ Agentic pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests to check current state."""
    print("🎯 Sentinel 2.0 - Current State Check")
    print("=" * 50)
    
    # Test imports
    imports_ok = test_imports()
    
    if not imports_ok:
        print("\n❌ Import tests failed - cannot proceed with functionality tests")
        return
    
    # Test basic functionality
    basic_ok = test_basic_functionality()
    
    # Test agentic pipeline
    agentic_ok = test_agentic_pipeline_direct()
    
    print("\n" + "=" * 50)
    print("🏁 Current State Check Results:")
    print(f"   Imports: {'✅' if imports_ok else '❌'}")
    print(f"   Basic functionality: {'✅' if basic_ok else '❌'}")
    print(f"   Agentic pipeline: {'✅' if agentic_ok else '❌'}")
    
    if imports_ok and basic_ok and agentic_ok:
        print("\n🎉 All tests passed! System appears to be working correctly.")
    else:
        print("\n⚠️  Some tests failed. Issues need to be addressed.")


if __name__ == "__main__":
    main()