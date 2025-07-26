#!/usr/bin/env python3
"""GPU detection utility for Sentinel."""

import subprocess
import json

def detect_gpus():
    """Detect available GPUs."""
    gpus = ["Default CPU"]  # Always include CPU option
    
    try:
        # Try NVIDIA GPUs first
        result = subprocess.run([
            'nvidia-smi', 
            '--query-gpu=name,memory.total', 
            '--format=csv,noheader,nounits'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split(', ')
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        memory = parts[1].strip()
                        gpus.append(f"{name} ({memory}MB VRAM)")
    except Exception:
        pass
    
    try:
        # Try AMD GPUs (if available)
        # This would require different tools, skipping for now
        pass
    except Exception:
        pass
    
    return gpus

if __name__ == "__main__":
    gpus = detect_gpus()
    print("Available GPUs:")
    for i, gpu in enumerate(gpus):
        print(f"  {i}: {gpu}")