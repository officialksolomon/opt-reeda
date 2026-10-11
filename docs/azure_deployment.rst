Azure Deployment Guide
======================

This guide documents the automated deployment architecture for **opt-reeda** on **Microsoft Azure**, using Infrastructure-as-Code (Bicep) and Azure Container Apps.

Overview
--------

Similar to how ``render.yaml`` orchestrates resources on Render, the Azure deployment is declaratively defined using:

* ``azure.yaml``: Defines services and container configurations for Azure Developer CLI (``azd``).
* ``infra/main.bicep``: Defines all cloud resources, including PostgreSQL Flexible Server, Azure Cache for Redis, Azure Container Registry (ACR), and Azure Container Apps (ACA).
* ``infra/main.parameters.json``: Stores default environment parameters and deployment options.

Architecture
------------

.. code-block:: text

    Internet
       │ (HTTPS)
       ▼
    Azure Container Apps Ingress (:5000)
       │
       ▼
    optreeda-web (Gunicorn + Django) ──────┐
       │                                   │
       ▼                                   ▼
    PostgreSQL Flexible Server (v15)    Azure Cache for Redis (TLS :6380)
       ▲                                   ▲
       │                                   │
    optreeda-worker (Celery, optional) ────┘

Quick Deployment Options
------------------------

Option A: Using Azure Developer CLI (azd) - Recommended
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Install the Azure Developer CLI:
   
   .. code-block:: bash

       winget install microsoft.azd

2. Log in and deploy:

   .. code-block:: bash

       azd auth login
       azd up

3. ``azd up`` provisions the infrastructure, builds the production Docker container, configures environment secrets, and prints the live URL.

Option B: Using Azure CLI (az)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Create a Resource Group:

   .. code-block:: bash

       az group create --name rg-optreeda-prod --location eastus

2. Deploy the Bicep template:

   .. code-block:: bash

       az deployment group create \
         --resource-group rg-optreeda-prod \
         --template-file infra/main.bicep \
         --parameters infra/main.parameters.json

3. Build and push the Docker image to the created Azure Container Registry (ACR):

   .. code-block:: bash

       az acr build --registry <acrName> --image optreeda:latest --file Dockerfile.prod .

Environment Variables Managed
-----------------------------

* ``DATABASE_URL``: Injected dynamically with SSL enabled (``sslmode=require``).
* ``REDIS_URL``: Injected dynamically with TLS enabled (``rediss://``).
* ``DJANGO_SETTINGS_MODULE``: Set to ``config.settings.production``.
* ``DJANGO_SECRET_KEY``: Automatically generated cryptographically secure secret.
* ``DJANGO_CSRF_TRUSTED_ORIGINS``: Pre-configured for ``https://*.azurecontainerapps.io``.
* ``CELERY_TASK_ALWAYS_EAGER``: Set to ``False`` if Celery worker is deployed, ``True`` if single-container.
