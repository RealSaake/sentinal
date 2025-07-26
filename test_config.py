#!/usr/bin/env python3
"""
Test the Helios configuration system
"""

from helios.core.config import load_config
from pathlib import Path

def test_config():
    """Test configuration loading and validation."""
    print("🧪 Testing Helios Configuration System...")
    
    # Load configuration
    config = load_config("helios/config/helios_config.yaml")
    
    # Print summary
    print("\n📋 Configuration Summary:")
    summary = config.get_summary()
    for section, details in summary.items():
        print(f"\n{section.upper()}:")
        for key, value in details.items():
            print(f"  {key}: {value}")
    
    # Validate configuration
    print("\n🔍 Validating Configuration...")
    issues = config.validate_config()
    
    if issues:
        print("❌ Configuration Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ Configuration is valid!")
    
    # Test skip rules
    print(f"\n📝 Skip Rules: {len(config.get_skip_rules())} rules loaded")
    for i, rule in enumerate(config.get_skip_rules()[:3]):  # Show first 3
        print(f"  {i+1}. {rule.reason}")
        if rule.pattern:
            print(f"     Pattern: {rule.pattern}")
        if rule.path_contains:
            print(f"     Path contains: {rule.path_contains}")
    
    # Test category rules
    print(f"\n📂 Category Rules: {len(config.get_category_rules())} categories loaded")
    for name, rule in list(config.get_category_rules().items())[:3]:  # Show first 3
        print(f"  {name}: {rule.base_path}")
        print(f"    Extensions: {rule.extensions[:5]}...")  # Show first 5 extensions
    
    print("\n🎉 Configuration test completed!")

if __name__ == "__main__":
    test_config()