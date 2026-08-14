from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import DeleteView
from django.http import HttpResponse

from core.applications.documents.forms import DocumentForm
from core.applications.documents.models import Document
from core.applications.documents.services import PipelineService


from django.contrib.auth.mixins import LoginRequiredMixin

class DocumentFilterMixin:
    def get_filtered_queryset(self, base_queryset):
        queryset = base_queryset
        
        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status')
        domain_type = self.request.GET.get('domain_type')
        sort = self.request.GET.get('sort')

        if q:
            queryset = queryset.filter(title__icontains=q)
        if status:
            queryset = queryset.filter(status=status)
        if domain_type:
            queryset = queryset.filter(domain_type=domain_type)
            
        if sort == 'oldest':
            queryset = queryset.order_by("created_at")
        elif sort == 'title_asc':
            queryset = queryset.order_by("title")
        elif sort == 'title_desc':
            queryset = queryset.order_by("-title")
        elif sort == 'status':
            queryset = queryset.order_by("status", "-created_at")
        else:
            queryset = queryset.order_by("-created_at") # default newest
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from core.applications.documents.models import Document
        context['status_choices'] = Document.Status.choices
        context['domain_choices'] = Document.DomainType.choices
        context['current_q'] = self.request.GET.get('q', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_domain_type'] = self.request.GET.get('domain_type', '')
        context['current_sort'] = self.request.GET.get('sort', '')
        return context


class DocumentListView(LoginRequiredMixin, DocumentFilterMixin, ListView):
    model = Document
    template_name = "documents/document_list.html"
    context_object_name = "documents"

    def get_queryset(self):
        qs = Document.objects.filter(user=self.request.user)
        qs = self.get_filtered_queryset(qs)
        # If user is actively searching/filtering, maybe show all?
        # The prompt says "implement search, filter and sorting on dashboard".
        # If they apply a filter, let's not limit to 6, otherwise they can't find what they searched for.
        has_filters = any(self.request.GET.get(k) for k in ['q', 'status', 'domain_type', 'sort'])
        if not has_filters:
            return qs[:6]
        return qs


class DocumentTableView(LoginRequiredMixin, DocumentFilterMixin, ListView):
    model = Document
    template_name = "documents/document_table.html"
    context_object_name = "documents"

    def get_queryset(self):
        qs = Document.objects.filter(user=self.request.user)
        return self.get_filtered_queryset(qs)


from django.http import HttpResponseRedirect

class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = Document
    success_url = reverse_lazy("documents:document-table")

    def get_queryset(self):
        # Ensure a user can only delete their own documents
        return super().get_queryset().filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.headers.get('HX-Request') or request.META.get('HTTP_HX_REQUEST'):
            return HttpResponse("")
        return HttpResponseRedirect(self.get_success_url())


class DocumentCreateView(CreateView):
    model = Document
    form_class = DocumentForm
    template_name = "documents/document_form.html"
    success_url = reverse_lazy("documents:document-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_success_url(self):
        if not self.request.user.is_authenticated:
            from django.urls import reverse
            return reverse("account_login") + f"?next={reverse('documents:document-detail', kwargs={'pk': self.object.pk})}"
        return super().get_success_url()

    def form_valid(self, form):
        if self.request.user.is_authenticated:
            form.instance.user = self.request.user
        else:
            from core.helpers.enums import OptimizationMode
            form.instance.optimization_mode = OptimizationMode.MANUAL
            
        response = super().form_valid(form)
        # Only process immediately if the user is authenticated
        if self.request.user.is_authenticated:
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
    
    # Process only if pending and user is authenticated (or just if pending, since unauthenticated shouldn't be here)
    if document.status == Document.Status.PENDING and request.user.is_authenticated:
        PipelineService.process_document(document)
        
    chunks = document.chunks.all().order_by("chunk_index")
    return render(request, "documents/partials/chunk_list.html", {"document": document, "chunks": chunks})
