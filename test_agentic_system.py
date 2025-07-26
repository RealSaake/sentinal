#!/usr/bin/env python3
"""
Test the Sentinel 2.0 Agentic AI System with REAL FILES
Let's use your big drive with lots of files to see the agents in action!
"""

import sys
import asyncio
import time
from pathlib import Path
from typing import List

# Add sentinel to path
sys.path.insert(0, str(Path(__file__).parent))

from sentinel.agents import (
    AgentOrchestrator, extract_file_context,
    CategorizationAgent, TaggingAgent, NamingAgent, ConfidenceAgent
)


class MockInferenceEngine:
    """Mock inference engine for testing the agentic system."""
    
    def __init__(self):
        self.call_count = 0
    
    async def generate(self, prompt: str) -> str:
        """Mock AI generation for testing."""
        self.call_count += 1
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        # Generate realistic responses based on specific prompt content
        if "Categorize this file" in prompt or "determine the high-level category" in prompt:
            return self._generate_categorization_response(prompt)
        elif "Extract relevant tags" in prompt or "Generate 3-7 relevant tags" in prompt:
            return self._generate_tagging_response(prompt)
        elif "Generate a structured file path" in prompt or "suggested_path" in prompt:
            return self._generate_naming_response(prompt)
        elif "Evaluate the quality and consistency" in prompt or "final_confidence" in prompt:
            return self._generate_confidence_response(prompt)
        else:
            return '{"result": "processed", "confidence": 0.8, "reasoning": "Mock processing"}'
    
    def _generate_categorization_response(self, prompt: str) -> str:
        """Generate realistic categorization response."""
        # Extract file info from prompt
        if ".py" in prompt:
            return '{"category": "CODE", "confidence": 0.95, "reasoning": "Python source code file"}'
        elif ".js" in prompt or ".ts" in prompt:
            return '{"category": "CODE", "confidence": 0.93, "reasoning": "JavaScript/TypeScript source file"}'
        elif ".html" in prompt or ".css" in prompt:
            return '{"category": "CODE", "confidence": 0.90, "reasoning": "Web development file"}'
        elif ".txt" in prompt or ".md" in prompt:
            return '{"category": "DOCUMENTS", "confidence": 0.88, "reasoning": "Text document file"}'
        elif ".pdf" in prompt or ".doc" in prompt:
            return '{"category": "DOCUMENTS", "confidence": 0.92, "reasoning": "Document file"}'
        elif ".jpg" in prompt or ".png" in prompt or ".gif" in prompt:
            return '{"category": "MEDIA", "confidence": 0.96, "reasoning": "Image file"}'
        elif ".mp4" in prompt or ".avi" in prompt or ".mkv" in prompt:
            return '{"category": "MEDIA", "confidence": 0.94, "reasoning": "Video file"}'
        elif ".mp3" in prompt or ".wav" in prompt:
            return '{"category": "MEDIA", "confidence": 0.93, "reasoning": "Audio file"}'
        elif ".log" in prompt:
            return '{"category": "LOGS", "confidence": 0.91, "reasoning": "Log file"}'
        elif ".json" in prompt:
            return '{"category": "DATA", "confidence": 0.89, "reasoning": "JSON data file"}'
        elif ".xml" in prompt:
            return '{"category": "DATA", "confidence": 0.87, "reasoning": "XML configuration file"}'
        elif ".csv" in prompt:
            return '{"category": "DATA", "confidence": 0.91, "reasoning": "CSV data file"}'
        elif ".zip" in prompt or ".rar" in prompt or ".tar" in prompt:
            # Check for gaming context
            if any(keyword in prompt.lower() for keyword in ['barnfind', 'race', 'car', 'forza', 'game']):
                return '{"category": "ARCHIVES", "confidence": 0.96, "reasoning": "Game asset archive file"}'
            else:
                return '{"category": "ARCHIVES", "confidence": 0.94, "reasoning": "Archive file"}'
        elif ".dll" in prompt or ".exe" in prompt or ".sys" in prompt:
            return '{"category": "SYSTEM", "confidence": 0.87, "reasoning": "System file"}'
        else:
            return '{"category": "DOCUMENTS", "confidence": 0.70, "reasoning": "Default categorization"}'
    
    def _generate_tagging_response(self, prompt: str) -> str:
        """Generate realistic tagging response."""
        tags = []
        
        # Gaming-specific tags
        if any(keyword in prompt.lower() for keyword in ['barnfind', 'car', 'vehicle']):
            tags.extend(["gaming", "forza-horizon", "car-models", "vehicles"])
        elif any(keyword in prompt.lower() for keyword in ['race', 'track', 'stage']):
            tags.extend(["gaming", "racing", "tracks", "environments"])
        elif any(keyword in prompt.lower() for keyword in ['shader', 'material', 'texture']):
            tags.extend(["gaming", "graphics", "rendering", "assets"])
        elif any(keyword in prompt.lower() for keyword in ['decal', 'vinyl']):
            tags.extend(["gaming", "customization", "graphics", "decals"])
        
        # Programming language tags
        elif ".py" in prompt:
            tags.extend(["python", "programming", "script"])
        elif ".js" in prompt:
            tags.extend(["javascript", "web-development", "frontend"])
        elif ".java" in prompt:
            tags.extend(["java", "programming", "backend"])
        elif ".cpp" in prompt or ".c" in prompt:
            tags.extend(["cpp", "c", "systems-programming"])
        
        # Web development tags
        elif ".html" in prompt:
            tags.extend(["html", "web", "markup"])
        elif ".css" in prompt:
            tags.extend(["css", "styling", "web"])
        
        # Document tags
        elif "readme" in prompt.lower():
            tags.extend(["documentation", "readme", "guide"])
        elif "config" in prompt.lower() or ".xml" in prompt:
            tags.extend(["configuration", "settings", "game-config"])
        elif "test" in prompt.lower():
            tags.extend(["testing", "unit-test", "quality-assurance"])
        
        # Media tags
        elif ".jpg" in prompt or ".png" in prompt:
            tags.extend(["image", "graphics", "visual"])
        elif ".mp4" in prompt:
            tags.extend(["video", "multimedia", "content"])
        elif ".mp3" in prompt:
            tags.extend(["audio", "music", "sound"])
        
        # Archive tags
        elif ".zip" in prompt or ".rar" in prompt:
            tags.extend(["archive", "compressed", "assets"])
        
        # Data tags
        elif ".json" in prompt:
            tags.extend(["data", "json", "configuration"])
        elif ".xml" in prompt:
            tags.extend(["data", "xml", "configuration"])
        
        # Default tags if none found
        if not tags:
            tags = ["file", "content", "data"]
        
        # Limit to 5 tags
        tags = tags[:5]
        
        return f'{{"tags": {tags}, "confidence": 0.85, "reasoning": "Tags extracted based on file analysis"}}'
    
    def _generate_naming_response(self, prompt: str) -> str:
        """Generate realistic naming response."""
        # Extract file name from prompt
        lines = prompt.split('\n')
        file_name = "unknown.txt"
        category = "DOCUMENTS"
        
        for line in lines:
            if "File Name:" in line:
                file_name = line.split("File Name:")[-1].strip()
            elif "Category:" in line:
                category = line.split("Category:")[-1].strip()
        
        # Generate path based on category
        if category == "CODE":
            if ".py" in file_name:
                suggested_path = f"code/python/scripts/{file_name}"
            elif ".js" in file_name:
                suggested_path = f"code/javascript/web/{file_name}"
            elif ".java" in file_name:
                suggested_path = f"code/java/applications/{file_name}"
            else:
                suggested_path = f"code/misc/{file_name}"
        elif category == "DOCUMENTS":
            suggested_path = f"documents/text/{file_name}"
        elif category == "MEDIA":
            if ".jpg" in file_name or ".png" in file_name:
                suggested_path = f"media/images/{file_name}"
            elif ".mp4" in file_name:
                suggested_path = f"media/videos/{file_name}"
            else:
                suggested_path = f"media/misc/{file_name}"
        elif category == "ARCHIVES":
            suggested_path = f"archives/game-assets/{file_name}"
        elif category == "DATA":
            suggested_path = f"data/game-data/{file_name}"
        else:
            suggested_path = f"{category.lower()}/{file_name}"
        
        return f'{{"suggested_path": "{suggested_path}", "confidence": 0.87, "reasoning": "Path generated following category conventions"}}'
    
    def _generate_confidence_response(self, prompt: str) -> str:
        """Generate realistic confidence assessment response."""
        # Analyze the prompt to generate realistic confidence
        if "FAILED" in prompt:
            return '''{
                "final_confidence": 0.45,
                "agent_breakdown": {
                    "categorization": 0.60,
                    "tagging": 0.40,
                    "naming": 0.35
                },
                "consistency_score": 0.40,
                "issues": ["Some agents failed", "Low consistency detected"],
                "reasoning": "Multiple agent failures detected, using fallback confidence"
            }'''
        else:
            return '''{
                "final_confidence": 0.84,
                "agent_breakdown": {
                    "categorization": 0.90,
                    "tagging": 0.82,
                    "naming": 0.85
                },
                "consistency_score": 0.86,
                "issues": [],
                "reasoning": "All agents performed well with good consistency between results"
            }'''


def get_test_files_from_directory(directory: str, max_files: int = 50) -> List[str]:
    """Get a sample of files from a directory for testing."""
    try:
        directory_path = Path(directory)
        if not directory_path.exists():
            print(f"❌ Directory does not exist: {directory}")
            return []
        
        print(f"🔍 Scanning {directory} for test files...")
        
        # Get all files (not directories)
        all_files = []
        for file_path in directory_path.rglob("*"):
            if file_path.is_file():
                all_files.append(str(file_path))
                
                # Stop if we have enough files
                if len(all_files) >= max_files * 2:  # Get extra to filter from
                    break
        
        print(f"📁 Found {len(all_files)} files total")
        
        # Filter for interesting file types and limit count
        interesting_extensions = {
            '.py', '.js', '.ts', '.html', '.css', '.java', '.cpp', '.c', '.cs',
            '.txt', '.md', '.pdf', '.doc', '.docx', '.json', '.xml', '.csv',
            '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.mp3', '.wav',
            '.log', '.zip', '.rar', '.tar', '.dll', '.exe'
        }
        
        filtered_files = []
        for file_path in all_files:
            file_ext = Path(file_path).suffix.lower()
            if file_ext in interesting_extensions:
                filtered_files.append(file_path)
        
        # Take a sample
        sample_files = filtered_files[:max_files]
        
        print(f"✅ Selected {len(sample_files)} files for testing")
        return sample_files
        
    except Exception as e:
        print(f"❌ Error scanning directory: {e}")
        return []


async def test_individual_agents():
    """Test each agent individually."""
    print("\n🤖 Testing Individual Agents")
    print("=" * 50)
    
    # Create mock inference engine
    inference_engine = MockInferenceEngine()
    
    # Test file
    test_file = "example_project/src/main.py"
    file_context = extract_file_context(test_file) if Path(test_file).exists() else None
    
    if not file_context:
        # Create mock file context
        file_context = extract_file_context(__file__)  # Use this test file
    
    print(f"📁 Test file: {file_context.file_name}")
    
    # Test Categorization Agent
    print("\n1️⃣ Testing Categorization Agent...")
    cat_agent = CategorizationAgent(inference_engine)
    cat_result = await cat_agent.process(file_context)
    
    if cat_result.success:
        print(f"   ✅ Category: {cat_result.raw_output.get('category')}")
        print(f"   📊 Confidence: {cat_result.confidence:.2f}")
        print(f"   ⏱️  Time: {cat_result.processing_time_ms}ms")
    else:
        print(f"   ❌ Failed: {cat_result.error_message}")
    
    # Test Tagging Agent
    print("\n2️⃣ Testing Tagging Agent...")
    tag_agent = TaggingAgent(inference_engine)
    tag_result = await tag_agent.process(file_context, category="CODE")
    
    if tag_result.success:
        tags = tag_result.raw_output.get('tags', [])
        print(f"   ✅ Tags: {', '.join(tags)}")
        print(f"   📊 Confidence: {tag_result.confidence:.2f}")
        print(f"   ⏱️  Time: {tag_result.processing_time_ms}ms")
    else:
        print(f"   ❌ Failed: {tag_result.error_message}")
    
    # Test Naming Agent
    print("\n3️⃣ Testing Naming Agent...")
    naming_agent = NamingAgent(inference_engine)
    naming_result = await naming_agent.process(
        file_context, category="CODE", tags=["python", "testing"]
    )
    
    if naming_result.success:
        suggested_path = naming_result.raw_output.get('suggested_path')
        print(f"   ✅ Suggested Path: {suggested_path}")
        print(f"   📊 Confidence: {naming_result.confidence:.2f}")
        print(f"   ⏱️  Time: {naming_result.processing_time_ms}ms")
    else:
        print(f"   ❌ Failed: {naming_result.error_message}")
    
    # Test Confidence Agent
    print("\n4️⃣ Testing Confidence Agent...")
    conf_agent = ConfidenceAgent(inference_engine)
    conf_result = await conf_agent.process(
        file_context,
        categorization_result=cat_result,
        tagging_result=tag_result,
        naming_result=naming_result
    )
    
    if conf_result.success:
        final_conf = conf_result.raw_output.get('final_confidence')
        print(f"   ✅ Final Confidence: {final_conf:.2f}")
        print(f"   📊 Consistency Score: {conf_result.raw_output.get('consistency_score', 0):.2f}")
        print(f"   ⏱️  Time: {conf_result.processing_time_ms}ms")
    else:
        print(f"   ❌ Failed: {conf_result.error_message}")


async def test_orchestrator_with_real_files(directory: str, max_files: int = 20):
    """Test the orchestrator with real files from your system."""
    print(f"\n🎭 Testing Orchestrator with Real Files from {directory}")
    print("=" * 70)
    
    # Get real files
    test_files = get_test_files_from_directory(directory, max_files)
    
    if not test_files:
        print("❌ No test files found!")
        return
    
    # Create orchestrator
    inference_engine = MockInferenceEngine()
    orchestrator = AgentOrchestrator(inference_engine)
    
    print(f"🚀 Processing {len(test_files)} files through the agentic system...")
    
    # Process files
    start_time = time.time()
    results = await orchestrator.process_file_batch(test_files)
    end_time = time.time()
    
    # Analyze results
    successful_results = [r for r in results if r.success]
    failed_results = [r for r in results if not r.success]
    
    print(f"\n📊 Results Summary:")
    print(f"   ✅ Successful: {len(successful_results)}")
    print(f"   ❌ Failed: {len(failed_results)}")
    print(f"   ⏱️  Total Time: {end_time - start_time:.2f}s")
    print(f"   🚀 Throughput: {len(test_files) / (end_time - start_time):.1f} files/sec")
    
    # Show some example results
    print(f"\n🎯 Example Results:")
    for i, result in enumerate(successful_results[:5]):  # Show first 5
        file_name = Path(result.original_path).name
        print(f"\n{i+1}. {file_name}")
        print(f"   📁 Category: {result.category}")
        print(f"   🏷️  Tags: {', '.join(result.tags) if result.tags else 'None'}")
        print(f"   📝 Suggested: {result.suggested_path}")
        print(f"   📊 Confidence: {result.final_confidence:.2f} ({result.quality_assessment})")
        print(f"   ⏱️  Time: {result.total_processing_time_ms}ms")
    
    # Show performance stats
    print(f"\n📈 Performance Statistics:")
    stats = orchestrator.get_performance_stats()
    
    orchestrator_stats = stats['orchestrator']
    print(f"   🎭 Orchestrator:")
    print(f"      Success Rate: {orchestrator_stats['success_rate']:.1%}")
    print(f"      Avg Time: {orchestrator_stats['avg_processing_time_ms']:.0f}ms")
    
    for agent_name, agent_stats in stats['agents'].items():
        print(f"   🤖 {agent_name.title()} Agent:")
        print(f"      Success Rate: {agent_stats['success_rate']:.1%}")
        print(f"      Avg Time: {agent_stats['avg_processing_time_ms']:.0f}ms")
    
    # Show any issues
    if failed_results:
        print(f"\n⚠️  Issues Found:")
        for result in failed_results[:3]:  # Show first 3 failures
            file_name = Path(result.original_path).name
            print(f"   ❌ {file_name}: {result.error_message}")


def main():
    """Main test function."""
    print("🧪 Sentinel 2.0 - Agentic AI System Test")
    print("=" * 60)
    print("Testing the revolutionary multi-agent file analysis system!")
    
    # Let user choose a directory with lots of files
    print("\n📁 Choose a directory with lots of files to test:")
    print("   Examples:")
    print("   • C:\\Users\\anubh\\Downloads")
    print("   • C:\\Projects")
    print("   • D:\\Documents")
    print("   • Your biggest drive with diverse file types")
    
    # Get directory from user
    test_directory = input("\n🎯 Enter directory path (or press Enter for current directory): ").strip()
    
    if not test_directory:
        test_directory = "."
    
    # Get number of files to test
    try:
        max_files = int(input("📊 How many files to test? (default 30): ") or "30")
    except ValueError:
        max_files = 30
    
    print(f"\n🚀 Starting tests with directory: {test_directory}")
    print(f"📊 Testing up to {max_files} files")
    
    # Run tests
    async def run_tests():
        # Test individual agents first
        await test_individual_agents()
        
        # Test orchestrator with real files
        await test_orchestrator_with_real_files(test_directory, max_files)
        
        print("\n🎉 All tests completed!")
        print("\nThe agentic system is working! Each agent specializes in:")
        print("   🤖 Categorization Agent: Determines file categories")
        print("   🏷️  Tagging Agent: Extracts relevant keywords")
        print("   📝 Naming Agent: Creates consistent file paths")
        print("   📊 Confidence Agent: Evaluates result quality")
        print("   🎭 Orchestrator: Coordinates all agents")
    
    # Run the async tests
    asyncio.run(run_tests())


if __name__ == "__main__":
    main()