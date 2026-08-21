from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView

from core.applications.documents.forms import DocumentForm
from core.applications.documents.models import Document
from core.applications.documents.models import DocumentChunk
from core.applications.documents.services import PipelineService
from core.applications.documents.services import UserOptimizationExampleService
from core.applications.pricing.querysets import user_has_feature
from core.helpers.enums import OptimizationMode


class DocumentFilterMixin:
    """Mixin that applies search, filter, and sort params from the request to a queryset."""

    def get_filtered_queryset(self, base_queryset):
        return base_queryset.apply_filters(
            q=self.request.GET.get("q", "").strip(),
            status=self.request.GET.get("status", ""),
            domain_type=self.request.GET.get("domain_type", ""),
            sort=self.request.GET.get("sort", ""),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Document.Status.choices
        context["domain_choices"] = Document.DomainType.choices
        context["current_q"] = self.request.GET.get("q", "")
        context["current_status"] = self.request.GET.get("status", "")
        context["current_domain_type"] = self.request.GET.get("domain_type", "")
        context["current_sort"] = self.request.GET.get("sort", "")
        return context


class DocumentListView(LoginRequiredMixin, DocumentFilterMixin, ListView):
    model = Document
    template_name = "documents/document_list.html"
    context_object_name = "documents"

    def get_queryset(self):
        qs = Document.objects.for_user(self.request.user)
        qs = self.get_filtered_queryset(qs)
        # When no filters are active, cap the dashboard at 6 documents.
        # When the user is actively searching or filtering, show all results.
        has_filters = any(
            self.request.GET.get(k) for k in ["q", "status", "domain_type", "sort"]
        )
        if not has_filters:
            return qs[:6]
        return qs


class DocumentTableView(LoginRequiredMixin, DocumentFilterMixin, ListView):
    model = Document
    template_name = "documents/document_table.html"
    context_object_name = "documents"

    def get_queryset(self):
        qs = Document.objects.for_user(self.request.user)
        return self.get_filtered_queryset(qs)


class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = Document
    success_url = reverse_lazy("documents:document-table")

    def get_queryset(self):
        # Users may only delete their own documents.
        return super().get_queryset().for_user(self.request.user)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.headers.get("HX-Request") or request.META.get("HTTP_HX_REQUEST"):
            return HttpResponse("")
        return HttpResponseRedirect(self.get_success_url())


class DocumentCreateView(CreateView):
    model = Document
    form_class = DocumentForm
    template_name = "documents/document_form.html"
    success_url = reverse_lazy("documents:document-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_success_url(self):
        if not self.request.user.is_authenticated:
            from django.urls import reverse  # noqa: PLC0415

            return (
                reverse("account_login")
                + f"?next={reverse('documents:document-detail', kwargs={'pk': self.object.pk})}"
            )
        return super().get_success_url()

    def form_valid(self, form):
        if self.request.user.is_authenticated:
            form.instance.user = self.request.user
        else:
            form.instance.optimization_mode = OptimizationMode.MANUAL

        response = super().form_valid(form)
        # Only run the pipeline immediately for authenticated users.
        if self.request.user.is_authenticated:
            PipelineService.process_document(self.object)
        return response


class DocumentDetailView(DetailView):
    model = Document
    template_name = "documents/document_detail.html"
    context_object_name = "document"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["chunks"] = self.object.chunks.ordered()
        context["has_edit_feature"] = user_has_feature(
            self.request.user, "edit_optimized_text"
        )
        return context


def process_document_htmx(request, pk):
    document = get_object_or_404(Document, pk=pk)

    # Determine whether this user lacks the LLM feature before processing.
    manual_mode_forced = not user_has_feature(request.user, "llm_optimization")

    if (
        document.status == Document.Status.PENDING
        and request.user.is_authenticated
    ):
        PipelineService.process_document(document)

    chunks = document.chunks.ordered()
    has_edit_feature = user_has_feature(request.user, "edit_optimized_text")
    response = render(
        request,
        "documents/partials/chunk_list.html",
        {
            "document": document,
            "chunks": chunks,
            "has_edit_feature": has_edit_feature,
            "manual_mode_forced": manual_mode_forced,
        },
    )
    # Priority order: manual_mode_forced > llm_fallback (both use offline mode
    # but for different reasons — different toast messages).
    if document.status == Document.Status.COMPLETED:
        if manual_mode_forced:
            response["HX-Trigger"] = "manualModeForced"
        elif getattr(document, "_llm_fallback_used", False):
            response["HX-Trigger"] = "llmFallbackUsed"
    return response


@login_required
def edit_chunk_htmx(request, pk):
    chunk = get_object_or_404(DocumentChunk, pk=pk, document__user=request.user)
    has_edit_feature = user_has_feature(request.user, "edit_optimized_text")

    if request.method == "POST":
        if has_edit_feature:
            new_text = request.POST.get("optimized_text", "").strip()
            if new_text and new_text != chunk.optimized_text and new_text != chunk.raw_text:
                # Capture the meaningful edit for LLM few-shot learning and regex generation
                UserOptimizationExampleService.capture_example(
                    user=request.user,
                    domain_type=chunk.document.domain_type,
                    raw_text=chunk.raw_text,
                    edited_text=new_text,
                )
                chunk.optimized_text = new_text
                chunk.save()
        return render(
            request,
            "documents/partials/chunk_optimized_display.html",
            {"chunk": chunk, "has_edit_feature": has_edit_feature},
        )

    if has_edit_feature:
        return render(
            request,
            "documents/partials/chunk_edit_form.html",
            {"chunk": chunk},
        )
    return render(
        request,
        "documents/partials/chunk_optimized_display.html",
        {"chunk": chunk, "has_edit_feature": has_edit_feature},
    )


@login_required
def record_chunk_audio_htmx(request, pk):
    from core.applications.documents.models import ChunkAudioRecording  # noqa: PLC0415

    chunk = get_object_or_404(DocumentChunk, pk=pk, document__user=request.user)
    has_edit_feature = user_has_feature(request.user, "edit_optimized_text")

    if request.method == "POST":
        from core.applications.documents.tts import get_tts_provider  # noqa: PLC0415

        provider = get_tts_provider()
        audio_content = provider.generate_audio(chunk.optimized_text)
        audio_content.name = (
            f"document_{chunk.document.pk}_chunk_{chunk.chunk_index}.mp3"
        )

        recording, _created = ChunkAudioRecording.objects.get_or_create(chunk=chunk)
        recording.audio_file.save(audio_content.name, audio_content, save=True)
        chunk.refresh_from_db()

    return render(
        request,
        "documents/partials/chunk_optimized_display.html",
        {"chunk": chunk, "has_edit_feature": has_edit_feature},
    )


class AudioListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = "documents/audio_list.html"
    context_object_name = "documents"

    def get_queryset(self):
        return Document.objects.for_user(self.request.user).with_audio()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_edit_feature"] = user_has_feature(
            self.request.user, "edit_optimized_text"
        )
        return context


def manual_mode_toast_view(request):
    """
    Renders the manual-mode upgrade toast partial.
    Called via htmx.ajax() when the server fires the `manualModeForced`
    HX-Trigger after completing document processing in offline mode.
    """
    return render(request, "documents/partials/manual_mode_toast.html")


def llm_fallback_toast_view(request):
    """
    Renders the LLM-fallback toast partial.
    Called via htmx.ajax() when the server fires the `llmFallbackUsed`
    HX-Trigger after the LLM optimizer exhausted all retries and fell
    back to offline mode mid-processing.
    """
    return render(request, "documents/partials/llm_fallback_toast.html")
