Users App PRD
=============

Product Requirements Document
-----------------------------

The **Users** application manages authentication, authorization, and user profiles for the ``opt-reeda`` project. It is built to seamlessly integrate with ``django-allauth`` to support both local password-based accounts and third-party social logins.

**Key Objectives:**
* Override the default Django ``AbstractUser`` to support a single, unified ``name`` field instead of localized ``first_name`` and ``last_name`` fields, catering to a global user base.
* Ensure all new users are routed correctly through the standard or social sign-up forms.
* Expose user profile data through standard DRF API endpoints.

Architecture Diagram
--------------------

The following entity-relationship diagram shows how the custom User model relates to the broader authentication systems:

.. mermaid::

    erDiagram
        USER {
            int id PK
            string username
            string email
            string name "Unified Name Field"
            boolean is_active
            datetime date_joined
        }
        SOCIALACCOUNT {
            int id PK
            int user_id FK
            string provider
            string uid
            json extra_data
        }
        USER ||--o{ SOCIALACCOUNT : "authenticates via"

Models Description
------------------

1. **User** (Inherits ``django.contrib.auth.models.AbstractUser``)
   
   * **Attributes**: ``name`` (CharField). 
   * **Omissions**: ``first_name`` and ``last_name`` are explicitly set to ``None``.
   * **Usage**: The default authentication model defined in ``settings.AUTH_USER_MODEL``.

API Summary
-----------

The Users API exposes profile and authentication endpoints.

* **GET /api/users/me/**: Retrieves the current authenticated user's profile information.
* **PATCH /api/users/me/**: Allows updating the user's ``name`` and other profile fields.
* **Authentication**: Handled primarily via standard token or session auth integrations configured at the project level, utilizing ``django-allauth`` underneath.
