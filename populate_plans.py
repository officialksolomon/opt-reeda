import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from core.applications.pricing.models import Plan, Price, Feature, PlanFeature, Subscription

Subscription.objects.all().delete()
PlanFeature.objects.all().delete()
Feature.objects.all().delete()
Price.objects.all().delete()
Plan.objects.all().delete()

# 1. Create Features
f_formatting = Feature.objects.create(name="Manual Formatting & Cleanup", key="manual_formatting", value_type="boolean")
f_abbreviation = Feature.objects.create(name="Basic abbreviation expansion", key="basic_abbreviation", value_type="boolean")
f_playback = Feature.objects.create(name="Audio playback in browser", key="audio_playback", value_type="boolean")
f_doc_limit = Feature.objects.create(name="Public documents limit", key="public_documents_limit", value_type="string")
f_voices = Feature.objects.create(name="Voice types", key="voice_types", value_type="string")

f_rewriting = Feature.objects.create(name="AI-Powered Contextual Rewriting", key="ai_rewriting", value_type="boolean")
f_math = Feature.objects.create(name="Intelligent Math & Equation Parsing", key="math_parsing", value_type="boolean")
f_code = Feature.objects.create(name="Smart Code Block Summarization", key="code_summarization", value_type="boolean")
f_analytics = Feature.objects.create(name="Analytics", key="analytics", value_type="boolean")
f_api = Feature.objects.create(name="API access", key="api_access", value_type="boolean")
f_domain = Feature.objects.create(name="Custom domain", key="custom_domain", value_type="boolean")
f_edit_text = Feature.objects.create(name="Edit Optimized Text", key="edit_optimized_text", value_type="boolean")
f_total_docs = Feature.objects.create(name="Documents limit", key="documents_limit", value_type="integer")


# 2. Create Plans
free_plan = Plan.objects.create(
    name="Basic Listen",
    slug="basic-listen",
    description="Perfect for casual listeners who need straightforward text extraction and cleanup."
)

pro_plan = Plan.objects.create(
    name="Pro Intelligent",
    slug="pro-intelligent",
    description="For students and researchers who need flawless audio extraction from complex documents."
)

business_plan = Plan.objects.create(
    name="Business",
    slug="business",
    description="For power users needing API access, custom domains, and deeper analytics."
)

enterprise_plan = Plan.objects.create(
    name="Enterprise",
    slug="enterprise",
    description="For large organizations needing maximum throughput and scale."
)


# 3. Create PlanFeatures
# Basic Listen Features
PlanFeature.objects.create(plan=free_plan, feature=f_formatting, value=True)
PlanFeature.objects.create(plan=free_plan, feature=f_abbreviation, value=True)
PlanFeature.objects.create(plan=free_plan, feature=f_playback, value=True)
PlanFeature.objects.create(plan=free_plan, feature=f_doc_limit, value="Unlimited")
PlanFeature.objects.create(plan=free_plan, feature=f_voices, value="Standard")

# Helper to assign all premium features
def assign_premium_features(plan_obj, doc_limit):
    PlanFeature.objects.create(plan=plan_obj, feature=f_formatting, value=True)
    PlanFeature.objects.create(plan=plan_obj, feature=f_abbreviation, value=True)
    PlanFeature.objects.create(plan=plan_obj, feature=f_playback, value=True)
    PlanFeature.objects.create(plan=plan_obj, feature=f_rewriting, value=True)
    PlanFeature.objects.create(plan=plan_obj, feature=f_math, value=True)
    PlanFeature.objects.create(plan=plan_obj, feature=f_code, value=True)
    PlanFeature.objects.create(plan=plan_obj, feature=f_analytics, value=True)
    PlanFeature.objects.create(plan=plan_obj, feature=f_api, value=True)
    PlanFeature.objects.create(plan=plan_obj, feature=f_domain, value=True)
    PlanFeature.objects.create(plan=plan_obj, feature=f_edit_text, value=True)
    PlanFeature.objects.create(plan=plan_obj, feature=f_total_docs, value=doc_limit)

# Assign features with diff document limits
assign_premium_features(pro_plan, 20)
assign_premium_features(business_plan, 40)
assign_premium_features(enterprise_plan, 60)


# 4. Create Prices
Price.objects.create(
    plan=free_plan,
    amount=0.00,
    currency="NGN",
    interval="forever"
)

# Paid Plan 1 (+0)
Price.objects.create(
    plan=pro_plan,
    amount=1999.00,
    currency="NGN",
    interval="month"
)
Price.objects.create(
    plan=pro_plan,
    amount=20000.00,
    currency="NGN",
    interval="year"
)

# Paid Plan 2 (+2000)
Price.objects.create(
    plan=business_plan,
    amount=3999.00,
    currency="NGN",
    interval="month"
)
Price.objects.create(
    plan=business_plan,
    amount=40000.00,
    currency="NGN",
    interval="year"
)

# Paid Plan 3 (+4000)
Price.objects.create(
    plan=enterprise_plan,
    amount=5999.00,
    currency="NGN",
    interval="month"
)
Price.objects.create(
    plan=enterprise_plan,
    amount=60000.00,
    currency="NGN",
    interval="year"
)

print("Plans, Features, and Prices populated successfully!")
