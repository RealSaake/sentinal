#!/usr/bin/env python3
"""
Debug the agent JSON parsing issues
"""

import sys
import asyncio
from pathlib import Path

# Add sentinel to path
sys.path.insert(0, str(Path(__file__).parent))

from sentinel.agents import CategorizationAgent, TaggingAgent, NamingAgent, ConfidenceAgent, extract_file_context


class DebugInferenceEngine:
    """Debug inference engine to see what's happening."""
    
    async def generate(self, prompt: str) -> str:
        """Generate response and show what's happening."""
        print(f"\n🔍 PROMPT RECEIVED:")
        print(f"Length: {len(prompt)} characters")
        print(f"Contains 'categorize': {'categorize' in prompt.lower()}")
        print(f"Contains 'tags': {'tags' in prompt.lower()}")
        print(f"Contains 'path': {'path' in prompt.lower()}")
        print(f"Contains 'confidence': {'confidence' in prompt.lower()}")
        
        # Generate response based on more specific content analysis
        if "Categorize this file" in prompt or "determine the high-level category" in prompt:
            response = '{"category": "ARCHIVES", "confidence": 0.94, "reasoning": "Game asset archive file"}'
        elif "Extract relevant tags" in prompt or "Generate 3-7 relevant tags" in prompt:
            response = '{"tags": ["gaming", "forza-horizon", "car-models"], "confidence": 0.85, "reasoning": "Tags extracted based on file analysis"}'
        elif "Generate a structured file path" in prompt or "suggested_path" in prompt:
            response = '{"suggested_path": "archives/game-assets/test.zip", "confidence": 0.87, "reasoning": "Path generated following category conventions"}'
        elif "Evaluate the quality and consistency" in prompt or "final_confidence" in prompt:
            response = '{"final_confidence": 0.84, "agent_breakdown": {"categorization": 0.90, "tagging": 0.82, "naming": 0.85}, "consistency_score": 0.86, "issues": [], "reasoning": "All agents performed well"}'
        else:
            response = '{"result": "unknown", "confidence": 0.5, "reasoning": "Unknown prompt type"}'
        
        print(f"\n📤 RESPONSE GENERATED:")
        print(f"Response: {response}")
        print(f"Length: {len(response)} characters")
        
        return response


async def debug_individual_agents():
    """Debug each agent individually."""
    print("🐛 Debugging Individual Agents")
    print("=" * 50)
    
    # Create debug inference engine
    inference_engine = DebugInferenceEngine()
    
    # Test file
    test_file = "Barnfind_BMW_2002Turbo_73.zip"
    file_context = extract_file_context(test_file) if Path(test_file).exists() else None
    
    if not file_context:
        # Create mock file context
        from sentinel.agents.base_agent import FileContext
        file_context = FileContext(
            file_path=test_file,
            file_name=test_file,
            file_extension=".zip",
            file_size_bytes=1024000,
            directory_path=".",
            directory_name="test"
        )
    
    print(f"📁 Test file: {file_context.file_name}")
    
    # Test Categorization Agent
    print("\n" + "="*60)
    print("1️⃣ Testing Categorization Agent...")
    print("="*60)
    
    try:
        cat_agent = CategorizationAgent(inference_engine)
        cat_result = await cat_agent.process(file_context)
        
        print(f"\n✅ CATEGORIZATION RESULT:")
        print(f"   Success: {cat_result.success}")
        print(f"   Category: {cat_result.raw_output.get('category', 'N/A')}")
        print(f"   Confidence: {cat_result.confidence:.2f}")
        print(f"   Reasoning: {cat_result.reasoning}")
        if not cat_result.success:
            print(f"   Error: {cat_result.error_message}")
    except Exception as e:
        print(f"❌ CATEGORIZATION FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Tagging Agent
    print("\n" + "="*60)
    print("2️⃣ Testing Tagging Agent...")
    print("="*60)
    
    try:
        tag_agent = TaggingAgent(inference_engine)
        tag_result = await tag_agent.process(file_context, category="ARCHIVES")
        
        print(f"\n✅ TAGGING RESULT:")
        print(f"   Success: {tag_result.success}")
        print(f"   Tags: {tag_result.raw_output.get('tags', [])}")
        print(f"   Confidence: {tag_result.confidence:.2f}")
        print(f"   Reasoning: {tag_result.reasoning}")
        if not tag_result.success:
            print(f"   Error: {tag_result.error_message}")
    except Exception as e:
        print(f"❌ TAGGING FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Naming Agent
    print("\n" + "="*60)
    print("3️⃣ Testing Naming Agent...")
    print("="*60)
    
    try:
        naming_agent = NamingAgent(inference_engine)
        naming_result = await naming_agent.process(
            file_context, category="ARCHIVES", tags=["gaming", "forza-horizon"]
        )
        
        print(f"\n✅ NAMING RESULT:")
        print(f"   Success: {naming_result.success}")
        print(f"   Suggested Path: {naming_result.raw_output.get('suggested_path', 'N/A')}")
        print(f"   Confidence: {naming_result.confidence:.2f}")
        print(f"   Reasoning: {naming_result.reasoning}")
        if not naming_result.success:
            print(f"   Error: {naming_result.error_message}")
    except Exception as e:
        print(f"❌ NAMING FAILED: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run debug tests."""
    await debug_individual_agents()


if __name__ == "__main__":
    asyncio.run(main())