
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

Background Task Abstraction
---------------------------
Heavy IO-bound tasks, such as LLM generation and Text-to-Speech processing, are handled asynchronously to prevent blocking the web request cycle.

* **Celery + Redis**: We use Celery as a robust, distributed task queue. It runs in a separate process, meaning the web request cycle is completely unblocked regardless of the WSGI/ASGI web server threading model used. Redis serves as the message broker.
* **@shared_task**: Document processing and TTS generation are decorated with Celery's `@shared_task`, allowing for configurable retries, timeouts, and asynchronous execution tracking.

Models Description
------------------

1. **Document** (Inherits ``TimeBasedModel``)
   
   * **Attributes**: ``user``, ``title``, ``file``, ``file_type``, ``domain_type``, ``status``, ``code_mode``, ``optimization_mode``.
   * **Data**: ``additional_instructions``, ``raw_text``, ``optimized_speech_text``, ``summary``, ``error_message``.
   * **Usage**: Used as the primary entry point for a user's upload. Uses ``auto_prefetch`` for optimized queries.

2. **DocumentChunk** (Inherits ``TimeBasedModel``)
   
   * **Attributes**: ``document`` (ForeignKey), ``chunk_index``, ``estimated_duration_seconds``.
   * **Data**: ``title``, ``raw_text``, ``optimized_text``.
   * **Usage**: Stores smaller pieces of the optimized document text for audio generation and playback.

3. **ChunkAudioRecording** (Inherits ``TimeBasedModel``)
   
   * **Attributes**: ``chunk`` (OneToOneField), ``audio_file``.
   * **Usage**: Stores the generated audio file for a specific document chunk.

4. **UserOptimizationExample** (Inherits ``TimeBasedModel``)
   
   * **Attributes**: ``user`` (ForeignKey), ``domain_type``.
   * **Data**: ``raw_text``, ``edited_text``.
   * **Usage**: Stores examples of how a user manually optimized text, potentially used for few-shot learning in AI mode.

5. **OptimizationRegexRule** (Inherits ``TimeBasedModel``)
   
   * **Attributes**: ``user`` (ForeignKey), ``domain_type``, ``is_active``.
   * **Data**: ``pattern``, ``replacement``.
   * **Usage**: Stores user-defined regex rules for manual text substitution.

API Summary
-----------

The Documents API uses Django REST Framework (DRF) and is fully documented via ``drf-spectacular``.

* **GET /api/documents/**: Lists all documents for the authenticated user.
* **POST /api/documents/**: Uploads a new document and kicks off the background processing pipeline.
* **POST /api/documents/{id}/process/**: Triggers document optimization. Enforces ``OptimizationMode.MANUAL`` if the user is on a 'Free' plan.
* **GET /api/documents/{id}/**: Retrieves the processing status and finalized optimized text of a specific document.
* **GET /api/documents/{id}/chunks/**: Retrieves the pagination chunks associated with a completed document.

Views and UI (HTMX)
-------------------

The web interface uses Django's generic class-based views (CBVs) combined with **HTMX** for dynamic, SPA-like interactions without full page reloads.

* **Standard Views**: Generic CBVs like `DocumentListView`, `DocumentDetailView`, `DocumentCreateView`, and `DocumentDeleteView` are used for standard page rendering and form handling.
* **HTMX Views**: Certain interactive elements are handled by specialized function-based views (FBVs) that return HTML partials rather than full page templates:
  * `process_document_htmx`: Handles document processing initiation and returns an updated list of document chunks.
  * `edit_chunk_htmx`: Handles both the display of a chunk's edit form and the inline POST submission of the optimized text.
  * `record_chunk_audio_htmx`: Handles asynchronous audio file uploads for specific chunks.

Pending Implementation
--------------------

* **Gemini API Key**: We have not yet added the actual Gemini API key to make the Gemini LLM work (AI Mode). This is one of the final pieces of the puzzle we need to take care of before we can say this project is complete.

