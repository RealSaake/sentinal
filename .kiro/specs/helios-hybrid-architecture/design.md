# Helios Hybrid Architecture Design Document

## Overview

The Helios system implements a high-performance hybrid architecture that combines asyncio for I/O-bound file discovery with multiprocessing for CPU/GPU-bound AI inference. This design maximizes throughput by optimally utilizing system resources while providing comprehensive observability through Prometheus metrics and real-time dashboard monitoring.

## Architecture

### High-Level Architecture Diagram

```mermaid
graph TB
    subgraph "Asyncio Producer Layer"
        FS[File System Scanner] --> Q[Shared Queue]
        FS --> M[Metrics Collector]
    end
    
    subgraph "Multiprocessing Consumer Layer"
        Q --> W1[GPU Worker 1<br/>ONNX Runtime]
        Q --> W2[GPU Worker 2<br/>ONNX Runtime]
        Q --> WN[GPU Worker N<br/>ONNX Runtime]
    end
    
    subgraph "Observability Layer"
        W1 --> PM[Prometheus Metrics]
        W2 --> PM
        WN --> PM
        M --> PM
        PM --> ME[/metrics Endpoint]
    end
    
    subgraph "UI Dashboard Layer"
        ME --> UI[Real-time Dashboard]
        UI --> Charts[Live Performance Charts]
    end
    
    subgraph "Storage Layer"
        W1 --> DB[(SQLite Database)]
        W2 --> DB
        WN --> DB
    end
```

### Process Architecture

The system operates with the following process structure:

1. **Main Process**: Coordinates the entire system, manages configuration, and hosts the UI
2. **Asyncio Producer Process**: Handles non-blocking file system scanning
3. **GPU Worker Processes**: Multiple independent processes for AI inference (configurable count)
4. **Metrics Server Process**: Hosts the Prometheus metrics endpoint

## Components and Interfaces

### 1. Asyncio File Scanner (Producer)

**Purpose**: Non-blocking discovery of file paths using asyncio

**Key Classes**:
```python
class AsyncFileScanner:
    async def scan_directory(self, path: str) -> AsyncGenerator[FileTask, None]
    async def enqueue_files(self, queue: multiprocessing.Queue)
    def get_scan_metrics(self) -> ScanMetrics
```

**Interface**:
- Input: Directory path from configuration
- Output: FileTask objects placed in shared multiprocessing queue
- Metrics: Files discovered per second, scan progress

### 2. ONNX Inference Engine

**Purpose**: High-performance AI inference using ONNX Runtime with CUDA

**Key Classes**:
```python
class ONNXInferenceEngine:
    def __init__(self, model_path: str, use_cuda: bool = True)
    def initialize_session(self) -> onnxruntime.InferenceSession
    def process_batch(self, batch: List[FileTask]) -> List[AnalysisResult]
    def generate_structured_output(self, file_info: FileTask) -> Dict[str, Any]
```

**Interface**:
- Input: Batch of FileTask objects
- Output: Structured JSON conforming to schema:
```json
{
    "categorized_path": "SourceType/Category/Sub-Category/file.ext",
    "confidence": 0.95,
    "tags": ["tag1", "tag2", "relevant_keyword"]
}
```

### 3. GPU Worker Process

**Purpose**: Independent multiprocessing workers for true parallel inference

**Key Classes**:
```python
class GPUWorker:
    def __init__(self, worker_id: int, queue: multiprocessing.Queue, config: Dict)
    def run(self) -> None
    def process_batch_with_metrics(self, batch: List[FileTask]) -> List[AnalysisResult]
    def report_metrics(self, metrics: WorkerMetrics) -> None
```

**Interface**:
- Input: Shared multiprocessing queue
- Output: Analysis results to database, metrics to Prometheus
- Lifecycle: Independent process with automatic restart on failure

### 4. Prometheus Metrics System

**Purpose**: Comprehensive observability and monitoring

**Key Metrics**:
```python
# Counters
sentinel_files_processed_total = Counter('sentinel_files_processed_total', 'Total files processed')

# Histograms  
sentinel_inference_duration_seconds = Histogram('sentinel_inference_duration_seconds', 'AI inference latency')

# Gauges
sentinel_batch_size = Gauge('sentinel_batch_size', 'Current batch size')
sentinel_gpu_utilization_percent = Gauge('sentinel_gpu_utilization_percent', 'GPU utilization')
sentinel_gpu_memory_used_bytes = Gauge('sentinel_gpu_memory_used_bytes', 'GPU memory usage')
```

**Interface**:
- Endpoint: `/metrics` on configurable port (default: 9090)
- Format: Prometheus exposition format
- Update frequency: Real-time as events occur

### 5. Real-time Dashboard UI

**Purpose**: Live monitoring and control interface

**Key Components**:
```python
class HeliosDashboard(QMainWindow):
    def __init__(self, metrics_endpoint: str)
    def setup_live_charts(self) -> None
    def update_performance_charts(self) -> None
    def display_batch_progress(self) -> None
    def show_gpu_utilization(self) -> None
```

**Features**:
- Live updating charts using QTimer
- Non-blocking UI updates
- Granular batch-level progress
- GPU utilization visualization
- Files/second performance tracking

## Data Models

### Core Data Structures

```python
@dataclass
class FileTask:
    """File to be analyzed"""
    path: str
    size: int
    extension: str
    relative_path: str
    discovered_at: datetime
    
@dataclass  
class AnalysisResult:
    """AI inference result"""
    original_path: str
    categorized_path: str
    confidence: float
    tags: List[str]
    processing_time: float
    worker_id: int
    timestamp: datetime

@dataclass
class WorkerMetrics:
    """Per-worker performance metrics"""
    worker_id: int
    files_processed: int
    avg_inference_time: float
    gpu_utilization: float
    gpu_memory_used: int
    batch_size: int

@dataclass
class SystemHealth:
    """Overall system health"""
    total_files_processed: int
    files_per_second: float
    active_workers: int
    queue_size: int
    gpu_temperature: float
    memory_usage_percent: float
```

### Database Schema

```sql
-- Analysis results table
CREATE TABLE analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_path TEXT NOT NULL,
    categorized_path TEXT NOT NULL,
    confidence REAL NOT NULL,
    tags JSON NOT NULL,
    processing_time REAL NOT NULL,
    worker_id INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp (timestamp),
    INDEX idx_worker_id (worker_id)
);

-- Performance metrics table
CREATE TABLE performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    worker_id INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_metric_timestamp (metric_name, timestamp)
);
```

## Error Handling

### Failure Scenarios and Recovery

1. **Worker Process Failure**
   - Detection: Process monitoring with heartbeat
   - Recovery: Automatic process restart with exponential backoff
   - Metrics: Track worker restart events

2. **ONNX Model Loading Failure**
   - Detection: Exception during model initialization
   - Recovery: Fallback to CPU execution provider
   - Logging: Structured error with model path and CUDA availability

3. **GPU Memory Exhaustion**
   - Detection: CUDA out-of-memory exceptions
   - Recovery: Dynamic batch size reduction
   - Metrics: Track memory usage and batch size adjustments

4. **Queue Overflow**
   - Detection: Queue size monitoring
   - Recovery: Backpressure mechanism to slow producer
   - Metrics: Track queue depth and backpressure events

5. **Metrics Endpoint Failure**
   - Detection: HTTP server exceptions
   - Recovery: Restart metrics server, continue core processing
   - Isolation: Metrics failures don't affect inference pipeline

## Testing Strategy

### Unit Testing
- **AsyncFileScanner**: Mock file system, test asyncio patterns
- **ONNXInferenceEngine**: Mock ONNX runtime, test batch processing
- **GPUWorker**: Mock multiprocessing queue, test worker lifecycle
- **Metrics**: Test Prometheus metric collection and exposition

### Integration Testing
- **Producer-Consumer Pipeline**: End-to-end queue flow testing
- **Multi-process Communication**: Test shared queue and metrics aggregation
- **ONNX Runtime Integration**: Test actual model loading and inference
- **Database Operations**: Test concurrent writes from multiple workers

### Performance Testing
- **Throughput Benchmarks**: Measure files/second under various loads
- **Scalability Testing**: Test performance with different worker counts
- **Memory Usage**: Monitor memory consumption under sustained load
- **GPU Utilization**: Verify optimal GPU resource usage

### Load Testing
- **50,000 File Target**: Validate 10-minute processing requirement
- **Concurrent Access**: Test multiple simultaneous directory scans
- **Resource Exhaustion**: Test behavior under memory/GPU limits
- **Long-running Stability**: 24-hour continuous operation test

## Configuration Schema

### Enhanced config.yaml Structure

```yaml
# Sentinel Analyzer - Helios Configuration
logging:
  level: INFO
  directory: "logs"
  structured: true
  
database:
  path: "db/sentinel.db"
  connection_pool_size: 10
  
performance:
  # Helios Hybrid Asynchronous Pipeline Settings
  io_workers: 4          # For asyncio file scanning
  gpu_workers: 2         # Number of separate Python processes for inference
  batch_size: 128        # Files per inference batch
  queue_max_size: 10000  # Maximum queue depth
  
inference:
  # Mandating optimized runtimes
  runtime: "onnx"
  onnx_model_path: "models/sentinel_v1.onnx"
  cuda_enabled: true
  fallback_to_cpu: true
  max_sequence_length: 512
  
observability:
  prometheus_port: 9090
  metrics_update_interval: 1.0  # seconds
  health_check_interval: 5.0    # seconds
  
ui:
  dashboard_port: 8080
  chart_update_interval: 1.0    # seconds
  max_chart_points: 1000
```

## Deployment Considerations

### System Requirements
- **Python**: 3.9+ with multiprocessing support
- **GPU**: NVIDIA GPU with CUDA 11.0+ for optimal performance
- **Memory**: Minimum 16GB RAM for large-scale processing
- **Storage**: SSD recommended for database performance

### Dependencies
- **Core**: `onnxruntime-gpu`, `prometheus-client`, `PyQt6`
- **AI**: `transformers`, `torch` (for model conversion)
- **Database**: `sqlite3`, `sqlalchemy`
- **Monitoring**: `psutil`, `nvidia-ml-py`

### Performance Tuning
- **Worker Count**: Set gpu_workers to number of available GPUs
- **Batch Size**: Tune based on GPU memory capacity
- **Queue Size**: Balance memory usage vs. throughput
- **I/O Workers**: Match to storage subsystem capabilities

This design provides a robust, scalable, and observable architecture that meets the demanding performance requirements while maintaining system reliability and operational visibility.