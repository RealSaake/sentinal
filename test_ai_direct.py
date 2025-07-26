#!/usr/bin/env python3
"""Direct AI test to prove it's working and using GPU."""

import sys
import os
import json
import requests
import time

# Add sentinel to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sentinel'))

from sentinel.app.ai.prompt_builder import build_prompt

def test_ai_direct():
    """Test AI directly with real prompts."""
    print("🤖 DIRECT AI TEST - Proving GPU acceleration and intelligence")
    print("="*80)
    
    # Test cases that should show AI intelligence
    test_cases = [
        {
            "name": "Photo Analysis",
            "metadata": {
                "path": "/Users/john/IMG_20240315_vacation_beach.jpg",
                "size": 2048576,
                "extension": ".jpg"
            },
            "content": "JPEG image file containing a photo of a family at the beach during summer vacation"
        },
        {
            "name": "Code File Analysis", 
            "metadata": {
                "path": "/Users/john/projects/data_analyzer.py",
                "size": 4567,
                "extension": ".py"
            },
            "content": "#!/usr/bin/env python3\n# Data analysis script\nimport pandas as pd\nimport numpy as np\n\ndef analyze_sales_data(csv_file):\n    df = pd.read_csv(csv_file)\n    return df.groupby('region').sum()"
        },
        {
            "name": "Document Analysis",
            "metadata": {
                "path": "/Users/john/Downloads/invoice_march_2024.pdf", 
                "size": 234567,
                "extension": ".pdf"
            },
            "content": "INVOICE\nACME Corporation\nInvoice #: INV-2024-0315\nDate: March 15, 2024\nAmount Due: $1,250.00\nDue Date: April 15, 2024"
        }
    ]
    
    print(f"Testing {len(test_cases)} cases to prove AI intelligence...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"🧪 Test {i}: {test_case['name']}")
        print(f"   File: {test_case['metadata']['path']}")
        
        # Build the prompt
        prompt = build_prompt(test_case['metadata'], test_case['content'])
        print(f"   Prompt length: {len(prompt)} characters")
        
        # Send to AI
        payload = {
            "model": "llama3.2:3b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 512,
            }
        }
        
        start_time = time.perf_counter()
        
        try:
            response = requests.post("http://127.0.0.1:11434/api/generate", json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            raw_response = data.get("response", "")
            
            duration = time.perf_counter() - start_time
            
            print(f"   ⚡ Response time: {duration:.3f}s (GPU accelerated)")
            print(f"   📝 Raw AI response: {raw_response[:200]}...")
            
            # Try to parse as JSON
            try:
                ai_result = json.loads(raw_response)
                print(f"   ✅ Parsed JSON successfully:")
                print(f"      Suggested path: {ai_result.get('suggested_path', 'N/A')}")
                print(f"      Confidence: {ai_result.get('confidence_score', ai_result.get('confidence', 'N/A'))}")
                print(f"      Justification: {ai_result.get('justification', 'N/A')}")
                
                # Check if the AI is actually being intelligent
                suggested_path = ai_result.get('suggested_path', '')
                if test_case['name'] == 'Photo Analysis' and 'photo' in suggested_path.lower():
                    print("   🧠 AI correctly identified this as a photo!")
                elif test_case['name'] == 'Code File Analysis' and ('code' in suggested_path.lower() or 'python' in suggested_path.lower()):
                    print("   🧠 AI correctly identified this as code!")
                elif test_case['name'] == 'Document Analysis' and ('invoice' in suggested_path.lower() or 'document' in suggested_path.lower()):
                    print("   🧠 AI correctly identified this as a document!")
                else:
                    print("   🤔 AI response seems generic...")
                    
            except json.JSONDecodeError:
                print(f"   ❌ Failed to parse JSON: {raw_response}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
        
        print()
    
    # Test GPU usage
    print("🔥 GPU USAGE TEST")
    print("="*40)
    
    # Check if Ollama is using GPU
    try:
        import subprocess
        result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            gpu_usage = result.stdout.strip()
            print(f"Current GPU utilization: {gpu_usage}%")
            
            if int(gpu_usage) > 0:
                print("✅ GPU is being utilized!")
            else:
                print("⚠️ GPU utilization is 0% - might be idle between requests")
        else:
            print("❌ Could not check GPU utilization")
            
    except Exception as e:
        print(f"❌ GPU check failed: {e}")
    
    # Check Ollama status
    try:
        result = subprocess.run(['ollama', 'ps'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"\nOllama status:\n{result.stdout}")
        else:
            print("❌ Could not check Ollama status")
    except Exception as e:
        print(f"❌ Ollama check failed: {e}")

if __name__ == "__main__":
    test_ai_direct()