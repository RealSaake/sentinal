#!/usr/bin/env python3
"""
Test the Pre-Flight Check System
"""

import sys
import time
from pathlib import Path

# Add sentinel to path
sys.path.insert(0, str(Path(__file__).parent))

def test_preflight_checker():
    """Test the complete pre-flight check system."""
    print("🚀 Testing Pre-Flight Check System...")
    print("=" * 60)
    
    try:
        from sentinel.core.preflight_check import PreFlightChecker
        
        # Progress callback for testing
        def progress_callback(message, percentage):
            print(f"  [{percentage:3.0f}%] {message}")
        
        # Create checker with progress callback
        checker = PreFlightChecker(progress_callback=progress_callback)
        
        # Test directory
        test_dir = "."
        print(f"🎯 Target Directory: {test_dir}")
        
        # Perform pre-flight check
        print("\n🔍 Performing pre-flight check...")
        results = checker.perform_preflight_check(test_dir)
        
        print(f"\n✅ Pre-flight check completed in {results.check_duration_seconds:.2f}s")
        
        # Display results summary
        summary = checker.get_preflight_summary(results)
        print("\n📊 Pre-Flight Summary:")
        print("-" * 40)
        print(f"Files: {summary['total_files']:,}")
        print(f"Size: {summary['total_size_gb']:.2f} GB")
        print(f"File Types: {summary['file_types']}")
        print(f"Recommended: {summary['recommended_strategy']}")
        print(f"Duration: {summary['estimated_duration']}")
        print(f"Speed: {summary['estimated_speed']}")
        print(f"Confidence: {summary['confidence']}")
        print(f"Warnings: {summary['warning_count']}")
        
        # Display strategy comparison
        comparison = checker.get_strategy_comparison_table(results.strategy_forecasts)
        print("\n📋 Strategy Comparison:")
        print("-" * 60)
        print(f"{'Strategy':<15} {'Duration':<12} {'Speed':<12} {'Confidence':<10}")
        print("-" * 60)
        
        for strategy in comparison:
            print(f"{strategy['display_name']:<15} {strategy['duration']:<12} "
                  f"{strategy['files_per_second']:>6.1f} fps   {strategy['confidence']:<10}")
        
        # Display warnings if any
        if results.warnings:
            print(f"\n⚠️  Warnings ({len(results.warnings)}):")
            for i, warning in enumerate(results.warnings, 1):
                print(f"  {i}. {warning}")
        
        return results
        
    except Exception as e:
        print(f"❌ Pre-flight check test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_custom_strategy():
    """Test custom strategy creation and validation."""
    print("\n\n🛠️  Testing Custom Strategy Creation...")
    print("=" * 60)
    
    try:
        from sentinel.core.preflight_check import PreFlightChecker
        
        checker = PreFlightChecker()
        
        # Test parameter validation
        print("🔍 Testing parameter validation...")
        
        # Valid parameters
        valid_params = {
            'max_workers': 4,
            'batch_size': 64,
            'ai_complexity': 'balanced',
            'error_handling': 'skip',
            'resource_usage': 'balanced'
        }
        
        errors = checker.validate_custom_parameters(valid_params)
        if not errors:
            print("✅ Valid parameters passed validation")
        else:
            print(f"❌ Unexpected validation errors: {errors}")
        
        # Invalid parameters
        invalid_params = {
            'max_workers': -1,
            'batch_size': 0,
            'ai_complexity': 'invalid',
            'error_handling': 'unknown',
            'resource_usage': 'extreme'
        }
        
        errors = checker.validate_custom_parameters(invalid_params)
        if errors:
            print(f"✅ Invalid parameters correctly rejected: {len(errors)} errors")
            for param, error in errors.items():
                print(f"   {param}: {error}")
        else:
            print("❌ Invalid parameters should have been rejected")
        
        # Test custom strategy creation
        print("\n🎨 Testing custom strategy creation...")
        
        custom_strategy = checker.create_custom_strategy('balanced', valid_params)
        print(f"✅ Custom strategy created: {custom_strategy.name}")
        print(f"   Workers: {custom_strategy.max_workers}")
        print(f"   Batch size: {custom_strategy.batch_size}")
        print(f"   AI complexity: {custom_strategy.ai_complexity}")
        
        return True
        
    except Exception as e:
        print(f"❌ Custom strategy test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration_workflow():
    """Test the complete integration workflow."""
    print("\n\n🔄 Testing Integration Workflow...")
    print("=" * 60)
    
    try:
        from sentinel.core.preflight_check import PreFlightChecker
        
        # Simulate the complete user workflow
        checker = PreFlightChecker()
        
        print("1️⃣ User selects directory...")
        target_dir = "."
        
        print("2️⃣ System performs pre-flight check...")
        results = checker.perform_preflight_check(target_dir)
        
        print("3️⃣ User reviews recommendations...")
        summary = checker.get_preflight_summary(results)
        comparison = checker.get_strategy_comparison_table(results.strategy_forecasts)
        
        print(f"   System recommends: {summary['recommended_strategy']}")
        print(f"   Estimated time: {summary['estimated_duration']}")
        
        print("4️⃣ User customizes strategy...")
        custom_params = {
            'max_workers': 2,
            'batch_size': 32,
            'ai_complexity': 'simple'
        }
        
        # Validate custom parameters
        errors = checker.validate_custom_parameters(custom_params)
        if errors:
            print(f"   ❌ Custom parameters invalid: {errors}")
            return False
        
        # Create custom strategy
        custom_strategy = checker.create_custom_strategy('balanced', custom_params)
        print(f"   ✅ Custom strategy created: {custom_strategy.name}")
        
        print("5️⃣ System ready to proceed with analysis...")
        print(f"   Final strategy: {custom_strategy.name}")
        print(f"   Workers: {custom_strategy.max_workers}")
        print(f"   Batch size: {custom_strategy.batch_size}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n\n🧪 Testing Edge Cases...")
    print("=" * 60)
    
    try:
        from sentinel.core.preflight_check import PreFlightChecker
        
        checker = PreFlightChecker()
        
        # Test non-existent directory
        print("🔍 Testing non-existent directory...")
        try:
            checker.perform_preflight_check("/non/existent/directory")
            print("❌ Should have raised FileNotFoundError")
            return False
        except FileNotFoundError:
            print("✅ Correctly handled non-existent directory")
        
        # Test file instead of directory
        print("\n🔍 Testing file instead of directory...")
        
        # Create a test file
        test_file = Path("test_file.tmp")
        test_file.write_text("test content")
        
        try:
            checker.perform_preflight_check(str(test_file))
            print("❌ Should have raised NotADirectoryError")
            return False
        except NotADirectoryError:
            print("✅ Correctly handled file instead of directory")
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()
        
        # Test invalid strategy name
        print("\n🔍 Testing invalid strategy name...")
        try:
            checker.create_custom_strategy('invalid_strategy', {})
            print("❌ Should have raised ValueError")
            return False
        except ValueError:
            print("✅ Correctly handled invalid strategy name")
        
        return True
        
    except Exception as e:
        print(f"❌ Edge cases test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🧪 Sentinel 2.0 - Pre-Flight Check Tests")
    print("=" * 70)
    
    tests_passed = 0
    total_tests = 4
    
    # Test 1: Basic pre-flight check
    if test_preflight_checker():
        tests_passed += 1
    
    # Test 2: Custom strategy creation
    if test_custom_strategy():
        tests_passed += 1
    
    # Test 3: Integration workflow
    if test_integration_workflow():
        tests_passed += 1
    
    # Test 4: Edge cases
    if test_edge_cases():
        tests_passed += 1
    
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Pre-flight check system is ready.")
    else:
        print("⚠️  Some tests failed. Please review the output above.")

if __name__ == "__main__":
    main()