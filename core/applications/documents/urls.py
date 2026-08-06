from django.urls import path

from core.applications.documents.views import DocumentCreateView
from core.applications.documents.views import DocumentDetailView
from core.applications.documents.views import DocumentListView
from core.applications.documents.views import process_document_htmx

app_name = "documents"

urlpatterns = [
    path("", DocumentListView.as_view(), name="document-list"),
    path("upload/", DocumentCreateView.as_view(), name="document-upload"),
    path("<int:pk>/", DocumentDetailView.as_view(), name="document-detail"),
    path("<int:pk>/process/", process_document_htmx, name="document-process"),
]
