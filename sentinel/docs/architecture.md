# Architecture Overview

Sentinel follows a **layered, modular architecture** that separates the UI, core processing, AI inference, and data persistence.

```mermaid
flowchart TD
    subgraph UI
        A[PyQt6 MainWindow]
        B[ReviewDialog]
    end
    subgraph Core
        C[File Scanner]
        D[Content Extractor]
        E[Integrity Checker]
    end
    subgraph AI
        F[Prompt Builder]
        G[Inference Engine]
    end
    subgraph Persistence
        H[DatabaseManager(SQLAlchemy)]
    end
    A --select dir--> C
    C --metadata--> D
    D --text--> F
    F --prompt--> G
    G --suggestion--> B
    B --feedback--> H
    C --metadata--> H
    G --results--> H
```

## Layers

1. **UI Layer (`app/ui`)**
   * Built with **PyQt6**.
   * Handles user interactions, progress updates, and review workflows.

2. **Core Layer (`app/core`)**
   * `file_scanner.py` – Recursively discovers files, collects metadata.
   * `content_extractor.py` – Converts files to plain-text using PyMuPDF, python-docx, pytesseract, etc.
   * `integrity_checker.py` – Computes/validates checksums.

3. **AI Layer (`app/ai`)**
   * `prompt_builder.py` – Formats metadata/content into a prompt.
   * `inference_engine.py` – Currently heuristic; pluggable for LLM backends.

4. **Persistence Layer (`app/db`)**
   * `database_manager.py` – SQLAlchemy ORM storing files, inferences, and user feedback.

5. **Pipeline (`app/pipeline.py`)**
   * Orchestrates Core → AI → DB and feeds results back to the UI.

## Threading Model

* Heavy work runs in `AnalysisWorker` (QThread) to keep UI responsive.
* `closeEvent` ensures the worker is terminated gracefully on exit.

## Configuration

* `config/config.yaml` – runtime options such as backend mode and default paths.

## Extensibility

* Swap in a real LLM by implementing `InferenceEngine.analyze`.
* Add new extractors by extending `content_extractor.extract_content`.
* Data migrations via SQLAlchemy’s metadata. 