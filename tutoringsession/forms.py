from django import forms
from .models import TutoringSession
from classes.models import Class

class TutoringSessionForm(forms.ModelForm):
    subject = forms.CharField(
        required=True,
        widget=forms.HiddenInput(),
        help_text="Select the class for this tutoring session"
    )
    
    class Meta:
        model = TutoringSession
        fields = [
            "subject",
            "description",
            "date",
            "start_time",
            "end_time",
            "location",
            "is_remote",
            "capacity",
        ]

        widgets = {
            "description": forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "start_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "end_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter location or leave blank if remote"}),
            "is_remote": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "capacity": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        }