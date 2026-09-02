from django.urls import path

from core.applications.documents.views import DocumentCreateView
from core.applications.documents.views import DocumentDetailView
from core.applications.documents.views import DocumentListView
from core.applications.documents.views import DocumentTableView
from core.applications.documents.views import DocumentDeleteView
from core.applications.documents.views import ProcessDocumentHTMXView
from core.applications.documents.views import EditChunkHTMXView
from core.applications.documents.views import RecordChunkAudioHTMXView
from core.applications.documents.views import manual_mode_toast_view
from core.applications.documents.views import llm_fallback_toast_view

from core.applications.documents.views import AudioListView

app_name = "documents"

urlpatterns = [
    path("", DocumentListView.as_view(), name="document-list"),
    path("audio/", AudioListView.as_view(), name="audio-list"),
    path("table/", DocumentTableView.as_view(), name="document-table"),
    path("upload/", DocumentCreateView.as_view(), name="document-upload"),
    path("<int:pk>/", DocumentDetailView.as_view(), name="document-detail"),
    path("<int:pk>/delete/", DocumentDeleteView.as_view(), name="document-delete"),
    path("<int:pk>/process/", ProcessDocumentHTMXView.as_view(), name="document-process"),
    path("chunks/<int:pk>/edit/", EditChunkHTMXView.as_view(), name="chunk-edit"),
    path("chunks/<int:pk>/record/", RecordChunkAudioHTMXView.as_view(), name="chunk-record"),
    path("manual-mode-toast/", manual_mode_toast_view, name="manual-mode-toast"),
    path("llm-fallback-toast/", llm_fallback_toast_view, name="llm-fallback-toast"),
]
