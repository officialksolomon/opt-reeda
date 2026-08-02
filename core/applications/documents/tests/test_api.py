from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from core.applications.documents.models import Document

User: Any = get_user_model()


class DocumentAPITestCase(APITestCase):
    client: Any

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="password123",  # noqa: S106
        )
        self.client.force_authenticate(user=self.user)

    def test_create_and_process_educational_document(self):
        # 1. Create document
        response = self.client.post(
            "/api/documents/",
            {
                "title": "Physics Textbook Chapter 3",
                "domain_type": Document.DomainType.EDUCATIONAL,
                "raw_text": "-------------------\nChapter 3: Work and Energy\nAs stated in Fig. 1, E = mc^2 holds true.\n(Smith et al., 2024)",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        doc_id = response.data["id"]

        # 2. Trigger process
        process_resp = self.client.post(
            f"/api/documents/{doc_id}/process/",
            {"domain_type": "educational"},
            format="json",
        )
        assert process_resp.status_code == status.HTTP_200_OK
        assert process_resp.data["status"] == Document.Status.COMPLETED
        assert (
            "Energy equals mass times the speed of light squared"
            in process_resp.data["optimized_speech_text"]
        )

        # 3. Retrieve chunks
        chunks_resp = self.client.get(f"/api/documents/{doc_id}/chunks/")
        assert chunks_resp.status_code == status.HTTP_200_OK
        assert len(chunks_resp.data) >= 1

    def test_create_and_process_programming_document(self):
        response = self.client.post(
            "/api/documents/",
            {
                "title": "Python Guide",
                "domain_type": Document.DomainType.PROGRAMMING,
                "code_mode": Document.CodeMode.SUMMARIZE,
                "raw_text": "Overview of code.\n```python\ndef calculate(x):\n    return x * 2\n```\nDone.",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        doc_id = response.data["id"]

        process_resp = self.client.post(
            f"/api/documents/{doc_id}/process/",
            format="json",
        )
        assert process_resp.status_code == status.HTTP_200_OK
        assert (
            "[Code snippet containing 3 lines of source code.]"
            in process_resp.data["optimized_speech_text"]
        )

    def test_openapi_schema_endpoint(self):
        response = self.client.get("/api/schema/")
        assert response.status_code == status.HTTP_200_OK
