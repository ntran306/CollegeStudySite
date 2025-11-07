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
                year=self.cleaned_data.get('year', ''),
            )
        return user


class TutorSignUpForm(UserCreationForm):
    subjects = forms.MultipleChoiceField(
        choices=TutorProfile.SUBJECT_CHOICES,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 6}),
        required=False,
        help_text="Hold CTRL (Windows) or CMD (Mac) to select multiple subjects."
    )
    rate = forms.DecimalField(
        max_digits=6,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter hourly rate',
            'min': '0',
            'step': '1',
        }),
        label="Hourly Rate ($)",
    )
    bio = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )
    location = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your city or campus'}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            subjects_list = self.cleaned_data.get('subjects', [])
            subjects_str = ', '.join(subjects_list)
            TutorProfile.objects.create(
                user=user,
                subjects=subjects_str,
                rate=self.cleaned_data.get('rate'),
                bio=self.cleaned_data.get('bio', ''),
                location=self.cleaned_data.get('location', ''),
            )
        return user


class TutorProfileForm(forms.ModelForm):
    subjects = forms.MultipleChoiceField(
        choices=TutorProfile.SUBJECT_CHOICES,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 6}),
        required=False,
        help_text="Hold CTRL (Windows) or CMD (Mac) to select multiple subjects."
    )

    class Meta:
        model = TutorProfile
        fields = [
            'subjects', 'rate', 'bio', 'school',
            'location', 'latitude', 'longitude',
            'avatar',
        ]
        widgets = {
            'rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter hourly rate',
                'min': '0',
                'step': '1',
            }),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'school': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your school (optional)'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Favorite study spot (optional)'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.subjects:
            self.initial['subjects'] = [s.strip() for s in self.instance.subjects.split(',')]

    def save(self, commit=True):
        tutor_profile = super().save(commit=False)
        subjects_list = self.cleaned_data.get('subjects', [])
        tutor_profile.subjects = ', '.join(subjects_list)
        if commit:
            tutor_profile.save()
        return tutor_profile


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = [
            'major', 'year', 'school',
            'location', 'latitude', 'longitude',
            'avatar',
        ]
        widgets = {
            'major': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your major'}),
            'year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Year (e.g. Freshman, Sophomore)'}),
            'school': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your school (optional)'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Favorite study spot (optional)'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }