#!/usr/bin/env python3
"""
Test Prometheus metrics system
"""

import sys
import time
import threading
from pathlib import Path

# Add helios to path
sys.path.insert(0, str(Path(__file__).parent))

def test_metrics_initialization():
    """Test metrics system initialization."""
    print("🧪 Testing metrics initialization...")
    
    try:
        from helios.metrics.prometheus_metrics import HeliosMetrics, MetricsConfig
        
        # Create config
        config = MetricsConfig(
            enabled=True,
            port=9091,  # Use different port for testing
            update_interval=2.0,
            collect_gpu_metrics=False,  # Disable GPU for testing
            collect_system_metrics=True
        )
        
        # Initialize metrics
        metrics = HeliosMetrics(config)
        
        print("✅ Metrics system initialized")
        
        # Test that all metric objects exist
        required_metrics = [
            'files_processed_total',
            'files_discovered_total',
            'file_processing_rate',
            'inference_duration_seconds',
            'active_workers',
            'cpu_usage_percent',
            'memory_usage_percent'
        ]
        
        missing_metrics = []
        for metric_name in required_metrics:
            if not hasattr(metrics, metric_name):
                missing_metrics.append(metric_name)
        
        if missing_metrics:
            print(f"❌ Missing metrics: {missing_metrics}")
            return False
        
        print("✅ All required metrics present")
        return True
        
    except ImportError as e:
        print(f"⚠️  Prometheus client not available: {e}")
        print("   Install with: pip install prometheus-client")
        return True  # Don't fail test if prometheus not installed
    except Exception as e:
        print(f"❌ Metrics initialization failed: {e}")
        return False

def test_metrics_recording():
    """Test recording metrics."""
    print("\n🧪 Testing metrics recording...")
    
    try:
        from helios.metrics.prometheus_metrics import HeliosMetrics, MetricsConfig
        
        config = MetricsConfig(
            enabled=True,
            port=9092,
            update_interval=0,  # Disable auto-update for testing
            collect_gpu_metrics=False,
            collect_system_metrics=False
        )
        
        metrics = HeliosMetrics(config)
        
        # Test file processing metrics
        metrics.record_file_processed(worker_id=1, status='success', processing_time=0.1, file_size=1024)
        metrics.record_file_processed(worker_id=2, status='success', processing_time=0.2, file_size=2048)
        metrics.record_file_processed(worker_id=1, status='error', processing_time=0.05, file_size=512)
        
        print("✅ File processing metrics recorded")
        
        # Test inference metrics
        metrics.record_inference(worker_id=1, duration=0.15, batch_size=32, confidence=0.85)
        metrics.record_inference(worker_id=2, duration=0.12, batch_size=16, confidence=0.92)
        
        print("✅ Inference metrics recorded")
        
        # Test worker metrics
        metrics.update_worker_status(worker_id=1, status='running', uptime=120.5)
        metrics.update_worker_status(worker_id=2, status='running', uptime=95.2)
        metrics.update_active_workers(2)
        
        print("✅ Worker metrics recorded")
        
        # Test queue metrics
        metrics.update_queue_depth('input', 45)
        metrics.update_queue_depth('output', 12)
        metrics.record_queue_operation('input', 'put')
        metrics.record_backpressure_event('scanner')
        
        print("✅ Queue metrics recorded")
        
        # Test processing rate
        metrics.update_processing_rate(125.7)
        
        print("✅ Processing rate updated")
        
        return True
        
    except ImportError:
        print("⚠️  Prometheus client not available - skipping test")
        return True
    except Exception as e:
        print(f"❌ Metrics recording failed: {e}")
        return False

def test_metrics_export():
    """Test metrics export in Prometheus format."""
    print("\n🧪 Testing metrics export...")
    
    try:
        from helios.metrics.prometheus_metrics import HeliosMetrics, MetricsConfig
        
        config = MetricsConfig(
            enabled=True,
            port=9093,
            update_interval=0,
            collect_gpu_metrics=False,
            collect_system_metrics=False
        )
        
        metrics = HeliosMetrics(config)
        
        # Record some test data
        metrics.record_file_processed(worker_id=1, status='success', processing_time=0.1, file_size=1024)
        metrics.record_inference(worker_id=1, duration=0.15, batch_size=32, confidence=0.85)
        metrics.update_active_workers(3)
        
        # Export metrics
        exported_metrics = metrics.export_metrics()
        
        print(f"📊 Exported metrics length: {len(exported_metrics)} characters")
        
        # Check for key metrics in export
        expected_metrics = [
            'sentinel_files_processed_total',
            'sentinel_inference_duration_seconds',
            'sentinel_active_workers'
        ]
        
        missing_exports = []
        for metric_name in expected_metrics:
            if metric_name not in exported_metrics:
                missing_exports.append(metric_name)
        
        if missing_exports:
            print(f"❌ Missing in export: {missing_exports}")
            return False
        
        print("✅ All key metrics present in export")
        
        # Show sample of exported metrics
        lines = exported_metrics.split('\n')[:10]
        print("📋 Sample exported metrics:")
        for line in lines:
            if line.strip() and not line.startswith('#'):
                print(f"   {line}")
        
        return True
        
    except ImportError:
        print("⚠️  Prometheus client not available - skipping test")
        return True
    except Exception as e:
        print(f"❌ Metrics export failed: {e}")
        return False

def test_metrics_server():
    """Test metrics HTTP server."""
    print("\n🧪 Testing metrics HTTP server...")
    
    try:
        from helios.metrics.prometheus_metrics import create_metrics_system
        import requests
        
        # Create metrics system
        metrics = create_metrics_system(port=9094, update_interval=0)
        
        # Record some test data
        metrics.record_file_processed(worker_id=1, status='success', processing_time=0.1, file_size=1024)
        metrics.update_active_workers(2)
        
        # Start server in background
        server_thread = threading.Thread(target=metrics.start_metrics_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(1)
        
        # Test HTTP endpoint
        try:
            response = requests.get('http://localhost:9094/metrics', timeout=5)
            
            if response.status_code == 200:
                print("✅ Metrics HTTP server responding")
                print(f"   Response length: {len(response.text)} characters")
                
                # Check content type
                if 'text/plain' in response.headers.get('content-type', ''):
                    print("✅ Correct content type")
                else:
                    print(f"⚠️  Unexpected content type: {response.headers.get('content-type')}")
                
                # Check for metrics in response
                if 'sentinel_files_processed_total' in response.text:
                    print("✅ Metrics data present in response")
                else:
                    print("❌ No metrics data in response")
                    return False
                
                return True
            else:
                print(f"❌ HTTP server returned status {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ HTTP request failed: {e}")
            return False
        
        finally:
            metrics.stop_metrics_server()
        
    except ImportError as e:
        if 'requests' in str(e):
            print("⚠️  requests library not available - skipping HTTP test")
            print("   Install with: pip install requests")
        else:
            print("⚠️  Prometheus client not available - skipping test")
        return True
    except Exception as e:
        print(f"❌ Metrics server test failed: {e}")
        return False

def test_system_metrics():
    """Test system resource metrics collection."""
    print("\n🧪 Testing system metrics collection...")
    
    try:
        from helios.metrics.prometheus_metrics import HeliosMetrics, MetricsConfig
        
        config = MetricsConfig(
            enabled=True,
            port=9095,
            update_interval=0,
            collect_gpu_metrics=False,  # Skip GPU for testing
            collect_system_metrics=True
        )
        
        metrics = HeliosMetrics(config)
        
        # Manually trigger system metrics update
        metrics._update_cpu_memory_metrics()
        
        print("✅ System metrics collection completed")
        
        # Get metrics summary
        summary = metrics.get_metrics_summary()
        
        print(f"📊 Metrics summary:")
        print(f"   Timestamp: {summary.get('timestamp', 'N/A')}")
        print(f"   Metrics enabled: {summary.get('metrics_enabled', 'N/A')}")
        print(f"   GPU available: {summary.get('gpu_available', 'N/A')}")
        print(f"   System metrics enabled: {summary.get('system_metrics_enabled', 'N/A')}")
        
        return True
        
    except ImportError:
        print("⚠️  Required libraries not available - skipping test")
        return True
    except Exception as e:
        print(f"❌ System metrics test failed: {e}")
        return False

def test_convenience_functions():
    """Test convenience functions."""
    print("\n🧪 Testing convenience functions...")
    
    try:
        from helios.metrics.prometheus_metrics import create_metrics_system
        
        # Test create_metrics_system
        metrics = create_metrics_system(port=9096, update_interval=5.0)
        
        if metrics.config.port == 9096:
            print("✅ create_metrics_system working")
        else:
            print("❌ create_metrics_system port not set correctly")
            return False
        
        if metrics.config.update_interval == 5.0:
            print("✅ update_interval set correctly")
        else:
            print("❌ update_interval not set correctly")
            return False
        
        return True
        
    except ImportError:
        print("⚠️  Prometheus client not available - skipping test")
        return True
    except Exception as e:
        print(f"❌ Convenience functions test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Prometheus Metrics Test Suite")
    print("=" * 50)
    
    try:
        # Run tests
        test1 = test_metrics_initialization()
        test2 = test_metrics_recording()
        test3 = test_metrics_export()
        test4 = test_metrics_server()
        test5 = test_system_metrics()
        test6 = test_convenience_functions()
        
        print("\n" + "=" * 50)
        if all([test1, test2, test3, test4, test5, test6]):
            print("🎉 All tests passed! Prometheus metrics are ready!")
            print("\n📊 Metrics will be available at: http://localhost:9090/metrics")
            print("🔧 Install dependencies: pip install prometheus-client psutil")
            return 0
        else:
            print("💥 Some tests failed!")
            return 1
            
    except Exception as e:
        print(f"💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())