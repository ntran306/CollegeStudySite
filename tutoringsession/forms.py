from django import forms
from .models import TutoringSession

class TutoringSessionForm(forms.ModelForm):
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
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }
