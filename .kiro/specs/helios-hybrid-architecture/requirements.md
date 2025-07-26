# Requirements Document

## Introduction

The Helios system represents a next-generation file analysis architecture that combines asyncio for I/O-bound operations with multiprocessing for CPU/GPU-bound AI inference. This hybrid approach bypasses Python's GIL limitations while providing real-time observability through Prometheus metrics and a dynamic dashboard interface.

## Requirements

### Requirement 1: Hybrid Producer-Consumer Architecture

**User Story:** As a system architect, I want a hybrid asyncio-multiprocessing pipeline, so that I can achieve maximum performance by optimally handling both I/O-bound and CPU-bound operations.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL initialize an asyncio-based file scanner producer
2. WHEN scanning directories THEN the producer SHALL discover file paths non-blockingly using asyncio
3. WHEN files are discovered THEN they SHALL be placed into a shared multiprocessing queue
4. WHEN the system initializes THEN it SHALL create a configurable number of multiprocessing worker processes
5. WHEN workers start THEN each process SHALL initialize its own inference engine instance
6. WHEN workers are active THEN they SHALL pull batches from the shared queue in true parallel
7. WHEN processing occurs THEN it SHALL bypass Python's GIL through multiprocessing

### Requirement 2: ONNX Runtime Inference Engine

**User Story:** As a performance engineer, I want ONNX Runtime with CUDA execution provider, so that I can achieve maximum AI inference performance beyond native PyTorch.

#### Acceptance Criteria

1. WHEN the inference engine initializes THEN it SHALL use ONNX Runtime exclusively
2. WHEN CUDA is available THEN it SHALL use the CUDA Execution Provider
3. WHEN CUDA is unavailable THEN it SHALL fallback to CPU execution provider
4. WHEN processing files THEN the AI model SHALL be llama3.2:3b in ONNX format
5. WHEN inference occurs THEN it SHALL return structured JSON objects
6. WHEN JSON is returned THEN it SHALL conform to the exact schema: {"categorized_path": "SourceType/Category/Sub-Category/file.ext", "confidence": 0.95, "tags": ["tag1", "tag2", "relevant_keyword"]}
7. WHEN prompting the model THEN it SHALL instruct for JSON-only responses

### Requirement 3: Prometheus Observability Suite

**User Story:** As a system operator, I want comprehensive Prometheus metrics and monitoring, so that I can observe system health and performance in real-time.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL initialize prometheus-client library
2. WHEN metrics are enabled THEN it SHALL expose a /metrics endpoint on configurable port
3. WHEN files are processed THEN it SHALL increment sentinel_files_processed_total counter
4. WHEN inference occurs THEN it SHALL record sentinel_inference_duration_seconds histogram
5. WHEN batches are processed THEN it SHALL update sentinel_batch_size gauge
6. WHEN GPU is active THEN it SHALL monitor sentinel_gpu_utilization_percent gauge
7. WHEN GPU memory changes THEN it SHALL track sentinel_gpu_memory_used_bytes gauge
8. WHEN logs are generated THEN they SHALL remain structured JSON format

### Requirement 4: Dynamic Real-time Dashboard

**User Story:** As a system user, I want a non-blocking dashboard with live charts, so that I can monitor the Helios engine performance in real-time.

#### Acceptance Criteria

1. WHEN the UI loads THEN it SHALL connect to the /metrics endpoint
2. WHEN metrics are available THEN it SHALL display live updating charts
3. WHEN processing occurs THEN it SHALL show files/sec performance charts
4. WHEN GPU is active THEN it SHALL display GPU utilization charts
5. WHEN batches are processed THEN it SHALL show granular batch-level progress
6. WHEN the UI updates THEN it SHALL remain fully non-blocking
7. WHEN charts refresh THEN they SHALL update without user interaction

### Requirement 5: Enhanced Configuration Management

**User Story:** As a system administrator, I want comprehensive YAML configuration, so that I can tune the hybrid architecture parameters for optimal performance.

#### Acceptance Criteria

1. WHEN the system loads THEN it SHALL read from updated config.yaml
2. WHEN configuring I/O THEN it SHALL support io_workers parameter for asyncio scanning
3. WHEN configuring GPU THEN it SHALL support gpu_workers parameter for inference processes
4. WHEN configuring batches THEN it SHALL support batch_size parameter
5. WHEN configuring inference THEN it SHALL specify runtime as "onnx"
6. WHEN configuring models THEN it SHALL specify onnx_model_path location
7. WHEN configuring observability THEN it SHALL specify prometheus_port
8. WHEN parameters change THEN the system SHALL adapt without code changes

### Requirement 6: Performance Targets

**User Story:** As a performance engineer, I want specific performance benchmarks, so that I can validate the system meets enterprise-grade requirements.

#### Acceptance Criteria

1. WHEN processing 50,000 files THEN it SHALL complete within 10 minutes
2. WHEN measuring throughput THEN it SHALL achieve minimum 83 files/second
3. WHEN using GPU acceleration THEN it SHALL show measurable performance improvement over CPU
4. WHEN processing batches THEN it SHALL maintain consistent throughput
5. WHEN monitoring memory THEN it SHALL not exceed configured limits
6. WHEN scaling workers THEN performance SHALL increase proportionally up to hardware limits

### Requirement 7: Error Handling and Resilience

**User Story:** As a system operator, I want robust error handling, so that the system remains stable under various failure conditions.

#### Acceptance Criteria

1. WHEN a worker process fails THEN it SHALL restart automatically
2. WHEN ONNX model loading fails THEN it SHALL log structured error and fallback gracefully
3. WHEN GPU memory is exhausted THEN it SHALL reduce batch size automatically
4. WHEN file access is denied THEN it SHALL skip and continue processing
5. WHEN the metrics endpoint fails THEN it SHALL not affect core processing
6. WHEN configuration is invalid THEN it SHALL provide clear error messages
7. WHEN queue is full THEN it SHALL implement backpressure mechanisms