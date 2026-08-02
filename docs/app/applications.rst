Applications
============

The ``opt-reeda`` project is modularized into several Django applications located in the ``core/applications/`` directory. 

Users Application
-----------------

The ``users`` application provides custom user management for the project. 

* **User Model**: Extends Django's ``AbstractUser``. It overrides the default first and last names in favor of a single ``name`` field to better accommodate global name patterns.

Documents Application
---------------------

The ``documents`` application manages the core functionality for uploading, parsing, and processing text and code documents, particularly for generating optimized summaries and speech-ready text.

* **Document Model**: Represents an uploaded file or raw text input.
  
  * **Domain Types**: Supports Educational, Programming, or Auto-Detect contexts.
  * **Status**: Tracks background processing states (Pending, Processing, Completed, Failed).
  * **Code Modes**: Specifies how code blocks within documents should be handled (Skip Code, Summarize Code, Read Signature & Clean).
  * **Processing Results**: Stores raw text extraction, summary generation, and optimized speech text output.

* **DocumentChunk Model**: Large documents are broken down into manageable chunks to be processed iteratively (e.g., for AI summarization or text-to-speech conversion). Each chunk is tied back to its parent ``Document`` and stores its own ``raw_text`` and ``optimized_text``.
