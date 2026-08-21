from django.urls import path

from core.applications.documents.views import DocumentCreateView
from core.applications.documents.views import DocumentDetailView
from core.applications.documents.views import DocumentListView
from core.applications.documents.views import DocumentTableView
from core.applications.documents.views import DocumentDeleteView
from core.applications.documents.views import process_document_htmx
from core.applications.documents.views import edit_chunk_htmx
from core.applications.documents.views import record_chunk_audio_htmx
from core.applications.documents.views import manual_mode_toast_view

from core.applications.documents.views import AudioListView

app_name = "documents"

urlpatterns = [
    path("", DocumentListView.as_view(), name="document-list"),
    path("audio/", AudioListView.as_view(), name="audio-list"),
    path("table/", DocumentTableView.as_view(), name="document-table"),
    path("upload/", DocumentCreateView.as_view(), name="document-upload"),
    path("<int:pk>/", DocumentDetailView.as_view(), name="document-detail"),
    path("<int:pk>/delete/", DocumentDeleteView.as_view(), name="document-delete"),
    path("<int:pk>/process/", process_document_htmx, name="document-process"),
    path("chunks/<int:pk>/edit/", edit_chunk_htmx, name="chunk-edit"),
    path("chunks/<int:pk>/record/", record_chunk_audio_htmx, name="chunk-record"),
    path("manual-mode-toast/", manual_mode_toast_view, name="manual-mode-toast"),
]
