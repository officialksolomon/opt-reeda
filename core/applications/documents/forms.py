from django import forms

from core.applications.documents.models import Document


from django.core.exceptions import ValidationError

class DocumentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Document
        fields = ["title", "file", "domain_type", "code_mode"]

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file:
            # If user is anonymous, restrict file size to 2MB
            if not self.request or not self.request.user.is_authenticated:
                if file.size > 2 * 1024 * 1024:
                    raise ValidationError("Oops, this file is a bit too big! Guests can upload up to 2MB. Please log in to process larger documents.")
        return file
