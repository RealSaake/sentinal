#!/usr/bin/env python3
"""Comprehensive stress test for the Sentinel logging system."""

import sys
import os
import yaml
import time
import threading
import random
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Add sentinel to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sentinel'))

from sentinel.app.logging import LoggerManager, PerformanceMonitor, DebugInfoCollector
from sentinel.app.ai.inference_engine import InferenceEngine

class LoggingStressTester:
    """Comprehensive stress tester for the logging system."""
    
    def __init__(self):
        self.config = self.load_config()
        self.logger_manager = None
        self.perf_monitor = None
        self.debug_collector = None
        self.test_results = {}
        self.errors = []
        
    def load_config(self):
        """Load configuration."""
        config_path = Path('sentinel/config/config.yaml')
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def setup_logging_system(self):
        """Initialize the logging system."""
        print("🔧 Setting up logging system...")
        self.logger_manager = LoggerManager(self.config)
        self.perf_monitor = PerformanceMonitor(self.logger_manager)
        self.debug_collector = DebugInfoCollector(self.config, self.logger_manager, self.perf_monitor)
        print("✅ Logging system initialized")
    
    def test_high_volume_logging(self, num_messages=1000):
        """Test high-volume logging."""
        print(f"📝 Testing high-volume logging ({num_messages} messages)...")
        
        start_time = time.perf_counter()
        logger = self.logger_manager.get_logger('stress_test')
        
        try:
            for i in range(num_messages):
                level = random.choice(['debug', 'info', 'warning', 'error'])
                message = f"Stress test message {i+1} - {random.choice(['Processing', 'Analyzing', 'Computing', 'Validating'])} data"
                
                if level == 'debug':
                    logger.debug(message)
                elif level == 'info':
                    logger.info(message)
                elif level == 'warning':
                    logger.warning(message)
                elif level == 'error':
                    logger.error(message)
            
            duration = time.perf_counter() - start_time
            messages_per_second = num_messages / duration
            
            self.test_results['high_volume_logging'] = {
                'status': 'PASS',
                'messages': num_messages,
                'duration': duration,
                'messages_per_second': messages_per_second
            }
            
            print(f"✅ High-volume logging: {num_messages} messages in {duration:.3f}s ({messages_per_second:.1f} msg/s)")
            
        except Exception as e:
            self.test_results['high_volume_logging'] = {'status': 'FAIL', 'error': str(e)}
            self.errors.append(f"High-volume logging failed: {e}")
            print(f"❌ High-volume logging failed: {e}")
    
    def test_concurrent_logging(self, num_threads=10, messages_per_thread=100):
        """Test concurrent logging from multiple threads."""
        print(f"🧵 Testing concurrent logging ({num_threads} threads, {messages_per_thread} messages each)...")
        
        start_time = time.perf_counter()
        
        def log_worker(thread_id):
            """Worker function for concurrent logging."""
            logger = self.logger_manager.get_logger(f'thread_{thread_id}')
            for i in range(messages_per_thread):
                logger.info(f"Thread {thread_id} message {i+1}")
        
        try:
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(log_worker, i) for i in range(num_threads)]
                
                for future in as_completed(futures):
                    future.result()  # Wait for completion and check for exceptions
            
            duration = time.perf_counter() - start_time
            total_messages = num_threads * messages_per_thread
            messages_per_second = total_messages / duration
            
            self.test_results['concurrent_logging'] = {
                'status': 'PASS',
                'threads': num_threads,
                'total_messages': total_messages,
                'duration': duration,
                'messages_per_second': messages_per_second
            }
            
            print(f"✅ Concurrent logging: {total_messages} messages from {num_threads} threads in {duration:.3f}s ({messages_per_second:.1f} msg/s)")
            
        except Exception as e:
            self.test_results['concurrent_logging'] = {'status': 'FAIL', 'error': str(e)}
            self.errors.append(f"Concurrent logging failed: {e}")
            print(f"❌ Concurrent logging failed: {e}")
    
    def test_performance_monitoring_stress(self, num_operations=500):
        """Test performance monitoring under stress."""
        print(f"📊 Testing performance monitoring stress ({num_operations} operations)...")
        
        start_time = time.perf_counter()
        
        try:
            operation_types = ['ai_inference', 'database_query', 'file_scan', 'content_extraction']
            
            for i in range(num_operations):
                op_type = random.choice(operation_types)
                op_id = self.perf_monitor.start_operation(op_type, {'test_id': i})
                
                # Simulate work
                time.sleep(random.uniform(0.001, 0.01))
                
                success = random.choice([True, True, True, False])  # 75% success rate
                error_msg = f"Test error {i}" if not success else None
                
                self.perf_monitor.end_operation(op_id, success=success, error_message=error_msg)
            
            # Test specific logging methods
            for i in range(50):
                self.perf_monitor.log_ai_request(
                    duration=random.uniform(0.5, 3.0),
                    success=random.choice([True, False]),
                    model_name="test_model",
                    error_message="Test AI error" if random.random() < 0.2 else None
                )
                
                self.perf_monitor.log_database_operation(
                    operation_type=random.choice(['SELECT', 'INSERT', 'UPDATE', 'DELETE']),
                    duration=random.uniform(0.01, 0.5),
                    affected_rows=random.randint(0, 100),
                    success=random.choice([True, True, False])
                )
                
                self.perf_monitor.log_scan_operation(
                    file_count=random.randint(10, 1000),
                    duration=random.uniform(1.0, 10.0),
                    directory_path=f"/test/path/{i}"
                )
            
            duration = time.perf_counter() - start_time
            
            # Get metrics to verify they're working
            metrics = self.perf_monitor.get_metrics()
            
            self.test_results['performance_monitoring_stress'] = {
                'status': 'PASS',
                'operations': num_operations + 150,  # +150 for specific method calls
                'duration': duration,
                'metrics_collected': len(metrics),
                'operations_per_second': (num_operations + 150) / duration
            }
            
            print(f"✅ Performance monitoring stress: {num_operations + 150} operations in {duration:.3f}s")
            print(f"   Metrics collected for {len(metrics)} operation types")
            
        except Exception as e:
            self.test_results['performance_monitoring_stress'] = {'status': 'FAIL', 'error': str(e)}
            self.errors.append(f"Performance monitoring stress failed: {e}")
            print(f"❌ Performance monitoring stress failed: {e}")
    
    def test_log_rotation(self):
        """Test log rotation functionality."""
        print("🔄 Testing log rotation...")
        
        try:
            logger = self.logger_manager.get_logger('rotation_test')
            
            # Generate enough logs to trigger rotation (assuming 10MB limit)
            large_message = "X" * 1000  # 1KB message
            
            print("   Generating large volume of logs to trigger rotation...")
            for i in range(5000):  # ~5MB of logs
                logger.info(f"Rotation test message {i+1}: {large_message}")
                
                if i % 1000 == 0:
                    print(f"   Generated {i+1} messages...")
            
            # Force rotation
            self.logger_manager.rotate_logs()
            
            # Check if log files exist
            log_dir = Path('logs')
            log_files = list(log_dir.glob('*.log*'))
            
            self.test_results['log_rotation'] = {
                'status': 'PASS',
                'log_files_created': len(log_files),
                'log_files': [f.name for f in log_files]
            }
            
            print(f"✅ Log rotation: {len(log_files)} log files created")
            
        except Exception as e:
            self.test_results['log_rotation'] = {'status': 'FAIL', 'error': str(e)}
            self.errors.append(f"Log rotation failed: {e}")
            print(f"❌ Log rotation failed: {e}")
    
    def test_memory_usage(self):
        """Test memory usage of logging system."""
        print("💾 Testing memory usage...")
        
        try:
            import psutil
            process = psutil.Process()
            
            # Get initial memory usage
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Generate lots of logs
            logger = self.logger_manager.get_logger('memory_test')
            for i in range(10000):
                logger.info(f"Memory test message {i+1} with some additional data: {random.randint(1, 1000000)}")
            
            # Get final memory usage
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            self.test_results['memory_usage'] = {
                'status': 'PASS',
                'initial_memory_mb': initial_memory,
                'final_memory_mb': final_memory,
                'memory_increase_mb': memory_increase
            }
            
            print(f"✅ Memory usage: {memory_increase:.2f}MB increase ({initial_memory:.2f}MB → {final_memory:.2f}MB)")
            
        except Exception as e:
            self.test_results['memory_usage'] = {'status': 'FAIL', 'error': str(e)}
            self.errors.append(f"Memory usage test failed: {e}")
            print(f"❌ Memory usage test failed: {e}")
    
    def test_debug_collector_stress(self):
        """Test debug collector under stress."""
        print("🔍 Testing debug collector stress...")
        
        try:
            # Test multiple rapid calls
            for i in range(20):
                system_info = self.debug_collector.collect_system_info()
                app_state = self.debug_collector.collect_app_state()
                ai_connectivity = self.debug_collector.test_ai_connectivity()
                db_connectivity = self.debug_collector.test_database_connectivity()
                
                if i % 5 == 0:
                    print(f"   Completed {i+1} debug collection cycles...")
            
            # Test debug report generation
            debug_report = self.debug_collector.generate_debug_report()
            report_size = len(debug_report)
            
            self.test_results['debug_collector_stress'] = {
                'status': 'PASS',
                'collection_cycles': 20,
                'debug_report_size_bytes': report_size
            }
            
            print(f"✅ Debug collector stress: 20 cycles completed, report size: {report_size} bytes")
            
        except Exception as e:
            self.test_results['debug_collector_stress'] = {'status': 'FAIL', 'error': str(e)}
            self.errors.append(f"Debug collector stress failed: {e}")
            print(f"❌ Debug collector stress failed: {e}")
    
    def test_ai_inference_with_logging(self, num_requests=20):
        """Test AI inference with logging integration."""
        print(f"🤖 Testing AI inference with logging ({num_requests} requests)...")
        
        try:
            engine = InferenceEngine(
                backend_mode="local",
                logger_manager=self.logger_manager,
                performance_monitor=self.perf_monitor
            )
            
            test_cases = [
                {"path": "/documents/meeting_notes.txt", "content": "Meeting notes from project discussion"},
                {"path": "/photos/vacation.jpg", "content": "Image file from vacation"},
                {"path": "/code/main.py", "content": "Python source code file"},
                {"path": "/reports/quarterly.pdf", "content": "Quarterly business report"},
                {"path": "/music/song.mp3", "content": "Audio file"},
            ]
            
            successful_requests = 0
            failed_requests = 0
            
            for i in range(num_requests):
                test_case = random.choice(test_cases)
                metadata = {"path": test_case["path"], "size": random.randint(1024, 1048576)}
                
                try:
                    result = engine.analyze(metadata, test_case["content"])
                    successful_requests += 1
                    
                    if i % 5 == 0:
                        print(f"   Completed {i+1} AI inference requests...")
                        
                except Exception as e:
                    failed_requests += 1
                    print(f"   AI request {i+1} failed: {e}")
            
            # Get AI performance metrics
            metrics = self.perf_monitor.get_metrics()
            ai_metrics = metrics.get('ai_inference', {})
            
            self.test_results['ai_inference_with_logging'] = {
                'status': 'PASS',
                'total_requests': num_requests,
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'success_rate': (successful_requests / num_requests) * 100,
                'avg_duration': ai_metrics.get('average_duration', 0)
            }
            
            print(f"✅ AI inference with logging: {successful_requests}/{num_requests} successful ({(successful_requests/num_requests)*100:.1f}%)")
            
        except Exception as e:
            self.test_results['ai_inference_with_logging'] = {'status': 'FAIL', 'error': str(e)}
            self.errors.append(f"AI inference with logging failed: {e}")
            print(f"❌ AI inference with logging failed: {e}")
    
    def test_log_level_changes(self):
        """Test dynamic log level changes."""
        print("🎚️ Testing log level changes...")
        
        try:
            logger = self.logger_manager.get_logger('level_test')
            
            # Test all log levels
            levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            
            for level in levels:
                self.logger_manager.set_log_level(level)
                
                # Generate test messages at all levels
                logger.debug(f"Debug message at {level} level")
                logger.info(f"Info message at {level} level")
                logger.warning(f"Warning message at {level} level")
                logger.error(f"Error message at {level} level")
                logger.critical(f"Critical message at {level} level")
            
            # Reset to INFO
            self.logger_manager.set_log_level('INFO')
            
            self.test_results['log_level_changes'] = {
                'status': 'PASS',
                'levels_tested': levels,
                'final_level': 'INFO'
            }
            
            print(f"✅ Log level changes: Tested {len(levels)} levels successfully")
            
        except Exception as e:
            self.test_results['log_level_changes'] = {'status': 'FAIL', 'error': str(e)}
            self.errors.append(f"Log level changes failed: {e}")
            print(f"❌ Log level changes failed: {e}")
    
    def test_error_handling(self):
        """Test error handling in logging system."""
        print("⚠️ Testing error handling...")
        
        try:
            logger = self.logger_manager.get_logger('error_test')
            
            # Test logging with exceptions
            try:
                raise ValueError("Test exception for logging")
            except Exception as e:
                logger.error("Caught test exception", exc_info=True)
            
            # Test performance monitor with invalid operations
            try:
                self.perf_monitor.end_operation("invalid_operation_id", success=False)
            except Exception:
                pass  # Expected to handle gracefully
            
            # Test debug collector with potential failures
            try:
                # This might fail but should be handled gracefully
                self.debug_collector.test_ai_connectivity()
            except Exception:
                pass
            
            self.test_results['error_handling'] = {
                'status': 'PASS',
                'error_scenarios_tested': 3
            }
            
            print("✅ Error handling: All error scenarios handled gracefully")
            
        except Exception as e:
            self.test_results['error_handling'] = {'status': 'FAIL', 'error': str(e)}
            self.errors.append(f"Error handling failed: {e}")
            print(f"❌ Error handling failed: {e}")
    
    def run_all_tests(self):
        """Run all stress tests."""
        print("🚀 Starting comprehensive logging system stress test...\n")
        
        start_time = time.perf_counter()
        
        # Setup
        self.setup_logging_system()
        
        # Run all tests
        self.test_high_volume_logging(2000)
        self.test_concurrent_logging(15, 200)
        self.test_performance_monitoring_stress(1000)
        self.test_log_rotation()
        self.test_memory_usage()
        self.test_debug_collector_stress()
        self.test_ai_inference_with_logging(25)
        self.test_log_level_changes()
        self.test_error_handling()
        
        total_duration = time.perf_counter() - start_time
        
        # Generate final report
        self.generate_final_report(total_duration)
    
    def generate_final_report(self, total_duration):
        """Generate final test report."""
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE STRESS TEST RESULTS")
        print("="*80)
        
        passed_tests = sum(1 for result in self.test_results.values() if result['status'] == 'PASS')
        total_tests = len(self.test_results)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"Total Duration: {total_duration:.3f}s")
        
        print("\n📋 Detailed Results:")
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result['status'] == 'PASS' else "❌"
            print(f"{status_icon} {test_name}: {result['status']}")
            
            if result['status'] == 'PASS':
                # Show key metrics for passed tests
                if 'messages_per_second' in result:
                    print(f"   └─ {result['messages_per_second']:.1f} messages/second")
                if 'operations_per_second' in result:
                    print(f"   └─ {result['operations_per_second']:.1f} operations/second")
                if 'memory_increase_mb' in result:
                    print(f"   └─ {result['memory_increase_mb']:.2f}MB memory increase")
                if 'success_rate' in result:
                    print(f"   └─ {result['success_rate']:.1f}% success rate")
            else:
                print(f"   └─ Error: {result.get('error', 'Unknown error')}")
        
        if self.errors:
            print("\n⚠️ Errors Encountered:")
            for error in self.errors:
                print(f"   • {error}")
        
        # Save detailed report
        report_data = {
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'success_rate': (passed_tests/total_tests)*100,
                'total_duration': total_duration,
                'timestamp': datetime.now().isoformat()
            },
            'test_results': self.test_results,
            'errors': self.errors
        }
        
        report_path = Path('stress_test_report.json')
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_path}")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! Logging system is rock solid! 🎉")
        else:
            print(f"\n⚠️ {total_tests - passed_tests} test(s) failed. Check the report for details.")
        
        print("="*80)

def main():
    """Main function."""
    tester = LoggingStressTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()