from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.http import HttpResponse

from core.applications.documents.forms import DocumentForm
from core.applications.documents.models import Document
from core.applications.documents.services import PipelineService


from django.contrib.auth.mixins import LoginRequiredMixin

class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = "documents/document_list.html"
    context_object_name = "documents"

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user).order_by("-created_at")


class DocumentCreateView(CreateView):
    model = Document
    form_class = DocumentForm
    template_name = "documents/document_form.html"
    success_url = reverse_lazy("documents:document-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        if self.request.user.is_authenticated:
            form.instance.user = self.request.user
        response = super().form_valid(form)
        # We can trigger pipeline processing immediately or let the user click a button later.
        # Let's trigger it immediately for convenience
        PipelineService.process_document(self.object)
        return response


class DocumentDetailView(DetailView):
    model = Document
    template_name = "documents/document_detail.html"
    context_object_name = "document"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Prefetch chunks so we can render them in the template
        context["chunks"] = self.object.chunks.all().order_by("chunk_index")
        return context

def process_document_htmx(request, pk):
    document = get_object_or_404(Document, pk=pk)
    # Re-process if needed
    PipelineService.process_document(document)
    chunks = document.chunks.all().order_by("chunk_index")
    return render(request, "documents/partials/chunk_list.html", {"document": document, "chunks": chunks})
