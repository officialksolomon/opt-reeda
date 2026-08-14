Pricing Application PRD
=======================

High-Level Overview
-------------------
The **Pricing Application** is a dedicated Django app managing the billing plans, limits, and user subscriptions for OptReeda. It is separated from the core user management models to maintain a clean architecture based on the DRF pattern.

Models
------
- **Plan**: Defines the available plans (e.g., Basic Listen, Pro Intelligent). Stores `features` and `limits` as JSON fields.
- **Pricing**: Defines the price structure (amount, currency, billing cycle) linked to a specific Plan.
- **Subscription**: Links a `User` to a specific `Plan` and `Pricing`.

Flowcharts
----------
.. mermaid::

    graph TD
    A[User] -->|Subscribes to| B[Subscription]
    B -->|Linked to| C[Plan]
    B -->|Billed via| D[Pricing]
    C -->|Has many| D

API Summary
-----------
The `pricing` API is fully documented using drf-spectacular.
- ``/api/plans/``: List, retrieve, and manage plans.
- ``/api/subscriptions/``: Manage active subscriptions.
