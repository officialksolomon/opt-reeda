Pricing Application PRD
=======================

High-Level Overview
-------------------
The **Pricing Application** is a dedicated Django app managing the billing plans, limits, and user subscriptions for OptReeda. It is separated from the core user management models to maintain a clean architecture based on the DRF pattern.

Models
------
- **Plan**: Defines the available plans (e.g., Basic Listen, Pro Intelligent).
- **Feature**: Defines an individual feature (e.g. integer, boolean) that can be linked to a plan.
- **PlanFeature**: Links a `Plan` to a `Feature` with a specific `value` (JSON).
- **Price**: Defines the price structure (amount, currency, billing cycle) linked to a specific Plan.
- **Subscription**: Links a `User` to a specific `Price` (which determines the `Plan`).

Flowcharts
----------
.. mermaid::

    graph TD
    A[User] -->|Subscribes to| B[Subscription]
    B -->|Linked to| D[Price]
    D -->|Belongs to| C[Plan]
    C -->|Has many| E[PlanFeature]
    E -->|Linked to| F[Feature]

API Summary
-----------
The `pricing` API is fully documented using drf-spectacular.
- ``/api/plans/``: List, retrieve, and manage plans.
- ``/api/subscriptions/``: Manage active subscriptions.

Views and API Design
--------------------
Following the project's architectural guidelines, the Pricing Application exclusively uses the highest appropriate class-based abstractions:
- **API Endpoints**: Utilize Django REST Framework's `ModelViewSet` (`PlanViewSet`, `SubscriptionViewSet`) to handle CRUD semantics efficiently.
- **Web Views**: Template-rendering views, such as `PricingView`, inherit from Django's generic `TemplateView`.
