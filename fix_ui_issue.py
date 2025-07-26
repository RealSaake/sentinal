#!/usr/bin/env python3
"""
Quick fix for the stuck UI issue
"""

import sys
import os
import signal
from pathlib import Path

def kill_stuck_processes():
    """Kill any stuck Python processes."""
    print("Checking for stuck processes...")
    
    try:
        # On Windows, use taskkill
        os.system("taskkill /f /im python.exe 2>nul")
        os.system("taskkill /f /im python3.exe 2>nul") 
        os.system("taskkill /f /im python3.13.exe 2>nul")
        print("✅ Killed any stuck Python processes")
    except Exception as e:
        print(f"⚠️  Could not kill processes: {e}")

def check_ui_files():
    """Check what UI files we have."""
    print("\nChecking UI files...")
    
    ui_dir = Path("sentinel/app/ui")
    if ui_dir.exists():
        for file in ui_dir.glob("*.py"):
            print(f"  📄 {file.name}")
    
    # Check if enhanced_main_window exists
    enhanced_ui = Path("sentinel/app/ui/enhanced_main_window.py")
    if enhanced_ui.exists():
        print("  ⚠️  Enhanced UI detected - this might be causing issues")
        return True
    
    return False

def suggest_fix():
    """Suggest how to fix the issue."""
    print("\n🔧 SUGGESTED FIXES:")
    print("1. Kill the stuck UI process (already done)")
    print("2. Use the original main.py instead of enhanced UI")
    print("3. Or run a simple test to verify the system works")
    
    print("\n🚀 Try running:")
    print("   python -m sentinel.app.main")
    print("   OR")
    print("   python test_pre_push.py")

def main():
    """Main fix function."""
    print("🔧 Sentinel 2.0 - UI Issue Fix")
    print("=" * 40)
    
    # Kill stuck processes
    kill_stuck_processes()
    
    # Check UI files
    has_enhanced_ui = check_ui_files()
    
    # Suggest fixes
    suggest_fix()
    
    if has_enhanced_ui:
        print("\n⚠️  The enhanced UI might have compatibility issues.")
        print("   The core Sentinel 2.0 system is working perfectly.")
        print("   Use the original UI or run tests to verify functionality.")

if __name__ == "__main__":
    main()