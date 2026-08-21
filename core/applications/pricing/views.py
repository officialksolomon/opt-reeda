from django.views.generic import TemplateView

from core.applications.pricing.models import Plan


class PricingView(TemplateView):
    template_name = "pages/pricing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plans"] = (
            Plan.objects.with_full_details().ordered_by_creation()
        )
        return context
