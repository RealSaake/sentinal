# Sentinel 2.0: The Agentic Architecture - Requirements

## Project Overview

Sentinel 2.0 represents a fundamental re-architecture of the file organization system, transforming it from a monolithic application into a sophisticated, transparent, and user-empowered agentic system.

## Core Principles

### 1. Radical Transparency
- **Glass Engine**: Users must see exactly how the system works at all times
- **Real-time Visibility**: Live monitoring of all parallel processes and AI decisions
- **Undeniable Proof**: Visual evidence of multiprocessing, GPU utilization, and AI reasoning
- **No Black Boxes**: Every decision and operation must be explainable and visible

### 2. User Empowerment
- **User as Pilot**: Users control the system, not the other way around
- **Intelligent Defaults**: System provides smart recommendations but allows full customization
- **Fine-grained Control**: Granular control over analysis parameters and AI behavior
- **Final Authority**: Users have final say on all file organization decisions

### 3. Agentic Intelligence
- **Multi-Agent System**: Replace monolithic AI with specialized agent team
- **Collaborative AI**: Agents work together to produce superior results
- **Consistent Output**: Structured, reliable, and predictable AI responses
- **Specialized Expertise**: Each agent has a specific role and optimized prompt

## Functional Requirements

### Phase 1: Scout & Pre-Flight System

#### 1.1 Directory Scout Module
- **FR-1.1.1**: High-speed directory traversal without reading file contents
- **FR-1.1.2**: Collect comprehensive metadata: file count, size, extensions, problematic files
- **FR-1.1.3**: Parallel scanning with configurable worker threads
- **FR-1.1.4**: Skip system directories and hidden files (configurable)
- **FR-1.1.5**: Generate detailed histogram of file extensions
- **FR-1.1.6**: Identify large files above configurable threshold
- **FR-1.1.7**: Detect files without extensions or with access issues

#### 1.2 Performance Forecaster
- **FR-1.2.1**: Analyze system hardware capabilities (CPU, GPU, RAM)
- **FR-1.2.2**: Generate accurate ETA predictions based on scout data
- **FR-1.2.3**: Provide multiple strategy options with trade-offs
- **FR-1.2.4**: Calculate confidence scores for predictions
- **FR-1.2.5**: Identify potential bottlenecks (CPU, GPU, Memory, Storage)
- **FR-1.2.6**: Learn from historical performance data
- **FR-1.2.7**: Warn about potential issues before processing

#### 1.3 Pre-Flight Check UI
- **FR-1.3.1**: Modal pre-flight window before main analysis
- **FR-1.3.2**: Display scout findings with visual charts
- **FR-1.3.3**: Show forecasted ETA with confidence indicator
- **FR-1.3.4**: Present strategy selection with clear trade-offs
- **FR-1.3.5**: Allow custom parameter adjustment with validation
- **FR-1.3.6**: Provide strategy comparison table
- **FR-1.3.7**: Show warnings and recommendations clearly

#### 1.4 Strategy Configuration
- **FR-1.4.1**: Predefined strategies: Speed Demon, Balanced, Deep Analysis
- **FR-1.4.2**: Custom strategy creation with parameter validation
- **FR-1.4.3**: Real-time parameter impact preview
- **FR-1.4.4**: Save and load custom strategy presets
- **FR-1.4.5**: Strategy recommendation based on system and data characteristics

### Phase 2: Agentic AI Core

#### 2.1 Agent Orchestrator
- **FR-2.1.1**: Manage team of specialized AI agents
- **FR-2.1.2**: Route tasks to appropriate agents based on file type and context
- **FR-2.1.3**: Coordinate multi-step agent workflows
- **FR-2.1.4**: Aggregate and validate agent outputs
- **FR-2.1.5**: Handle agent failures and retries gracefully

#### 2.2 Categorization Agent
- **FR-2.2.1**: Determine high-level file categories (Code, Documents, Media, System, Logs)
- **FR-2.2.2**: Use file metadata, path information, and extension analysis
- **FR-2.2.3**: Provide confidence scores for categorization decisions
- **FR-2.2.4**: Handle edge cases and ambiguous files
- **FR-2.2.5**: Learn from user corrections and feedback

#### 2.3 Tagging Agent
- **FR-2.3.1**: Extract relevant keywords and tags from file content or names
- **FR-2.3.2**: Analyze file content when necessary for accurate tagging
- **FR-2.3.3**: Generate contextual tags based on file relationships
- **FR-2.3.4**: Avoid tagging system files and binaries inappropriately
- **FR-2.3.5**: Provide structured tag hierarchies

#### 2.4 Naming Agent
- **FR-2.4.1**: Enforce consistent naming conventions across all files
- **FR-2.4.2**: Generate structured paths based on category and tags
- **FR-2.4.3**: Ensure files of same type get identical path structures
- **FR-2.4.4**: Handle naming conflicts and duplicates intelligently
- **FR-2.4.5**: Respect user-defined naming rules and preferences

#### 2.5 Confidence Agent
- **FR-2.5.1**: Evaluate outputs from all other agents
- **FR-2.5.2**: Assign final confidence scores to complete results
- **FR-2.5.3**: Flag low-confidence results for user review
- **FR-2.5.4**: Identify inconsistencies between agent outputs
- **FR-2.5.5**: Provide explanations for confidence assessments

### Phase 3: Glass Engine - Transparency UI

#### 3.1 Live Worker Dashboard
- **FR-3.1.1**: Real-time grid of worker process cards
- **FR-3.1.2**: Display worker ID, status, batch size, and throughput for each worker
- **FR-3.1.3**: Visual proof of parallel processing in action
- **FR-3.1.4**: Color-coded status indicators (Idle, Processing, Waiting, Error)
- **FR-3.1.5**: Click-to-expand detailed worker information

#### 3.2 Advanced Progress System
- **FR-3.2.1**: Multi-layered progress bars (Scouting, Analyzing, Finalizing)
- **FR-3.2.2**: Dynamic ETA updates based on real-time throughput
- **FR-3.2.3**: Progress breakdown by file type and category
- **FR-3.2.4**: Bottleneck identification and visualization
- **FR-3.2.5**: Historical progress comparison

#### 3.3 Interactive Log Viewer
- **FR-3.3.1**: Real-time log streaming with filtering capabilities
- **FR-3.3.2**: Filter by worker ID, log level, and component
- **FR-3.3.3**: Search functionality across all log messages
- **FR-3.3.4**: Export and save log segments
- **FR-3.3.5**: Highlight errors and warnings prominently

#### 3.4 AI Decision Transparency
- **FR-3.4.1**: Show AI reasoning for each file decision
- **FR-3.4.2**: Display agent collaboration workflow
- **FR-3.4.3**: Confidence score visualization with explanations
- **FR-3.4.4**: Allow users to see and understand AI prompts
- **FR-3.4.5**: Track and display AI model performance metrics

### Phase 4: Production Hardening

#### 4.1 Session Management
- **FR-4.1.1**: Pause running analysis with state preservation
- **FR-4.1.2**: Resume paused analysis from exact stopping point
- **FR-4.1.3**: Save analysis state to database automatically
- **FR-4.1.4**: Handle unexpected shutdowns gracefully
- **FR-4.1.5**: Multiple concurrent session support

#### 4.2 Results Review System
- **FR-4.2.1**: Post-analysis review screen with all suggestions
- **FR-4.2.2**: Side-by-side comparison of original vs suggested paths
- **FR-4.2.3**: Bulk approval and rejection capabilities
- **FR-4.2.4**: Individual result override functionality
- **FR-4.2.5**: Confidence-based filtering and sorting

#### 4.3 Health Check System
- **FR-4.3.1**: Pre-analysis comprehensive system health check
- **FR-4.3.2**: Disk space validation and warnings
- **FR-4.3.3**: GPU driver and memory verification
- **FR-4.3.4**: Model file integrity validation
- **FR-4.3.5**: Clear, actionable error messages for all failures

## Non-Functional Requirements

### Performance Requirements
- **NFR-P.1**: Scout must complete directory analysis in under 30 seconds for 100K files
- **NFR-P.2**: Performance forecaster must generate predictions in under 5 seconds
- **NFR-P.3**: Pre-flight check complete workflow must finish in under 60 seconds
- **NFR-P.4**: UI must remain responsive during all operations (< 100ms response)
- **NFR-P.5**: Agent system must maintain throughput parity with monolithic approach

### Reliability Requirements
- **NFR-R.1**: System must handle worker process failures without data loss
- **NFR-R.2**: Session pause/resume must work 99.9% of the time
- **NFR-R.3**: Pre-flight predictions must be accurate within 20% margin
- **NFR-R.4**: Agent system must produce consistent results across runs
- **NFR-R.5**: Health checks must catch 95% of potential issues before processing

### Usability Requirements
- **NFR-U.1**: Pre-flight check must be completable by novice users in under 2 minutes
- **NFR-U.2**: All AI decisions must be explainable in plain English
- **NFR-U.3**: Worker dashboard must be interpretable without technical knowledge
- **NFR-U.4**: Error messages must provide clear next steps for resolution
- **NFR-U.5**: Strategy selection must clearly communicate trade-offs

### Scalability Requirements
- **NFR-S.1**: System must handle directories with up to 1M files
- **NFR-S.2**: Agent system must scale to 16+ parallel workers
- **NFR-S.3**: UI must handle real-time updates for 100+ concurrent operations
- **NFR-S.4**: Database must support concurrent access from all workers
- **NFR-S.5**: Memory usage must remain stable during long-running operations

## Technical Constraints

### Technology Stack
- **TC-1**: Python 3.9+ for all backend components
- **TC-2**: PyQt6 for all UI components
- **TC-3**: SQLite for session and results storage
- **TC-4**: Prometheus for metrics and monitoring
- **TC-5**: ONNX Runtime for AI inference

### Integration Requirements
- **TC-6**: Must integrate with existing Helios architecture
- **TC-7**: Must maintain backward compatibility with current file formats
- **TC-8**: Must support both CPU and GPU execution modes
- **TC-9**: Must work on Windows, macOS, and Linux
- **TC-10**: Must handle network-attached storage and cloud drives

## Success Criteria

### Phase 1 Success Criteria
- [ ] Scout can analyze 100K files in under 30 seconds
- [ ] Performance forecaster predictions accurate within 20%
- [ ] Pre-flight UI allows strategy selection in under 2 minutes
- [ ] Custom strategy validation prevents invalid configurations
- [ ] System provides clear warnings for potential issues

### Phase 2 Success Criteria
- [ ] Agent system produces more consistent results than monolithic approach
- [ ] Multi-agent workflow completes without performance degradation
- [ ] Agent decisions are explainable and traceable
- [ ] Confidence scoring accurately reflects result quality
- [ ] Agent failures are handled gracefully without system impact

### Phase 3 Success Criteria
- [ ] Worker dashboard provides real-time visibility into all processes
- [ ] Users can understand system operation without technical knowledge
- [ ] Log viewer enables effective troubleshooting and monitoring
- [ ] Progress system provides accurate real-time updates
- [ ] AI decision transparency builds user trust and understanding

### Phase 4 Success Criteria
- [ ] Session management works reliably across all scenarios
- [ ] Results review system enables confident decision-making
- [ ] Health checks prevent 95% of runtime issues
- [ ] System handles edge cases and failures gracefully
- [ ] Production deployment is stable and maintainable

## Risk Assessment

### High-Risk Items
- **R-H.1**: Agent system complexity may impact performance
- **R-H.2**: Real-time UI updates may cause performance bottlenecks
- **R-H.3**: Session state management complexity
- **R-H.4**: Multi-agent coordination reliability

### Medium-Risk Items
- **R-M.1**: Performance forecasting accuracy
- **R-M.2**: UI responsiveness during heavy processing
- **R-M.3**: Cross-platform compatibility issues
- **R-M.4**: Database concurrency handling

### Mitigation Strategies
- Extensive performance testing and optimization
- Incremental development with continuous validation
- Comprehensive error handling and recovery mechanisms
- User feedback integration throughout development process