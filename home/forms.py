from django import forms
from .models import DomicileApplication

class DomicileApplicationForm(forms.ModelForm):
    class Meta:
        model = DomicileApplication
        fields = '__all__'