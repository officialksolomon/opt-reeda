.. My Awesome Project documentation master file, created by
   sphinx-quickstart.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to opt-reeda Documentation!
===================================

**opt-reeda** is a modern, modularized Django web application designed primarily for document ingestion, processing, and intelligent transformation. 

At its core, the system acts as a text-processing engine that takes uploaded files (such as PDFs, DOCX, and raw code snippets), cleans the text formatting, and optimizes the content for specific domains (like Educational materials or Programming concepts) to produce high-quality speech-ready output. The documents are then intelligently chunked for progressive processing or audio playback.

The architecture is heavily influenced by Django REST Framework (DRF) patterns and separates business logic into dedicated services (`PipelineService`, `ExtractionService`, `OptimizerServices`). Authentication is handled securely through custom user models and `django-allauth` integration.

Below you will find the table of contents detailing the core features, applications, and APIs of the platform:

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   app/applications
   app/documents_prd
   app/users_prd
   howto
   users



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
