
Documents App PRD
=================

Product Requirements Document
-----------------------------

The **Documents** application is the core processing engine for ``opt-reeda``. Its primary purpose is to ingest user-uploaded documents (or raw text), clean them of formatting noise (e.g., page numbers, excessive dots), optimize the text based on its domain (Educational vs. Programming), and split the optimized text into manageable chunks that can be converted to speech or summarized.

**Key Objectives:**
* Provide a unified interface for extracting text from PDF, DOCX, and TXT files.
* Handle specialized formatting constraints in academic texts (e.g., converting "Fig. 1" to "Figure 1", standardizing math formulas like "E=mc^2").
* Process programming code blocks with configurable playback behaviors (Skip, Summarize, Read Signature).
* Efficiently divide large processed texts into timestamped chunks.
* Support a multi-tier optimization strategy where 'Free' users are processed via a sophisticated Manual mode, while Premium users utilize an AI (LLM) mode for contextual rewriting.

Architecture and Processing Pipeline
------------------------------------

The application heavily relies on the ``PipelineService`` to orchestrate document ingestion. Below is the Mermaid architectural diagram detailing the data flow:

.. mermaid::

    flowchart TD
        A[Document Uploaded] --> B{raw_text exists?}
        B -- No --> C[FileExtractionService]
        B -- Yes --> D[BaseCleanerService]
        C --> D
        D --> E{DomainType}
        E -- AUTO_DETECT --> F[Auto Detect Heuristics]
        F -- Educational --> K[Create Chunks]
        F -- Programming --> K[Create Chunks]
        E -- Educational --> K
        E -- Programming --> K
        K --> L{Optimization Mode}
        L -- AI Mode --> G[LLMOptimizerService]
        L -- Manual Mode --> H[ManualOptimizerService]
        G --> I[Save optimized_speech_text]
        H --> I
        I --> J[Document Status: Completed]

Models Description
------------------

1. **Document** (Inherits ``TimeBasedModel``)
   
   * **Attributes**: ``title``, ``file``, ``domain_type``, ``status``, ``code_mode``, ``optimization_mode``.
   * **Data**: ``raw_text``, ``optimized_speech_text``, ``summary``, ``error_message``.
   * **Usage**: Used as the primary entry point for a user's upload. Uses ``auto_prefetch`` for optimized queries.

2. **DocumentChunk** (Inherits ``TimeBasedModel``)
   
   * **Attributes**: ``document`` (ForeignKey), ``chunk_index``, ``estimated_duration_seconds``.
   * **Data**: ``raw_text``, ``optimized_text``.
   * **Usage**: Stores smaller pieces of the optimized document text for audio generation and playback.

API Summary
-----------

The Documents API uses Django REST Framework (DRF) and is fully documented via ``drf-spectacular``.

* **GET /api/documents/**: Lists all documents for the authenticated user.
* **POST /api/documents/**: Uploads a new document and kicks off the background processing pipeline.
* **POST /api/documents/{id}/process/**: Triggers document optimization. Enforces ``OptimizationMode.MANUAL`` if the user is on a 'Free' plan.
* **GET /api/documents/{id}/**: Retrieves the processing status and finalized optimized text of a specific document.
* **GET /api/documents/{id}/chunks/**: Retrieves the pagination chunks associated with a completed document.
