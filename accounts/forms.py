from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import StudentProfile, TutorProfile
from classes.models import Class


class StudentSignUpForm(UserCreationForm):
    major = forms.CharField(max_length=100, required=False)
    year = forms.CharField(max_length=20, required=False)
    
    # ✅ Add classes field (hidden, will be populated by JS)
    classes = forms.CharField(required=False, widget=forms.HiddenInput())

    location = forms.CharField(
            max_length=255,
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your city or campus'
            })
        )
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())
   
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile = StudentProfile.objects.create(
                user=user,
                major=self.cleaned_data.get('major', ''),
                year=self.cleaned_data.get('year', ''),
                location=self.cleaned_data.get('location', ''),
                latitude=self.cleaned_data.get('latitude') or None,
                longitude=self.cleaned_data.get('longitude') or None,
            )
            
            # ✅ Handle classes from hidden input
            class_ids = self.cleaned_data.get('classes', '').split(',')
            valid_classes = Class.objects.filter(id__in=[c for c in class_ids if c.isdigit()])
            profile.classes.set(valid_classes)
            
        return user


class TutorSignUpForm(UserCreationForm):
    classes = forms.CharField(required=False, widget=forms.HiddenInput())
    
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
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your city or campus'
            })
        )
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile = TutorProfile.objects.create(
                user=user,
                rate=self.cleaned_data.get('rate'),
                bio=self.cleaned_data.get('bio', ''),
                location=self.cleaned_data.get('location', ''),
                latitude=self.cleaned_data.get('latitude') or None,
                longitude=self.cleaned_data.get('longitude') or None,
            )
            
            # ✅ Handle classes from hidden input
            class_ids = self.cleaned_data.get('classes', '').split(',')
            valid_classes = Class.objects.filter(id__in=[c for c in class_ids if c.isdigit()])
            profile.classes.set(valid_classes)
            
        return user


class TutorProfileForm(forms.ModelForm):
    classes = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = TutorProfile
        fields = [
            'rate', 'bio', 'school',
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

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            
            # ✅ Handle classes from hidden input
            class_ids = self.cleaned_data.get('classes', '').split(',')
            valid_classes = Class.objects.filter(id__in=[c for c in class_ids if c.isdigit()])
            profile.classes.set(valid_classes)
            
        return profile


class StudentProfileForm(forms.ModelForm):
    # ✅ Add classes field
    classes = forms.CharField(required=False, widget=forms.HiddenInput())
    
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
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            
            # ✅ Handle classes from hidden input
            class_ids = self.cleaned_data.get('classes', '').split(',')
            valid_classes = Class.objects.filter(id__in=[c for c in class_ids if c.isdigit()])
            profile.classes.set(valid_classes)
            
        return profile