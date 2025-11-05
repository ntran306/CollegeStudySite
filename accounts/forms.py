from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import StudentProfile, TutorProfile

class StudentSignUpForm(UserCreationForm):
    major = forms.CharField(max_length=100, required=False)
    year = forms.CharField(max_length=20, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            StudentProfile.objects.create(
                user=user,
                major=self.cleaned_data.get('major', ''),
                year=self.cleaned_data.get('year', '')
            )
        return user


class TutorSignUpForm(UserCreationForm):
    subjects = forms.CharField(widget=forms.Textarea, required=False)
    rate = forms.DecimalField(max_digits=6, decimal_places=2, required=False)
    bio = forms.CharField(widget=forms.Textarea, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            TutorProfile.objects.create(
                user=user,
                subjects=self.cleaned_data.get('subjects', ''),
                rate=self.cleaned_data.get('rate'),
                bio=self.cleaned_data.get('bio', '')
            )
        return user
