from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views import View
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

from core.applications.documents.forms import DocumentForm
from core.applications.documents.models import Document
from core.applications.documents.models import DocumentChunk
from core.applications.documents.services import PipelineService
from core.applications.documents.services import UserOptimizationExampleService
from core.applications.documents.tasks import generate_chunk_audio_task
from core.applications.pricing.querysets import user_has_feature, consume_free_try
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
        import time
        print(f"[{time.time()}] About to call delay")
        if self.request.user.is_authenticated:
            from core.applications.documents.tasks import process_document_task
            process_document_task.delay(self.object.id)
        print(f"[{time.time()}] Delay called, returning response")
        return response


class DocumentDetailView(DetailView):
    model = Document
    template_name = "documents/document_detail.html"
    context_object_name = "document"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        chunks_list = self.object.chunks.ordered()
        paginator = Paginator(chunks_list, 20)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context["chunks"] = page_obj
        context["is_paginated"] = page_obj.has_other_pages()
        context["page_obj"] = page_obj
        
        context["has_edit_feature"] = user_has_feature(
            self.request.user, "edit_optimized_text"
        )
        return context


@method_decorator(ratelimit(key="user_or_ip", rate="5/m", block=True), name="dispatch")
class ProcessDocumentHTMXView(DetailView):
    model = Document
    template_name = "documents/partials/chunk_list.html"
    context_object_name = "document"

    def get(self, request, *args, **kwargs):
        return self._process(request)

    def post(self, request, *args, **kwargs):
        return self._process(request)

    def _process(self, request):
        document = self.get_object()

        # Determine whether this user lacks the LLM feature before processing.
        has_llm_feature = user_has_feature(request.user, "llm_optimization")
        manual_mode_forced = not has_llm_feature

        if (
            document.status == Document.Status.PENDING
            and request.user.is_authenticated
        ):
            # Mark as processing so UI updates immediately
            document.status = Document.Status.PROCESSING
            document.save(update_fields=["status"])
            
            # Consume a try if they used AI optimization and aren't subscribed
            if document.optimization_mode == "ai" and not manual_mode_forced:
                consumed = consume_free_try(request.user, "llm_optimization")
                if consumed and request.user.free_tries_used >= 20:
                    messages.warning(request, "You have exhausted your 20 free tries! Please upgrade your plan to continue using premium features.")
            
            from core.applications.documents.tasks import process_document_task
            process_document_task.delay(document.id)

        chunks_list = document.chunks.ordered()
        paginator = Paginator(chunks_list, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        has_edit_feature = user_has_feature(request.user, "edit_optimized_text")
        response = render(
            request,
            self.template_name,
            {
                "document": document,
                "chunks": page_obj,
                "is_paginated": page_obj.has_other_pages(),
                "page_obj": page_obj,
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


@method_decorator(ratelimit(key="user", rate="15/m", block=True), name="dispatch")
class ChunkDisplayHTMXView(LoginRequiredMixin, View):
    """Returns the HTMX partial for a single chunk's optimized display."""

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        chunk = get_object_or_404(
            DocumentChunk.objects.select_related("document"),
            pk=pk,
            document__user=request.user,
        )
        has_edit_feature = user_has_feature(request.user, "manual_edit")
        return render(
            request,
            "documents/partials/chunk_optimized_display.html",
            {"chunk": chunk, "has_edit_feature": has_edit_feature},
        )


@method_decorator(ratelimit(key="user", rate="15/m", block=True), name="dispatch")
class EditChunkHTMXView(LoginRequiredMixin, DetailView):
    model = DocumentChunk

    def get_queryset(self):
        return super().get_queryset().filter(document__user=self.request.user)

    def get(self, request, *args, **kwargs):
        chunk = self.get_object()
        has_edit_feature = user_has_feature(request.user, "edit_optimized_text")

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

    def post(self, request, *args, **kwargs):
        chunk = self.get_object()
        has_edit_feature = user_has_feature(request.user, "edit_optimized_text")

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


class RecordChunkAudioHTMXView(LoginRequiredMixin, DetailView):
    model = DocumentChunk

    def get_queryset(self):
        return super().get_queryset().filter(document__user=self.request.user)

    def get(self, request, *args, **kwargs):
        chunk = self.get_object()
        has_edit_feature = user_has_feature(request.user, "edit_optimized_text")
        has_tts_feature = user_has_feature(request.user, "tts_generation")
        return render(
            request,
            "documents/partials/chunk_optimized_display.html",
            {"chunk": chunk, "has_edit_feature": has_edit_feature, "has_tts_feature": has_tts_feature},
        )

    def post(self, request, *args, **kwargs):
        from django.http import HttpResponseForbidden

        chunk = self.get_object()
        has_edit_feature = user_has_feature(request.user, "edit_optimized_text")
        has_tts_feature = user_has_feature(request.user, "tts_generation")
        
        if not has_tts_feature:
            messages.error(request, "You have exhausted your 20 free tries! Please upgrade your plan to use the recording feature.")
            return HttpResponseForbidden("Feature locked")

        consumed = consume_free_try(request.user, "tts_generation")
        if consumed and request.user.free_tries_used >= 20:
            messages.warning(request, "You have exhausted your 20 free tries! Please upgrade your plan to continue using premium features.")

        chunk.is_recording = True
        chunk.save(update_fields=["is_recording"])

        generate_chunk_audio_task.delay(chunk.id)

        return render(
            request,
            "documents/partials/chunk_optimized_display.html",
            {"chunk": chunk, "has_edit_feature": has_edit_feature, "has_tts_feature": has_tts_feature},
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


class ManualDocumentCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        title = request.POST.get("title", "Untitled Document").strip() or "Untitled Document"
        domain_type = request.POST.get("domain_type", Document.DomainType.AUTO_DETECT)
        
        document = Document.objects.create(
            user=request.user,
            title=title,
            domain_type=domain_type,
            optimization_mode=OptimizationMode.MANUAL,
            status=Document.Status.COMPLETED
        )
        return HttpResponseRedirect(reverse_lazy('documents:document-detail', kwargs={'pk': document.pk}))


@method_decorator(ratelimit(key="user", rate="30/m", block=True), name="dispatch")
class ChunkCreateHTMXView(LoginRequiredMixin, View):
    def post(self, request, document_pk):
        document = get_object_or_404(Document, pk=document_pk, user=request.user)
        raw_text = request.POST.get("raw_text", "").strip()
        if raw_text:
            last_chunk = document.chunks.order_by("-chunk_index").first()
            new_index = (last_chunk.chunk_index + 1) if last_chunk else 1
            
            # Simple duration estimation (150 WPM)
            words = raw_text.split()
            est_seconds = max(5, int((len(words) / 150) * 60))
            
            DocumentChunk.objects.create(
                document=document,
                chunk_index=new_index,
                title=f"Section {new_index}",
                raw_text=raw_text,
                optimized_text=raw_text, # Will be replaced during processing
                estimated_duration_seconds=est_seconds,
                is_user_created=True
            )
            
            # If the document was already COMPLETED, change it back to PENDING so they can process the new chunk
            if document.status == Document.Status.COMPLETED:
                document.status = Document.Status.PENDING
                document.save(update_fields=["status"])
                
        # Return the chunks list partial so it updates immediately
        chunks_list = document.chunks.ordered()
        paginator = Paginator(chunks_list, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        has_edit_feature = user_has_feature(request.user, "edit_optimized_text")
        has_llm_feature = user_has_feature(request.user, "llm_optimization")
        manual_mode_forced = not has_llm_feature
        
        return render(
            request,
            "documents/partials/chunk_list.html",
            {
                "document": document,
                "chunks": page_obj,
                "is_paginated": page_obj.has_other_pages(),
                "page_obj": page_obj,
                "has_edit_feature": has_edit_feature,
                "manual_mode_forced": manual_mode_forced,
            },
        )


@method_decorator(ratelimit(key="user", rate="30/m", block=True), name="dispatch")
class ChunkDeleteHTMXView(LoginRequiredMixin, View):
    def post(self, request, pk):
        from django.http import HttpResponseForbidden
        chunk = get_object_or_404(DocumentChunk, pk=pk, document__user=request.user)
        
        if not chunk.is_user_created:
            return HttpResponseForbidden("Cannot delete system-generated chunks.")
            
        deleted_index = chunk.chunk_index
        document = chunk.document
        chunk.delete()
        
        # Re-index remaining chunks efficiently in a single query
        from django.db.models import F
        document.chunks.filter(chunk_index__gt=deleted_index).update(
            chunk_index=F('chunk_index') - 1
        )
                
        # Return empty response to let HTMX remove the element, or re-render chunk_list.
        return HttpResponse("")
